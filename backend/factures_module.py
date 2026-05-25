"""
Module Factures — Sprint 7
- CRUD complet sur les collections MongoDB `factures` et `facture_lignes`
- Référence auto-incrémentée FABS-FC-26-27-XXXX (factures) et FABS-AV-26-27-XXXX (avoirs)
- Type facture : facture / avoir
- Statut : brouillon, emise, partiellement_payee, payee, annulee
- Génération automatique depuis commandes validées/préparées
- Gestion paiements (montant_regle, montant_restant)
- Génération avoirs (credit notes)
- RBAC : 
    READ = {super_admin, DG, commercial, comptable, secrétariat}
    WRITE = {super_admin, DG, commercial, comptable}
    PAYMENT = {super_admin, DG, comptable}
"""
from __future__ import annotations

from datetime import datetime, timezone, date as date_type
from typing import Literal, Optional, List
from decimal import Decimal
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("fabsci.factures")

# RBAC
READ_ROLES = {
    "super_admin", "directeur_general", "directeur_commercial",
    "comptable", "secretariat",
}
WRITE_ROLES = {
    "super_admin", "directeur_general",
    "directeur_commercial", "comptable",
}
PAYMENT_ROLES = {"super_admin", "directeur_general", "comptable"}

TypeFacture = Literal["facture", "avoir"]
Statut = Literal["brouillon", "emise", "partiellement_payee", "payee", "annulee"]

TVA_RATE = 0.18  # 18% TVA in Côte d'Ivoire


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_facture_reference(db: AsyncIOMotorDatabase, type_facture: TypeFacture) -> str:
    """Generate FABS-FC-26-27-XXXX (facture) or FABS-AV-26-27-XXXX (avoir)"""
    counter_id = "factures" if type_facture == "facture" else "avoirs"
    prefix = "FABS-FC-26-27" if type_facture == "facture" else "FABS-AV-26-27"
    
    doc = await db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"]
    return f"{prefix}-{seq:04d}"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class LigneFactureIn(BaseModel):
    produit_id: str
    designation: str  # Product title/description
    quantite: int = Field(..., gt=0)
    prix_unitaire: float = Field(..., gt=0)
    remise_ligne: float = Field(default=0, ge=0, le=100)

    @property
    def montant_ht(self) -> float:
        base = self.quantite * self.prix_unitaire
        return base * (1 - self.remise_ligne / 100)


class LigneFactureOut(BaseModel):
    ligne_id: str
    facture_id: str
    produit_id: str
    designation: str
    quantite: int
    prix_unitaire: float
    remise_ligne: float
    montant_ht: float


class FactureIn(BaseModel):
    client_id: str
    commande_id: Optional[str] = None
    date_facture: Optional[str] = None  # ISO date YYYY-MM-DD
    date_echeance: Optional[str] = None
    remise_globale: float = Field(default=0, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=1000)
    lignes: List[LigneFactureIn] = Field(..., min_length=1)

    @field_validator("date_facture", "date_echeance", mode="before")
    @classmethod
    def _validate_date(cls, v):
        if v:
            try:
                date_type.fromisoformat(v)
            except ValueError:
                raise ValueError("Format de date invalide (YYYY-MM-DD attendu)")
        return v


class FacturePatch(BaseModel):
    date_facture: Optional[str] = None
    date_echeance: Optional[str] = None
    remise_globale: Optional[float] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=1000)
    lignes: Optional[List[LigneFactureIn]] = None


class FactureOut(BaseModel):
    facture_id: str
    reference: str
    type_facture: TypeFacture
    client_id: str
    client_nom: Optional[str] = None
    commande_id: Optional[str] = None
    commande_reference: Optional[str] = None
    statut: Statut
    date_facture: str
    date_echeance: Optional[str] = None
    date_emission: Optional[str] = None
    remise_globale: float
    montant_ht: float
    montant_tva: float
    montant_ttc: float
    montant_regle: float
    montant_restant: float
    notes: Optional[str] = None
    facture_origine_id: Optional[str] = None  # Pour les avoirs
    created_by: str
    created_at: str
    updated_at: str


class FactureDetail(FactureOut):
    lignes: List[LigneFactureOut]


class GenerateFactureFromCommandeIn(BaseModel):
    commande_id: str
    date_facture: Optional[str] = None
    date_echeance: Optional[str] = None


class GenerateAvoirIn(BaseModel):
    facture_id: str
    montant: float = Field(..., gt=0)
    motif: str = Field(..., min_length=10, max_length=500)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
async def _get_client_nom(db: AsyncIOMotorDatabase, client_id: str) -> Optional[str]:
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0, "nom": 1})
    return client["nom"] if client else None


async def _get_commande_reference(db: AsyncIOMotorDatabase, commande_id: str) -> Optional[str]:
    cmd = await db.commandes.find_one({"commande_id": commande_id}, {"_id": 0, "reference": 1})
    return cmd["reference"] if cmd else None


async def _calculate_totals(lignes: List[LigneFactureIn], remise_globale: float) -> dict:
    """Calculate montant_ht, montant_tva, montant_ttc"""
    montant_ht_brut = sum(l.montant_ht for l in lignes)
    montant_remise_globale = montant_ht_brut * (remise_globale / 100)
    montant_ht = montant_ht_brut - montant_remise_globale
    montant_tva = montant_ht * TVA_RATE
    montant_ttc = montant_ht + montant_tva
    
    return {
        "montant_ht": round(montant_ht, 2),
        "montant_tva": round(montant_tva, 2),
        "montant_ttc": round(montant_ttc, 2),
    }


async def _enrich_facture_with_client(db: AsyncIOMotorDatabase, facture: dict) -> dict:
    """Add client_nom and commande_reference to facture dict"""
    if facture.get("client_id"):
        facture["client_nom"] = await _get_client_nom(db, facture["client_id"])
    if facture.get("commande_id"):
        facture["commande_reference"] = await _get_commande_reference(db, facture["commande_id"])
    return facture


async def _get_facture_with_lignes(db: AsyncIOMotorDatabase, facture_id: str) -> Optional[dict]:
    """Fetch facture + lignes"""
    facture = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
    if not facture:
        return None
    
    # Fetch lignes
    lignes_cursor = db.facture_lignes.find({"facture_id": facture_id}, {"_id": 0})
    lignes = await lignes_cursor.to_list(500)
    
    facture["lignes"] = lignes
    await _enrich_facture_with_client(db, facture)
    return facture


async def _update_facture_statut(db: AsyncIOMotorDatabase, facture_id: str) -> None:
    """Update facture statut based on montant_regle"""
    facture = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
    if not facture:
        return
    
    montant_ttc = facture["montant_ttc"]
    montant_regle = facture["montant_regle"]
    
    if montant_regle >= montant_ttc:
        new_statut = "payee"
    elif montant_regle > 0:
        new_statut = "partiellement_payee"
    else:
        new_statut = facture["statut"]  # Keep current if no payment
    
    await db.factures.update_one(
        {"facture_id": facture_id},
        {"$set": {
            "statut": new_statut,
            "montant_restant": round(montant_ttc - montant_regle, 2),
            "updated_at": _now_iso(),
        }}
    )


# ---------------------------------------------------------------------------
# Router Builder
# ---------------------------------------------------------------------------
def build_factures_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/factures", tags=["factures"])

    # ---------- LIST ----------
    @router.get("", response_model=List[FactureOut])
    async def list_factures(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        type_facture: Optional[TypeFacture] = None,
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
        if type_facture:
            filters["type_facture"] = type_facture
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
            filters["date_facture"] = date_filter
        
        # Search by reference
        if q:
            filters["reference"] = {"$regex": q, "$options": "i"}

        cursor = db.factures.find(filters, {"_id": 0}).sort("date_facture", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(limit)
        
        # Enrich with client names
        for doc in docs:
            await _enrich_facture_with_client(db, doc)
        
        return [FactureOut(**d) for d in docs]

    # ---------- CREATE ----------
    @router.post("", response_model=FactureOut, status_code=201)
    async def create_facture(
        payload: FactureIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
        type_facture: TypeFacture = Query("facture"),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Verify client exists
        client = await db.clients.find_one({"client_id": payload.client_id, "actif": True}, {"_id": 0})
        _ensure(client is not None, 404, "Client introuvable ou inactif")

        # Verify commande if provided
        if payload.commande_id:
            cmd = await db.commandes.find_one({"commande_id": payload.commande_id}, {"_id": 0})
            _ensure(cmd is not None, 404, "Commande introuvable")

        # Calculate totals
        totals = await _calculate_totals(payload.lignes, payload.remise_globale)

        # Create facture
        facture_id = f"fac_{uuid.uuid4().hex[:12]}"
        reference = await next_facture_reference(db, type_facture)
        date_facture = payload.date_facture or _now_iso()[:10]

        now = _now_iso()
        facture_doc = {
            "facture_id": facture_id,
            "reference": reference,
            "type_facture": type_facture,
            "client_id": payload.client_id,
            "commande_id": payload.commande_id,
            "statut": "brouillon",
            "date_facture": date_facture,
            "date_echeance": payload.date_echeance,
            "date_emission": None,
            "remise_globale": payload.remise_globale,
            "montant_ht": totals["montant_ht"],
            "montant_tva": totals["montant_tva"],
            "montant_ttc": totals["montant_ttc"],
            "montant_regle": 0.0,
            "montant_restant": totals["montant_ttc"],
            "notes": payload.notes,
            "facture_origine_id": None,
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        await db.factures.insert_one(facture_doc)

        # Create lignes
        for ligne in payload.lignes:
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "facture_id": facture_id,
                "produit_id": ligne.produit_id,
                "designation": ligne.designation,
                "quantite": ligne.quantite,
                "prix_unitaire": ligne.prix_unitaire,
                "remise_ligne": ligne.remise_ligne,
                "montant_ht": ligne.montant_ht,
            }
            await db.facture_lignes.insert_one(ligne_doc)

        # Return with client_nom
        facture_doc["client_nom"] = client["nom"]
        if payload.commande_id:
            facture_doc["commande_reference"] = await _get_commande_reference(db, payload.commande_id)
        return FactureOut(**facture_doc)

    # ---------- GENERATE FROM COMMANDE ----------
    @router.post("/generer-depuis-commande", response_model=FactureOut, status_code=201)
    async def generate_facture_from_commande(
        payload: GenerateFactureFromCommandeIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Get commande with lignes
        cmd = await db.commandes.find_one({"commande_id": payload.commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] in {"validee", "preparee", "livree"}, 400, "Commande doit être validée, préparée ou livrée")

        # Get commande lignes
        lignes_cursor = db.commande_lignes.find({"commande_id": payload.commande_id}, {"_id": 0})
        cmd_lignes = await lignes_cursor.to_list(500)
        _ensure(len(cmd_lignes) > 0, 400, "Commande sans lignes")

        # Get product designations
        lignes_facture = []
        for ligne in cmd_lignes:
            prod = await db.produits.find_one({"product_id": ligne["produit_id"]}, {"_id": 0, "titre": 1})
            lignes_facture.append(LigneFactureIn(
                produit_id=ligne["produit_id"],
                designation=prod["titre"] if prod else ligne["produit_id"],
                quantite=ligne["quantite"],
                prix_unitaire=ligne["prix_unitaire"],
                remise_ligne=ligne["remise_ligne"],
            ))

        # Create facture
        facture_in = FactureIn(
            client_id=cmd["client_id"],
            commande_id=payload.commande_id,
            date_facture=payload.date_facture or _now_iso()[:10],
            date_echeance=payload.date_echeance,
            remise_globale=cmd["remise_globale"],
            notes=f"Facture générée depuis commande {cmd['reference']}",
            lignes=lignes_facture,
        )

        # Use create_facture logic
        totals = await _calculate_totals(facture_in.lignes, facture_in.remise_globale)
        
        facture_id = f"fac_{uuid.uuid4().hex[:12]}"
        reference = await next_facture_reference(db, "facture")
        
        now = _now_iso()
        facture_doc = {
            "facture_id": facture_id,
            "reference": reference,
            "type_facture": "facture",
            "client_id": facture_in.client_id,
            "commande_id": facture_in.commande_id,
            "statut": "emise",
            "date_facture": facture_in.date_facture,
            "date_echeance": facture_in.date_echeance,
            "date_emission": now[:10],
            "remise_globale": facture_in.remise_globale,
            "montant_ht": totals["montant_ht"],
            "montant_tva": totals["montant_tva"],
            "montant_ttc": totals["montant_ttc"],
            "montant_regle": 0.0,
            "montant_restant": totals["montant_ttc"],
            "notes": facture_in.notes,
            "facture_origine_id": None,
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        await db.factures.insert_one(facture_doc)

        # Create lignes
        for ligne in facture_in.lignes:
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "facture_id": facture_id,
                "produit_id": ligne.produit_id,
                "designation": ligne.designation,
                "quantite": ligne.quantite,
                "prix_unitaire": ligne.prix_unitaire,
                "remise_ligne": ligne.remise_ligne,
                "montant_ht": ligne.montant_ht,
            }
            await db.facture_lignes.insert_one(ligne_doc)

        # Enrich and return
        await _enrich_facture_with_client(db, facture_doc)
        return FactureOut(**facture_doc)

    # ---------- GET DETAIL ----------
    @router.get("/{facture_id}", response_model=FactureDetail)
    async def get_facture(
        facture_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        facture = await _get_facture_with_lignes(db, facture_id)
        _ensure(facture is not None, 404, "Facture introuvable")
        
        return FactureDetail(**facture)

    # ---------- UPDATE ----------
    @router.patch("/{facture_id}", response_model=FactureOut)
    async def update_facture(
        facture_id: str,
        payload: FacturePatch,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        facture = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
        _ensure(facture is not None, 404, "Facture introuvable")
        _ensure(facture["statut"] == "brouillon", 400, "Seules les factures brouillon peuvent être modifiées")

        updates = {"updated_at": _now_iso()}
        
        if payload.date_facture is not None:
            updates["date_facture"] = payload.date_facture
        
        if payload.date_echeance is not None:
            updates["date_echeance"] = payload.date_echeance
        
        if payload.remise_globale is not None:
            updates["remise_globale"] = payload.remise_globale
        
        if payload.notes is not None:
            updates["notes"] = payload.notes
        
        # Update lignes if provided
        if payload.lignes is not None:
            _ensure(len(payload.lignes) > 0, 400, "Au moins une ligne requise")
            
            # Delete old lignes
            await db.facture_lignes.delete_many({"facture_id": facture_id})
            
            # Create new lignes
            for ligne in payload.lignes:
                ligne_doc = {
                    "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                    "facture_id": facture_id,
                    "produit_id": ligne.produit_id,
                    "designation": ligne.designation,
                    "quantite": ligne.quantite,
                    "prix_unitaire": ligne.prix_unitaire,
                    "remise_ligne": ligne.remise_ligne,
                    "montant_ht": ligne.montant_ht,
                }
                await db.facture_lignes.insert_one(ligne_doc)
            
            # Recalculate totals
            totals = await _calculate_totals(payload.lignes, payload.remise_globale or facture["remise_globale"])
            updates.update(totals)
            updates["montant_restant"] = totals["montant_ttc"]

        await db.factures.update_one({"facture_id": facture_id}, {"$set": updates})
        
        updated = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
        await _enrich_facture_with_client(db, updated)
        return FactureOut(**updated)

    # ---------- EMETTRE (EMIT) ----------
    @router.post("/{facture_id}/emettre", response_model=FactureOut)
    async def emettre_facture(
        facture_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        facture = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
        _ensure(facture is not None, 404, "Facture introuvable")
        _ensure(facture["statut"] == "brouillon", 400, "Seules les factures brouillon peuvent être émises")

        now = _now_iso()
        await db.factures.update_one(
            {"facture_id": facture_id},
            {"$set": {
                "statut": "emise",
                "date_emission": now[:10],
                "updated_at": now,
            }}
        )
        
        updated = await db.factures.find_one({"facture_id": facture_id}, {"_id": 0})
        await _enrich_facture_with_client(db, updated)
        return FactureOut(**updated)

    # ---------- GENERER AVOIR ----------
    @router.post("/generer-avoir", response_model=FactureOut, status_code=201)
    async def generer_avoir(
        payload: GenerateAvoirIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Get original facture
        facture_orig = await _get_facture_with_lignes(db, payload.facture_id)
        _ensure(facture_orig is not None, 404, "Facture origine introuvable")
        _ensure(facture_orig["type_facture"] == "facture", 400, "Impossible de créer un avoir depuis un avoir")
        _ensure(payload.montant <= facture_orig["montant_ttc"], 400, "Montant avoir supérieur au montant facture")

        # Create avoir with same lignes but negative amounts
        avoir_id = f"fac_{uuid.uuid4().hex[:12]}"
        reference = await next_facture_reference(db, "avoir")
        
        # Calculate proportional amounts
        ratio = payload.montant / facture_orig["montant_ttc"]
        montant_ht = round(facture_orig["montant_ht"] * ratio, 2)
        montant_tva = round(facture_orig["montant_tva"] * ratio, 2)
        montant_ttc = round(payload.montant, 2)

        now = _now_iso()
        avoir_doc = {
            "avoir_id": avoir_id,
            "reference": reference,
            "type_facture": "avoir",
            "client_id": facture_orig["client_id"],
            "commande_id": facture_orig.get("commande_id"),
            "statut": "emise",
            "date_facture": now[:10],
            "date_echeance": None,
            "date_emission": now[:10],
            "remise_globale": 0,
            "montant_ht": -montant_ht,  # Negative
            "montant_tva": -montant_tva,
            "montant_ttc": -montant_ttc,
            "montant_regle": 0.0,
            "montant_restant": -montant_ttc,
            "notes": f"Avoir généré depuis facture {facture_orig['reference']}. Motif: {payload.motif}",
            "facture_origine_id": payload.facture_id,
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        # Fix: use facture_id as key
        avoir_doc["facture_id"] = avoir_id
        await db.factures.insert_one(avoir_doc)

        # Copy lignes (proportional quantities)
        for ligne_orig in facture_orig["lignes"]:
            ligne_avoir = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "facture_id": avoir_id,
                "produit_id": ligne_orig["produit_id"],
                "designation": ligne_orig["designation"],
                "quantite": -int(ligne_orig["quantite"] * ratio),  # Negative
                "prix_unitaire": ligne_orig["prix_unitaire"],
                "remise_ligne": ligne_orig["remise_ligne"],
                "montant_ht": -round(ligne_orig["montant_ht"] * ratio, 2),
            }
            await db.facture_lignes.insert_one(ligne_avoir)

        # Enrich and return
        await _enrich_facture_with_client(db, avoir_doc)
        return FactureOut(**avoir_doc)

    # ---------- PDF ----------
    @router.get("/{facture_id}/pdf")
    async def facture_pdf(
        facture_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        from fastapi.responses import StreamingResponse
        from pdf_generator import generate_facture_pdf

        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        facture = await _get_facture_with_lignes(db, facture_id)
        _ensure(facture is not None, 404, "Facture introuvable")

        client = await db.clients.find_one({"client_id": facture["client_id"]}, {"_id": 0}) or {}
        # Inject representant from client into facture context if missing
        facture.setdefault("representant", client.get("representant"))

        buffer = generate_facture_pdf(facture, facture.get("lignes", []), client)
        filename = f"{facture['reference']}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    return router


# ---------------------------------------------------------------------------
# Seed (optional demo data)
# ---------------------------------------------------------------------------
async def seed_factures(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed demo factures (optional)"""
    existing = await db.factures.count_documents({})
    if existing > 0:
        return 0
    
    # Get first client and first commande
    client = await db.clients.find_one({"actif": True}, {"_id": 0})
    if not client:
        return 0
    
    commandes = await db.commandes.find({"statut": {"$in": ["validee", "livree"]}}, {"_id": 0}).limit(2).to_list(2)
    if len(commandes) == 0:
        return 0

    demo_factures = []
    for i, cmd in enumerate(commandes):
        # Get commande lignes
        lignes_cursor = db.commande_lignes.find({"commande_id": cmd["commande_id"]}, {"_id": 0})
        cmd_lignes = await lignes_cursor.to_list(500)
        
        if len(cmd_lignes) == 0:
            continue

        facture_id = f"fac_{uuid.uuid4().hex[:12]}"
        reference = f"FABS-FC-26-27-{i+1:04d}"
        
        # Calculate totals from commande
        montant_ht = cmd["montant_ht"] - cmd["montant_remise"]
        montant_tva = round(montant_ht * TVA_RATE, 2)
        montant_ttc = round(montant_ht + montant_tva, 2)
        
        now = _now_iso()
        statut = "emise" if i == 0 else "payee"
        montant_regle = montant_ttc if i == 1 else 0.0
        
        facture_doc = {
            "facture_id": facture_id,
            "reference": reference,
            "type_facture": "facture",
            "client_id": cmd["client_id"],
            "commande_id": cmd["commande_id"],
            "statut": statut,
            "date_facture": now[:10],
            "date_echeance": None,
            "date_emission": now[:10],
            "remise_globale": cmd["remise_globale"],
            "montant_ht": montant_ht,
            "montant_tva": montant_tva,
            "montant_ttc": montant_ttc,
            "montant_regle": montant_regle,
            "montant_restant": montant_ttc - montant_regle,
            "notes": f"Facture de démonstration {i+1}",
            "facture_origine_id": None,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now,
        }
        demo_factures.append(facture_doc)
        
        # Insert lignes
        for ligne in cmd_lignes:
            prod = await db.produits.find_one({"product_id": ligne["produit_id"]}, {"_id": 0, "titre": 1})
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "facture_id": facture_id,
                "produit_id": ligne["produit_id"],
                "designation": prod["titre"] if prod else "Produit",
                "quantite": ligne["quantite"],
                "prix_unitaire": ligne["prix_unitaire"],
                "remise_ligne": ligne["remise_ligne"],
                "montant_ht": ligne["montant_ligne"],
            }
            await db.facture_lignes.insert_one(ligne_doc)
    
    if demo_factures:
        await db.factures.insert_many(demo_factures)
        # Update counter
        await db.counters.update_one(
            {"_id": "factures"},
            {"$set": {"seq": len(demo_factures)}},
            upsert=True
        )
    
    return len(demo_factures)
