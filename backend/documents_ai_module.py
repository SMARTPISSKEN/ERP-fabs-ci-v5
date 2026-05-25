"""
Module Documents AI - Gestion intelligente des documents
- Upload et parsing automatique de PDFs (BL, Factures, Commandes, Listes clients)
- Extraction automatique des données
- Analytics et rapports
- Export et partage (Print, PDF, WhatsApp)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
import re
import uuid

from fastapi import APIRouter, HTTPException, Header, Request, UploadFile, File, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger("fabsci.documents_ai")

# ============================================================================
# RBAC - Permissions
# ============================================================================
READ_ROLES = {
    "super_admin", "directeur_general", "comptable", 
    "directeur_commercial", "secretariat"
}
WRITE_ROLES = {
    "super_admin", "directeur_general", "directeur_commercial", "secretariat"
}

# ============================================================================
# TYPES DE DOCUMENTS
# ============================================================================
DOCUMENT_TYPES = {
    "BON_LIVRAISON": "Bon de Livraison",
    "FACTURE": "Facture",
    "COMMANDE": "Commande",
    "LISTE_CLIENTS": "Liste Clients",
    "AUTRE": "Autre"
}

# ============================================================================
# UTILITAIRES
# ============================================================================
def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def detect_document_type(text_content: str) -> str:
    """
    Détecte automatiquement le type de document basé sur le contenu
    """
    text_upper = text_content.upper()
    
    # Détection par référence FABS
    if re.search(r"FABS\s*\|\s*BL\s*\|", text_upper):
        return "BON_LIVRAISON"
    elif re.search(r"FABS\s*\|\s*FC\s*\|", text_upper):
        return "FACTURE"
    elif re.search(r"FABS\s*\|\s*BC\s*\|", text_upper):
        return "COMMANDE"
    
    # Détection par mots-clés
    if "BON DE LIVRAISON" in text_upper or "BON LIVRAISON" in text_upper:
        return "BON_LIVRAISON"
    elif "FACTURE" in text_upper and "CLIENT" in text_upper:
        return "FACTURE"
    elif "COMMANDE" in text_upper:
        return "COMMANDE"
    elif "LISTE" in text_upper and ("CLIENT" in text_upper or "CLIENTS" in text_upper):
        return "LISTE_CLIENTS"
    
    return "AUTRE"

def extract_reference(text_content: str, doc_type: str) -> Optional[str]:
    """
    Extrait la référence du document (FABS|XX|YY|ID)
    """
    patterns = {
        "BON_LIVRAISON": r"FABS\s*\|\s*BL\s*\|\s*(\d+)\s*\|\s*(\d+)",
        "FACTURE": r"FABS\s*\|\s*FC\s*\|\s*(\d+)\s*\|\s*(\d+)",
        "COMMANDE": r"FABS\s*\|\s*BC\s*\|\s*(\d+)\s*\|\s*(\d+)",
    }
    
    pattern = patterns.get(doc_type)
    if pattern:
        match = re.search(pattern, text_content.upper())
        if match:
            year = match.group(1)
            num = match.group(2)
            prefix = {"BON_LIVRAISON": "BL", "FACTURE": "FC", "COMMANDE": "BC"}[doc_type]
            return f"FABS|{prefix}|{year}|{num}"
    
    return None

def parse_document_content(text_content: str, doc_type: str) -> Dict[str, Any]:
    """
    Parse le contenu du document et extrait les données structurées
    """
    data = {
        "raw_text": text_content[:1000],  # Garder un extrait
        "reference": extract_reference(text_content, doc_type),
        "extracted_data": {}
    }
    
    # Extraction basique de données selon le type
    if doc_type in ["BON_LIVRAISON", "FACTURE", "COMMANDE"]:
        # Extraire date
        date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text_content)
        if date_match:
            data["extracted_data"]["date"] = date_match.group(0)
        
        # Extraire client
        client_match = re.search(r"Client\s*:\s*([^\n]+)", text_content, re.IGNORECASE)
        if client_match:
            data["extracted_data"]["client"] = client_match.group(1).strip()
        
        # Extraire représentant
        rep_match = re.search(r"Représentant\s*:\s*([^\n]+)", text_content, re.IGNORECASE)
        if rep_match:
            data["extracted_data"]["representant"] = rep_match.group(1).strip()
    
    return data

# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================
class DocumentCreate(BaseModel):
    nom_fichier: str
    type_document: str = "AUTRE"
    contenu_texte: Optional[str] = None
    donnees_extraites: Optional[Dict[str, Any]] = None
    tags: List[str] = []

class DocumentUpdate(BaseModel):
    nom_fichier: Optional[str] = None
    type_document: Optional[str] = None
    donnees_extraites: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    statut: Optional[str] = None

class DocumentOut(BaseModel):
    document_id: str
    nom_fichier: str
    type_document: str
    reference: Optional[str] = None
    statut: str
    donnees_extraites: Dict[str, Any]
    tags: List[str]
    taille_fichier: Optional[int] = None
    created_by: str
    created_at: str
    updated_at: str

class AnalyticsQuery(BaseModel):
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    type_document: Optional[str] = None
    client: Optional[str] = None

# ============================================================================
# ROUTER BUILDER
# ============================================================================
def build_documents_ai_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/documents-ai", tags=["documents-ai"])
    
    # ------------------------------------------------------------------------
    # LISTE DES DOCUMENTS
    # ------------------------------------------------------------------------
    @router.get("", response_model=Dict[str, Any])
    async def list_documents(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        type_document: Optional[str] = None,
        statut: Optional[str] = None,
        recherche: Optional[str] = None,
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        # Construire les filtres
        filters = {}
        if type_document:
            filters["type_document"] = type_document
        if statut:
            filters["statut"] = statut
        if recherche:
            filters["$or"] = [
                {"nom_fichier": {"$regex": recherche, "$options": "i"}},
                {"reference": {"$regex": recherche, "$options": "i"}},
                {"donnees_extraites.client": {"$regex": recherche, "$options": "i"}}
            ]
        
        # Compter le total
        total = await db.documents_intelligents.count_documents(filters)
        
        # Récupérer les documents
        skip = (page - 1) * limit
        cursor = db.documents_intelligents.find(filters, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        return {
            "items": [DocumentOut(**doc) for doc in documents],
            "total": total,
            "page": page,
            "page_size": limit,
            "total_pages": (total + limit - 1) // limit
        }
    
    # ------------------------------------------------------------------------
    # DÉTAIL D'UN DOCUMENT
    # ------------------------------------------------------------------------
    @router.get("/{document_id}", response_model=DocumentOut)
    async def get_document(
        document_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None)
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        doc = await db.documents_intelligents.find_one({"document_id": document_id}, {"_id": 0})
        _ensure(doc is not None, 404, "Document introuvable")
        
        return DocumentOut(**doc)
    
    # ------------------------------------------------------------------------
    # CRÉER UN DOCUMENT (Upload simulé pour l'instant)
    # ------------------------------------------------------------------------
    @router.post("", response_model=DocumentOut)
    async def create_document(
        data: DocumentCreate,
        request: Request,
        authorization: Optional[str] = Header(default=None)
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")
        
        now = _now_iso()
        
        # Détecter le type automatiquement si contenu fourni
        if data.contenu_texte and data.type_document == "AUTRE":
            data.type_document = detect_document_type(data.contenu_texte)
        
        # Parser le contenu si fourni
        parsed_data = {}
        if data.contenu_texte:
            parsed_data = parse_document_content(data.contenu_texte, data.type_document)
        
        document = {
            "document_id": str(uuid.uuid4()),
            "nom_fichier": data.nom_fichier,
            "type_document": data.type_document,
            "reference": parsed_data.get("reference"),
            "statut": "traite" if data.contenu_texte else "en_attente",
            "donnees_extraites": data.donnees_extraites or parsed_data.get("extracted_data", {}),
            "tags": data.tags,
            "taille_fichier": len(data.contenu_texte) if data.contenu_texte else 0,
            "created_by": me["user_id"],
            "created_at": now,
            "updated_at": now
        }
        
        await db.documents_intelligents.insert_one(document)
        
        logger.info(f"Document créé: {document['document_id']} par {me['email']}")
        return DocumentOut(**document)
    
    # ------------------------------------------------------------------------
    # METTRE À JOUR UN DOCUMENT
    # ------------------------------------------------------------------------
    @router.patch("/{document_id}", response_model=DocumentOut)
    async def update_document(
        document_id: str,
        data: DocumentUpdate,
        request: Request,
        authorization: Optional[str] = Header(default=None)
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")
        
        doc = await db.documents_intelligents.find_one({"document_id": document_id}, {"_id": 0})
        _ensure(doc is not None, 404, "Document introuvable")
        
        # Préparer les mises à jour
        updates = {"updated_at": _now_iso()}
        if data.nom_fichier is not None:
            updates["nom_fichier"] = data.nom_fichier
        if data.type_document is not None:
            updates["type_document"] = data.type_document
        if data.donnees_extraites is not None:
            updates["donnees_extraites"] = data.donnees_extraites
        if data.tags is not None:
            updates["tags"] = data.tags
        if data.statut is not None:
            updates["statut"] = data.statut
        
        await db.documents_intelligents.update_one(
            {"document_id": document_id},
            {"$set": updates}
        )
        
        # Récupérer le document mis à jour
        updated_doc = await db.documents_intelligents.find_one({"document_id": document_id}, {"_id": 0})
        return DocumentOut(**updated_doc)
    
    # ------------------------------------------------------------------------
    # SUPPRIMER UN DOCUMENT
    # ------------------------------------------------------------------------
    @router.delete("/{document_id}")
    async def delete_document(
        document_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None)
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")
        
        result = await db.documents_intelligents.delete_one({"document_id": document_id})
        _ensure(result.deleted_count > 0, 404, "Document introuvable")
        
        logger.info(f"Document supprimé: {document_id} par {me['email']}")
        return {"message": "Document supprimé avec succès"}
    
    # ------------------------------------------------------------------------
    # ANALYTICS - DASHBOARD
    # ------------------------------------------------------------------------
    @router.get("/analytics/dashboard", response_model=Dict[str, Any])
    async def get_analytics_dashboard(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        # Filtres de date
        filters = {}
        if date_debut:
            filters["created_at"] = {"$gte": date_debut}
        if date_fin:
            if "created_at" in filters:
                filters["created_at"]["$lte"] = date_fin
            else:
                filters["created_at"] = {"$lte": date_fin}
        
        # Statistiques globales
        total_documents = await db.documents_intelligents.count_documents(filters)
        
        # Répartition par type
        pipeline_type = [
            {"$match": filters},
            {"$group": {"_id": "$type_document", "count": {"$sum": 1}}}
        ]
        types_repartition = await db.documents_intelligents.aggregate(pipeline_type).to_list(100)
        
        # Répartition par statut
        pipeline_statut = [
            {"$match": filters},
            {"$group": {"_id": "$statut", "count": {"$sum": 1}}}
        ]
        statuts_repartition = await db.documents_intelligents.aggregate(pipeline_statut).to_list(100)
        
        # Documents récents
        recent_docs = await db.documents_intelligents.find(
            filters, {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(10)
        
        return {
            "total_documents": total_documents,
            "repartition_par_type": [
                {"type": item["_id"], "count": item["count"]} 
                for item in types_repartition
            ],
            "repartition_par_statut": [
                {"statut": item["_id"], "count": item["count"]} 
                for item in statuts_repartition
            ],
            "documents_recents": recent_docs[:5]
        }
    
    # ------------------------------------------------------------------------
    # TYPES DE DOCUMENTS DISPONIBLES
    # ------------------------------------------------------------------------
    @router.get("/meta/types")
    async def get_document_types(
        request: Request,
        authorization: Optional[str] = Header(default=None)
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        
        return {
            "types": [
                {"code": code, "label": label}
                for code, label in DOCUMENT_TYPES.items()
            ]
        }
    
    return router

# ============================================================================
# SEED DOCUMENTS DE DÉMO
# ============================================================================
async def seed_documents_demo(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed quelques documents de démonstration"""
    count = await db.documents_intelligents.count_documents({})
    if count > 0:
        return 0
    
    now = _now_iso()
    
    documents = [
        {
            "document_id": str(uuid.uuid4()),
            "nom_fichier": "BL_LYCEE_ABENGOUROU_20260107.pdf",
            "type_document": "BON_LIVRAISON",
            "reference": "FABS|BL|26|15",
            "statut": "traite",
            "donnees_extraites": {
                "date": "07/01/2026",
                "client": "LM ABENGOUROU",
                "type_client": "LYCEE",
                "representant": "M.OUATTARA",
                "telephone": "07 07 50 98 40",
                "commande": "FABS|BC|26|15",
                "articles": [
                    {
                        "classe": "Terminale",
                        "code": "FABS-C178",
                        "reference": "TEST PHYSIQUE-CHIMIE BAC",
                        "quantite": 30
                    }
                ]
            },
            "tags": ["lycee", "abengourou", "2026"],
            "taille_fichier": 37300,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now
        },
        {
            "document_id": str(uuid.uuid4()),
            "nom_fichier": "FC_LYCEE_ABENGOUROU_20260107.pdf",
            "type_document": "FACTURE",
            "reference": "FABS|FC|26|15",
            "statut": "traite",
            "donnees_extraites": {
                "date": "07/01/2026",
                "client": "LM ABENGOUROU",
                "representant": "M.OUATTARA",
                "articles": [
                    {
                        "code": "FABS-C178",
                        "reference": "TEST PHYSIQUE-CHIMIE BAC",
                        "quantite": 30,
                        "prix_unitaire": 4000,
                        "total": 120000
                    }
                ],
                "total_vente": 120000,
                "remise_pct": 37.50,
                "remise_montant": 45000,
                "montant_ht": 75000,
                "solde_du": 75000
            },
            "tags": ["facture", "lycee", "2026"],
            "taille_fichier": 42300,
            "created_by": user_id,
            "created_at": now,
            "updated_at": now
        }
    ]
    
    await db.documents_intelligents.insert_many(documents)
    return len(documents)
