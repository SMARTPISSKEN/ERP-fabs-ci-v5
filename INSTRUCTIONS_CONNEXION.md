# 🔐 Instructions de Connexion — ERP EDITIONS FABS-CI

## ✅ Configuration Actuelle

L'application a été configurée pour fonctionner avec le routage Kubernetes d'Emergent.

### URLs
- **Frontend** : Accessible via votre URL Emergent (ex: `https://xxx.emergent.sh`)
- **Backend** : Accessible via `/api` (redirigé automatiquement vers le backend)

### Compte Super Admin

**Email** : `pissken@editionsfabsci.com`  
**Mot de passe** : `Admin@2025`  
**Rôle** : Super Administrateur (accès complet à tous les modules)

---

## 🚀 Comment se connecter

1. **Accédez à l'application** via votre URL Emergent
2. Sur la page de connexion, entrez :
   - Email : `pissken@editionsfabsci.com`
   - Mot de passe : `Admin@2025`
3. Cliquez sur **"Se connecter"**

---

## 🔧 État des Services

```
✅ Backend (FastAPI)    : RUNNING sur port 8001
✅ Frontend (React)     : RUNNING sur port 3000  
✅ MongoDB              : RUNNING sur port 27017
✅ Nginx                : RUNNING (proxy)
```

---

## 📊 Données Seed Disponibles

L'application contient des données de démonstration :
- **8 clients** (écoles, librairies, distributeurs)
- **69 produits** (livres scolaires du catalogue FABS-CI)
- **3 commandes** de démonstration
- **1 facture** de test
- **1 paiement** de test
- **9 paramètres** système configurés

---

## 🎯 Modules Accessibles (Super Admin)

1. **Tableau de bord** — Vue d'ensemble avec KPIs
2. **Clients** — Gestion base clients
3. **Produits** — Catalogue livres (69 produits)
4. **Commandes** — Workflow complet
5. **Factures** — Facturation + avoirs (TVA 18%)
6. **Paiements** — 4 modes (espèces, chèque, virement, mobile money)
7. **Livraisons** — Bons de livraison
8. **Retours** — Bons de retour
9. **Stock** — Mouvements de stock
10. **Comptabilité** — Écritures, créances, balance
11. **Utilisateurs** — Gestion des 8 rôles
12. **Paramètres** — Configuration système

---

## ⚠️ Dépannage

### Si vous ne pouvez pas vous connecter :

1. **Vérifiez l'URL** : Assurez-vous d'utiliser l'URL Emergent fournie
2. **Vérifiez les identifiants** : 
   - Email : `pissken@editionsfabsci.com` (pas d'espace)
   - Mot de passe : `Admin@2025` (sensible à la casse)
3. **Vérifiez les services** :
   ```bash
   sudo supervisorctl status
   ```
4. **Vérifiez les logs backend** :
   ```bash
   tail -n 50 /var/log/supervisor/backend.err.log
   ```
5. **Vérifiez les logs frontend** :
   ```bash
   tail -n 50 /var/log/supervisor/frontend.err.log
   ```

### Message d'erreur "Une erreur est survenue"

Cela peut signifier :
- Le backend n'est pas accessible
- Les identifiants sont incorrects
- Un problème de réseau

**Solution** : Vérifiez que tous les services sont en cours d'exécution et que vous utilisez les bons identifiants.

---

## 📞 Support

Si le problème persiste :
1. Partagez le message d'erreur exact
2. Indiquez l'URL que vous utilisez
3. Partagez les logs si possible

---

**Version** : 1.0.0 (15 sprints complétés)  
**Date** : 24 mai 2026  
**Statut** : ✅ Production Ready
