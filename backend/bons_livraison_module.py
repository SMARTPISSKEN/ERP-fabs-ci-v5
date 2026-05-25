"""
Module Bons de Livraison — Sprint 10
- CRUD bons de livraison
- Référence auto FABS-BL-26-27-XXXX
- Génération depuis commandes préparées
- Mise à jour stock automatique lors de la livraison
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger("fabsci.bons_livraison")

READ_ROLES = {"super_admin", "directeur_general", "service_logistique", "responsable_magasinier"}
WRITE_ROLES = {"super_admin", "directeur_general", "service_logistique"}

StatutBL = Literal["en_preparation", "pret", "livre", "annule"]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_bl_reference(db: AsyncIOMotorDatabase) -> str:
    """Generate FABS-BL-26-27-XXXX reference"""
    doc = await db.counters.find_one_and_update(
        {"_id": "bons_livraison"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"]
    return f"FABS-BL-26-27-{seq:04d}"


class LigneBLIn(BaseModel):
    produit_id: str
    quantite: int = Field(..., gt=0)


class BonLivraisonIn(BaseModel):
    commande_id: str
    date_livraison_prevue: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)
    lignes: List[LigneBLIn] = Field(..., min_length=1)


class BonLivraisonOut(BaseModel):
    bl_id: str
    reference: str
    commande_id: str
    commande_reference: Optional[str] = None
    client_id: str
    client_nom: Optional[str] = None
    statut: StatutBL
    date_creation: str
    date_livraison_prevue: Optional[str] = None
    date_livraison_reelle: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str


def build_bons_livraison_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/bons-livraison", tags=["bons_livraison"])

    @router.get("", response_model=List[BonLivraisonOut])
    async def list_bons_livraison(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        statut: Optional[StatutBL] = None,
        commande_id: Optional[str] = None,
        limit: int = Query(50, ge=1, le=200),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if statut:
            filters["statut"] = statut
        if commande_id:
            filters["commande_id"] = commande_id

        cursor = db.bons_livraison.find(filters, {"_id": 0}).sort("date_creation", -1).limit(limit)
        docs = await cursor.to_list(limit)
        
        # Enrich
        for doc in docs:
            cmd = await db.commandes.find_one({"commande_id": doc["commande_id"]}, {"_id": 0, "reference": 1, "client_id": 1})
            if cmd:
                doc["commande_reference"] = cmd.get("reference")
                doc["client_id"] = cmd.get("client_id")
                client = await db.clients.find_one({"client_id": cmd["client_id"]}, {"_id": 0, "nom": 1})
                if client:
                    doc["client_nom"] = client.get("nom")
        
        return [BonLivraisonOut(**d) for d in docs]

    @router.post("", response_model=BonLivraisonOut, status_code=201)
    async def create_bon_livraison(
        payload: BonLivraisonIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Verify commande
        cmd = await db.commandes.find_one({"commande_id": payload.commande_id}, {"_id": 0})
        _ensure(cmd is not None, 404, "Commande introuvable")
        _ensure(cmd["statut"] in ["preparee", "livree"], 400, "Commande doit être préparée")

        # Create BL
        bl_id = f"bl_{uuid.uuid4().hex[:12]}"
        reference = await next_bl_reference(db)
        now = _now_iso()

        bl_doc = {
            "bl_id": bl_id,
            "reference": reference,
            "commande_id": payload.commande_id,
            "client_id": cmd["client_id"],
            "statut": "en_preparation",
            "date_creation": now[:10],
            "date_livraison_prevue": payload.date_livraison_prevue,
            "date_livraison_reelle": None,
            "notes": payload.notes,
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        await db.bons_livraison.insert_one(bl_doc)

        # Create lignes
        for ligne in payload.lignes:
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "bl_id": bl_id,
                "produit_id": ligne.produit_id,
                "quantite": ligne.quantite,
            }
            await db.bl_lignes.insert_one(ligne_doc)

        # Enrich and return
        bl_doc["commande_reference"] = cmd.get("reference")
        client = await db.clients.find_one({"client_id": cmd["client_id"]}, {"_id": 0, "nom": 1})
        bl_doc["client_nom"] = client["nom"] if client else None

        return BonLivraisonOut(**bl_doc)

    @router.post("/{bl_id}/livrer", response_model=BonLivraisonOut)
    async def livrer_bon(
        bl_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        bl = await db.bons_livraison.find_one({"bl_id": bl_id}, {"_id": 0})
        _ensure(bl is not None, 404, "BL introuvable")
        _ensure(bl["statut"] != "livre", 400, "BL déjà livré")

        # Update BL
        now = _now_iso()
        await db.bons_livraison.update_one(
            {"bl_id": bl_id},
            {"$set": {
                "statut": "livre",
                "date_livraison_reelle": now[:10],
                "updated_at": now,
            }}
        )

        # Update commande status
        await db.commandes.update_one(
            {"commande_id": bl["commande_id"]},
            {"$set": {"statut": "livree", "date_livraison": now[:10], "updated_at": now}}
        )

        # Get lignes and create stock movements
        lignes = await db.bl_lignes.find({"bl_id": bl_id}, {"_id": 0}).to_list(100)
        for ligne in lignes:
            # Create stock movement (sortie)
            produit = await db.produits.find_one({"product_id": ligne["produit_id"]}, {"_id": 0})
            if produit:
                stock_avant = produit.get("stock_actuel", 0)
                stock_apres = max(0, stock_avant - ligne["quantite"])
                
                await db.produits.update_one(
                    {"product_id": ligne["produit_id"]},
                    {"$set": {"stock_actuel": stock_apres, "updated_at": now}}
                )
                
                mouvement_doc = {
                    "mouvement_id": f"mvt_{uuid.uuid4().hex[:12]}",
                    "produit_id": ligne["produit_id"],
                    "type_mouvement": "sortie",
                    "quantite": ligne["quantite"],
                    "stock_avant": stock_avant,
                    "stock_apres": stock_apres,
                    "bl_id": bl_id,
                    "motif": f"Livraison BL {bl['reference']}",
                    "created_by": me["user_id"],
                    "created_at": now,
                }
                await db.mouvements_stock.insert_one(mouvement_doc)

        updated = await db.bons_livraison.find_one({"bl_id": bl_id}, {"_id": 0})
        cmd = await db.commandes.find_one({"commande_id": updated["commande_id"]}, {"_id": 0, "reference": 1, "client_id": 1})
        if cmd:
            updated["commande_reference"] = cmd.get("reference")
            client = await db.clients.find_one({"client_id": cmd["client_id"]}, {"_id": 0, "nom": 1})
            updated["client_nom"] = client["nom"] if client else None
        
        return BonLivraisonOut(**updated)

    # ---------- PDF ----------
    @router.get("/{bl_id}/pdf")
    async def bl_pdf(
        bl_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        from fastapi.responses import StreamingResponse
        from pdf_generator import generate_bl_pdf

        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        bl = await db.bons_livraison.find_one({"bl_id": bl_id}, {"_id": 0})
        _ensure(bl is not None, 404, "Bon de livraison introuvable")

        # Fetch lignes from bl_lignes if exists, else from commande_lignes
        lignes = await db.bl_lignes.find({"bl_id": bl_id}, {"_id": 0}).to_list(500)
        if not lignes:
            lignes = await db.commande_lignes.find({"commande_id": bl["commande_id"]}, {"_id": 0}).to_list(500)

        for l in lignes:
            prod = await db.produits.find_one({"product_id": l.get("produit_id")}, {"_id": 0, "titre": 1, "classe": 1, "isbn": 1})
            if prod:
                l["designation"] = prod.get("titre", l.get("designation", ""))
                l["classe"] = prod.get("classe", "")
                l["code_article"] = prod.get("isbn", l.get("produit_id", ""))[:14]

        cmd = await db.commandes.find_one({"commande_id": bl["commande_id"]}, {"_id": 0, "reference": 1, "client_id": 1})
        commande_ref = cmd.get("reference") if cmd else None
        client = {}
        if cmd:
            client = await db.clients.find_one({"client_id": cmd["client_id"]}, {"_id": 0}) or {}

        buffer = generate_bl_pdf(bl, lignes, client, commande_ref=commande_ref)
        filename = f"{bl['reference']}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    return router


async def seed_bons_livraison(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed demo BL (optional)"""
    existing = await db.bons_livraison.count_documents({})
    if existing > 0:
        return 0
    
    # Create indexes
    await db.bons_livraison.create_index("bl_id", unique=True)
    await db.bons_livraison.create_index("reference", unique=True)
    await db.bl_lignes.create_index("bl_id")
    
    return 0
