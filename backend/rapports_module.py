"""
Module Rapports — EDITIONS FABS-CI ERP
- Rapports de ventes avec filtres multiples
- Rapports de stock avec alertes
- Exports PDF
"""
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from collections import defaultdict
import logging

logger = logging.getLogger("fabsci")


def build_rapports_router(db, resolve_user):
    router = APIRouter(prefix="/rapports", tags=["Rapports"])
    
    # RBAC
    READ_ROLES = {"super_admin", "directeur_general", "comptable", "directeur_commercial"}
    
    async def check_read(request, authorization):
        u = await resolve_user(request, authorization)
        if u["role"] not in READ_ROLES:
            raise HTTPException(status_code=403, detail="Accès interdit")
        return u
    
    @router.get("/ventes")
    async def get_rapport_ventes(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        matiere: Optional[str] = None,
        ecole: Optional[str] = None,
        localite: Optional[str] = None,
        niveau_scolaire: Optional[str] = None,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ):
        """
        Rapport de ventes avec filtres multiples.
        Retourne les données agrégées par matière, école, localité, niveau.
        """
        await check_read(request, authorization)
        
        # Construction du pipeline d'agrégation MongoDB
        # Étape 1 : Récupérer toutes les factures émises/payées
        match_stage = {
            "statut": {"$in": ["emise", "partiellement_payee", "payee"]},
            "type_facture": "facture"
        }
        
        if date_debut:
            match_stage["date_facture"] = {"$gte": date_debut}
        if date_fin:
            if "date_facture" in match_stage:
                match_stage["date_facture"]["$lte"] = date_fin
            else:
                match_stage["date_facture"] = {"$lte": date_fin}
        
        factures = await db.factures.find(match_stage, {"_id": 0}).to_list(1000)
        
        # Étape 2 : Pour chaque facture, récupérer les lignes
        results = []
        total_quantite = 0
        total_montant = 0
        
        for facture in factures:
            facture_id = facture["facture_id"]
            client_id = facture.get("client_id")
            
            # Récupérer le client
            client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
            if not client:
                continue
            
            # Vérifier les filtres client
            if ecole and client.get("nom_client", "").lower().find(ecole.lower()) == -1:
                continue
            if localite and client.get("localite", "").lower().find(localite.lower()) == -1:
                continue
            
            # Récupérer les lignes de facture
            lignes = await db.facture_lignes.find({"facture_id": facture_id}, {"_id": 0}).to_list(100)
            
            for ligne in lignes:
                produit_id = ligne.get("produit_id")
                produit = await db.produits.find_one({"product_id": produit_id}, {"_id": 0})
                
                if not produit:
                    continue
                
                # Appliquer les filtres produit
                if matiere:
                    # La matière peut être dans le titre ou auteur
                    titre_auteur = f"{produit.get('titre', '')} {produit.get('auteur', '')}".lower()
                    if matiere.lower() not in titre_auteur:
                        continue
                
                if niveau_scolaire and produit.get("niveau_scolaire", "").lower().find(niveau_scolaire.lower()) == -1:
                    continue
                
                # Calculer les montants
                quantite = ligne.get("quantite", 0)
                montant_ht = ligne.get("montant_ht", 0)
                
                # Ajouter au résultat
                results.append({
                    "matiere": produit.get("auteur", "Non spécifié"),  # Utiliser auteur comme proxy pour matière
                    "titre_produit": produit.get("titre", ""),
                    "ecole": client.get("nom_client", ""),
                    "localite": client.get("localite", "Non spécifiée"),
                    "niveau_scolaire": produit.get("niveau_scolaire", "Non spécifié"),
                    "quantite_vendue": quantite,
                    "montant_total": montant_ht,
                    "date_facture": facture.get("date_facture", ""),
                    "reference_facture": facture.get("reference", ""),
                })
                
                total_quantite += quantite
                total_montant += montant_ht
        
        # Agrégations pour les graphiques
        # Par matière
        ventes_par_matiere = defaultdict(lambda: {"quantite": 0, "montant": 0})
        for r in results:
            matiere = r["matiere"]
            ventes_par_matiere[matiere]["quantite"] += r["quantite_vendue"]
            ventes_par_matiere[matiere]["montant"] += r["montant_total"]
        
        # Par localité
        ventes_par_localite = defaultdict(lambda: {"quantite": 0, "montant": 0})
        for r in results:
            loc = r["localite"]
            ventes_par_localite[loc]["quantite"] += r["quantite_vendue"]
            ventes_par_localite[loc]["montant"] += r["montant_total"]
        
        # Par date (agrégation par mois)
        ventes_par_mois = defaultdict(lambda: {"quantite": 0, "montant": 0})
        for r in results:
            if r["date_facture"]:
                mois = r["date_facture"][:7]  # YYYY-MM
                ventes_par_mois[mois]["quantite"] += r["quantite_vendue"]
                ventes_par_mois[mois]["montant"] += r["montant_total"]
        
        return {
            "lignes": results,
            "total_quantite": total_quantite,
            "total_montant": total_montant,
            "nombre_lignes": len(results),
            "agregations": {
                "par_matiere": [
                    {"matiere": k, **v} for k, v in ventes_par_matiere.items()
                ],
                "par_localite": [
                    {"localite": k, **v} for k, v in ventes_par_localite.items()
                ],
                "par_mois": [
                    {"mois": k, **v} for k, v in sorted(ventes_par_mois.items())
                ],
            }
        }
    
    @router.get("/stock")
    async def get_rapport_stock(
        request: Request,
        authorization: Optional[str] = Header(default=None),
        matiere: Optional[str] = None,
        niveau_scolaire: Optional[str] = None,
        alerte_uniquement: bool = False,
    ):
        """
        Rapport de stock avec alertes.
        """
        await check_read(request, authorization)
        
        # Récupérer tous les produits
        match_stage = {"actif": True}
        
        produits = await db.produits.find(match_stage, {"_id": 0}).to_list(1000)
        
        results = []
        total_stock_valeur = 0
        nb_alertes = 0
        
        for produit in produits:
            # Filtres
            if matiere:
                titre_auteur = f"{produit.get('titre', '')} {produit.get('auteur', '')}".lower()
                if matiere.lower() not in titre_auteur:
                    continue
            
            if niveau_scolaire and produit.get("niveau_scolaire", "").lower().find(niveau_scolaire.lower()) == -1:
                continue
            
            stock_actuel = produit.get("stock_actuel", 0)
            stock_minimum = produit.get("stock_minimum", 10)
            prix_vente = produit.get("prix_vente", 0)
            
            # Alerte si stock < minimum
            en_alerte = stock_actuel < stock_minimum
            
            if alerte_uniquement and not en_alerte:
                continue
            
            if en_alerte:
                nb_alertes += 1
            
            # Calculer la valeur du stock
            valeur_stock = stock_actuel * prix_vente
            total_stock_valeur += valeur_stock
            
            results.append({
                "reference": produit.get("reference", ""),
                "titre": produit.get("titre", ""),
                "auteur": produit.get("auteur", ""),
                "niveau_scolaire": produit.get("niveau_scolaire", ""),
                "categorie": produit.get("categorie", ""),
                "stock_actuel": stock_actuel,
                "stock_minimum": stock_minimum,
                "prix_vente": prix_vente,
                "valeur_stock": valeur_stock,
                "en_alerte": en_alerte,
                "statut_stock": "rupture" if stock_actuel == 0 else ("alerte" if en_alerte else "ok"),
            })
        
        # Récupérer l'historique des mouvements récents (30 derniers)
        mouvements = await db.mouvements_stock.find(
            {},
            {"_id": 0}
        ).sort("date_mouvement", -1).limit(30).to_list(30)
        
        # Enrichir les mouvements avec les infos produit
        for mouv in mouvements:
            produit_id = mouv.get("product_id")
            produit = await db.produits.find_one({"product_id": produit_id}, {"_id": 0, "titre": 1})
            if produit:
                mouv["titre_produit"] = produit.get("titre", "")
        
        return {
            "produits": results,
            "total_produits": len(results),
            "nb_alertes": nb_alertes,
            "valeur_stock_total": total_stock_valeur,
            "mouvements_recents": mouvements,
        }
    
    return router
