#!/usr/bin/env python3
"""
Script pour insérer les 35 produits réels FABS-CI
"""
from pymongo import MongoClient
from datetime import datetime, timezone
import uuid

# Connexion MongoDB
client = MongoClient("mongodb://localhost:27017")
db = client["fabsci_erp"]

# 35 Produits FABS-CI
PRODUITS = [
    # Maternelle
    {"code": "FABS-CI79", "titre": "MON CAHIER DE PRÉLECTURE CP1", "niveau": "Grande section", "categorie": "Maternelle", "prix": 2000},
    
    # Primaire
    {"code": "FABS-CI76", "titre": "MON CAHIER D'ÉCRITURE CP1", "niveau": "CP1", "categorie": "Primaire", "prix": 2000},
    {"code": "FABS-CI83", "titre": "MON CAHIER D'ÉCRITURE CP2", "niveau": "CP2", "categorie": "Primaire", "prix": 2000},
    {"code": "FABS-CI90", "titre": "MON CAHIER DÉCRITURE CE1", "niveau": "CE1", "categorie": "Primaire", "prix": 2000},
    {"code": "FABS-CI06", "titre": "MON CAHIER D'ÉCRITURE CE2", "niveau": "CE2", "categorie": "Primaire", "prix": 2000},
    {"code": "FABS-CI64", "titre": "MON CAHIER D'ÉCRITURE CM1", "niveau": "CM1", "categorie": "Primaire", "prix": 2000},
    {"code": "FABS-CI82", "titre": "MON CAHIER D'ÉCRITURE CM2", "niveau": "CM2", "categorie": "Primaire", "prix": 2000},
    
    # Premier Cycle - 6ème
    {"code": "FABS-CI24", "titre": "ACTIVITE PRATIQUE DE LA FLUTE A BEC SOPRANO 6ÈME", "niveau": "6ème", "categorie": "Premier cycle", "prix": 2000},
    {"code": "FABS-CI68", "titre": "MON CAHIER D'ACTIVITÉS D'ÉDUCATION MUSICALE 6IEME", "niveau": "6ème", "categorie": "Premier cycle", "prix": 2000},
    {"code": "FABS-CI31", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 6ÈME", "niveau": "6ème", "categorie": "Premier cycle", "prix": 3000},
    
    # Premier Cycle - 5ème
    {"code": "FABS-CI61", "titre": "ACTIVITE PRATIQUE DE LA FLUTE A BEC SOPRANO 5ÈME", "niveau": "5ème", "categorie": "Premier cycle", "prix": 2500},
    {"code": "FABS-CI75", "titre": "MON CAHIER D'ACTIVITE D'EDUCATION MUSICALE 5EME", "niveau": "5ème", "categorie": "Premier cycle", "prix": 2000},
    {"code": "FABS-CI48", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 5ÈME", "niveau": "5ème", "categorie": "Premier cycle", "prix": 3000},
    
    # Premier Cycle - 4ème
    {"code": "FABS-CI07", "titre": "MON CAHIER D'ACTIVITE D'EDUCATION MUSICALE 4ÈME", "niveau": "4ème", "categorie": "Premier cycle", "prix": 2000},
    {"code": "FABS-CI86", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'EDUCATION MUSICALE 4EME", "niveau": "4ème", "categorie": "Premier cycle", "prix": 3000},
    
    # Premier Cycle - 3ème (BEPC)
    {"code": "FABS-CI05", "titre": "MEMO HISTOIRE-GEOGRAPHIE BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix": 2500},
    {"code": "FABS-CI20", "titre": "MON CAHIER D'ACTIVITE D'EDUCATION MUSICALE 3ÈME", "niveau": "3ème", "categorie": "Premier cycle", "prix": 2000},
    {"code": "FABS-CI32", "titre": "TEST SVT - BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix": 3000},
    {"code": "FABS-CI25", "titre": "TEST FRANÇAIS BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix": 3500},
    {"code": "FABS-CI93", "titre": "MON CAHIER DE COURS ET D'ACTIVITÉS D'ÉDUCATION MUSICALE 3ÈME", "niveau": "3ème", "categorie": "Premier cycle", "prix": 3000},
    {"code": "FABS-CI18", "titre": "TEST PHYSIQUE-CHIMIE BEPC", "niveau": "3ème", "categorie": "Premier cycle", "prix": 3000},
    
    # Second Cycle - 2nde
    {"code": "FABS-CI33", "titre": "SACERDOCE", "niveau": "2nde", "categorie": "Second cycle", "prix": 3000},
    {"code": "FABS-CI17", "titre": "MON CAHIER DE COURS ET D'ACTIVITES D'EDUCATION MUSICALE 2ND", "niveau": "2nde", "categorie": "Second cycle", "prix": 3000},
    
    # Second Cycle - 1ère
    {"code": "FABS-CI85", "titre": "CAHIER DE COMPETENCE PHILO 1ÈRE", "niveau": "1ère", "categorie": "Second cycle", "prix": 3000},
    
    # Second Cycle - Terminale (BAC)
    {"code": "FABS-CI26", "titre": "MEMO SVT BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 3000},
    {"code": "FABS-CI99", "titre": "MEMO HISTOIRE-GEOGRAPHIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 3000},
    {"code": "FABS-CI02", "titre": "MEMO PHYSIQUE CHIMIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 3000},
    {"code": "FABS-CI57", "titre": "MEMO FRANÇAIS BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 3000},
    {"code": "FABS-CI29", "titre": "MEMO PHILOSOPHIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 4000},
    {"code": "FABS-CI195", "titre": "MEMO MATHEMATIQUE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 3000},
    {"code": "FABS-CI63", "titre": "TEST FRANÇAIS BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 3500},
    {"code": "FABS-CI78", "titre": "TEST PHYSIQUE-CHIMIE BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 4000},
    {"code": "FABS-CI00", "titre": "TEST SVT BAC", "niveau": "Terminale", "categorie": "Second cycle", "prix": 4000},
    
    # Livre commun
    {"code": "FABS-CI71", "titre": "MON CAHIER DE COURS D'ARTS PLASTIQUES", "niveau": "6ème à Terminale", "categorie": "Livre commun", "prix": 2000},
    {"code": "FABS-CI38", "titre": "MON CAHIER DE LEÇON D'EDUCATION MUSICALE", "niveau": "6ème à Terminale", "categorie": "Livre commun", "prix": 2000},
]

# Vider la collection
db.produits.delete_many({})
print("✅ Collection produits vidée")

# Insérer les 35 produits
now = datetime.now(timezone.utc).isoformat()
inserted = 0

for p in PRODUITS:
    doc = {
        "produit_id": str(uuid.uuid4()),
        "code_article": p["code"],
        "titre": p["titre"],
        "categorie": p["categorie"],
        "niveau_scolaire": p["niveau"],
        "prix_vente": p["prix"],
        "stock_actuel": 100,
        "seuil_alerte": 20,
        "actif": True,
        "created_by": "admin_super_001",
        "created_at": now,
        "updated_at": now
    }
    db.produits.insert_one(doc)
    inserted += 1

print(f"✅ {inserted} produits FABS-CI insérés avec succès!")

# Afficher les 5 premiers
print("\n=== 5 Premiers produits ===")
for p in db.produits.find({}, {"_id": 0, "code_article": 1, "titre": 1, "prix_vente": 1}).limit(5):
    print(f"  {p['code_article']:12} | {p['titre']:40} | {p['prix_vente']:,} FCFA")

client.close()
