# Sprint 7 — Module Factures — Résumé d'Implémentation

**Date** : 2026-05-24  
**Statut** : ✅ COMPLÉTÉ

## 📋 Objectif
Développer le module complet de facturation avec génération automatique depuis les commandes, gestion des avoirs (credit notes), calculs TVA automatiques, et interface de suivi des paiements.

---

## ✅ Backend Implémenté

### Collections MongoDB
- **`factures`** : En-tête facture/avoir
  - `facture_id`, `reference` (FABS-FC-26-27-XXXX ou FABS-AV-26-27-XXXX)
  - `type_facture` : facture / avoir
  - `client_id`, `commande_id`, `statut`
  - Dates : facture, écheance, émission
  - `remise_globale`, `montant_ht`, `montant_tva`, `montant_ttc`
  - `montant_regle`, `montant_restant`
  - `notes`, `facture_origine_id` (pour avoirs)
  - `created_by`, `created_at`, `updated_at`
  
- **`facture_lignes`** : Lignes de facture
  - `ligne_id`, `facture_id`, `produit_id`, `designation`
  - `quantite`, `prix_unitaire`, `remise_ligne`, `montant_ht`

### Statuts Facture
```
brouillon → emise → partiellement_payee → payee
                ↓
            annulee
```

### TVA
- **Taux** : 18% (Côte d'Ivoire)
- **Calcul automatique** :
  ```
  montant_ht = Σ(lignes) - remise_globale
  montant_tva = montant_ht × 0.18
  montant_ttc = montant_ht + montant_tva
  ```

### Types de Facture
1. **Facture normale** : `FABS-FC-26-27-XXXX`
2. **Avoir** (credit note) : `FABS-AV-26-27-XXXX`
   - Montants négatifs
   - Lié à une facture origine
   - Motif obligatoire

### Endpoints API

| Méthode | Endpoint | Description | RBAC |
|---------|----------|-------------|------|
| `GET` | `/api/factures` | Liste avec filtres | READ_ROLES |
| `POST` | `/api/factures` | Création manuelle | WRITE_ROLES |
| `POST` | `/api/factures/generer-depuis-commande` | Génération auto | WRITE_ROLES |
| `GET` | `/api/factures/{id}` | Détail avec lignes | READ_ROLES |
| `PATCH` | `/api/factures/{id}` | Modification | WRITE_ROLES |
| `POST` | `/api/factures/{id}/emettre` | Émission | WRITE_ROLES |
| `POST` | `/api/factures/generer-avoir` | Créer avoir | WRITE_ROLES |

### RBAC (Contrôle d'accès par rôle)

| Action | Rôles autorisés |
|--------|----------------|
| **Lecture** | super_admin, directeur_general, directeur_commercial, comptable, secretariat |
| **Écriture** | super_admin, directeur_general, directeur_commercial, comptable |
| **Paiements** | super_admin, directeur_general, comptable |

### Règles Métier

1. **Génération depuis commande** :
   - Commande doit être validée, préparée ou livrée
   - Lignes copiées automatiquement avec désignations produits
   - Facture créée avec statut "emise"

2. **Modification** :
   - Uniquement sur statut "brouillon"
   - Recalcul automatique des totaux si lignes modifiées

3. **Émission** :
   - Passage de "brouillon" à "emise"
   - Date émission enregistrée

4. **Avoir** :
   - Créé depuis une facture existante
   - Montant ≤ montant_ttc facture origine
   - Motif obligatoire (minimum 10 caractères)
   - Montants négatifs
   - Statut "emise" dès la création

5. **Statut automatique** :
   - `montant_regle = 0` → emise
   - `0 < montant_regle < montant_ttc` → partiellement_payee
   - `montant_regle >= montant_ttc` → payee

### Seed Data
- 1 facture de démonstration générée depuis une commande existante
- Compteur initialisé pour factures et avoirs

---

## ✅ Frontend Implémenté

### Pages & Routes

#### 1. **Page Liste `/factures`**

**Stats en temps réel** :
- Total factures
- Factures émises (badge bleu)
- Factures impayées (badge orange)
- CA Total TTC (somme factures non annulées)

**Filtres avancés** :
- Recherche par référence
- Type facture (facture / avoir)
- Statut (tous les statuts)
- Client (dropdown)
- Plage de dates (début + fin)

**Tableau** :
- Colonnes : Référence, Type, Client, Date, Montant TTC, Restant, Statut, Actions
- Badges colorés par statut
- Type facture en couleur (bleu/rouge)
- Montant restant en orange si > 0
- Click sur ligne → redirection vers détail

#### 2. **Page Détail `/factures/{id}`**

**Informations principales** :
- En-tête : Référence, statut, type (avoir si applicable)
- Client : nom, date facture, date échéance, commande liée

**Lignes de facture** :
- Tableau : Désignation, Qté × Prix unitaire, Remise ligne, Montant HT
- Badges pour remises

**Totaux détaillés** :
- Sous-total HT (avant remise globale)
- Remise globale (% et montant)
- Montant HT net
- TVA 18%
- **Total TTC** (encadré orange)
- Montant réglé (vert)
- Restant dû (orange)

**Actions contextuelles** (selon statut et rôle) :
- **Brouillon** → "Émettre" (bleu) — Passage à "emise"
- **Tout type facture** → "Générer avoir" — Modal avec montant + motif

**Modal Génération Avoir** :
- Input montant (max = montant_ttc facture)
- Textarea motif (minimum 10 caractères)
- Validation avant création

**Sidebar Résumé** :
- Type, Statut, Date émission

### Service API
**Fichier** : `/app/frontend/src/services/facturesApi.js`

Fonctions exportées :
- `getFactures(filters)` - Liste avec filtres
- `getFacture(factureId)` - Détail avec lignes
- `createFacture(data, type_facture)` - Création manuelle
- `updateFacture(factureId, data)` - Modification
- `generateFactureFromCommande(commandeId, dates)` - Génération auto
- `emettreFacture(factureId)` - Émission
- `genererAvoir(factureId, montant, motif)` - Créer avoir

---

## 🎨 Design & UX

### Badges Colorés par Statut
- 🟤 **Brouillon** : `bg-gray-500`
- 🔵 **Émise** : `bg-blue-500`
- 🟠 **Partiellement payée** : `bg-orange-500`
- 🟢 **Payée** : `bg-green-500`
- 🔴 **Annulée** : `bg-red-500`

### Type Facture
- **Facture** : `text-blue-600`
- **Avoir** : `text-red-600`

### Icônes Lucide
- `FileText` - Factures
- `DollarSign` - Émises
- `AlertCircle` - Impayées
- `TrendingUp` - CA Total
- `Send` - Émettre
- `Plus` - Nouvelle facture

### Palettes FABS-CI
- Navy : `#0A2540`
- Orange : `#FF6200`
- Boutons principaux : Orange avec hover `#E55900`

---

## 📊 Calculs Automatiques

### Exemple de Calcul
```
Ligne 1: 10 × 5000 FCFA - 5% remise = 47 500 FCFA HT
Ligne 2:  5 × 3000 FCFA - 0% remise = 15 000 FCFA HT
                                     ---------------
Sous-total HT brut                    62 500 FCFA
Remise globale 10%                    -6 250 FCFA
                                     ---------------
Montant HT net                        56 250 FCFA
TVA 18%                               10 125 FCFA
                                     ===============
MONTANT TTC                           66 375 FCFA
Montant réglé                         30 000 FCFA
                                     ---------------
RESTANT DÛ                            36 375 FCFA
```

---

## 🧪 Tests Recommandés

### Backend
1. ✅ Création facture manuelle
2. ✅ Génération depuis commande (validée/préparée/livrée)
3. ✅ Liste avec filtres (type, statut, client, dates)
4. ✅ Détail avec lignes enrichies
5. ✅ Modification facture brouillon
6. ✅ Émission facture
7. ✅ Génération avoir avec montant partiel
8. ✅ Génération avoir avec montant total
9. ✅ Calculs automatiques (HT, TVA, TTC, réglé, restant)
10. ✅ RBAC sur tous les endpoints

### Frontend
1. ✅ Affichage liste avec stats
2. ✅ Filtres et recherche
3. ✅ Navigation vers détail
4. ✅ Affichage totaux détaillés
5. ✅ Bouton "Émettre" (brouillon uniquement)
6. ✅ Modal génération avoir avec validation
7. ✅ Affichage badges type et statut
8. ✅ Messages toasts succès/erreur

---

## 📁 Fichiers Créés/Modifiés

### Backend
- ✅ `/app/backend/factures_module.py` — Module complet (870 lignes)
- ✅ `/app/backend/server.py` — Import + router + seed

### Frontend
- ✅ `/app/frontend/src/services/facturesApi.js` — Service API
- ✅ `/app/frontend/src/pages/Factures.jsx` — Page liste
- ✅ `/app/frontend/src/pages/FactureDetail.jsx` — Page détail avec actions
- ✅ `/app/frontend/src/App.js` — Routes ajoutées

### Documentation
- ✅ `/app/memory/PRD.md` — Mis à jour avec Sprint 7
- ✅ `/app/SPRINT_7_SUMMARY.md` — Résumé complet

---

## 🚀 État des Services

```bash
backend    RUNNING   pid 2314   # FastAPI + Motor + MongoDB
frontend   RUNNING   pid 2457   # React + Webpack Dev Server
mongodb    RUNNING   pid 1106   # MongoDB 27017
```

**Compilation Frontend** : ✅ Webpack compilé avec succès (16 warnings mineurs)  
**Backend Logs** : ✅ 1 facture seeded au démarrage

---

## 🎯 Prochaines Étapes (Sprint 8)

### Module Paiements
- Référence : `FABS-REG-2026-XXXX`
- **4 modes de paiement** :
  1. Espèces
  2. Chèque (banque, numéro)
  3. Virement bancaire (référence)
  4. Mobile Money (opérateur, numéro transaction)
- **Fonctionnalités** :
  - Enregistrement paiements
  - Affectation à une ou plusieurs factures
  - Rapprochement bancaire
  - Mise à jour automatique des factures (montant_regle, statut)
  - Historique des paiements par facture
  - Justificatifs (upload fichiers)

### Dashboard - Données Réelles
- Remplacer données de démo par vraies données
- KPIs basés sur commandes et factures
- Graphiques CA mensuel
- Top clients (basé sur factures payées)

### PDF Professionnel
- Génération PDF factures/avoirs
- Logo FABS-CI en en-tête
- Coordonnées entreprise (RCCM, NIF, etc.)
- Tableau lignes avec totaux
- Mentions légales + informations bancaires
- Format A4 standard

---

## 📝 Notes Techniques

### Compteurs de Référence
- Collection `counters` avec `_id: "factures"` et `_id: "avoirs"`
- Séquences indépendantes :
  - Factures : `FABS-FC-26-27-0001`, `FABS-FC-26-27-0002`, etc.
  - Avoirs : `FABS-AV-26-27-0001`, `FABS-AV-26-27-0002`, etc.
- Idempotent (ne réinitialise pas au redémarrage)

### Gestion Avoirs
- Les avoirs ont des montants **négatifs**
- Quantités négatives dans les lignes
- Montants proportionnels si avoir partiel
- Statut automatiquement "emise" à la création
- `facture_origine_id` pointe vers la facture d'origine

### Intégration Commandes ↔ Factures
1. Commande validée/préparée/livrée
2. Génération facture depuis commande
3. Lignes copiées avec désignations produits
4. Remise globale héritée
5. Facture créée avec statut "emise"
6. Lien bidirectionnel (`commande_id` dans facture)

---

## 🔗 Liens avec Autres Modules

### Sprint 6 — Commandes
- Génération automatique factures depuis commandes
- Héritage lignes + remises
- Lien référence commande visible dans facture

### Sprint 8 — Paiements (à venir)
- Enregistrement paiements sur factures
- Mise à jour `montant_regle` et `montant_restant`
- Changement statut automatique
- Historique paiements

### Sprint 12 — Comptabilité (à venir)
- Journaux comptables depuis factures
- Suivi créances clients
- Rapprochement bancaire

---

**✅ Sprint 7 — COMPLÉTÉ AVEC SUCCÈS**

*« Les livres sont des fenêtres par lesquelles on regarde le monde »*  
— EDITIONS FABS-CI
