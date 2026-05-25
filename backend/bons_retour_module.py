"""
Module Bons de Retour — Sprint 11
- CRUD bons de retour
- Référence auto FABS-BR-26-27-XXXX
- Génération automatique avoirs lors de la validation
- Mise à jour stock automatique (entrées retour)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger("fabsci.bons_retour")

READ_ROLES = {"super_admin", "directeur_general", "service_logistique", "responsable_magasinier", "comptable"}
WRITE_ROLES = {"super_admin", "directeur_general", "service_logistique", "comptable"}

StatutBR = Literal["en_attente", "valide", "avoir_genere", "annule"]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_br_reference(db: AsyncIOMotorDatabase) -> str:
    """Generate FABS-BR-26-27-XXXX reference"""
    doc = await db.counters.find_one_and_update(
        {"_id": "bons_retour"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"]
    return f"FABS-BR-26-27-{seq:04d}"


class LigneBRIn(BaseModel):
    produit_id: str
    quantite: int = Field(..., gt=0)
    prix_unitaire: float = Field(..., gt=0)
    motif: str = Field(..., min_length=5, max_length=200)


class BonRetourIn(BaseModel):
    facture_id: str
    client_id: str
    date_retour: str  # ISO date YYYY-MM-DD
    motif_global: str = Field(..., min_length=10, max_length=500)
    lignes: List[LigneBRIn] = Field(..., min_length=1)


class BonRetourOut(BaseModel):
    br_id: str
    reference: str
    facture_id: str
    facture_reference: Optional[str] = None
    client_id: str
    client_nom: Optional[str] = None
    statut: StatutBR
    date_retour: str
    date_validation: Optional[str] = None
    montant_total_ht: float
    montant_total_ttc: float
    avoir_id: Optional[str] = None
    avoir_reference: Optional[str] = None
    motif_global: str
    created_by: str
    validated_by: Optional[str] = None
    created_at: str
    updated_at: str


def build_bons_retour_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/bons-retour", tags=["bons_retour"])

    @router.get("", response_model=List[BonRetourOut])
    async def list_bons_retour(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        statut: Optional[StatutBR] = None,
        client_id: Optional[str] = None,
        limit: int = Query(50, ge=1, le=200),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if statut:
            filters["statut"] = statut
        if client_id:
            filters["client_id"] = client_id

        cursor = db.bons_retour.find(filters, {"_id": 0}).sort("date_retour", -1).limit(limit)
        docs = await cursor.to_list(limit)
        
        # Enrich
        for doc in docs:
            facture = await db.factures.find_one({"facture_id": doc["facture_id"]}, {"_id": 0, "reference": 1})
            if facture:
                doc["facture_reference"] = facture.get("reference")
            
            client = await db.clients.find_one({"client_id": doc["client_id"]}, {"_id": 0, "nom": 1})
            if client:
                doc["client_nom"] = client.get("nom")
            
            if doc.get("avoir_id"):
                avoir = await db.factures.find_one({"facture_id": doc["avoir_id"]}, {"_id": 0, "reference": 1})
                if avoir:
                    doc["avoir_reference"] = avoir.get("reference")
        
        return [BonRetourOut(**d) for d in docs]

    @router.post("", response_model=BonRetourOut, status_code=201)
    async def create_bon_retour(
        payload: BonRetourIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        # Verify facture exists
        facture = await db.factures.find_one({"facture_id": payload.facture_id}, {"_id": 0})
        _ensure(facture is not None, 404, "Facture introuvable")
        _ensure(facture["client_id"] == payload.client_id, 400, "Facture n'appartient pas au client")

        # Verify client
        client = await db.clients.find_one({"client_id": payload.client_id, "actif": True}, {"_id": 0})
        _ensure(client is not None, 404, "Client introuvable")

        # Calculate totals
        montant_total_ht = sum(l.quantite * l.prix_unitaire for l in payload.lignes)
        montant_total_ttc = montant_total_ht * 1.18  # TVA 18%

        # Create BR
        br_id = f"br_{uuid.uuid4().hex[:12]}"
        reference = await next_br_reference(db)
        now = _now_iso()

        br_doc = {
            "br_id": br_id,
            "reference": reference,
            "facture_id": payload.facture_id,
            "client_id": payload.client_id,
            "statut": "en_attente",
            "date_retour": payload.date_retour,
            "date_validation": None,
            "montant_total_ht": round(montant_total_ht, 2),
            "montant_total_ttc": round(montant_total_ttc, 2),
            "avoir_id": None,
            "motif_global": payload.motif_global,
            "created_by": me["user_id"],
            "validated_by": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.bons_retour.insert_one(br_doc)

        # Create lignes
        for ligne in payload.lignes:
            ligne_doc = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "br_id": br_id,
                "produit_id": ligne.produit_id,
                "quantite": ligne.quantite,
                "prix_unitaire": ligne.prix_unitaire,
                "motif": ligne.motif,
            }
            await db.br_lignes.insert_one(ligne_doc)

        # Enrich and return
        br_doc["facture_reference"] = facture.get("reference")
        br_doc["client_nom"] = client.get("nom")
        br_doc["avoir_reference"] = None

        return BonRetourOut(**br_doc)

    @router.post("/{br_id}/valider", response_model=BonRetourOut)
    async def valider_bon_retour(
        br_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        br = await db.bons_retour.find_one({"br_id": br_id}, {"_id": 0})
        _ensure(br is not None, 404, "BR introuvable")
        _ensure(br["statut"] == "en_attente", 400, "BR déjà validé ou annulé")

        now = _now_iso()

        # Generate avoir automatically
        from factures_module import next_facture_reference
        avoir_id = f"fac_{uuid.uuid4().hex[:12]}"
        avoir_reference = await next_facture_reference(db, "avoir")

        avoir_doc = {
            "facture_id": avoir_id,
            "reference": avoir_reference,
            "type_facture": "avoir",
            "client_id": br["client_id"],
            "commande_id": None,
            "statut": "emise",
            "date_facture": now[:10],
            "date_echeance": None,
            "date_emission": now[:10],
            "remise_globale": 0,
            "montant_ht": -br["montant_total_ht"],
            "montant_tva": -round(br["montant_total_ht"] * 0.18, 2),
            "montant_ttc": -br["montant_total_ttc"],
            "montant_regle": 0.0,
            "montant_restant": -br["montant_total_ttc"],
            "notes": f"Avoir généré depuis BR {br['reference']}. Motif: {br['motif_global']}",
            "facture_origine_id": br["facture_id"],
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now,
        }
        await db.factures.insert_one(avoir_doc)

        # Create avoir lignes from BR lignes
        br_lignes = await db.br_lignes.find({"br_id": br_id}, {"_id": 0}).to_list(100)
        for br_ligne in br_lignes:
            # FIX: projection must include stock_actuel (sinon corruption stock)
            produit = await db.produits.find_one(
                {"product_id": br_ligne["produit_id"]},
                {"_id": 0, "titre": 1, "stock_actuel": 1},
            )

            avoir_ligne = {
                "ligne_id": f"ligne_{uuid.uuid4().hex[:12]}",
                "facture_id": avoir_id,
                "produit_id": br_ligne["produit_id"],
                "designation": produit["titre"] if produit else br_ligne["produit_id"],
                "quantite": -br_ligne["quantite"],
                "prix_unitaire": br_ligne["prix_unitaire"],
                "remise_ligne": 0,
                "montant_ht": -round(br_ligne["quantite"] * br_ligne["prix_unitaire"], 2),
            }
            await db.facture_lignes.insert_one(avoir_ligne)

            # Stock movement (retour = entrée) — usage de $inc pour éviter race conditions
            stock_avant = produit.get("stock_actuel", 0) if produit else 0
            stock_apres = stock_avant + br_ligne["quantite"]

            if produit:
                await db.produits.update_one(
                    {"product_id": br_ligne["produit_id"]},
                    {
                        "$inc": {"stock_actuel": br_ligne["quantite"]},
                        "$set": {"updated_at": now},
                    },
                )
            
            mouvement_doc = {
                "mouvement_id": f"mvt_{uuid.uuid4().hex[:12]}",
                "produit_id": br_ligne["produit_id"],
                "type_mouvement": "retour",
                "quantite": br_ligne["quantite"],
                "stock_avant": stock_avant,
                "stock_apres": stock_apres,
                "bl_id": None,
                "motif": f"Retour BR {br['reference']} - {br_ligne['motif']}",
                "created_by": me["user_id"],
                "created_at": now,
            }
            await db.mouvements_stock.insert_one(mouvement_doc)

        # Update BR
        await db.bons_retour.update_one(
            {"br_id": br_id},
            {"$set": {
                "statut": "avoir_genere",
                "date_validation": now[:10],
                "avoir_id": avoir_id,
                "validated_by": me["user_id"],
                "updated_at": now,
            }}
        )

        # Get updated BR
        updated = await db.bons_retour.find_one({"br_id": br_id}, {"_id": 0})
        facture = await db.factures.find_one({"facture_id": updated["facture_id"]}, {"_id": 0, "reference": 1})
        client = await db.clients.find_one({"client_id": updated["client_id"]}, {"_id": 0, "nom": 1})
        
        updated["facture_reference"] = facture["reference"] if facture else None
        updated["client_nom"] = client["nom"] if client else None
        updated["avoir_reference"] = avoir_reference

        return BonRetourOut(**updated)

    # ---------- PDF ----------
    @router.get("/{br_id}/pdf")
    async def br_pdf(
        br_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        from fastapi.responses import StreamingResponse
        from pdf_generator import generate_retour_pdf

        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        br = await db.bons_retour.find_one({"br_id": br_id}, {"_id": 0})
        _ensure(br is not None, 404, "Bon de retour introuvable")

        lignes = await db.br_lignes.find({"br_id": br_id}, {"_id": 0}).to_list(500)
        for l in lignes:
            prod = await db.produits.find_one({"product_id": l.get("produit_id")}, {"_id": 0, "titre": 1, "classe": 1, "isbn": 1})
            if prod:
                l["designation"] = prod.get("titre", l.get("designation", ""))
                l["classe"] = prod.get("classe", "")
                l["code_article"] = prod.get("isbn", l.get("produit_id", ""))[:14]
            l["montant_ht"] = l.get("montant_ligne", l.get("montant_ht", 0))

        client = await db.clients.find_one({"client_id": br["client_id"]}, {"_id": 0}) or {}

        buffer = generate_retour_pdf(br, lignes, client)
        filename = f"{br['reference']}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    return router


async def seed_bons_retour(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed demo BR (optional)"""
    existing = await db.bons_retour.count_documents({})
    if existing > 0:
        return 0
    
    await db.bons_retour.create_index("br_id", unique=True)
    await db.bons_retour.create_index("reference", unique=True)
    await db.br_lignes.create_index("br_id")
    
    return 0
