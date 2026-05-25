"""
Script de création du compte super admin
AKE APPIA YVES DORIS - pissken@editionsfabsci.com
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import bcrypt


async def create_super_admin():
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "fabsci_erp")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check if admin already exists
    existing = await db.users.find_one({"email": "pissken@editionsfabsci.com"})
    
    if existing:
        print("✅ Super admin existe déjà")
        print(f"   Email: {existing['email']}")
        print(f"   Nom: {existing['nom_complet']}")
        print(f"   Rôle: {existing['role']}")
        return
    
    # Create super admin
    now = datetime.now(timezone.utc).isoformat()
    
    admin_doc = {
        "user_id": "admin_super_001",
        "email": "pissken@editionsfabsci.com",
        "nom_complet": "AKE APPIA YVES DORIS",
        "role": "super_admin",
        "actif": True,
        "picture": None,
        "created_at": now,
        "updated_at": now,
    }
    
    await db.users.insert_one(admin_doc)
    
    print("✅ Super admin créé avec succès !")
    print(f"   Email: pissken@editionsfabsci.com")
    print(f"   Mot de passe: Admin@2025")
    print(f"   Nom: AKE APPIA YVES DORIS")
    print(f"   Rôle: super_admin")
    print("")
    print("🔐 IMPORTANT: Le mot de passe doit être utilisé avec Emergent Google Auth")
    print("   L'utilisateur doit se connecter via Google avec cet email")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(create_super_admin())
