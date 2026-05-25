"""
ERP EDITIONS FABS-CI — Backend Server
FastAPI + Motor (MongoDB) + JWT Auth + RBAC
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
import bcrypt

from fastapi import FastAPI, APIRouter, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

# Import all ERP modules
from clients_module import build_clients_router, seed_clients
from products_module import build_products_router, seed_real_products
from products_test_module import build_products_test_router
from commandes_module import build_commandes_router, seed_commandes
from factures_module import build_factures_router, seed_factures
from paiements_module import build_paiements_router, seed_paiements
from stock_module import build_stock_router, seed_mouvements_stock
from bons_livraison_module import build_bons_livraison_router, seed_bons_livraison
from bons_retour_module import build_bons_retour_router, seed_bons_retour
from comptabilite_module import build_comptabilite_router, seed_comptabilite
from administration_module import build_utilisateurs_router, build_parametres_router, seed_parametres
from recherche_module import build_recherche_router
from documents_ai_module import build_documents_ai_router, seed_documents_demo
from analytics_module import build_analytics_router
from dashboard_data import build_dashboard_payload

# ============================================================================
# CONFIGURATION
# ============================================================================
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fabsci.server")

# MongoDB
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'fabsci_erp')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'fabsci-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_DAYS = 7

# CORS
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')

# ============================================================================
# AUTH UTILITIES
# ============================================================================
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    """Create JWT token"""
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS)
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": exp
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")

async def resolve_user(request: Request, authorization: Optional[str] = None) -> dict:
    """
    Resolve current user from Authorization header or cookie
    Returns user dict with: user_id, email, nom_complet, role, actif
    """
    token = None
    
    # Try Authorization header first (Bearer token)
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ')[1]
    
    # Fallback to cookie
    if not token:
        token = request.cookies.get('session_token')
    
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    # Decode JWT
    payload = decode_jwt_token(token)
    
    # Fetch user from database
    user = await db.users.find_one(
        {"user_id": payload['user_id']},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    if not user.get('actif', True):
        raise HTTPException(status_code=403, detail="Compte désactivé")
    
    return user

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    nom_complet: str
    role: str
    actif: bool
    picture: Optional[str] = None
    created_at: str
    updated_at: str

# ============================================================================
# FASTAPI APP
# ============================================================================
app = FastAPI(title="ERP EDITIONS FABS-CI API", version="1.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ['*'] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Main API router with /api prefix
api_router = APIRouter(prefix="/api")

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Login with email/password
    Returns JWT token
    """
    # Find user
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    # Verify password (if password field exists)
    if 'password_hash' in user:
        if not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    else:
        # For backward compatibility - allow login without password hash
        # This is for Google OAuth users
        pass
    
    if not user.get('actif', True):
        raise HTTPException(status_code=403, detail="Compte désactivé")
    
    # Create JWT token
    token = create_jwt_token(user['user_id'], user['email'], user['role'])
    
    # Return token and user info
    user_info = {
        "user_id": user['user_id'],
        "email": user['email'],
        "nom_complet": user['nom_complet'],
        "role": user['role'],
        "actif": user['actif'],
        "picture": user.get('picture'),
    }
    
    return LoginResponse(access_token=token, user=user_info)

@api_router.get("/auth/me", response_model=UserProfile)
async def get_me(
    request: Request,
    authorization: Optional[str] = Header(default=None)
):
    """Get current user profile"""
    user = await resolve_user(request, authorization)
    return UserProfile(**user)

@api_router.post("/auth/logout")
async def logout():
    """Logout (client-side should clear token)"""
    return {"message": "Déconnecté avec succès"}

# ============================================================================
# DASHBOARD ENDPOINT
# ============================================================================
@api_router.get("/dashboard/stats")
async def dashboard_stats(
    request: Request,
    authorization: Optional[str] = Header(default=None)
):
    """Get dashboard stats for current user role"""
    user = await resolve_user(request, authorization)
    return build_dashboard_payload(user['role'])

# ============================================================================
# HEALTH CHECK
# ============================================================================
@api_router.get("/")
async def root():
    return {"message": "ERP EDITIONS FABS-CI API v1.0.0", "status": "running"}

@api_router.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test MongoDB connection
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# ============================================================================
# REGISTER ALL MODULE ROUTERS
# ============================================================================
api_router.include_router(build_clients_router(db, resolve_user))
api_router.include_router(build_products_router(db, resolve_user))
api_router.include_router(build_products_test_router(db, resolve_user))
api_router.include_router(build_commandes_router(db, resolve_user))
api_router.include_router(build_factures_router(db, resolve_user))
api_router.include_router(build_paiements_router(db, resolve_user))
api_router.include_router(build_stock_router(db, resolve_user))
api_router.include_router(build_bons_livraison_router(db, resolve_user))
api_router.include_router(build_bons_retour_router(db, resolve_user))
api_router.include_router(build_comptabilite_router(db, resolve_user))
api_router.include_router(build_utilisateurs_router(db, resolve_user))
api_router.include_router(build_parametres_router(db, resolve_user))
api_router.include_router(build_recherche_router(db, resolve_user))
api_router.include_router(build_documents_ai_router(db, resolve_user))
api_router.include_router(build_analytics_router(db, resolve_user))

# Include API router in main app
app.include_router(api_router)

# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Seed database on startup"""
    logger.info("🚀 Starting ERP EDITIONS FABS-CI backend...")
    
    # Seed super admin if not exists
    admin_exists = await db.users.find_one({"email": "pissken@editionsfabsci.com"})
    if not admin_exists:
        logger.info("Creating super admin...")
        now = datetime.now(timezone.utc).isoformat()
        admin_doc = {
            "user_id": "admin_super_001",
            "email": "pissken@editionsfabsci.com",
            "nom_complet": "AKE APPIA YVES DORIS",
            "role": "super_admin",
            "actif": True,
            "password_hash": hash_password("Admin@2025"),
            "picture": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(admin_doc)
        logger.info("✅ Super admin created: pissken@editionsfabsci.com / Admin@2025")
    
    # Seed DG if not exists
    dg_exists = await db.users.find_one({"email": "ali.mamin@editionsfabsci.com"})
    if not dg_exists:
        logger.info("Creating DG...")
        now = datetime.now(timezone.utc).isoformat()
        dg_doc = {
            "user_id": "dg_001",
            "email": "ali.mamin@editionsfabsci.com",
            "nom_complet": "ALI MAMIN",
            "role": "directeur_general",
            "actif": True,
            "password_hash": hash_password("DG@2025"),
            "picture": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.users.insert_one(dg_doc)
        logger.info("✅ DG created: ali.mamin@editionsfabsci.com / DG@2025")
    
    # Seed system parameters if not exists
    param_count = await db.parametres.count_documents({})
    if param_count == 0:
        count = await seed_parametres(db)
        logger.info(f"✅ {count} system parameters seeded")
    
    # Seed clients if not exists
    client_count = await db.clients.count_documents({})
    if client_count == 0:
        logger.info("Seeding clients...")
        count = await seed_clients(db, "admin_super_001")
        logger.info(f"✅ {count} clients seeded")
    
    # Seed products if not exists
    product_count = await db.produits.count_documents({})
    if product_count == 0:
        logger.info("Seeding products...")
        count = await seed_real_products(db, "admin_super_001")
        logger.info(f"✅ {count} real products seeded")
    
    # Seed commandes if not exists
    commande_count = await db.commandes.count_documents({})
    if commande_count == 0:
        logger.info("Seeding commandes...")
        count = await seed_commandes(db, "admin_super_001")
        logger.info(f"✅ {count} commandes seeded")
    
    # Seed factures if not exists
    facture_count = await db.factures.count_documents({})
    if facture_count == 0:
        logger.info("Seeding factures...")
        count = await seed_factures(db, "admin_super_001")
        logger.info(f"✅ {count} factures seeded")
    
    # Seed paiements if not exists
    paiement_count = await db.paiements.count_documents({})
    if paiement_count == 0:
        logger.info("Seeding paiements...")
        count = await seed_paiements(db, "admin_super_001")
        logger.info(f"✅ {count} paiements seeded")
    
    # Seed mouvements stock if not exists
    mouvement_count = await db.mouvements_stock.count_documents({})
    if mouvement_count == 0:
        logger.info("Seeding stock movements...")
        count = await seed_mouvements_stock(db, "admin_super_001")
        logger.info(f"✅ {count} stock movements seeded")
    
    # Seed documents demo if not exists
    doc_count = await db.documents_intelligents.count_documents({})
    if doc_count == 0:
        logger.info("Seeding demo documents...")
        count = await seed_documents_demo(db, "admin_super_001")
        logger.info(f"✅ {count} demo documents seeded")
    
    logger.info("✅ ERP EDITIONS FABS-CI backend ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    logger.info("Shutting down ERP backend...")
    client.close()
    logger.info("✅ MongoDB connection closed")

# ============================================================================
# RUN SERVER (for development)
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
