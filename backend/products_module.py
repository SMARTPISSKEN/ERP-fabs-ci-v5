"""
Module Produits — Sprint 5
- CRUD complet sur la collection MongoDB `produits`
- Référence auto-incrémentée FABS-PRD-XXXX
- RBAC :
    READ/WRITE = {super_admin, DG, commercial, gestionnaire_stock, magasinier} (matrice Sprint 2)
    prix_achat visible UNIQUEMENT par {super_admin, DG, comptable}
- Soft delete (`actif=False`)
- Alertes stock pour le dashboard (stock_actuel <= stock_minimum)
- BONUS — recherche ISBN via Google Books API (auto-complétion titre/auteur/collection)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, List
import re
import uuid
import logging

import httpx
from fastapi import APIRouter, HTTPException, Header, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("fabsci.produits")

READ_ROLES = {
    "super_admin", "directeur_general", "directeur_commercial",
    "gestionnaire_stock", "responsable_magasinier",
}
WRITE_ROLES = READ_ROLES  # same set per Sprint 2 matrix
FINANCIAL_ROLES = {"super_admin", "directeur_general", "comptable"}  # see prix_achat

Categorie = Literal["maternelle", "primaire", "premier_cycle", "second_cycle", "litterature"]
CATEGORIE_LABELS = {
    "maternelle":     "Maternelle",
    "primaire":       "Primaire",
    "premier_cycle":  "Premier cycle",
    "second_cycle":   "Second cycle",
    "litterature":    "Littérature",
}


def _ensure(condition: bool, status: int, detail: str) -> None:
    if not condition:
        raise HTTPException(status_code=status, detail=detail)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def next_product_reference(db: AsyncIOMotorDatabase) -> str:
    doc = await db.counters.find_one_and_update(
        {"_id": "produits"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc["seq"]
    return f"FABS-PRD-{seq:04d}"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ProductIn(BaseModel):
    titre: str = Field(..., min_length=2, max_length=200)
    auteur: Optional[str] = Field(default=None, max_length=120)
    collection: Optional[str] = Field(default=None, max_length=120)
    categorie: Categorie
    niveau_scolaire: Optional[str] = Field(default=None, max_length=80)
    isbn: Optional[str] = Field(default=None, max_length=20)
    prix_achat: float = Field(default=0, ge=0)
    prix_vente: float = Field(..., gt=0)
    stock_actuel: int = Field(default=0, ge=0)
    stock_minimum: int = Field(default=10, ge=0)

    @field_validator("titre", "auteur", "collection", "isbn", "niveau_scolaire", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ProductPatch(BaseModel):
    titre: Optional[str] = Field(default=None, min_length=2, max_length=200)
    auteur: Optional[str] = Field(default=None, max_length=120)
    collection: Optional[str] = Field(default=None, max_length=120)
    categorie: Optional[Categorie] = None
    niveau_scolaire: Optional[str] = Field(default=None, max_length=80)
    isbn: Optional[str] = Field(default=None, max_length=20)
    prix_achat: Optional[float] = Field(default=None, ge=0)
    prix_vente: Optional[float] = Field(default=None, gt=0)
    stock_actuel: Optional[int] = Field(default=None, ge=0)
    stock_minimum: Optional[int] = Field(default=None, ge=0)
    actif: Optional[bool] = None


class ProductOut(BaseModel):
    product_id: str
    reference: str
    titre: str
    auteur: Optional[str] = None
    collection: Optional[str] = None
    categorie: Categorie
    niveau_scolaire: Optional[str] = None
    isbn: Optional[str] = None
    prix_achat: Optional[float] = None  # null if requester is not in FINANCIAL_ROLES
    prix_vente: float
    stock_actuel: int
    stock_minimum: int
    statut_stock: str  # ok | alerte | rupture
    actif: bool
    created_at: str
    updated_at: str


class ProductListOut(BaseModel):
    items: List[ProductOut]
    total: int
    page: int
    page_size: int


class IsbnLookupOut(BaseModel):
    isbn: str
    found: bool
    titre: Optional[str] = None
    auteur: Optional[str] = None
    collection: Optional[str] = None
    categorie: Optional[Categorie] = None
    raw_source: Optional[str] = None  # e.g. 'google_books'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def compute_stock_status(stock_actuel: int, stock_minimum: int) -> str:
    if stock_actuel <= 0:
        return "rupture"
    if stock_actuel <= stock_minimum:
        return "alerte"
    return "ok"


def project_product(doc: dict, *, see_prix_achat: bool) -> dict:
    if not doc:
        return doc
    d = {k: v for k, v in doc.items() if k != "_id"}
    d["statut_stock"] = compute_stock_status(d.get("stock_actuel", 0), d.get("stock_minimum", 0))
    if not see_prix_achat:
        d["prix_achat"] = None
    return d


# ---------------------------------------------------------------------------
# Google Books lookup (no API key required for /volumes search)
# ---------------------------------------------------------------------------
async def _lookup_isbn_google(isbn: str) -> Optional[dict]:
    isbn_clean = re.sub(r"[^0-9Xx]", "", isbn or "")
    if not isbn_clean:
        return None
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": f"isbn:{isbn_clean}", "maxResults": 1}
    try:
        async with httpx.AsyncClient(timeout=8.0) as http:
            r = await http.get(url, params=params)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data.get("items") or []
        if not items:
            return None
        info = items[0].get("volumeInfo") or {}
        return {
            "titre": info.get("title"),
            "auteur": ", ".join(info.get("authors") or []) or None,
            "collection": info.get("publisher"),
        }
    except httpx.HTTPError as exc:
        logger.warning("Google Books lookup failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------
def build_products_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/produits", tags=["produits"])

    # ---- LIST ------------------------------------------------------------
    @router.get("", response_model=ProductListOut)
    async def list_products(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        q: Optional[str] = Query(default=None, description="Recherche titre / référence / ISBN"),
        categorie: Optional[Categorie] = None,
        niveau_scolaire: Optional[str] = None,
        statut_stock: Optional[Literal["ok", "alerte", "rupture"]] = None,
        actif: Optional[bool] = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Module Produits non accessible à votre rôle")

        filt: dict = {}
        if categorie:
            filt["categorie"] = categorie
        if niveau_scolaire:
            filt["niveau_scolaire"] = {"$regex": f"^{re.escape(niveau_scolaire)}", "$options": "i"}
        if actif is not None:
            filt["actif"] = actif
        if q:
            esc = re.escape(q)
            filt["$or"] = [
                {"titre":     {"$regex": esc, "$options": "i"}},
                {"reference": {"$regex": esc, "$options": "i"}},
                {"isbn":      {"$regex": esc, "$options": "i"}},
                {"auteur":    {"$regex": esc, "$options": "i"}},
            ]

        # statut_stock is computed → translate to a Mongo filter when possible
        if statut_stock == "rupture":
            filt["stock_actuel"] = {"$lte": 0}
        elif statut_stock == "alerte":
            # stock between 1 and stock_minimum inclusive
            filt["$expr"] = {
                "$and": [
                    {"$gt": ["$stock_actuel", 0]},
                    {"$lte": ["$stock_actuel", "$stock_minimum"]},
                ]
            }
        elif statut_stock == "ok":
            filt["$expr"] = {"$gt": ["$stock_actuel", "$stock_minimum"]}

        see_prix_achat = me["role"] in FINANCIAL_ROLES
        total = await db.produits.count_documents(filt)
        cursor = (
            db.produits.find(filt, {"_id": 0})
            .sort([("reference", 1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        items = [ProductOut(**project_product(d, see_prix_achat=see_prix_achat)) async for d in cursor]
        return ProductListOut(items=items, total=total, page=page, page_size=page_size)

    # ---- ALERTES STOCK ---------------------------------------------------
    @router.get("/alertes-stock")
    async def alertes_stock(
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        # super_admin/DG/stock/magasinier can fetch (dashboard widget)
        allowed = READ_ROLES | {"comptable", "secretariat"}  # tolerant for dashboard usage
        _ensure(me["role"] in allowed, 403, "Accès refusé")
        cursor = db.produits.find(
            {
                "actif": True,
                "$expr": {"$lte": ["$stock_actuel", "$stock_minimum"]},
            },
            {"_id": 0, "product_id": 1, "reference": 1, "titre": 1, "stock_actuel": 1, "stock_minimum": 1, "categorie": 1},
        ).sort([("stock_actuel", 1)]).limit(50)
        items = [d async for d in cursor]
        rupture = sum(1 for i in items if i["stock_actuel"] <= 0)
        alerte = sum(1 for i in items if 0 < i["stock_actuel"] <= i["stock_minimum"])
        return {"items": items, "total": len(items), "rupture": rupture, "alerte": alerte}

    # ---- ISBN LOOKUP -----------------------------------------------------
    @router.get("/lookup-isbn", response_model=IsbnLookupOut)
    async def lookup_isbn(
        isbn: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Action non autorisée")
        if not isbn or len(re.sub(r"\D", "", isbn)) < 8:
            raise HTTPException(status_code=400, detail="ISBN invalide")
        info = await _lookup_isbn_google(isbn)
        if not info:
            return IsbnLookupOut(isbn=isbn, found=False)
        # Naive category guess from publisher/title keywords
        guessed_cat: Optional[Categorie] = None
        text = " ".join(filter(None, [info.get("titre"), info.get("collection")])).lower()
        if any(k in text for k in ["mater", "ms ", " ps "]):
            guessed_cat = "maternelle"
        elif any(k in text for k in ["cp1", "cp2", "ce1", "ce2", "cm1", "cm2", "primaire"]):
            guessed_cat = "primaire"
        elif any(k in text for k in ["6e", "5e", "4e", "3e", "premier cycle", "college"]):
            guessed_cat = "premier_cycle"
        elif any(k in text for k in ["2nde", "1ère", "terminale", "second cycle", "lycee"]):
            guessed_cat = "second_cycle"
        elif any(k in text for k in ["roman", "litteratur", "poesie", "theatre"]):
            guessed_cat = "litterature"
        return IsbnLookupOut(
            isbn=isbn,
            found=True,
            titre=info.get("titre"),
            auteur=info.get("auteur"),
            collection=info.get("collection"),
            categorie=guessed_cat,
            raw_source="google_books",
        )

    # ---- GET -------------------------------------------------------------
    @router.get("/{product_id}", response_model=ProductOut)
    async def get_product(
        product_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in READ_ROLES, 403, "Accès refusé")
        doc = await db.produits.find_one({"product_id": product_id}, {"_id": 0})
        _ensure(doc is not None, 404, "Produit introuvable")
        return ProductOut(**project_product(doc, see_prix_achat=me["role"] in FINANCIAL_ROLES))

    # ---- CREATE ----------------------------------------------------------
    @router.post("", response_model=ProductOut, status_code=201)
    async def create_product(
        payload: ProductIn,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Création non autorisée pour votre rôle")
        doc = {
            "product_id": f"prd_{uuid.uuid4().hex[:12]}",
            "reference": await next_product_reference(db),
            **payload.model_dump(),
            "actif": True,
            "created_by": me["user_id"],
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await db.produits.insert_one(doc)
        return ProductOut(**project_product(doc, see_prix_achat=me["role"] in FINANCIAL_ROLES))

    # ---- UPDATE ----------------------------------------------------------
    @router.patch("/{product_id}", response_model=ProductOut)
    async def update_product(
        product_id: str,
        payload: ProductPatch,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Modification non autorisée")
        updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="Aucune modification fournie")
        updates["updated_at"] = _now_iso()
        result = await db.produits.find_one_and_update(
            {"product_id": product_id},
            {"$set": updates},
            return_document=True,
        )
        _ensure(result is not None, 404, "Produit introuvable")
        return ProductOut(**project_product(result, see_prix_achat=me["role"] in FINANCIAL_ROLES))

    # ---- SOFT DELETE -----------------------------------------------------
    @router.delete("/{product_id}", response_model=ProductOut)
    async def disable_product(
        product_id: str,
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ):
        me = await resolve_user(request, authorization)
        _ensure(me["role"] in WRITE_ROLES, 403, "Désactivation non autorisée")
        result = await db.produits.find_one_and_update(
            {"product_id": product_id},
            {"$set": {"actif": False, "updated_at": _now_iso()}},
            return_document=True,
        )
        _ensure(result is not None, 404, "Produit introuvable")
        return ProductOut(**project_product(result, see_prix_achat=me["role"] in FINANCIAL_ROLES))

    return router


# ---------------------------------------------------------------------------
# Seed — 35 livres scolaires Côte d'Ivoire
# ---------------------------------------------------------------------------
SEED_PRODUCTS: List[dict] = [
    # Maternelle - Grande section
    {"code": "FABS-CI79", "titre": "MON CAHIER DE PRÉLECTURE CP1", "niveau": "Grande section", "categorie": "Maternelle", "prix_vente": 2000, "stock_actuel": 150},
    
    # Primaire - CP1 à CM2
    {"code": "FABS-CI76", "titre": "MON CAHIER D'ÉCRITURE CP1", "niveau": "CP1", "categorie": "Primaire", "prix_vente": 2000, "stock_actuel": 200},
    {"code": "FABS-CI83", "titre": "MON CAHIER D'ÉCRITURE CP2", "niveau": "CP2", "categorie": "Primaire", "prix_vente": 2000, "stock_actuel": 200},
    {"code": "FABS-CI90", "titre": "MON CAHIER DÉCRITURE CE1", "niveau": "CE1", "categorie": "Primaire", "prix_vente": 2000, "stock_actuel": 180},
    {"code": "FABS-CI06", "titre": "MON CAHIER D'ÉCRITURE CE2", "niveau": "CE2", "categorie": "Primaire", "prix_vente": 2000, "stock_actuel": 180},
    {"code": "FABS-CI64", "titre": "MON CAHIER D'ÉCRITURE CM1", "niveau": "CM1", "categorie": "Primaire", "prix_vente": 2000, "stock_actuel": 170},
    {"code": "FABS-CI82", "titre": "MON CAHIER D'ÉCRITURE CM2", "niveau": "CM2", "categorie": "Primaire", "prix_vente": 2000, "stock_actuel": 170},
    
    # Premier Cycle - 6ème
    {"code": "FABS-CI24", "titre": "ACTIVITE PRATIQUE DE LA FLUTE A BEC SOPRANO 6ÈME", "niveau": "6ème", "categorie": "Premier cycle", "prix_vente": 2000, "stock_actuel": 120},
    {"code": "FABS-CI68", "titre": "MON CAHIER D'ACTIVITÉS D'ÉDUCATION MUSICALE 6IEME", "niveau": "6ème", "categorie": "Premier cycle", "prix_vente": 2000, "stock_actuel": 120},
    {"code": "FABS-CI31", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 6ÈME", "niveau": "6ème", "categorie": "Premier cycle", "prix_vente": 3000, "stock_actuel": 100},
    
    # Premier Cycle - 5ème
    {"code": "FABS-CI61", "titre": "ACTIVITE PRATIQUE DE LA FLUTE A BEC SOPRANO 5ÈME", "niveau": "5ème", "categorie": "Premier cycle", "prix_vente": 2500, "stock_actuel": 110},
    {"code": "FABS-CI75", "titre": "MON CAHIER D'ACTIVITE D'EDUCATION MUSICALE 5EME", "niveau": "5ème", "categorie": "Premier cycle", "prix_vente": 2000, "stock_actuel": 110},
    {"code": "FABS-CI48", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 5ÈME", "niveau": "5ème", "categorie": "Premier cycle", "prix_vente": 3000, "stock_actuel": 95},
    
    # Premier Cycle - 4ème
    {"code": "FABS-CI07", "titre": "MON CAHIER D'ACTIVITE D'EDUCATION MUSICALE 4ÈME", "niveau": "4ème", "categorie": "Premier cycle", "prix_vente": 2000, "stock_actuel": 105},
    {"code": "FABS-CI86", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'EDUCATION MUSICALE 4EME", "niveau": "4ème", "categorie": "Premier cycle", "prix_vente": 3000, "stock_actuel": 90},
    
    # Premier Cycle - 3ème (BEPC)
    {"code": "FABS-CI05", "titre": "MEMO HISTOIRE-GEOGRAPHIE BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix_vente": 2500, "stock_actuel": 130},
    {"code": "FABS-CI20", "titre": "MON CAHIER D'ACTIVITE D'EDUCATION MUSICALE 3ÈME", "niveau": "3ème", "categorie": "Premier cycle", "prix_vente": 2000, "stock_actuel": 100},
    {"code": "FABS-CI32", "titre": "TEST SVT - BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix_vente": 3000, "stock_actuel": 120},
    {"code": "FABS-CI25", "titre": "TEST FRANÇAIS BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix_vente": 3500, "stock_actuel": 125},
    {"code": "FABS-CI93", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 3ÈME", "niveau": "3ème", "categorie": "Premier cycle", "prix_vente": 3000, "stock_actuel": 85},
    {"code": "FABS-CI18", "titre": "TEST PHYSIQUE-CHIMIE BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix_vente": 3000, "stock_actuel": 115},
    
    # Second Cycle - 2nde
    {"code": "FABS-CI33", "titre": "SACERDOCE", "niveau": "2nde", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 80},
    {"code": "FABS-CI17", "titre": "MON CAHIER DE COURS ET D'ACTIVITES D'EDUCATION MUSICALE 2ND", "niveau": "2nde", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 75},
    
    # Second Cycle - 1ère
    {"code": "FABS-CI85", "titre": "CAHIER DE COMPETENCE PHILO 1ÈRE", "niveau": "1ère", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 90},
    
    # Second Cycle - Terminale (BAC)
    {"code": "FABS-CI26", "titre": "MEMO SVT BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 140},
    {"code": "FABS-CI99", "titre": "MEMO HISTOIRE-GEOGRAPHIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 135},
    {"code": "FABS-CI02", "titre": "MEMO PHYSIQUE CHIMIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 130},
    {"code": "FABS-CI57", "titre": "MEMO FRANÇAIS BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 125},
    {"code": "FABS-CI29", "titre": "MEMO PHILOSOPHIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 4000, "stock_actuel": 110},
    {"code": "FABS-CI195", "titre": "MEMO MATHEMATIQUE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 3000, "stock_actuel": 145},
    {"code": "FABS-CI63", "titre": "TEST FRANÇAIS BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 3500, "stock_actuel": 100},
    {"code": "FABS-CI78", "titre": "TEST PHYSIQUE-CHIMIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 4000, "stock_actuel": 95},
    {"code": "FABS-CI00", "titre": "TEST SVT BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix_vente": 4000, "stock_actuel": 90},
    
    # Livre commun - 6ème à Terminale
    {"code": "FABS-CI71", "titre": "MON CAHIER DE COURS D'ARTS PLASTIQUES", "niveau": "6ème à Terminale", "categorie": "Livre commun", "prix_vente": 2000, "stock_actuel": 200},
    {"code": "FABS-CI38", "titre": "MON CAHIER DE LEÇON D'EDUCATION MUSICALE", "niveau": "6ème à Terminale", "categorie": "Livre commun", "prix_vente": 2000, "stock_actuel": 180},
]


async def seed_real_products(db: AsyncIOMotorDatabase, owner_user_id: str) -> int:
    """Seed les 35 produits réels FABS-CI"""
    existing = await db.produits.count_documents({})
    if existing:
        return 0
    
    now = _now_iso()
    inserted = 0
    
    for p in SEED_PRODUCTS:
        doc = {
            "produit_id": str(uuid.uuid4()),
            "code_article": p["code"],
            "titre": p["titre"],
            "categorie": p["categorie"],
            "niveau_scolaire": p["niveau"],
            "prix_vente": p["prix_vente"],
            "stock_actuel": p["stock_actuel"],
            "seuil_alerte": 20,
            "actif": True,
            "created_by": owner_user_id,
            "created_at": now,
            "updated_at": now
        }
        await db.produits.insert_one(doc)
        inserted += 1
    
    return inserted

# ---------------------------------------------------------------------------
# Catalogue officiel EDITIONS FABS-CI (idempotent — ajoute uniquement les titres
# qui ne sont pas déjà présents dans la base, comparaison par `titre` exact).
# ---------------------------------------------------------------------------
REAL_PRODUCTS = [
    # --- Cahiers d'écriture & pré-lecture (Primaire) ---
    {"titre": "MON CAHIER DE PRELECTURE CP1", "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CP1", "prix_achat": 900,  "prix_vente": 1500},
    {"titre": "MON CAHIER D'ECRITURE CP1",    "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CP1", "prix_achat": 900,  "prix_vente": 1500},
    {"titre": "MON CAHIER D'ECRITURE CP2",    "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CP2", "prix_achat": 900,  "prix_vente": 1500},
    {"titre": "MON CAHIER D'ECRITURE CE1",    "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CE1", "prix_achat": 1000, "prix_vente": 1700},
    {"titre": "MON CAHIER D'ECRITURE CE2",    "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CE2", "prix_achat": 1000, "prix_vente": 1700},
    {"titre": "MON CAHIER D'ECRITURE CM1",    "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CM1", "prix_achat": 1100, "prix_vente": 1800},
    {"titre": "MON CAHIER D'ECRITURE CM2",    "auteur": "Collectif FABS-CI", "collection": "Bases",       "categorie": "primaire",     "niveau_scolaire": "CM2", "prix_achat": 1100, "prix_vente": 1800},

    # --- Arts plastiques & Éducation musicale ---
    {"titre": "MON CAHIER DE COURS D'ARTS PLASTIQUE",                                         "auteur": "Collectif FABS-CI", "collection": "Arts",     "categorie": "primaire",      "niveau_scolaire": "Primaire",        "prix_achat": 1500, "prix_vente": 2500},
    {"titre": "MON CAHIER DE LEÇON D'EDUCATION MUSICALE",                                     "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "primaire",      "niveau_scolaire": "Primaire",        "prix_achat": 1500, "prix_vente": 2500},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 6ème ancien",          "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "premier_cycle", "niveau_scolaire": "6ème",            "prix_achat": 1600, "prix_vente": 2700},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 6ème NP",              "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "premier_cycle", "niveau_scolaire": "6ème",            "prix_achat": 1600, "prix_vente": 2700},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 5ème",                 "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "premier_cycle", "niveau_scolaire": "5ème",            "prix_achat": 1600, "prix_vente": 2700},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 4ème",                 "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "premier_cycle", "niveau_scolaire": "4ème",            "prix_achat": 1600, "prix_vente": 2700},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 3ème",                 "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "premier_cycle", "niveau_scolaire": "3ème",            "prix_achat": 1600, "prix_vente": 2700},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 2nde",                 "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "second_cycle",  "niveau_scolaire": "2nde",            "prix_achat": 1800, "prix_vente": 3000},
    {"titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 1ère",                 "auteur": "Collectif FABS-CI", "collection": "Musique",  "categorie": "second_cycle",  "niveau_scolaire": "1ère",            "prix_achat": 1800, "prix_vente": 3000},
    {"titre": "MON CAHIER DE COURS DES ARTS PLASTIQUE 6e – 3e",                               "auteur": "Collectif FABS-CI", "collection": "Arts",     "categorie": "premier_cycle", "niveau_scolaire": "6ème-3ème",       "prix_achat": 1800, "prix_vente": 3000},

    # --- Examens & révisions Primaire (CM1 / CEPE) ---
    {"titre": "Réussir mes sujets de composition CM1",                                        "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CM1",             "prix_achat": 1500, "prix_vente": 2800},
    {"titre": "Corrigé Réussir mes sujets de composition CM1",                                "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CM1",             "prix_achat": 1500, "prix_vente": 2800},
    {"titre": "Réussir mes révisions CM1",                                                     "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CM1",             "prix_achat": 1500, "prix_vente": 2800},
    {"titre": "Corrigé Réussir mes révisions CM1",                                             "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CM1",             "prix_achat": 1500, "prix_vente": 2800},
    {"titre": "Réussir mes sujets types CEPE",                                                 "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CEPE",            "prix_achat": 1600, "prix_vente": 3000},
    {"titre": "Corrigé Réussir mes sujets types CEPE",                                         "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CEPE",            "prix_achat": 1600, "prix_vente": 3000},
    {"titre": "Réussir mon CEPE — Mes révisions",                                              "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CEPE",            "prix_achat": 1600, "prix_vente": 3000},
    {"titre": "Corrigé Réussir mon CEPE — Mes révisions",                                      "auteur": "Collectif FABS-CI", "collection": "Réussir",  "categorie": "primaire",      "niveau_scolaire": "CEPE",            "prix_achat": 1600, "prix_vente": 3000},

    # --- Mémos & Tests BEPC / BAC ---
    {"titre": "MEMO BEPC MATHEMATIQUE",                                                        "auteur": "Pr A. Diallo",       "collection": "Mémos",    "categorie": "premier_cycle", "niveau_scolaire": "3ème",            "prix_achat": 1800, "prix_vente": 3200},
    {"titre": "MEMO BAC MATHEMATIQUE",                                                          "auteur": "Pr A. Diallo",       "collection": "Mémos",    "categorie": "second_cycle",  "niveau_scolaire": "Terminale",       "prix_achat": 2200, "prix_vente": 3800},
    {"titre": "TEST-BEPC Anglais",                                                              "auteur": "S. Konan",           "collection": "Tests",    "categorie": "premier_cycle", "niveau_scolaire": "3ème",            "prix_achat": 2000, "prix_vente": 3500},
    {"titre": "TEST-BAC PHILOSOPHIE",                                                           "auteur": "M. B. Aké",          "collection": "Tests",    "categorie": "second_cycle",  "niveau_scolaire": "Terminale",       "prix_achat": 2200, "prix_vente": 3800},
    {"titre": "TEST-BAC Anglais",                                                               "auteur": "S. Konan",           "collection": "Tests",    "categorie": "second_cycle",  "niveau_scolaire": "Terminale",       "prix_achat": 2200, "prix_vente": 3800},
    {"titre": "L'EPREUVE D'ORAL D'ANGLAIS — Préparation BAC/BEPC",                               "auteur": "S. Konan",           "collection": "Languages","categorie": "second_cycle",  "niveau_scolaire": "Lycée",           "prix_achat": 2500, "prix_vente": 4000},

    # --- Renforcement Philo Lycée ---
    {"titre": "MON CAHIER DE RENFORCEMENT DE MES CAPACITES PHILO 1RE",                          "auteur": "M. B. Aké",          "collection": "Renforce", "categorie": "second_cycle",  "niveau_scolaire": "1ère",            "prix_achat": 2500, "prix_vente": 4500},
    {"titre": "MON CAHIER DE RENFORCEMENT DE MES CAPACITES PHILO TLE",                          "auteur": "M. B. Aké",          "collection": "Renforce", "categorie": "second_cycle",  "niveau_scolaire": "Terminale",       "prix_achat": 2500, "prix_vente": 4500},
