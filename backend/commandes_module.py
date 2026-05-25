"""
Module Commandes — Sprint 6
- CRUD complet sur les collections MongoDB `commandes` et `commande_lignes`
- Référence auto-incrémentée FABS-CMD-26-27-XXXX
- Workflow : brouillon → en_attente → validee → preparee → livree → annulee
- Validation DG obligatoire si montant_total > 500 000 FCFA
- Actions : valider, préparer, livrer, annuler
- RBAC : 
    READ = {super_admin, DG, commercial, secrétariat, comptable}
    WRITE = {super_admin, DG, commercial, secrétariat}
    VALIDATE = DG (si > 500k), commercial (si <= 500k)
    PREPARE = magasinier
    DELIVER = logistique
- Génération PDF Bon de Commande
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Literal, Optional, List
from decimal import Decimal
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("fabsci.commandes")

# RBAC
READ_ROLES = {
    "super_admin", "directeur_general", "directeur_commercial",
    "secretariat", "comptable",
}
WRITE_ROLES = {
    "super_admin", "directeur_general",
    "directeur_commercial", "secretariat",
}
VALIDATE_ROLES = {"super_admin", "directeur_general", "directeur_commercial"}
PREPARE_ROLES = {"super_admin", "directeur_general", "responsable_magasinier"}
DELIVER_ROLES = {"super_admin", "directeur_general", "service_logistique"}

Statut = Literal["brouillon", "en_attente", "validee", "preparee", "livree", "annulee"]
STATUT_FLOW = ["brouillon", "en_attente", "validee", "preparee", "livree"]

VALIDATION_THRESHOLD = 500_000  # FCFA


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_commande_reference(db: AsyncIOMotorDatabase) -> str:
    """Generate FABS-CMD-26-27-XXXX reference"""
    doc = await db.counters.find_one_and_update(
        {"_id": "commandes"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"]
    return f"FABS-CMD-26-27-{seq:04d}"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class LigneCommandeIn(BaseModel):
    produit_id: str
    quantite: int = Field(..., gt=0)
    prix_unitaire: float = Field(..., gt=0)
    remise_ligne: float = Field(default=0, ge=0, le=100)  # percentage

    @property
    def montant_ligne(self) -> float:
        base = self.quantite * self.prix_unitaire
        return base * (1 - self.remise_ligne / 100)


class LigneCommandeOut(BaseModel):
    ligne_id: str
    commande_id: str
    produit_id: str
    produit_reference: Optional[str] = None
    produit_titre: Optional[str] = None
    quantite: int
    prix_unitaire: float
    remise_ligne: float
    montant_ligne: float


class CommandeIn(BaseModel):
    client_id: str
    date_livraison_prevue: Optional[str] = None  # ISO date YYYY-MM-DD
    remise_globale: float = Field(default=0, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=1000)
    lignes: List[LigneCommandeIn] = Field(..., min_length=1)

    @field_validator("date_livraison_prevue", mode="before")
    @classmethod
    def _validate_date(cls, v):
        if v:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError("Format de date invalide (YYYY-MM-DD attendu)")
        return v


class CommandePatch(BaseModel):
    client_id: Optional[str] = None
    date_livraison_prevue: Optional[str] = None
    remise_globale: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=1000)
    lignes: Optional[List[LigneCommandeIn]] = None


class CommandeOut(BaseModel):
    commande_id: str
    reference: str
    client_id: str
    client_nom: Optional[str] = None
    statut: Statut
    date_commande: str
    date_livraison_prevue: Optional[str] = None
    date_validation: Optional[str] = None
    date_preparation: Optional[str] = None
    date_livraison: Optional[str] = None
    remise_globale: float
    montant_ht: float
    montant_remise: float
    montant_total: float
    notes: Optional[str] = None
    motif_annulation: Optional[str] = None
    created_by: str
    validated_by: Optional[str] = None
    prepared_by: Optional[str] = None
    delivered_by: Optional[str] = None
    created_at: str
    updated_at: str


class CommandeDetail(CommandeOut):
    lignes: List[LigneCommandeOut]


class AnnulerCommandeIn(BaseModel):
    motif: str = Field(..., min_length=10, max_length=500)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
async def _get_client_nom(db: AsyncIOMotorDatabase, client_id: str) -> Optional[str]:
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0, "nom": 1})
    return client["nom"] if client else None


async def _get_produit_info(db: AsyncIOMotorDatabase, produit_id: str) -> dict:
    produit = await db.produits.find_one(
        {"product_id": produit_id},
        {"_id": 0, "reference": 1, "titre": 1, "prix_vente": 1}
    )
    return produit or {}


async def _calculate_totals(lignes: List[LigneCommandeIn], remise_globale: float) -> dict:
    """Calculate montant_ht, montant_remise, montant_total"""
    montant_ht = sum(l.montant_ligne for l in lignes)
    montant_remise = montant_ht * (remise_globale / 100)
    montant_total = montant_ht - montant_remise
    return {
        "montant_ht": round(montant_ht, 2),
        "montant_remise": round(montant_remise, 2),
        "montant_total": round(montant_total, 2),
    }


async def _enrich_commande_with_client(db: AsyncIOMotorDatabase, cmd: dict) -> dict:
    """Add client_nom to commande dict"""
    if cmd.get("client_id"):
        cmd["client_nom"] = await _get_client_nom(db, cmd["client_id"])
    return cmd


async def _get_commande_with_lignes(db: AsyncIOMotorDatabase, commande_id: str) -> Optional[dict]:
    """Fetch commande + lignes"""
    cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
    if not cmd:
        return None
    
    # Fetch lignes
    lignes_cursor = db.commande_lignes.find({"commande_id": commande_id}, {"_id": 0})
    lignes = await lignes_cursor.to_list(500)
    
    # Enrich lignes with product info
    for ligne in lignes:
        prod_info = await _get_produit_info(db, ligne["produit_id"])
        ligne["produit_reference"] = prod_info.get("reference")
        ligne["produit_titre"] = prod_info.get("titre")
    
    cmd["lignes"] = lignes
    await _enrich_commande_with_client(db, cmd)
    return cmd


# ---------------------------------------------------------------------------
# Router Builder
# ---------------------------------------------------------------------------
def build_commandes_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/commandes", tags=["commandes"])

    # ---------- LIST ----------
    @router.get("", response_model=List[CommandeOut])
    async def list_commandes(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        statut: Optional[Statut] = None,
        client_id: Optional[str] = None,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
        q: Optional[str] = None,
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if statut:
            filters["statut"] = statut
        if client_id:
            filters["client_id"] = client_id
        if date_debut or date_fin:
            date_filter = {}
            if date_debut:
                date_filter["$gte"] = date_debut
            if date_fin:
                date_filter["$lte"] = date_fin
            filters["date_commande"] = date_filter
        
        # Search by reference
        if q:
            filters["reference"] = {"$regex": q, "$options": "i"}

        cursor = db.commandes.find(filters, {"_id": 0}).sort("date_commande", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(limit)
        
        # Enrich with client names
        for doc in docs:
            await _enrich_commande_with_client(db, doc)
        
        return [CommandeOut(**d) for d in docs]

    # ---------- CREATE ----------
    @router.post("", response_model=CommandeOut, status_code=201)
    async def create_commande(
        payload: CommandeIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
        submit: bool = Query(False, description="True to submit (en_attente), False for draft"),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Verify client exists
        client = await db.clients.find_one({"client_id": payload.client_id, "actif": True}, {"_id": 0})
        _ensure(client is not None, 404, "Client introuvable ou inactif")

        # Verify all products exist and are active
        for ligne in payload.lignes:
            prod = await db.produits.find_one({"product_id": ligne.produit_id, "actif": True}, {"_id": 0})
            _ensure(prod is not None, 404, f"Produit {ligne.produit_id} introuvable ou inactif")

        # Calculate totals
        totals = await _calculate_totals(payload.lignes, payload.remise_globale)

        # Create commande
        commande_id = f"cmd_{uuid.uuid4().hex[:12]}"
        reference = await next_commande_reference(db)
        statut = "en_attente" if submit else "brouillon"

        now = _now_iso()
        commande_doc = {
            "commande_id": commande_id,
            "reference": reference,
            "client_id": payload.client_id,
            "statut": statut,
            "date_commande": now[:10],  # YYYY-MM-DD
            "date_livraison_prevue": payload.date_livraison_prevue,
            "date_validation": None,
            "date_preparation": None,
            "date_livraison": None,
            "remise_globale": payload.remise_globale,
            "montant_ht": totals["montant_ht"],
            "montant_remise": totals["montant_remise"],
            "montant_total": totals["montant_total"],
            "notes": payload.notes,
            "motif_annulation": None,
            "created_by": me["user_id"],
            "validated_by": None,
            "prepared_by": None,
            "delivered_by": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.commandes.insert_one(commande_doc)

        # Create lignes
        for ligne in payload.lignes:
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "commande_id": commande_id,
                "produit_id": ligne.produit_id,
                "quantite": ligne.quantite,
                "prix_unitaire": ligne.prix_unitaire,
                "remise_ligne": ligne.remise_ligne,
                "montant_ligne": ligne.montant_ligne,
            }
            await db.commande_lignes.insert_one(ligne_doc)

        # Return with client_nom
        commande_doc["client_nom"] = client["nom"]
        return CommandeOut(**commande_doc)

    # ---------- GET DETAIL ----------
    @router.get("/{commande_id}", response_model=CommandeDetail)
    async def get_commande(
        commande_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        cmd = await _get_commande_with_lignes(db, commande_id)
        _ensure(cmd is not None, 404, "Commande introuvable")
        
        return CommandeDetail(**cmd)

    # ---------- UPDATE ----------
    @router.patch("/{commande_id}", response_model=CommandeOut)
    async def update_commande(
        commande_id: str,
        payload: CommandePatch,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] == "brouillon", 400, "Seules les commandes brouillon peuvent être modifiées")

        updates = {"updated_at": _now_iso()}
        
        if payload.client_id is not None:
            client = await db.clients.find_one({"client_id": payload.client_id, "actif": True}, {"_id": 0})
            _ensure(client is not None, 404, "Client introuvable")
            updates["client_id"] = payload.client_id
        
        if payload.date_livraison_prevue is not None:
            updates["date_livraison_prevue"] = payload.date_livraison_prevue
        
        if payload.remise_globale is not None:
            updates["remise_globale"] = payload.remise_globale
        
        if payload.notes is not None:
            updates["notes"] = payload.notes
        
        # Update lignes if provided
        if payload.lignes is not None:
            _ensure(len(payload.lignes) > 0, 400, "Au moins une ligne requise")
            # Verify products
            for ligne in payload.lignes:
                prod = await db.produits.find_one({"product_id": ligne.produit_id, "actif": True}, {"_id": 0})
                _ensure(prod is not None, 404, f"Produit {ligne.produit_id} introuvable")
            
            # Delete old lignes
            await db.commande_lignes.delete_many({"commande_id": commande_id})
            
            # Create new lignes
            for ligne in payload.lignes:
                ligne_doc = {
                    "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                    "commande_id": commande_id,
                    "produit_id": ligne.produit_id,
                    "quantite": ligne.quantite,
                    "prix_unitaire": ligne.prix_unitaire,
                    "remise_ligne": ligne.remise_ligne,
                    "montant_ligne": ligne.montant_ligne,
                }
                await db.commande_lignes.insert_one(ligne_doc)
            
            # Recalculate totals
            totals = await _calculate_totals(payload.lignes, payload.remise_globale or cmd["remise_globale"])
            updates.update(totals)

        await db.commandes.update_one({"commande_id": commande_id}, {"$set": updates})
        
        updated = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        await _enrich_commande_with_client(db, updated)
        return CommandeOut(**updated)

    # ---------- VALIDER ----------
    @router.post("/{commande_id}/valider", response_model=CommandeOut)
    async def valider_commande(
        commande_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        
        cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] == "en_attente", 400, f"Commande déjà {cmd['statut']}")

        # Check validation threshold
        needs_dg = cmd["montant_total"] > VALIDATION_THRESHOLD
        if needs_dg:
            _ensure(me["role"] in {"super_admin", "directeur_general"}, 403, 
                   "Validation DG requise pour montant > 500 000 FCFA")
        else:
            _ensure(me["role"] in VALIDATE_ROLES, 403, "Accès refusé")

        now = _now_iso()
        await db.commandes.update_one(
            {"commande_id": commande_id},
            {"$set": {
                "statut": "validee",
                "date_validation": now[:10],
                "validated_by": me["user_id"],
                "updated_at": now,
            }}
        )
        
        # 🆕 GÉNÉRATION AUTOMATIQUE DE LA FACTURE
        logger.info(f"Génération automatique de facture pour commande {commande_id}")
        
        try:
            # Récupérer les lignes
            lignes = await db.commande_lignes.find({"commande_id": commande_id}, {"_id": 0}).to_list(100)
            
            # Créer la facture
            from uuid import uuid4
            facture_id = f"facture_{uuid4().hex[:12]}"
            
            # Générer référence
            year = datetime.now().year % 100
            month = datetime.now().month
            count = await db.factures.count_documents({"reference": {"$regex": f"^FABS-FACT-{year:02d}-{month:02d}-"}})
            facture_ref = f"FABS-FACT-{year:02d}-{month:02d}-{count + 1:04d}"
            
            # Préparer lignes facture
            facture_lignes = []
            for ligne in lignes:
                facture_ligne = {
                    "ligne_id": f"fac_ligne_{uuid4().hex[:12]}",
                    "facture_id": facture_id,
                    "produit_id": ligne["produit_id"],
                    "designation": ligne["designation"],
                    "quantite": ligne["quantite"],
                    "prix_unitaire": ligne["prix_unitaire"],
                    "remise_ligne": ligne.get("remise_ligne", 0),
                    "montant_ht": ligne["montant_ht"],
                }
                facture_lignes.append(facture_ligne)
            
            # Calculer montants
            tva_rate = 0.18
            montant_ht = cmd["montant_total"]
            montant_tva = montant_ht * tva_rate
            montant_ttc = montant_ht + montant_tva
            
            facture_doc = {
                "facture_id": facture_id,
                "reference": facture_ref,
                "commande_id": commande_id,
                "client_id": cmd["client_id"],
                "type_facture": "facture",
                "statut": "emise",
                "date_facture": now[:10],
                "date_echeance": now[:10],
                "montant_ht": montant_ht,
                "remise_globale": cmd.get("remise_globale", 0),
                "tva_taux": tva_rate,
                "montant_tva": montant_tva,
                "montant_ttc": montant_ttc,
                "montant_paye": 0,
                "montant_restant": montant_ttc,
                "notes": f"Facture auto depuis commande {cmd['reference']}",
                "avoir_pour_facture_id": None,
                "created_by": me["user_id"],
                "created_at": now,
                "updated_at": now,
            }
            
            await db.factures.insert_one(facture_doc)
            if facture_lignes:
                await db.facture_lignes.insert_many(facture_lignes)
            
            logger.info(f"✅ Facture {facture_ref} créée pour commande {cmd['reference']}")
            
        except Exception as e:
            logger.error(f"❌ Erreur génération facture: {e}")
        
        updated = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        await _enrich_commande_with_client(db, updated)
        return CommandeOut(**updated)

    # ---------- PREPARER ----------
    @router.post("/{commande_id}/preparer", response_model=CommandeOut)
    async def preparer_commande(
        commande_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in PREPARE_ROLES, 403, "Accès refusé")

        cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] == "validee", 400, f"Commande doit être validée (actuellement {cmd['statut']})")

        now = _now_iso()
        await db.commandes.update_one(
            {"commande_id": commande_id},
            {"$set": {
                "statut": "preparee",
                "date_preparation": now[:10],
                "prepared_by": me["user_id"],
                "updated_at": now,
            }}
        )
        
        updated = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        await _enrich_commande_with_client(db, updated)
        return CommandeOut(**updated)

    # ---------- LIVRER ----------
    @router.post("/{commande_id}/livrer", response_model=CommandeOut)
    async def livrer_commande(
        commande_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in DELIVER_ROLES, 403, "Accès refusé")

        cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] == "preparee", 400, f"Commande doit être préparée (actuellement {cmd['statut']})")

        now = _now_iso()
        await db.commandes.update_one(
            {"commande_id": commande_id},
            {"$set": {
                "statut": "livree",
                "date_livraison": now[:10],
                "delivered_by": me["user_id"],
                "updated_at": now,
            }}
        )
        
        updated = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        await _enrich_commande_with_client(db, updated)
        return CommandeOut(**updated)

    # ---------- ANNULER ----------
    @router.post("/{commande_id}/annuler", response_model=CommandeOut)
    async def annuler_commande(
        commande_id: str,
        payload: AnnulerCommandeIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] not in {"livree", "annulee"}, 400, "Impossible d'annuler une commande livrée ou déjà annulée")

        now = _now_iso()
        await db.commandes.update_one(
            {"commande_id": commande_id},
            {"$set": {
                "statut": "annulee",
                "motif_annulation": payload.motif,
                "updated_at": now,
            }}
        )
        
        updated = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        await _enrich_commande_with_client(db, updated)
        return CommandeOut(**updated)

    # ---------- PDF ----------
    @router.get("/{commande_id}/pdf")
    async def commande_pdf(
        commande_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        from fastapi.responses import StreamingResponse
        from pdf_generator import generate_commande_pdf

        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")

        lignes = await db.commande_lignes.find({"commande_id": commande_id}, {"_id": 0}).to_list(500)
        # Enrich lignes with designation from products
        for l in lignes:
            prod = await db.produits.find_one({"product_id": l.get("produit_id")}, {"_id": 0, "titre": 1, "classe": 1, "isbn": 1})
            if prod:
                l["designation"] = prod.get("titre", l.get("designation", ""))
                l["classe"] = prod.get("classe", "")
                l["code_article"] = prod.get("isbn", l.get("produit_id", ""))[:14]
            l["montant_ht"] = l.get("montant_ligne", l.get("montant_ht", 0))

        client = await db.clients.find_one({"client_id": cmd["client_id"]}, {"_id": 0}) or {}
        buffer = generate_commande_pdf(cmd, lignes, client)
        filename = f"{cmd['reference']}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    return router


# ---------------------------------------------------------------------------
# Seed (optional demo data)
# ---------------------------------------------------------------------------
async def seed_commandes(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed demo commandes (optional)"""
    existing = await db.commandes.count_documents({})
    if existing > 0:
        return 0
    
    # Get first client and products
    client = await db.clients.find_one({"actif": True}, {"_id": 0})
    if not client:
        return 0
    
    products = await db.produits.find({"actif": True}, {"_id": 0}).limit(5).to_list(5)
    if len(products) < 2:
        return 0
    
    # Create 3 demo commandes
    demo_commandes = []
    for i in range(3):
        commande_id = f"cmd_{uuid.uuid4().hex[:12]}"
        reference = f"FABS-CMD-26-27-{i+1:04d}"
        
        lignes = [
            {
                "produit_id": products[0]["product_id"],
                "quantite": 10,
                "prix_unitaire": products[0]["prix_vente"],
                "remise_ligne": 0,
            },
            {
                "produit_id": products[1]["product_id"],
                "quantite": 5,
                "prix_unitaire": products[1]["prix_vente"],
                "remise_ligne": 5,
            },
        ]
        
        montant_ht = sum(
            l["quantite"] * l["prix_unitaire"] * (1 - l["remise_ligne"] / 100)
            for l in lignes
        )
        montant_total = montant_ht
        
        statuts = ["validee", "preparee", "brouillon"]
        now = _now_iso()
        
        cmd_doc = {
            "commande_id": commande_id,
            "reference": reference,
            "client_id": client["client_id"],
            "statut": statuts[i],
            "date_commande": now[:10],
            "date_livraison_prevue": None,
            "date_validation": now[:10] if i < 2 else None,
            "date_preparation": now[:10] if i < 1 else None,
            "date_livraison": None,
            "remise_globale": 0,
            "montant_ht": round(montant_ht, 2),
            "montant_remise": 0,
            "montant_total": round(montant_total, 2),
            "notes": f"Commande de démonstration {i+1}",
            "motif_annulation": None,
            "created_by": user_id,
            "validated_by": user_id if i < 2 else None,
            "prepared_by": user_id if i < 1 else None,
            "delivered_by": None,
            "created_at": now,
            "updated_at": now,
        }
        demo_commandes.append(cmd_doc)
        
        # Insert lignes
        for ligne in lignes:
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "commande_id": commande_id,
                "produit_id": ligne["produit_id"],
                "quantite": ligne["quantite"],
                "prix_unitaire": ligne["prix_unitaire"],
                "remise_ligne": ligne["remise_ligne"],
                "montant_ligne": ligne["quantite"] * ligne["prix_unitaire"] * (1 - ligne["remise_ligne"] / 100),
            }
            await db.commande_lignes.insert_one(ligne_doc)
    
    if demo_commandes:
        await db.commandes.insert_many(demo_commandes)
        # Update counter
        await db.counters.update_one(
            {"_id": "commandes"},
            {"$set": {"seq": 3}},
            upsert=True
        )
    
    return len(demo_commandes)
