"""
Endpoint de test temporaire pour les produits
"""
from fastapi import APIRouter, Header, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

def build_products_test_router(db: AsyncIOMotorDatabase, resolve_user) -> APIRouter:
    router = APIRouter(prefix="/products-test", tags=["products-test"])
    
    @router.get("")
    async def get_products_simple(
        request: Request,
        authorization: Optional[str] = Header(default=None)
    ):
        """Retourne les produits directement depuis MongoDB"""
        me = await resolve_user(request, authorization)
        
        # Récupérer tous les produits
        cursor = db.produits.find({}, {"_id": 0}).sort("code_article", 1)
        products = await cursor.to_list(100)
        
        return {
            "total": len(products),
            "items": products
        }
    
    return router
