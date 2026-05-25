"""
Module Recherche Globale — Sprint 15
Recherche multi-modules : clients, produits, commandes, factures, BL
"""
from __future__ import annotations

from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

logger = logging.getLogger("fabsci.recherche")


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


class ResultatRecherche(BaseModel):
    type: str  # client, produit, commande, facture, bl
    id: str
    reference: str
    titre: str
    sous_titre: Optional[str] = None
    url: str


def build_recherche_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/recherche", tags=["recherche"])

    @router.get("/globale", response_model=List[ResultatRecherche])
    async def recherche_globale(
        q: str = Query(..., min_length=2),
        request: Request = None,
        authorization: Optional[str] = Header(default=None),
        limit: int = Query(20, ge=1, le=50),
    ):
        me = await resolve_user(request, authorization)
        
        resultats = []
        query_regex = {"$regex": q, "$options": "i"}
        
        # Search Clients
        if me["role"] in {"super_admin", "directeur_general", "directeur_commercial", "secretariat"}:
            clients = await db.clients.find(
                {"$or": [{"nom": query_regex}, {"reference": query_regex}], "actif": True},
                {"_id": 0, "client_id": 1, "reference": 1, "nom": 1, "type_client": 1}
            ).limit(5).to_list(5)
            
            for client in clients:
                resultats.append(ResultatRecherche(
                    type="client",
                    id=client["client_id"],
                    reference=client["reference"],
                    titre=client["nom"],
                    sous_titre=client.get("type_client"),
                    url=f"/clients/{client['client_id']}"
                ))
        
        # Search Produits
        if me["role"] in {"super_admin", "directeur_general", "directeur_commercial", "gestionnaire_stock"}:
            produits = await db.produits.find(
                {"$or": [{"titre": query_regex}, {"reference": query_regex}], "actif": True},
                {"_id": 0, "product_id": 1, "reference": 1, "titre": 1, "auteur": 1}
            ).limit(5).to_list(5)
            
            for produit in produits:
                resultats.append(ResultatRecherche(
                    type="produit",
                    id=produit["product_id"],
                    reference=produit["reference"],
                    titre=produit["titre"],
                    sous_titre=produit.get("auteur"),
                    url=f"/produits/{produit['product_id']}"
                ))
        
        # Search Commandes
        if me["role"] in {"super_admin", "directeur_general", "directeur_commercial", "comptable"}:
            commandes = await db.commandes.find(
                {"reference": query_regex},
                {"_id": 0, "commande_id": 1, "reference": 1, "statut": 1, "montant_total": 1}
            ).limit(5).to_list(5)
            
            for cmd in commandes:
                resultats.append(ResultatRecherche(
                    type="commande",
                    id=cmd["commande_id"],
                    reference=cmd["reference"],
                    titre=f"Commande {cmd['reference']}",
                    sous_titre=f"{cmd['statut']} - {cmd['montant_total']} FCFA",
                    url=f"/commandes/{cmd['commande_id']}"
                ))
        
        # Search Factures
        if me["role"] in {"super_admin", "directeur_general", "comptable"}:
            factures = await db.factures.find(
                {"reference": query_regex},
                {"_id": 0, "facture_id": 1, "reference": 1, "type_facture": 1, "statut": 1, "montant_ttc": 1}
            ).limit(5).to_list(5)
            
            for facture in factures:
                type_label = "Facture" if facture["type_facture"] == "facture" else "Avoir"
                resultats.append(ResultatRecherche(
                    type="facture",
                    id=facture["facture_id"],
                    reference=facture["reference"],
                    titre=f"{type_label} {facture['reference']}",
                    sous_titre=f"{facture['statut']} - {facture['montant_ttc']} FCFA",
                    url=f"/factures/{facture['facture_id']}"
                ))
        
        # Search BL
        if me["role"] in {"super_admin", "directeur_general", "service_logistique"}:
            bls = await db.bons_livraison.find(
                {"reference": query_regex},
                {"_id": 0, "bl_id": 1, "reference": 1, "statut": 1}
            ).limit(5).to_list(5)
            
            for bl in bls:
                resultats.append(ResultatRecherche(
                    type="bon_livraison",
                    id=bl["bl_id"],
                    reference=bl["reference"],
                    titre=f"BL {bl['reference']}",
                    sous_titre=bl["statut"],
                    url=f"/livraisons/{bl['bl_id']}"
                ))
        
        # Limit total results
        return resultats[:limit]

    return router
