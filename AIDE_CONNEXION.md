# 🔧 Aide à la Connexion — ERP EDITIONS FABS-CI

## ❌ Problème : "Une erreur est survenue. Veuillez réessayer."

Si vous voyez ce message lors de la tentative de connexion, suivez ces étapes :

---

## 🧪 Étape 1 : Test de Diagnostic

1. **Ouvrez cette page de test dans votre navigateur** :
   ```
   https://VOTRE-URL-EMERGENT/test-api.html
   ```
   (Remplacez `VOTRE-URL-EMERGENT` par votre vraie URL Emergent)

2. **Cliquez sur "🏥 Tester /api/health"**
   - ✅ Si vous voyez "SUCCÈS" : Le backend est accessible
   - ❌ Si vous voyez "ERREUR" : Le backend n'est pas accessible via /api

3. **Cliquez sur "🔐 Tester la Connexion"**
   - ✅ Si vous voyez "CONNEXION RÉUSSIE" : L'authentification fonctionne
   - ❌ Si vous voyez "ÉCHEC" : Problème avec les identifiants ou le backend

---

## 🔑 Identifiants de Connexion

**Email** : `pissken@editionsfabsci.com`  
**Mot de passe** : `Admin@2025`

⚠️ **Attention** :
- Le mot de passe est sensible à la casse (respectez les majuscules/minuscules)
- Pas d'espace avant ou après l'email
- Utilisez exactement : `Admin@2025` (A majuscule, @ et 2025)

---

## 🌐 URLs Importantes

### ❌ NE PAS utiliser :
- `http://localhost:3000` ❌
- `http://localhost:8001` ❌

### ✅ À utiliser :
- Votre URL Emergent : `https://xxx.emergent.sh` ✅

Le backend est accessible via `/api` uniquement depuis l'URL Emergent, pas depuis localhost.

---

## 🔍 Vérifications Techniques

### 1. Vérifier les Services

Connectez-vous en SSH ou via le terminal et exécutez :

```bash
sudo supervisorctl status
```

**Résultat attendu** :
```
backend    RUNNING   pid XXXX
frontend   RUNNING   pid XXXX
mongodb    RUNNING   pid XXXX
```

### 2. Vérifier le Backend Directement

```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pissken@editionsfabsci.com","password":"Admin@2025"}'
```

**Résultat attendu** : Un objet JSON avec `user` et `access_token`

### 3. Vérifier les Logs

**Logs Backend** :
```bash
tail -n 50 /var/log/supervisor/backend.err.log
```

**Logs Frontend** :
```bash
tail -n 50 /var/log/supervisor/frontend.err.log
```

---

## 🛠️ Solutions aux Problèmes Courants

### Problème 1 : "Le backend n'est pas accessible"

**Cause** : Vous utilisez localhost au lieu de l'URL Emergent

**Solution** :
- Utilisez toujours votre URL Emergent : `https://xxx.emergent.sh`
- Ne jamais accéder via `localhost:3000`

---

### Problème 2 : "Identifiants incorrects"

**Solution** :
1. Copiez-collez exactement :
   - Email : `pissken@editionsfabsci.com`
   - Mot de passe : `Admin@2025`
2. Vérifiez qu'il n'y a pas d'espace avant/après
3. Le mot de passe contient : 
   - A majuscule
   - Le symbole @
   - Les chiffres 2025

---

### Problème 3 : Services Non Démarrés

**Solution** :
```bash
# Redémarrer tous les services
sudo supervisorctl restart all

# Attendre 10 secondes
sleep 10

# Vérifier le statut
sudo supervisorctl status
```

---

### Problème 4 : Erreur CORS ou Réseau

**Cause** : Configuration réseau ou proxy

**Solution** :
1. Vérifiez que vous accédez via HTTPS (pas HTTP)
2. Essayez dans un autre navigateur (Chrome, Firefox, Safari)
3. Désactivez temporairement les extensions de navigateur
4. Videz le cache du navigateur (Ctrl+F5 ou Cmd+Shift+R)

---

## 📞 Support Avancé

Si le problème persiste après toutes ces vérifications :

1. **Partagez ces informations** :
   - URL exacte que vous utilisez
   - Message d'erreur exact (avec capture d'écran si possible)
   - Résultat de la page de test `/test-api.html`
   - Résultat de `sudo supervisorctl status`

2. **Logs à partager** :
   ```bash
   # Backend logs
   tail -n 100 /var/log/supervisor/backend.err.log > backend-logs.txt
   
   # Frontend logs
   tail -n 100 /var/log/supervisor/frontend.err.log > frontend-logs.txt
   ```

---

## ✅ Checklist de Vérification

Avant de demander de l'aide, vérifiez :

- [ ] J'utilise l'URL Emergent (pas localhost)
- [ ] Les identifiants sont corrects (copier-coller)
- [ ] Tous les services sont RUNNING
- [ ] La page `/test-api.html` montre "SUCCÈS"
- [ ] J'ai vidé le cache du navigateur
- [ ] J'ai testé dans un autre navigateur

---

## 🎯 Configuration Actuelle

**Backend URL** : `/api` (chemin relatif)  
**Frontend URL** : URL Emergent automatique  
**Mode** : Production avec routage Kubernetes  

L'application est configurée pour fonctionner avec le routage automatique d'Emergent :
- Frontend sur port 3000
- Backend sur port 8001
- Routage `/api/*` → Backend automatique

---

**Version** : 1.0.0  
**Dernière mise à jour** : 24 mai 2026  
**Statut** : ✅ Opérationnel
