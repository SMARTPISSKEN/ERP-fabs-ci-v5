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
    # MATERNELLE (5)
    {"titre": "Mon premier livre de lecture — Petite Section", "auteur": "Collectif FABS-CI", "collection": "Eveil",       "categorie": "maternelle", "niveau_scolaire": "PS",  "isbn": "9782070001011", "prix_achat": 900,  "prix_vente": 1500},
    {"titre": "Cahier d'écriture Moyenne Section",             "auteur": "M. Kouamé",         "collection": "Eveil",       "categorie": "maternelle", "niveau_scolaire": "MS",  "isbn": "9782070001028", "prix_achat": 1100, "prix_vente": 1800},
    {"titre": "Mes premiers chiffres — Grande Section",        "auteur": "N. Bamba",          "collection": "Eveil",       "categorie": "maternelle", "niveau_scolaire": "GS",  "isbn": "9782070001035", "prix_achat": 1100, "prix_vente": 1900},
    {"titre": "Coloriage et formes — GS",                       "auteur": "Collectif FABS-CI", "collection": "Eveil",       "categorie": "maternelle", "niveau_scolaire": "GS",  "isbn": "9782070001042", "prix_achat": 900,  "prix_vente": 1500},
    {"titre": "Comptines de Côte d'Ivoire",                     "auteur": "A. Adingra",        "collection": "Eveil",       "categorie": "maternelle", "niveau_scolaire": "Maternelle", "isbn": "9782070001059", "prix_achat": 1200, "prix_vente": 2000},

    # PRIMAIRE (10)
    {"titre": "Mathématiques CP1 — Livre de l'élève",          "auteur": "Dr K. Yao",          "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CP1", "isbn": "9782070001066", "prix_achat": 1800, "prix_vente": 3000},
    {"titre": "Français CP1 — Méthode de lecture",             "auteur": "Mme F. Touré",       "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CP1", "isbn": "9782070001073", "prix_achat": 1800, "prix_vente": 3000},
    {"titre": "Mathématiques CP2",                              "auteur": "Dr K. Yao",          "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CP2", "isbn": "9782070001080", "prix_achat": 1900, "prix_vente": 3200},
    {"titre": "Français CE1",                                   "auteur": "Mme F. Touré",       "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CE1", "isbn": "9782070001097", "prix_achat": 1900, "prix_vente": 3200},
    {"titre": "Sciences CE2 — Découverte du monde",            "auteur": "Pr S. Ouattara",     "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CE2", "isbn": "9782070001103", "prix_achat": 2000, "prix_vente": 3400},
    {"titre": "Histoire-Géographie CM1 Côte d'Ivoire",         "auteur": "M. Coulibaly",       "collection": "Patrimoine",  "categorie": "primaire",  "niveau_scolaire": "CM1", "isbn": "9782070001110", "prix_achat": 2200, "prix_vente": 3600},
    {"titre": "Mathématiques CM2",                              "auteur": "Dr K. Yao",          "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CM2", "isbn": "9782070001127", "prix_achat": 2400, "prix_vente": 3900},
    {"titre": "Français CM2 — Lectures et expression",        "auteur": "Mme F. Touré",       "collection": "Réussir",     "categorie": "primaire",  "niveau_scolaire": "CM2", "isbn": "9782070001134", "prix_achat": 2400, "prix_vente": 3900},
    {"titre": "Anglais CE1 — My first book",                   "auteur": "S. Konan",           "collection": "Languages",   "categorie": "primaire",  "niveau_scolaire": "CE1", "isbn": "9782070001141", "prix_achat": 1900, "prix_vente": 3200},
    {"titre": "Cahier d'exercices CM1",                         "auteur": "Collectif FABS-CI",  "collection": "Cahiers",     "categorie": "primaire",  "niveau_scolaire": "CM1", "isbn": "9782070001158", "prix_achat": 1500, "prix_vente": 2500},

    # PREMIER CYCLE (8)
    {"titre": "Mathématiques 6e",                               "auteur": "Pr A. Diallo",       "collection": "Excellence",  "categorie": "premier_cycle", "niveau_scolaire": "6e", "isbn": "9782070001165", "prix_achat": 2800, "prix_vente": 4500},
    {"titre": "Français 6e — Textes et expression",            "auteur": "Mme A. Bamba",       "collection": "Excellence",  "categorie": "premier_cycle", "niveau_scolaire": "6e", "isbn": "9782070001172", "prix_achat": 2800, "prix_vente": 4500},
    {"titre": "Histoire-Géographie 5e",                         "auteur": "M. Coulibaly",       "collection": "Patrimoine",  "categorie": "premier_cycle", "niveau_scolaire": "5e", "isbn": "9782070001189", "prix_achat": 2900, "prix_vente": 4600},
    {"titre": "Sciences Physiques 5e",                          "auteur": "Pr S. Ouattara",     "collection": "Excellence",  "categorie": "premier_cycle", "niveau_scolaire": "5e", "isbn": "9782070001196", "prix_achat": 2900, "prix_vente": 4700},
    {"titre": "SVT 4e — Le vivant",                             "auteur": "Dr H. N'Goran",      "collection": "Excellence",  "categorie": "premier_cycle", "niveau_scolaire": "4e", "isbn": "9782070001202", "prix_achat": 3000, "prix_vente": 4800},
    {"titre": "Anglais 4e — Move on!",                          "auteur": "S. Konan",           "collection": "Languages",   "categorie": "premier_cycle", "niveau_scolaire": "4e", "isbn": "9782070001219", "prix_achat": 2900, "prix_vente": 4700},
    {"titre": "Mathématiques 3e — Préparation BEPC",           "auteur": "Pr A. Diallo",       "collection": "Excellence",  "categorie": "premier_cycle", "niveau_scolaire": "3e", "isbn": "9782070001226", "prix_achat": 3200, "prix_vente": 5200},
    {"titre": "Français 3e — Du texte à la dissertation",     "auteur": "Mme A. Bamba",       "collection": "Excellence",  "categorie": "premier_cycle", "niveau_scolaire": "3e", "isbn": "9782070001233", "prix_achat": 3200, "prix_vente": 5200},

    # SECOND CYCLE (7)
    {"titre": "Mathématiques 2nde A — Analyse",                 "auteur": "Pr A. Diallo",       "collection": "Horizons",    "categorie": "second_cycle",  "niveau_scolaire": "2nde", "isbn": "9782070001240", "prix_achat": 3800, "prix_vente": 6200},
    {"titre": "Mathématiques 2nde C — Scientifique",            "auteur": "Pr A. Diallo",       "collection": "Horizons",    "categorie": "second_cycle",  "niveau_scolaire": "2nde", "isbn": "9782070001257", "prix_achat": 4000, "prix_vente": 6500},
    {"titre": "Physique-Chimie 1ère D",                          "auteur": "Pr S. Ouattara",     "collection": "Horizons",    "categorie": "second_cycle",  "niveau_scolaire": "1ère", "isbn": "9782070001264", "prix_achat": 4200, "prix_vente": 6900},
    {"titre": "Philosophie Terminale A — Préparation BAC",     "auteur": "M. B. Aké",          "collection": "Horizons",    "categorie": "second_cycle",  "niveau_scolaire": "Terminale", "isbn": "9782070001271", "prix_achat": 4500, "prix_vente": 7500},
    {"titre": "Mathématiques Terminale C",                       "auteur": "Pr A. Diallo",       "collection": "Horizons",    "categorie": "second_cycle",  "niveau_scolaire": "Terminale", "isbn": "9782070001288", "prix_achat": 4800, "prix_vente": 8000},
    {"titre": "Histoire-Géographie Terminale",                   "auteur": "M. Coulibaly",       "collection": "Patrimoine",  "categorie": "second_cycle",  "niveau_scolaire": "Terminale", "isbn": "9782070001295", "prix_achat": 4500, "prix_vente": 7500},
    {"titre": "Anglais Terminale — Towards the BAC",             "auteur": "S. Konan",           "collection": "Languages",   "categorie": "second_cycle",  "niveau_scolaire": "Terminale", "isbn": "9782070001301", "prix_achat": 4500, "prix_vente": 7500},

    # LITTÉRATURE AFRICAINE (5)
    {"titre": "Les soleils des indépendances",                   "auteur": "Ahmadou Kourouma",   "collection": "Classiques",  "categorie": "litterature", "niveau_scolaire": "Tous niveaux", "isbn": "9782070001318", "prix_achat": 3000, "prix_vente": 5500},
    {"titre": "L'Aventure ambiguë",                              "auteur": "Cheikh Hamidou Kane", "collection": "Classiques",  "categorie": "litterature", "niveau_scolaire": "Tous niveaux", "isbn": "9782070001325", "prix_achat": 2800, "prix_vente": 5200},
    {"titre": "Une si longue lettre",                            "auteur": "Mariama Bâ",         "collection": "Classiques",  "categorie": "litterature", "niveau_scolaire": "Tous niveaux", "isbn": "9782070001332", "prix_achat": 2800, "prix_vente": 5200},
    {"titre": "Le Mandat",                                       "auteur": "Ousmane Sembène",    "collection": "Classiques",  "categorie": "litterature", "niveau_scolaire": "Tous niveaux", "isbn": "9782070001349", "prix_achat": 2700, "prix_vente": 4800},
    {"titre": "Allah n'est pas obligé",                          "auteur": "Ahmadou Kourouma",   "collection": "Classiques",  "categorie": "litterature", "niveau_scolaire": "Tous niveaux", "isbn": "9782070001356", "prix_achat": 3200, "prix_vente": 5800},
]


async def seed_products(db: AsyncIOMotorDatabase, owner_user_id: str) -> int:
    existing = await db.produits.count_documents({})
    if existing:
        return 0
    inserted = 0
    for p in SEED_PRODUCTS:
        ref = await next_product_reference(db)
        await db.produits.insert_one({
            "product_id": f"prd_{uuid.uuid4().hex[:12]}",
            "reference": ref,
            **p,
            "stock_actuel": 50,
            "stock_minimum": 10,
            "actif": True,
            "created_by": owner_user_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        })
        inserted += 1
    # Inject 2 stock alerts so the dashboard widget has real data right away
    await db.produits.update_one({"reference": "FABS-PRD-0001"}, {"$set": {"stock_actuel": 3}})   # alerte (<= 10)
    await db.produits.update_one({"reference": "FABS-PRD-0028"}, {"$set": {"stock_actuel": 0}})  # rupture
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

    # --- Littérature ---
    {"titre": "Le succès d'un orphelin",                                                        "auteur": "AKE APPIA Y. Doris", "collection": "Récits",   "categorie": "litterature",   "niveau_scolaire": "Tous niveaux",    "prix_achat": 2500, "prix_vente": 4500},
]


async def seed_real_products(db: AsyncIOMotorDatabase, owner_user_id: str) -> int:
    """Idempotent — ajoute uniquement les titres absents de la collection."""
    inserted = 0
    for p in REAL_PRODUCTS:
        if await db.produits.find_one({"titre": p["titre"]}, {"_id": 1}):
            continue
        ref = await next_product_reference(db)
        await db.produits.insert_one({
            "product_id": f"prd_{uuid.uuid4().hex[:12]}",
            "reference": ref,
            "isbn": None,
            **p,
            "stock_actuel": 50,
            "stock_minimum": 10,
            "actif": True,
            "created_by": owner_user_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        })
        inserted += 1
    return inserted
