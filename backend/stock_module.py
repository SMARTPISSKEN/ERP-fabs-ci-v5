"""
Module Stock & Mouvements — Sprint 9
- Suivi des mouvements de stock (entrées/sorties)
- Ajustements d'inventaire
- Historique des mouvements par produit
- Alertes stock automatiques
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger("fabsci.stock")

READ_ROLES = {"super_admin", "directeur_general", "gestionnaire_stock", "responsable_magasinier"}
WRITE_ROLES = {"super_admin", "directeur_general", "gestionnaire_stock", "responsable_magasinier"}

TypeMouvement = Literal["entree", "sortie", "ajustement", "retour", "specimen_gratuit"]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MouvementStockIn(BaseModel):
    produit_id: str
    type_mouvement: TypeMouvement
    quantite: int = Field(..., gt=0)
    commande_id: Optional[str] = None
    bl_id: Optional[str] = None
    motif: Optional[str] = Field(default=None, max_length=500)


class MouvementStockOut(BaseModel):
    mouvement_id: str
    produit_id: str
    produit_reference: Optional[str] = None
    produit_titre: Optional[str] = None
    type_mouvement: TypeMouvement
    quantite: int
    stock_avant: int
    stock_apres: int
    commande_id: Optional[str] = None
    bl_id: Optional[str] = None
    motif: Optional[str] = None
    created_by: str
    created_at: str


def build_stock_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/stock", tags=["stock"])

    @router.get("/mouvements", response_model=List[MouvementStockOut])
    async def list_mouvements(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        produit_id: Optional[str] = None,
        type_mouvement: Optional[TypeMouvement] = None,
        limit: int = Query(50, ge=1, le=200),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if produit_id:
            filters["produit_id"] = produit_id
        if type_mouvement:
            filters["type_mouvement"] = type_mouvement

        cursor = db.mouvements_stock.find(filters, {"_id": 0}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(limit)
        
        for doc in docs:
            prod = await db.produits.find_one({"product_id": doc["produit_id"]}, {"_id": 0, "reference": 1, "titre": 1})
            if prod:
                doc["produit_reference"] = prod.get("reference")
                doc["produit_titre"] = prod.get("titre")
        
        return [MouvementStockOut(**d) for d in docs]

    @router.post("/mouvements", response_model=MouvementStockOut, status_code=201)
    async def create_mouvement(
        payload: MouvementStockIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Get product
        produit = await db.produits.find_one({"product_id": payload.produit_id}, {"_id": 0})
        _ensure(produit is not None, 404, "Produit introuvable")

        stock_avant = produit.get("stock_actuel", 0)
        
        # Calculate new stock
        if payload.type_mouvement in ["entree", "retour"]:
            stock_apres = stock_avant + payload.quantite
        elif payload.type_mouvement == "specimen_gratuit":
            # Specimens gratuits : sortie sans facturation
            stock_apres = max(0, stock_avant - payload.quantite)
        else:  # sortie, ajustement
            stock_apres = max(0, stock_avant - payload.quantite)

        # Update product stock
        await db.produits.update_one(
            {"product_id": payload.produit_id},
            {"$set": {"stock_actuel": stock_apres, "updated_at": _now_iso()}}
        )

        # Create mouvement
        mouvement_id = f"mvt_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        
        mouvement_doc = {
            "mouvement_id": mouvement_id,
            "produit_id": payload.produit_id,
            "type_mouvement": payload.type_mouvement,
            "quantite": payload.quantite,
            "stock_avant": stock_avant,
            "stock_apres": stock_apres,
            "commande_id": payload.commande_id,
            "bl_id": payload.bl_id,
            "motif": payload.motif,
            "created_by": me["user_id"],
            "created_at": now,
        }
        await db.mouvements_stock.insert_one(mouvement_doc)

        mouvement_doc["produit_reference"] = produit.get("reference")
        mouvement_doc["produit_titre"] = produit.get("titre")
        
        return MouvementStockOut(**mouvement_doc)

    return router


async def seed_mouvements_stock(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed demo mouvements (optional)"""
    existing = await db.mouvements_stock.count_documents({})
    if existing > 0:
        return 0
    
    # Create indexes
    await db.mouvements_stock.create_index("mouvement_id", unique=True)
    await db.mouvements_stock.create_index("produit_id")
    
    return 0
