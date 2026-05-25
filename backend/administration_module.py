"""
Module Utilisateurs & Paramètres — Sprint 13
- CRUD utilisateurs complet (super_admin uniquement)
- Gestion rôles et permissions
- Paramètres système (entreprise, banques, TVA, etc.)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, EmailStr

logger = logging.getLogger("fabsci.administration")

ADMIN_ROLES = {"super_admin"}
# PRD : seul le super_admin a accès au module Utilisateurs (le DG en est exclu)
READ_ROLES = {"super_admin"}

ROLES_DISPONIBLES = [
    "super_admin",
    "directeur_general",
    "comptable",
    "directeur_commercial",
    "gestionnaire_stock",
    "responsable_magasinier",
    "secretariat",
    "service_logistique",
]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# UTILISATEURS
# ---------------------------------------------------------------------------
class UtilisateurUpdate(BaseModel):
    nom_complet: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None


class UtilisateurOut(BaseModel):
    user_id: str
    email: EmailStr
    nom_complet: str
    role: str
    actif: bool
    picture: Optional[str] = None
    created_at: str
    updated_at: str


def build_utilisateurs_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])

    @router.get("", response_model=List[UtilisateurOut])
    async def list_utilisateurs(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        actif: Optional[bool] = None,
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if actif is not None:
            filters["actif"] = actif

        cursor = db.users.find(filters, {"_id": 0}).sort("created_at", -1)
        docs = await cursor.to_list(200)
        
        return [UtilisateurOut(**d) for d in docs]

    @router.get("/{user_id}", response_model=UtilisateurOut)
    async def get_utilisateur(
        user_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        _ensure(user is not None, 404, "Utilisateur introuvable")
        
        return UtilisateurOut(**user)

    @router.patch("/{user_id}", response_model=UtilisateurOut)
    async def update_utilisateur(
        user_id: str,
        payload: UtilisateurUpdate,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in ADMIN_ROLES, 403, "Accès refusé - super_admin requis")

        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        _ensure(user is not None, 404, "Utilisateur introuvable")

        updates = {"updated_at": _now_iso()}
        
        if payload.nom_complet is not None:
            updates["nom_complet"] = payload.nom_complet
        
        if payload.role is not None:
            _ensure(payload.role in ROLES_DISPONIBLES, 400, f"Rôle invalide. Valeurs: {ROLES_DISPONIBLES}")
            updates["role"] = payload.role
        
        if payload.actif is not None:
            # Prevent deactivating last super_admin
            if not payload.actif and user["role"] == "super_admin":
                count_admins = await db.users.count_documents({"role": "super_admin", "actif": True})
                _ensure(count_admins > 1, 400, "Impossible de désactiver le dernier super_admin")
            updates["actif"] = payload.actif

        await db.users.update_one({"user_id": user_id}, {"$set": updates})
        
        updated = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        return UtilisateurOut(**updated)

    @router.delete("/{user_id}")
    async def delete_utilisateur(
        user_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in ADMIN_ROLES, 403, "Accès refusé - super_admin requis")

        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        _ensure(user is not None, 404, "Utilisateur introuvable")
        
        # Prevent deleting last super_admin
        if user["role"] == "super_admin":
            count_admins = await db.users.count_documents({"role": "super_admin", "actif": True})
            _ensure(count_admins > 1, 400, "Impossible de supprimer le dernier super_admin")
        
        # Soft delete
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"actif": False, "updated_at": _now_iso()}}
        )
        
        return {"message": "Utilisateur désactivé avec succès"}

    return router


# ---------------------------------------------------------------------------
# PARAMETRES
# ---------------------------------------------------------------------------
class ParametreUpdate(BaseModel):
    valeur: str


class ParametreOut(BaseModel):
    cle: str
    valeur: str
    description: Optional[str] = None
    updated_at: str


def build_parametres_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/parametres", tags=["parametres"])

    @router.get("", response_model=List[ParametreOut])
    async def list_parametres(
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        cursor = db.parametres.find({}, {"_id": 0}).sort("cle", 1)
        docs = await cursor.to_list(100)
        
        return [ParametreOut(**d) for d in docs]

    @router.get("/{cle}", response_model=ParametreOut)
    async def get_parametre(
        cle: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        param = await db.parametres.find_one({"cle": cle}, {"_id": 0})
        _ensure(param is not None, 404, "Paramètre introuvable")
        
        return ParametreOut(**param)

    @router.patch("/{cle}", response_model=ParametreOut)
    async def update_parametre(
        cle: str,
        payload: ParametreUpdate,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in ADMIN_ROLES, 403, "Accès refusé - super_admin requis")

        param = await db.parametres.find_one({"cle": cle}, {"_id": 0})
        _ensure(param is not None, 404, "Paramètre introuvable")

        now = _now_iso()
        await db.parametres.update_one(
            {"cle": cle},
            {"$set": {"valeur": payload.valeur, "updated_at": now}}
        )
        
        updated = await db.parametres.find_one({"cle": cle}, {"_id": 0})
        return ParametreOut(**updated)

    return router


async def seed_parametres(db: AsyncIOMotorDatabase) -> int:
    """Seed default parametres"""
    existing = await db.parametres.count_documents({})
    if existing > 0:
        return 0
    
    now = _now_iso()
    
    parametres_default = [
        {
            "cle": "entreprise_nom",
            "valeur": "EDITIONS FABS-CI",
            "description": "Nom de l'entreprise",
            "updated_at": now
        },
        {
            "cle": "entreprise_slogan",
            "valeur": "Les livres sont des fenêtres par lesquelles on regarde le monde",
            "description": "Slogan de l'entreprise",
            "updated_at": now
        },
        {
            "cle": "entreprise_telephone",
            "valeur": "+225 XX XX XX XX XX",
            "description": "Téléphone principal",
            "updated_at": now
        },
        {
            "cle": "entreprise_email",
            "valeur": "contact@editionsfabsci.com",
            "description": "Email de contact",
            "updated_at": now
        },
        {
            "cle": "entreprise_adresse",
            "valeur": "Abidjan, Côte d'Ivoire",
            "description": "Adresse postale",
            "updated_at": now
        },
        {
            "cle": "tva_taux",
            "valeur": "18",
            "description": "Taux TVA en pourcentage",
            "updated_at": now
        },
        {
            "cle": "banque_principale",
            "valeur": "CORIS BANK",
            "description": "Nom de la banque principale",
            "updated_at": now
        },
        {
            "cle": "banque_iban",
            "valeur": "CI XX XXXX XXXX XXXX XXXX XXXX",
            "description": "IBAN compte principal",
            "updated_at": now
        },
        {
            "cle": "seuil_validation_dg",
            "valeur": "500000",
            "description": "Seuil montant pour validation DG (FCFA)",
            "updated_at": now
        },
    ]
    
    await db.parametres.insert_many(parametres_default)
    await db.parametres.create_index("cle", unique=True)
    
    return len(parametres_default)
