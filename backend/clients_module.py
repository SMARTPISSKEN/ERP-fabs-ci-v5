"""
Module Clients — Sprint 4
- CRUD complet sur la collection MongoDB `clients`
- Référence auto-incrémentée FABS-CLI-XXXX (séquentielle, persistée dans `counters`)
- Détection intelligente de doublons (Levenshtein normalisé sur nom + comparaison téléphone)
- RBAC : lecture super_admin/DG/comptable/commercial/secrétariat,
         écriture super_admin/DG/commercial/secrétariat
- Soft delete (`actif=False`, jamais de DELETE physique)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
READ_ROLES = {
    "super_admin", "directeur_general", "comptable",
    "directeur_commercial", "secretariat",
}
WRITE_ROLES = {
    "super_admin", "directeur_general",
    "directeur_commercial", "secretariat",
}

ClientType = Literal["librairie", "ecole", "particulier", "distributeur", "representant"]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


# ---------------------------------------------------------------------------
# Levenshtein + normalisation (détection de doublons)
# ---------------------------------------------------------------------------
_NAME_NOISE = re.compile(
    r"\b(la|le|les|de|du|des|et|ets|ste|sarl|sa|lib|librairie|college|college|ecole|lycee|cours)\b\.?",
    flags=re.IGNORECASE,
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # strip accents
    accents = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")
    s = s.translate(accents)
    s = _NAME_NOISE.sub(" ", s)
    s = _NON_ALNUM.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_phone(s: Optional[str]) -> str:
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    return digits[-8:] if len(digits) >= 8 else digits


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            ins = curr[j] + 1
            dele = prev[j + 1] + 1
            sub = prev[j] + (0 if ca == cb else 1)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]


def name_similarity(a: str, b: str) -> float:
    """1.0 = identical, 0.0 = totally different."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    longest = max(len(na), len(nb))
    dist = levenshtein(na, nb)
    return 1.0 - (dist / longest)


# ---------------------------------------------------------------------------
# Reference generation FABS-CLI-XXXX
# ---------------------------------------------------------------------------
async def next_client_reference(db: AsyncIOMotorDatabase) -> str:
    """Atomically increments the `clients` counter and returns FABS-CLI-XXXX."""
    doc = await db.counters.find_one_and_update(
        {"_id": "clients"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"] if doc else 1
    return f"FABS-CLI-{seq:04d}"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ClientIn(BaseModel):
    nom: str = Field(..., min_length=2, max_length=120)
    type_client: ClientType
    representant: str = Field(..., min_length=2, max_length=120, description="Nom du représentant (obligatoire)")
    representative_id: Optional[str] = None  # legacy — ID du représentant (optionnel)
    telephone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[EmailStr] = None
    adresse: Optional[str] = Field(default=None, max_length=240)
    ville: Optional[str] = Field(default=None, max_length=80)
    plafond_credit: float = 0
    notes: Optional[str] = Field(default=None, max_length=600)

    @field_validator("nom")
    @classmethod
    def _strip_nom(cls, v: str) -> str:
        return v.strip()


class ClientPatch(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=2, max_length=120)
    type_client: Optional[ClientType] = None
    representant: Optional[str] = Field(default=None, min_length=2, max_length=120)
    representative_id: Optional[str] = None
    telephone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[EmailStr] = None
    adresse: Optional[str] = Field(default=None, max_length=240)
    ville: Optional[str] = Field(default=None, max_length=80)
    plafond_credit: Optional[float] = None
    notes: Optional[str] = Field(default=None, max_length=600)
    actif: Optional[bool] = None


class ClientOut(BaseModel):
    client_id: str
    reference: str
    nom: str
    type_client: ClientType
    representant: Optional[str] = None
    representative_id: Optional[str] = None
    representative_nom: Optional[str] = None  # Nom du représentant (legacy lookup)
    telephone: Optional[str] = None
    email: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    solde: float = 0
    plafond_credit: float = 0
    actif: bool = True
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str


class ClientListOut(BaseModel):
    items: List[ClientOut]
    total: int
    page: int
    page_size: int


class DuplicateMatch(BaseModel):
    client_id: str
    reference: str
    nom: str
    ville: Optional[str] = None
    telephone: Optional[str] = None
    similarity: float          # 0.0..1.0 on normalized name
    phone_match: bool          # last 8 digits identical
    reason: str                # human-readable summary (FR)


class DuplicateCheckIn(BaseModel):
    nom: str
    telephone: Optional[str] = None
    exclude_id: Optional[str] = None  # ignore this client_id when editing


class DuplicateCheckOut(BaseModel):
    matches: List[DuplicateMatch]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_client(doc: dict) -> dict:
    """Strip MongoDB _id, ensure consistent shape."""
    if not doc:
        return doc
    doc = {k: v for k, v in doc.items() if k != "_id"}
    return doc


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------
def build_clients_router(
    db: AsyncIOMotorDatabase,
    resolve_user,  # async dep: (Request, Authorization) -> dict
) -> APIRouter:
    router = APIRouter(prefix="/clients", tags=["clients"])

    # ---- helpers ---------------------------------------------------------
    async def _scan_duplicates(
        nom: str, telephone: Optional[str], exclude_id: Optional[str] = None
    ) -> List[DuplicateMatch]:
        norm_phone = normalize_phone(telephone)
        candidates: List[DuplicateMatch] = []
        # Scan all active clients (acceptable for <1k entries; replace by Atlas Search later)
        async for doc in db.clients.find({"actif": True}, {"_id": 0}):
            if exclude_id and doc["client_id"] == exclude_id:
                continue
            sim = name_similarity(nom, doc["nom"])
            ph_match = bool(
                norm_phone
                and normalize_phone(doc.get("telephone")) == norm_phone
            )
            if sim >= 0.78 or ph_match:
                if ph_match and sim >= 0.5:
                    reason = "Téléphone identique et nom similaire"
                elif ph_match:
                    reason = "Téléphone identique"
                else:
                    reason = "Nom très proche"
                candidates.append(DuplicateMatch(
                    client_id=doc["client_id"],
                    reference=doc["reference"],
                    nom=doc["nom"],
                    ville=doc.get("ville"),
                    telephone=doc.get("telephone"),
                    similarity=round(sim, 3),
                    phone_match=ph_match,
                    reason=reason,
                ))
        # sort: phone match first, then by similarity desc
        candidates.sort(key=lambda m: (not m.phone_match, -m.similarity))
        return candidates[:5]

    # ---- LIST ------------------------------------------------------------
    @router.get("", response_model=ClientListOut)
    async def list_clients(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        q: Optional[str] = Query(default=None, description="Recherche nom / téléphone / référence"),
        type_client: Optional[ClientType] = None,
        ville: Optional[str] = None,
        actif: Optional[bool] = Query(default=None),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Module Clients non accessible à votre rôle")

        filt: dict = {}
        if type_client:
            filt["type_client"] = type_client
        if ville:
            filt["ville"] = {"$regex": f"^{re.escape(ville)}", "$options": "i"}
        if actif is not None:
            filt["actif"] = actif
        if q:
            esc = re.escape(q)
            filt["$or"] = [
                {"nom": {"$regex": esc, "$options": "i"}},
                {"telephone": {"$regex": esc, "$options": "i"}},
                {"reference": {"$regex": esc, "$options": "i"}},
            ]

        total = await db.clients.count_documents(filt)
        cursor = (
            db.clients.find(filt, {"_id": 0})
            .sort([("created_at", -1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = [ClientOut(**d) async for d in cursor]
        return ClientListOut(items=items, total=total, page=page, page_size=page_size)

    # ---- DUPLICATES ------------------------------------------------------
    @router.post("/check-duplicates", response_model=DuplicateCheckOut)
    async def check_duplicates(
        payload: DuplicateCheckIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Action non autorisée")
        matches = await _scan_duplicates(payload.nom, payload.telephone, payload.exclude_id)
        return DuplicateCheckOut(matches=matches)

    # ---- GET -------------------------------------------------------------
    @router.get("/{client_id}", response_model=ClientOut)
    async def get_client(
        client_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        doc = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
        _ensure(doc is not None, 404, "Client introuvable")
        return ClientOut(**doc)

    # ---- CREATE ----------------------------------------------------------
    @router.post("", response_model=ClientOut, status_code=201)
    async def create_client(
        payload: ClientIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
        force: bool = Query(default=False, description="Ignorer l'alerte doublons"),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Création non autorisée pour votre rôle")

        if not force:
            dups = await _scan_duplicates(payload.nom, payload.telephone)
            if dups:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DUPLICATE_SUSPECTED",
                        "message": "Doublon possible détecté. Confirmez avec ?force=true pour passer outre.",
                        "matches": [m.model_dump() for m in dups],
                    },
                )

        doc = {
            "client_id": f"cli_{uuid.uuid4().hex[:12]}",
            "reference": await next_client_reference(db),
            **payload.model_dump(),
            "solde": 0,
            "actif": True,
            "created_by": me["user_id"],
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await db.clients.insert_one(doc)
        return ClientOut(**_project_client(doc))

    # ---- UPDATE ----------------------------------------------------------
    @router.patch("/{client_id}", response_model=ClientOut)
    async def update_client(
        client_id: str,
        payload: ClientPatch,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Modification non autorisée")

        updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="Aucune modification fournie")
        updates["updated_at"] = _now_iso()

        result = await db.clients.find_one_and_update(
            {"client_id": client_id},
            {"$set": updates},
            return_document=True,
        )
        _ensure(result is not None, 404, "Client introuvable")
        return ClientOut(**_project_client(result))

    # ---- SOFT DELETE -----------------------------------------------------
    @router.delete("/{client_id}", response_model=ClientOut)
    async def disable_client(
        client_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Désactivation non autorisée")
        result = await db.clients.find_one_and_update(
            {"client_id": client_id},
            {"$set": {"actif": False, "updated_at": _now_iso()}},
            return_document=True,
        )
        _ensure(result is not None, 404, "Client introuvable")
        return ClientOut(**_project_client(result))

    return router


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
SEED_CLIENTS = [
    {"nom": "Librairie de France",        "type_client": "librairie",     "representant": "M. Konaté", "telephone": "+225 27 22 44 30 30", "email": "contact@librairiedefrance.ci",  "adresse": "Bd Latrille",        "ville": "Abidjan",  "plafond_credit": 2_500_000, "notes": "Client historique, paiement à 30 jours"},
    {"nom": "Librairie Carrefour Cocody", "type_client": "librairie",     "representant": "M. Diallo", "telephone": "+225 27 22 44 50 10", "email": "carrefour.cocody@example.ci",   "adresse": "Carrefour Cocody",   "ville": "Abidjan",  "plafond_credit": 1_500_000},
]


async def seed_clients(db: AsyncIOMotorDatabase, owner_user_id: str) -> int:
    """Seed initial clients if collection is empty. Returns number inserted."""
    existing = await db.clients.count_documents({})
    if existing:
        return 0
    inserted = 0
    for c in SEED_CLIENTS:
        ref = await next_client_reference(db)
        await db.clients.insert_one({
            "client_id": f"cli_{uuid.uuid4().hex[:12]}",
            "reference": ref,
            **c,
            "solde": 0,
            "actif": True,
            "created_by": owner_user_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        })
        inserted += 1
    return inserted
