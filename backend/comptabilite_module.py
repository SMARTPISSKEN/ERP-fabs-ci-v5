"""
Module Comptabilité — Sprint 12
- Génération écritures comptables depuis factures/paiements
- Suivi créances clients
- Journaux comptables (ventes, banque, caisse)
- États comptables (balance, grand livre)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger("fabsci.comptabilite")

READ_ROLES = {"super_admin", "directeur_general", "comptable"}
WRITE_ROLES = {"super_admin", "comptable"}

TypeJournal = Literal["ventes", "achats", "banque", "caisse", "operations_diverses"]


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EcritureComptableIn(BaseModel):
    journal: TypeJournal
    date_ecriture: str
    compte: str  # Numéro de compte
    libelle: str
    debit: float = Field(default=0, ge=0)
    credit: float = Field(default=0, ge=0)
    piece_reference: Optional[str] = None  # Reference facture/paiement


class EcritureComptableOut(BaseModel):
    ecriture_id: str
    journal: TypeJournal
    date_ecriture: str
    compte: str
    libelle: str
    debit: float
    credit: float
    piece_reference: Optional[str] = None
    created_by: str
    created_at: str


class CreanceClient(BaseModel):
    client_id: str
    client_nom: str
    montant_total_factures: float
    montant_total_paye: float
    montant_restant: float
    nombre_factures: int


def build_comptabilite_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/comptabilite", tags=["comptabilite"])

    # ---------- ECRITURES COMPTABLES ----------
    @router.get("/ecritures", response_model=List[EcritureComptableOut])
    async def list_ecritures(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        journal: Optional[TypeJournal] = None,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
        limit: int = Query(100, ge=1, le=500),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if journal:
            filters["journal"] = journal
        if date_debut or date_fin:
            date_filter = {}
            if date_debut:
                date_filter["$gte"] = date_debut
            if date_fin:
                date_filter["$lte"] = date_fin
            filters["date_ecriture"] = date_filter

        cursor = db.ecritures_comptables.find(filters, {"_id": 0}).sort("date_ecriture", -1).limit(limit)
        docs = await cursor.to_list(limit)
        
        return [EcritureComptableOut(**d) for d in docs]

    @router.post("/ecritures", response_model=EcritureComptableOut, status_code=201)
    async def create_ecriture(
        payload: EcritureComptableIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Accès refusé")

        _ensure(payload.debit > 0 or payload.credit > 0, 400, "Débit ou crédit doit être > 0")
        _ensure(not (payload.debit > 0 and payload.credit > 0), 400, "Débit et crédit ne peuvent pas être tous les deux > 0")

        ecriture_id = f"ecr_{uuid.uuid4().hex[:12]}"
        now = _now_iso()

        ecriture_doc = {
            "ecriture_id": ecriture_id,
            "journal": payload.journal,
            "date_ecriture": payload.date_ecriture,
            "compte": payload.compte,
            "libelle": payload.libelle,
            "debit": payload.debit,
            "credit": payload.credit,
            "piece_reference": payload.piece_reference,
            "created_by": me["user_id"],
            "created_at": now,
        }
        await db.ecritures_comptables.insert_one(ecriture_doc)

        return EcritureComptableOut(**ecriture_doc)

    # ---------- CREANCES CLIENTS ----------
    @router.get("/creances", response_model=List[CreanceClient])
    async def get_creances_clients(
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        # Aggregate factures par client
        pipeline = [
            {
                "$match": {
                    "type_facture": "facture",
                    "statut": {"$in": ["emise", "partiellement_payee"]}
                }
            },
            {
                "$group": {
                    "_id": "$client_id",
                    "montant_total_factures": {"$sum": "$montant_ttc"},
                    "montant_total_paye": {"$sum": "$montant_regle"},
                    "montant_restant": {"$sum": "$montant_restant"},
                    "nombre_factures": {"$sum": 1}
                }
            }
        ]
        
        cursor = db.factures.aggregate(pipeline)
        creances = await cursor.to_list(200)
        
        # Enrich with client names
        result = []
        for creance in creances:
            client = await db.clients.find_one({"client_id": creance["_id"]}, {"_id": 0, "nom": 1})
            if client:
                result.append(CreanceClient(
                    client_id=creance["_id"],
                    client_nom=client["nom"],
                    montant_total_factures=round(creance["montant_total_factures"], 2),
                    montant_total_paye=round(creance["montant_total_paye"], 2),
                    montant_restant=round(creance["montant_restant"], 2),
                    nombre_factures=creance["nombre_factures"]
                ))
        
        # Sort by montant_restant desc
        result.sort(key=lambda x: x.montant_restant, reverse=True)
        
        return result

    # ---------- BALANCE ----------
    @router.get("/balance")
    async def get_balance(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")

        filters = {}
        if date_debut or date_fin:
            date_filter = {}
            if date_debut:
                date_filter["$gte"] = date_debut
            if date_fin:
                date_filter["$lte"] = date_fin
            filters["date_ecriture"] = date_filter

        # Aggregate by compte
        pipeline = [
            {"$match": filters} if filters else {"$match": {}},
            {
                "$group": {
                    "_id": "$compte",
                    "total_debit": {"$sum": "$debit"},
                    "total_credit": {"$sum": "$credit"}
                }
            }
        ]
        
        cursor = db.ecritures_comptables.aggregate(pipeline)
        balances = await cursor.to_list(500)
        
        result = []
        for balance in balances:
            solde = balance["total_debit"] - balance["total_credit"]
            result.append({
                "compte": balance["_id"],
                "total_debit": round(balance["total_debit"], 2),
                "total_credit": round(balance["total_credit"], 2),
                "solde": round(solde, 2)
            })
        
        return result

    return router


async def seed_comptabilite(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Seed indexes"""
    await db.ecritures_comptables.create_index("ecriture_id", unique=True)
    await db.ecritures_comptables.create_index("journal")
    await db.ecritures_comptables.create_index("date_ecriture")
    await db.ecritures_comptables.create_index("compte")
    
    return 0
