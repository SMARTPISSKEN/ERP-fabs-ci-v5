"""
Module Paiements — Sprint 8
- CRUD complet sur la collection MongoDB `paiements`
- Référence auto-incrémentée FABS-REG-2026-XXXX
- 4 modes de paiement : especes, cheque, virement, mobile_money
- Affectation à une ou plusieurs factures
- Mise à jour automatique des factures (montant_regle, statut)
- Rapprochement bancaire
- RBAC : 
    READ = {super_admin, DG, comptable}
    WRITE = {super_admin, DG, comptable}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger("fabsci.paiements")

# RBAC
READ_ROLES = {"super_admin", "directeur_general", "comptable"}
WRITE_ROLES = {"super_admin", "directeur_general", "comptable"}

ModePaiement = Literal["especes", "cheque", "virement", "mobile_money"]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_paiement_reference(db: AsyncIOMotorDatabase) -> str:
    """Generate FABS-REG-2026-XXXX reference"""
    current_year = datetime.now().year
    doc = await db.counters.find_one_and_update(
        {"_id": "paiements"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"]
    return f"FABS-REG-{current_year}-{seq:04d}"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AffectationFacture(BaseModel):
    facture_id: str
    montant_affecte: float = Field(..., gt=0)


class PaiementIn(BaseModel):
    client_id: str
    date_paiement: str  # ISO date YYYY-MM-DD
    mode_paiement: ModePaiement
    montant_total: float = Field(..., gt=0)
    # Chèque
    banque: Optional[str] = None
    numero_cheque: Optional[str] = None
    # Virement
    reference_virement: Optional[str] = None
    # Mobile Money
    operateur: Optional[str] = None
    numero_transaction: Optional[str] = None
    # Affectation factures
    factures: List[AffectationFacture] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, max_length=500)


class PaiementOut(BaseModel):
    paiement_id: str
    reference: str
    client_id: str
    client_nom: Optional[str] = None
    date_paiement: str
    mode_paiement: ModePaiement
    montant_total: float
    montant_affecte: float
    montant_non_affecte: float
    # Details mode paiement
    banque: Optional[str] = None
    numero_cheque: Optional[str] = None
    reference_virement: Optional[str] = None
    operateur: Optional[str] = None
    numero_transaction: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str


class PaiementDetail(PaiementOut):
    factures: List[dict]  # [{facture_id, facture_reference, montant_affecte}]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
async def _get_client_nom(db: AsyncIOMotorDatabase, client_id: str) -> Optional[str]:
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0, "nom": 1})
    return client["nom"] if client else None


async def _update_facture_paiement(db: AsyncIOMotorDatabase, facture_id: str, montant: float) -> None:
    """Add payment to facture and update status"""
    facture = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
    if not facture:
        return
    
    new_montant_regle = facture["montant_regle"] + montant
    montant_restant = facture["montant_ttc"] - new_montant_regle
    
    # Update status
    if new_montant_regle >= facture["montant_ttc"]:
        new_statut = "payee"
    elif new_montant_regle > 0:
        new_statut = "partiellement_payee"
    else:
        new_statut = facture["statut"]
    
    await db.factures.update_one(
        {"facture_id": facture_id},
        {"$set": {
            "montant_regle": round(new_montant_regle, 2),
            "montant_restant": round(montant_restant, 2),
            "statut": new_statut,
            "updated_at": _now_iso(),
        }}
    )


async def _enrich_paiement(db: AsyncIOMotorDatabase, paiement: dict) -> dict:
    """Add client_nom to paiement"""
    if paiement.get("client_id"):
        paiement["client_nom"] = await _get_client_nom(db, paiement["client_id"])
    return paiement


# ---------------------------------------------------------------------------
# Router Builder
# ---------------------------------------------------------------------------
def build_paiements_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/paiements", tags=["paiements"])

    # ---------- LIST ----------
    @router.get("", response_model=List[PaiementOut])
    async def list_paiements(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        mode_paiement: Optional[ModePaiement] = None,
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
        if mode_paiement:
            filters["mode_paiement"] = mode_paiement
        if client_id:
            filters["client_id"] = client_id
        if date_debut or date_fin:
            date_filter = {}
            if date_debut:
                date_filter["$gte"] = date_debut
            if date_fin:
                date_filter["$lte"] = date_fin
            filters["date_paiement"] = date_filter
        
        # Search by reference
        if q:
            filters["reference"] = {"$regex": q, "$options": "i"}

        cursor = db.paiements.find(filters, {"_id": 0}).sort("date_paiement", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(limit)
        
        # Enrich with client names
        for doc in docs:
            await _enrich_paiement(db, doc)
        
        return [PaiementOut(**d) for d in docs]

    # ---------- CREATE ----------
    @router.post("", response_model=PaiementOut, status_code=201)
    async def create_paiement(
        payload: PaiementIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Verify client exists
        client = await db.clients.find_one({"client_id": payload.client_id, "actif": True}, {"_id": 0})
        _ensure(client is not None, 404, "Client introuvable ou inactif")

        # Verify factures if any
        total_affecte = 0.0
        for affect in payload.factures:
            facture = await db.factures.find_one({"facture_id": affect.facture_id}, {"_id": 0})
            _ensure(facture is not None, 404, f"Facture {affect.facture_id} introuvable")
            _ensure(facture["client_id"] == payload.client_id, 400, "Facture n'appartient pas au client")
            total_affecte += affect.montant_affecte

        _ensure(total_affecte <= payload.montant_total, 400, "Montant affecté > montant total")

        # Create paiement
        paiement_id = f"pay_{uuid.uuid4().hex[:12]}"
        reference = await next_paiement_reference(db)
        montant_non_affecte = payload.montant_total - total_affecte

        now = _now_iso()
        paiement_doc = {
            "paiement_id": paiement_id,
            "reference": reference,
            "client_id": payload.client_id,
            "date_paiement": payload.date_paiement,
            "mode_paiement": payload.mode_paiement,
            "montant_total": payload.montant_total,
            "montant_affecte": total_affecte,
            "montant_non_affecte": montant_non_affecte,
            "banque": payload.banque,
            "numero_cheque": payload.numero_cheque,
            "reference_virement": payload.reference_virement,
            "operateur": payload.operateur,
            "numero_transaction": payload.numero_transaction,
            "notes": payload.notes,
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        await db.paiements.insert_one(paiement_doc)

        # Create affectations and update factures
        for affect in payload.factures:
            affectation_doc = {
                "affectation_id": f"aff_{uuid.uuid4().hex[:12]}",
                "paiement_id": paiement_id,
                "facture_id": affect.facture_id,
                "montant_affecte": affect.montant_affecte,
                "created_at": now,
            }
            await db.affectations_paiement.insert_one(affectation_doc)
            
            # Update facture
            await _update_facture_paiement(db, affect.facture_id, affect.montant_affecte)

        # Return with client_nom
        paiement_doc["client_nom"] = client["nom"]
        return PaiementOut(**paiement_doc)

    # ---------- GET DETAIL ----------
    @router.get("/{paiement_id}", response_model=PaiementDetail)
    async def get_paiement(
        paiement_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        paiement = await db.paiements.find_one({"paiement_id": paiement_id}, {"_id": 0})
        _ensure(paiement is not None, 404, "Paiement introuvable")
        
        # Get affectations
        affectations_cursor = db.affectations_paiement.find({"paiement_id": paiement_id}, {"_id": 0})
        affectations = await affectations_cursor.to_list(100)
        
        # Enrich with facture references
        factures_list = []
        for aff in affectations:
            facture = await db.factures.find_one({"facture_id": aff["facture_id"]}, {"_id": 0, "reference": 1})
            factures_list.append({
                "facture_id": aff["facture_id"],
                "facture_reference": facture["reference"] if facture else None,
                "montant_affecte": aff["montant_affecte"],
            })
        
        paiement["factures"] = factures_list
        await _enrich_paiement(db, paiement)
        
        return PaiementDetail(**paiement)

    # ---------- GET PAIEMENTS BY FACTURE ----------
    @router.get("/facture/{facture_id}", response_model=List[dict])
    async def get_paiements_by_facture(
        facture_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        # Get affectations for this facture
        affectations_cursor = db.affectations_paiement.find({"facture_id": facture_id}, {"_id": 0})
        affectations = await affectations_cursor.to_list(100)
        
        result = []
        for aff in affectations:
            paiement = await db.paiements.find_one({"paiement_id": aff["paiement_id"]}, {"_id": 0})
            if paiement:
                result.append({
                    "paiement_id": paiement["paiement_id"],
                    "reference": paiement["reference"],
                    "date_paiement": paiement["date_paiement"],
                    "mode_paiement": paiement["mode_paiement"],
                    "montant_affecte": aff["montant_affecte"],
                    "created_at": aff["created_at"],
                })
        
        return result

    return router


# ---------------------------------------------------------------------------
# Seed (optional demo data)
# ---------------------------------------------------------------------------
async def seed_paiements(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed demo paiements (optional)"""
    existing = await db.paiements.count_documents({})
    if existing > 0:
        return 0
    
    # Get first client and first facture emise
    client = await db.clients.find_one({"actif": True}, {"_id": 0})
    if not client:
        return 0
    
    factures = await db.factures.find({"statut": "emise", "type_facture": "facture"}, {"_id": 0}).limit(1).to_list(1)
    if len(factures) == 0:
        return 0

    facture = factures[0]
    
    # Create 1 demo paiement
    paiement_id = f"pay_{uuid.uuid4().hex[:12]}"
    reference = "FABS-REG-2026-0001"
    montant_affecte = min(facture["montant_ttc"] / 2, 50000)  # Half or 50k max
    
    now = _now_iso()
    paiement_doc = {
        "paiement_id": paiement_id,
        "reference": reference,
        "client_id": client["client_id"],
        "date_paiement": now[:10],
        "mode_paiement": "especes",
        "montant_total": montant_affecte,
        "montant_affecte": montant_affecte,
        "montant_non_affecte": 0.0,
        "banque": None,
        "numero_cheque": None,
        "reference_virement": None,
        "operateur": None,
        "numero_transaction": None,
        "notes": "Paiement de démonstration",
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }
    await db.paiements.insert_one(paiement_doc)
    
    # Create affectation
    affectation_doc = {
        "affectation_id": f"aff_{uuid.uuid4().hex[:12]}",
        "paiement_id": paiement_id,
        "facture_id": facture["facture_id"],
        "montant_affecte": montant_affecte,
        "created_at": now,
    }
    await db.affectations_paiement.insert_one(affectation_doc)
    
    # Update facture
    new_montant_regle = facture.get("montant_regle", 0) + montant_affecte
    montant_restant = facture["montant_ttc"] - new_montant_regle
    new_statut = "partiellement_payee" if montant_restant > 0 else "payee"
    
    await db.factures.update_one(
        {"facture_id": facture["facture_id"]},
        {"$set": {
            "montant_regle": round(new_montant_regle, 2),
            "montant_restant": round(montant_restant, 2),
            "statut": new_statut,
            "updated_at": now,
        }}
    )
    
    # Update counter
    await db.counters.update_one(
        {"_id": "paiements"},
        {"$set": {"seq": 1}},
        upsert=True
    )
    
    return 1
