"""
Script d'import des vrais clients depuis le PDF de la liste FABS-CI.

USAGE :
    python -m import_real_clients          # Mode dry-run (affiche stats)
    python -m import_real_clients --apply  # Insère réellement en base
    python -m import_real_clients --apply --purge  # Purge d'abord les dummies puis insère

Fonctionnement :
- Lit le fichier `/app/backend/data/clients_real.txt` (format CSV-like par localité)
- Map TYPE_CLIENT du PDF (LYCEES, COLLEGES, LIBRAIRIES, EPP, IEP, GROUPE SCOLAIRE,
  CATHOLIQUE, METHODISTE, INSTITUT, MEMO, DREN, INSPECTEUR, PARTICULIERS, UP, MEMO)
  vers les types du système (ecole, librairie, particulier, distributeur, representant)
- Supprime les doublons exacts (même nom + même ville + même représentant)
- Référence auto FABS-CLI-XXXX continue du compteur existant
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

DATA_FILE = Path(__file__).parent / "data" / "clients_real.txt"

# Mapping du type d'établissement (PDF) → type_client (système)
TYPE_MAPPING = {
    "LYCEES": "ecole",
    "LYCEE": "ecole",
    "COLLEGES": "ecole",
    "COLLEGE": "ecole",
    "EPP": "ecole",
    "IEP": "ecole",
    "GROUPE SCOLAIRE": "ecole",
    "CATHOLIQUE": "ecole",
    "METHODISTE": "ecole",
    "INSTITUT": "ecole",
    "MEMO": "ecole",
    "DREN": "ecole",
    "INSPECTEUR": "ecole",
    "UP": "ecole",
    "LIBRAIRIES": "librairie",
    "LIBRAIRIE": "librairie",
    "PARTICULIERS": "particulier",
    "PARTICULIER": "particulier",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_phone(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", "", s.strip())
    if s and not s.startswith("+") and not s.startswith("0"):
        return s
    return s


def map_type(raw: str) -> str:
    if not raw:
        return "particulier"
    raw = raw.strip().upper()
    for key, mapped in TYPE_MAPPING.items():
        if raw.startswith(key):
            return mapped
    return "particulier"


def parse_data_file(path: Path):
    """Yield dict per client. Format attendu :
       Lignes `**LOCALITE**` annoncent un groupe.
       Lignes `nom;ville;tel;representant_alt;representant;tel_alt;type`
       (cas 6 ou 7 colonnes ; on tolère les deux)
    """
    if not path.exists():
        return
    current_ville = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^\*\*(.+?)\*\*$", line)
        if m:
            current_ville = m.group(1).strip()
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 2:
            continue
        # tolérance : 7 colonnes (avec representant_alt) ou moins
        nom = parts[0]
        ville = parts[1] if len(parts) > 1 and parts[1] else current_ville or ""
        # representant et téléphone sont aux positions variables — heuristique :
        # nom;ville;tel;email_or_alt_rep;rep;tel2;type_pdf
        telephone = parts[2] if len(parts) > 2 else ""
        representant = ""
        type_pdf = ""
        # try last-but-one as representant, last as type
        if len(parts) >= 7:
            representant = parts[4] or parts[3] or ""
            type_pdf = parts[6]
        elif len(parts) == 6:
            representant = parts[3] or ""
            type_pdf = parts[5]
        elif len(parts) == 5:
            representant = parts[2] or ""
            type_pdf = parts[4]
        else:
            representant = parts[-2] if len(parts) >= 4 else nom
            type_pdf = parts[-1] if len(parts) >= 3 else ""

        if not representant:
            representant = nom  # fallback : représentant = nom de l'entité

        yield {
            "nom": nom,
            "ville": ville,
            "telephone": parse_phone(telephone),
            "representant": representant,
            "type_client": map_type(type_pdf),
            "type_pdf": type_pdf,
        }


async def next_reference(db, counter_seq: int) -> str:
    return f"FABS-CLI-{counter_seq:04d}"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Insère réellement en base")
    parser.add_argument("--purge", action="store_true", help="Supprime tous les clients existants avant insertion")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("ERREUR : MONGO_URL ou DB_NAME absent du .env", file=sys.stderr)
        sys.exit(1)

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    rows = list(parse_data_file(DATA_FILE))
    print(f"📋  {len(rows)} lignes parsées depuis {DATA_FILE.name}")

    # Dedup local (nom+ville+representant)
    seen = set()
    unique_rows = []
    for r in rows:
        key = (r["nom"].lower(), r["ville"].lower(), r["representant"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(r)
    print(f"🧹  Après déduplication interne : {len(unique_rows)} clients uniques")

    # Stats par type
    by_type = {}
    by_ville = {}
    for r in unique_rows:
        by_type[r["type_client"]] = by_type.get(r["type_client"], 0) + 1
        by_ville[r["ville"]] = by_ville.get(r["ville"], 0) + 1
    print("\n📊  Répartition par type :")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {t:<14} {n:>4}")
    print(f"\n🏘  Localités distinctes : {len(by_ville)}")

    if not args.apply:
        print("\n⚙️  Mode dry-run (utilisez --apply pour insérer)")
        return

    if args.purge:
        # Supprime physiquement tous les clients existants + remet le compteur à 0
        deleted = await db.clients.delete_many({})
        await db.counters.update_one(
            {"_id": "clients"}, {"$set": {"seq": 0}}, upsert=True
        )
        print(f"\n🗑   Suppression : {deleted.deleted_count} clients existants purgés")

    # Récupère le compteur courant
    seq_doc = await db.counters.find_one({"_id": "clients"}) or {"seq": 0}
    next_seq = seq_doc.get("seq", 0)

    # Trouve un user owner pour created_by
    user = await db.users.find_one({"role": "super_admin"}, {"_id": 0, "user_id": 1})
    owner = user["user_id"] if user else "system_import"

    inserted = 0
    skipped = 0
    docs = []
    for r in unique_rows:
        # Skip si déjà présent (sécurité supplémentaire si --purge non utilisé)
        if not args.purge:
            existing = await db.clients.find_one({
                "nom": r["nom"],
                "ville": r["ville"],
                "representant": r["representant"],
            })
            if existing:
                skipped += 1
                continue

        next_seq += 1
        now = _now_iso()
        doc = {
            "client_id": f"cli_{uuid.uuid4().hex[:12]}",
            "reference": f"FABS-CLI-{next_seq:04d}",
            "nom": r["nom"],
            "type_client": r["type_client"],
            "representant": r["representant"],
            "telephone": r["telephone"] or None,
            "email": None,
            "adresse": None,
            "ville": r["ville"],
            "plafond_credit": 0,
            "solde": 0,
            "actif": True,
            "notes": f"Import PDF — type d'origine : {r.get('type_pdf', '-')}",
            "created_by": owner,
            "created_at": now,
            "updated_at": now,
        }
        docs.append(doc)
        inserted += 1

    if docs:
        # Bulk insert
        await db.clients.insert_many(docs)
        # Update counter
        await db.counters.update_one(
            {"_id": "clients"}, {"$set": {"seq": next_seq}}, upsert=True
        )

    print(f"\n✅  Insérés : {inserted}")
    if skipped:
        print(f"⏭   Déjà présents (skip) : {skipped}")
    print(f"📌  Compteur clients : {next_seq}")


if __name__ == "__main__":
    asyncio.run(main())
