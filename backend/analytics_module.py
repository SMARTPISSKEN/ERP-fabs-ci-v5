"""
Module Rapports & Analytics — Analyses complètes des ventes
- Ventes globales, par matière, par niveau, par zone, par client
- Filtres dynamiques et exports
- Agrégations MongoDB optimisées
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging

from fastapi import APIRouter, HTTPException, Header, Request, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

logger = logging.getLogger("fabsci.analytics")

# RBAC
READ_ROLES = {
    "super_admin", "directeur_general", "comptable", 
    "directeur_commercial"
}

def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ============================================================================
# ROUTER BUILDER
# ============================================================================
def build_analytics_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/analytics", tags=["analytics"])
    
    # ------------------------------------------------------------------------
    # DASHBOARD GLOBAL
    # ------------------------------------------------------------------------
    @router.get("/dashboard")
    async def get_analytics_dashboard(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Dashboard principal avec KPIs globaux"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        # Filtres de date
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Total des ventes
        pipeline_total = [
            {"$match": filters},
            {"$group": {
                "_id": None,
                "total_ventes": {"$sum": "$montant_ht"},
                "total_factures": {"$sum": 1},
                "total_remises": {"$sum": "$remise_montant"},
                "total_ttc": {"$sum": "$montant_ttc"}
            }}
        ]
        total_result = await db.factures.aggregate(pipeline_total).to_list(1)
        totals = total_result[0] if total_result else {
            "total_ventes": 0,
            "total_factures": 0,
            "total_remises": 0,
            "total_ttc": 0
        }
        
        # Nombre de clients actifs
        clients_actifs = await db.clients.count_documents({"actif": True})
        
        # Quantité totale vendue (somme des quantités dans les lignes)
        pipeline_qty = [
            {"$match": filters},
            {"$unwind": "$lignes"},
            {"$group": {"_id": None, "total_qty": {"$sum": "$lignes.quantite"}}}
        ]
        qty_result = await db.factures.aggregate(pipeline_qty).to_list(1)
        total_qty = qty_result[0]["total_qty"] if qty_result else 0
        
        return {
            "total_ventes": totals.get("total_ventes", 0),
            "total_factures": totals.get("total_factures", 0),
            "total_remises": totals.get("total_remises", 0),
            "total_ttc": totals.get("total_ttc", 0),
            "clients_actifs": clients_actifs,
            "quantite_totale": total_qty
        }
    
    # ------------------------------------------------------------------------
    # VENTES PAR MATIÈRE/CATÉGORIE
    # ------------------------------------------------------------------------
    @router.get("/by-matiere")
    async def get_ventes_by_matiere(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Analyse des ventes par matière/catégorie"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        # Filtres
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Agrégation par catégorie de produit
        pipeline = [
            {"$match": filters},
            {"$unwind": "$lignes"},
            {"$lookup": {
                "from": "produits",
                "localField": "lignes.produit_id",
                "foreignField": "produit_id",
                "as": "produit"
            }},
            {"$unwind": {"path": "$produit", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$produit.categorie",
                "total_ventes": {"$sum": "$lignes.total"},
                "quantite": {"$sum": "$lignes.quantite"},
                "nb_factures": {"$sum": 1}
            }},
            {"$sort": {"total_ventes": -1}}
        ]
        
        results = await db.factures.aggregate(pipeline).to_list(100)
        
        return {
            "data": [
                {
                    "categorie": r["_id"] or "Non catégorisé",
                    "total_ventes": r["total_ventes"],
                    "quantite": r["quantite"],
                    "nb_factures": r["nb_factures"]
                }
                for r in results
            ]
        }
    
    # ------------------------------------------------------------------------
    # VENTES PAR NIVEAU SCOLAIRE
    # ------------------------------------------------------------------------
    @router.get("/by-niveau")
    async def get_ventes_by_niveau(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Analyse des ventes par niveau scolaire"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Agrégation par niveau
        pipeline = [
            {"$match": filters},
            {"$unwind": "$lignes"},
            {"$lookup": {
                "from": "produits",
                "localField": "lignes.produit_id",
                "foreignField": "produit_id",
                "as": "produit"
            }},
            {"$unwind": {"path": "$produit", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$produit.niveau_scolaire",
                "total_ventes": {"$sum": "$lignes.total"},
                "quantite": {"$sum": "$lignes.quantite"}
            }},
            {"$sort": {"total_ventes": -1}}
        ]
        
        results = await db.factures.aggregate(pipeline).to_list(100)
        
        return {
            "data": [
                {
                    "niveau": r["_id"] or "Non défini",
                    "total_ventes": r["total_ventes"],
                    "quantite": r["quantite"]
                }
                for r in results
            ]
        }
    
    # ------------------------------------------------------------------------
    # TOP CLIENTS
    # ------------------------------------------------------------------------
    @router.get("/top-clients")
    async def get_top_clients(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        limit: int = Query(10, ge=1, le=50),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Top clients par chiffre d'affaires"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Agrégation par client
        pipeline = [
            {"$match": filters},
            {"$group": {
                "_id": "$client_nom",
                "total_ventes": {"$sum": "$montant_ht"},
                "nb_factures": {"$sum": 1},
                "total_qty": {"$sum": {"$sum": "$lignes.quantite"}}
            }},
            {"$sort": {"total_ventes": -1}},
            {"$limit": limit}
        ]
        
        results = await db.factures.aggregate(pipeline).to_list(limit)
        
        return {
            "data": [
                {
                    "client": r["_id"],
                    "total_ventes": r["total_ventes"],
                    "nb_factures": r["nb_factures"],
                    "quantite_totale": r.get("total_qty", 0)
                }
                for r in results
            ]
        }
    
    # ------------------------------------------------------------------------
    # TOP ARTICLES VENDUS
    # ------------------------------------------------------------------------
    @router.get("/top-articles")
    async def get_top_articles(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        limit: int = Query(20, ge=1, le=100),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Articles les plus vendus"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Agrégation par produit
        pipeline = [
            {"$match": filters},
            {"$unwind": "$lignes"},
            {"$lookup": {
                "from": "produits",
                "localField": "lignes.produit_id",
                "foreignField": "produit_id",
                "as": "produit"
            }},
            {"$unwind": {"path": "$produit", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$lignes.produit_id",
                "code_article": {"$first": "$produit.code_article"},
                "titre": {"$first": "$produit.titre"},
                "quantite_vendue": {"$sum": "$lignes.quantite"},
                "ca_total": {"$sum": "$lignes.total"}
            }},
            {"$sort": {"quantite_vendue": -1}},
            {"$limit": limit}
        ]
        
        results = await db.factures.aggregate(pipeline).to_list(limit)
        
        return {
            "data": [
                {
                    "produit_id": r["_id"],
                    "code_article": r.get("code_article", "N/A"),
                    "titre": r.get("titre", "Produit inconnu"),
                    "quantite_vendue": r["quantite_vendue"],
                    "ca_total": r["ca_total"]
                }
                for r in results
            ]
        }
    
    # ------------------------------------------------------------------------
    # ÉVOLUTION DES VENTES (PAR MOIS)
    # ------------------------------------------------------------------------
    @router.get("/evolution")
    async def get_ventes_evolution(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Évolution des ventes par mois"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Agrégation par mois
        pipeline = [
            {"$match": filters},
            {"$addFields": {
                "mois": {"$substr": ["$date_facture", 0, 7]}  # YYYY-MM
            }},
            {"$group": {
                "_id": "$mois",
                "total_ventes": {"$sum": "$montant_ht"},
                "nb_factures": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = await db.factures.aggregate(pipeline).to_list(100)
        
        return {
            "data": [
                {
                    "mois": r["_id"],
                    "total_ventes": r["total_ventes"],
                    "nb_factures": r["nb_factures"]
                }
                for r in results
            ]
        }
    
    # ------------------------------------------------------------------------
    # ANALYSE FINANCIÈRE
    # ------------------------------------------------------------------------
    @router.get("/financial")
    async def get_financial_analysis(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        """Analyse financière détaillée"""
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        filters = {}
        if date_debut:
            filters["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in filters:
                filters["date_facture"]["$lte"] = date_fin
            else:
                filters["date_facture"] = {"$lte": date_fin}
        
        # Agrégation financière
        pipeline = [
            {"$match": filters},
            {"$group": {
                "_id": None,
                "total_ht": {"$sum": "$montant_ht"},
                "total_remises": {"$sum": "$remise_montant"},
                "total_ttc": {"$sum": "$montant_ttc"},
                "total_factures": {"$sum": 1}
            }}
        ]
        
        result = await db.factures.aggregate(pipeline).to_list(1)
        financial = result[0] if result else {
            "total_ht": 0,
            "total_remises": 0,
            "total_ttc": 0,
            "total_factures": 0
        }
        
        # Total encaissé (paiements)
        pipeline_paid = [
            {"$match": {}},  # Tous les paiements
            {"$group": {"_id": None, "total_encaisse": {"$sum": "$montant"}}}
        ]
        paid_result = await db.paiements.aggregate(pipeline_paid).to_list(1)
        total_encaisse = paid_result[0]["total_encaisse"] if paid_result else 0
        
        # Total restant dû
        total_du = financial.get("total_ttc", 0) - total_encaisse
        
        return {
            "total_ht": financial.get("total_ht", 0),
            "total_remises": financial.get("total_remises", 0),
            "total_ttc": financial.get("total_ttc", 0),
            "total_encaisse": total_encaisse,
            "total_du": max(0, total_du),
            "nb_factures": financial.get("total_factures", 0)
        }
    
    return router
