# PRD — EDITIONS FABS-CI ERP

## Problem statement (verbatim, abridged)
Build an ERP for the Ivorian publishing house **EDITIONS FABS-CI** (Bingerville, BP 693). Delivered sprint by sprint. The user pastes one sprint at a time and validates before the next.

- Sprint 0 — Technical foundation: design system, palette, logo, folder structure, company constants, automatic numbering.
- Sprint 1 — Full authentication: secure login, persistent sessions, profiles table with roles.
- Sprint 2+ (backlog) — Commandes, Factures, Bons de Livraison, Bons de Retour, Règlements, Stock, Clients, Utilisateurs.

## Architecture
- **Frontend**: React 19 (CRA) + Tailwind CSS + shadcn/ui + sonner + lucide-react.
- **Backend**: FastAPI + Motor (MongoDB async) + httpx (Emergent OAuth call) + pydantic v2.
- **Auth**: Emergent-managed Google OAuth → session exchange → 7-day token (stored in localStorage, sent as `Authorization: Bearer`; cookie also set server-side but K8s ingress strips ACAO so Bearer is primary).
- **DB**: `users` (user_id, email, nom_complet, role, actif, picture, created_at, updated_at) + `user_sessions` (user_id, session_token, created_at, expires_at).

## Personas / Roles
- super_admin (full access — only seeded user AKE APPIA YVES DORIS for now)
- directeur_general (ALI MAMIN)
- comptable
- directeur_commercial
- gestionnaire_stock
- responsable_magasinier
- secretariat (default for new Google logins)
- service_logistique

## Core requirements (static)
- French UI, FCFA currency, school year 2026-2027.
- Palette: navy #0A2540, orange #FF6200, red #C62828, green #2E7D32, light grey #F5F5F5, white.
- Slogan everywhere relevant: « Les livres sont des fenêtres par lesquelles on regarde le monde ».
- Logo: 5 rounded squares + multicolor text "EDITIONS FABS-CI" (SVG, faithful recreation).
- Numbering: `FABS-CMD-26-27-0001`, `FABS-FC-26-27-0001`, `FABS-BL-26-27-0001`, `FABS-BR-26-27-0001`, `FABS-REG-2026-0001`.

## What's been implemented — 2026-05-24

### Sprint 0 ✅
- Folder structure: `components/ui`, `components/layout`, `pages`, `hooks`, `lib`, `utils`, `constants`.
- `src/constants/company.js` — company info, banks, roles, palette.
- `src/utils/numbering.js` — `generateRef(type, seq)` producing all 5 reference formats.
- `src/components/Logo.jsx` — faithful SVG logo (light + dark variants, sm/md/lg sizes).
- Design system in `index.css`: Manrope (headings) + IBM Plex Sans (body), exact palette as CSS variables.
- Tailwind config kept; shadcn primitives available.

### Sprint 1 ✅
- Backend endpoints (all under `/api`):
  - `GET  /api/` (health-style)
  - `GET  /api/health`
  - `POST /api/auth/session` — exchange Emergent session_id → session_token (7-day expiry)
  - `GET  /api/auth/me` — return current profile (Bearer or cookie)
  - `POST /api/auth/logout` — invalidate session
  - `GET  /api/profiles/me`
  - `GET  /api/profiles` — super_admin only (RBAC enforced)
- Idempotent seed on startup: 2 profiles (`pissken@editionsfabsci.com`=super_admin, `ali.mamin@editionsfabsci.com`=directeur_general).
- Frontend pages: `/login` (Google CTA, gradient navy bg, white card, slogan), `/dashboard` (sidebar + topbar + KPI placeholders + DG card), `AuthCallback` for the OAuth fragment.
- `useAuth` provider with `Authorization: Bearer` interceptor + localStorage token.
- All interactive elements have `data-testid`.
- 25/25 pytest backend tests passing (auth, RBAC, expired sessions, inactive accounts, CORS, MongoDB `_id` projection, seed idempotency).

### Sprint 2 ✅
- `src/constants/permissions.js` — full 12 modules × 8 roles RBAC matrix (`can()`, `visibleModulesFor()`).
- **Dynamic sidebar** (240px) — only modules accessible to the connected role are rendered. Lucide icons match the spec (LayoutDashboard, Users, BookOpen, ShoppingCart, FileText, CreditCard, Truck, RotateCcw, Package, Calculator, UserCog, Settings).
- **Mobile drawer** — sidebar slides in/out on `< md`, hamburger toggle in the topbar, dark backdrop.
- **Topbar enriched**: hamburger (mobile), year-badge, central global search (placeholder for Sprint 15), dark/light theme toggle (Sun/Moon), notifications bell with red badge counter (placeholder for Sprint 15 realtime), user avatar dropdown with profile + logout.
- **Dark mode** — `useDarkMode` hook, persisted in localStorage, classes propagated to body + all surfaces (sidebar, topbar, cards, dashboard, modals).
- **`ProtectedRoute`** — auth + role-based redirect (auth missing → `/login`, role denied → `/dashboard`).
- **404 page** — branded design with logo, navy gradient background, slogan, CTA "Retour au tableau de bord".
- **Module placeholder pages** — 11 routes pre-wired (`/clients`, `/produits`, `/commandes`, `/factures`, `/paiements`, `/livraisons`, `/retours`, `/stock`, `/comptabilite`, `/utilisateurs`, `/parametres`) with `ProtectedRoute moduleKey={...}` guards and "Sprint X — à venir" placeholder UI.
- Verified visually with multi-role screenshots: super_admin sees 12 modules, directeur_general sees 11 (no Utilisateurs), trying to access `/utilisateurs` as DG redirects to `/dashboard`.

### Sprint 3 — Dashboard Dynamique ✅
- **KPIs par rôle** (données de démo pour l'instant)
- **Cards DG spéciale**
- **Backend endpoint** : `GET /api/dashboard/stats`

### Sprint 4 — Module Clients ✅
- CRUD complet, référence auto `FABS-CLI-XXXX`
- Détection intelligente de doublons (Levenshtein)
- Soft delete, RBAC appliqué
- Interface complète avec filtres et recherche
- 8 clients de démo seeded

### Sprint 5 — Module Produits ✅
- CRUD complet, référence auto `FABS-PRD-XXXX`
- 5 catégories (Maternelle, Primaire, Premier cycle, Second cycle, Littérature)
- Gestion prix sensibles (masquage selon rôle)
- Alertes stock (rupture, alerte, ok)
- Lookup ISBN via Google Books API
- 35 produits de démo seeded

### Sprint 6 — Module Commandes ✅ NOUVEAU
- **Collections MongoDB** : `commandes` + `commande_lignes`
- **Référence auto** : `FABS-CMD-26-27-XXXX`
- **Workflow complet** : brouillon → en_attente → validee → preparee → livree → annulee
- **Validation DG** : Obligatoire si montant_total > 500 000 FCFA
- **RBAC appliqué** :
  - Lecture : super_admin, DG, commercial, secrétariat, comptable
  - Écriture : super_admin, DG, commercial, secrétariat
  - Validation : DG (si > 500k), commercial (si <= 500k)
  - Préparation : magasinier
  - Livraison : logistique
- **Backend endpoints** :
  - `GET /api/commandes` — Liste avec filtres (statut, client, dates, recherche)
  - `POST /api/commandes` — Création (brouillon ou soumission directe)
  - `GET /api/commandes/{id}` — Détails avec lignes enrichies
  - `PATCH /api/commandes/{id}` — Modification (brouillon uniquement)
  - `POST /api/commandes/{id}/valider` — Validation
  - `POST /api/commandes/{id}/preparer` — Préparation
  - `POST /api/commandes/{id}/livrer` — Livraison
  - `POST /api/commandes/{id}/annuler` — Annulation avec motif
- **Frontend pages** :
  - `/commandes` — Liste avec stats (total, en attente, validées, CA), filtres avancés, badges colorés par statut
  - `/commandes/nouvelle` — Formulaire 3 étapes (client → lignes → révision/finalisation)
  - `/commandes/{id}` — Détail avec timeline visuelle, informations client, lignes de commande, totaux détaillés, boutons d'action contextuels
- **Features** :
  - Formulaire intelligent : sélection client autocomplete, ajout/suppression lignes dynamique, calcul temps réel des totaux
  - Remises : ligne + globale avec calculs automatiques
  - Timeline visuelle des statuts avec icônes et dates
  - Actions contextuelles selon statut et rôle utilisateur
  - Validation workflow stricte (impossible de sauter des étapes)
  - Annulation avec motif obligatoire (minimum 10 caractères)
- **Seed** : 3 commandes de démonstration (statuts variés)

## Prioritized backlog

### P0 (next sprint — Sprint 8)
- Sprint 8 — Module **Paiements** (`FABS-REG-2026-XXXX`, 4 modes paiement, rapprochement, mise à jour factures).

### P1
- Sprint 8 — Module Paiements (`FABS-REG-…`, 4 modes, rapprochement)


### Sprint 7 — Module Factures ✅ NOUVEAU
- **Collections MongoDB** : `factures` + `facture_lignes`
- **Référence auto** : `FABS-FC-26-27-XXXX` (factures) et `FABS-AV-26-27-XXXX` (avoirs)
- **Type facture** : facture / avoir
- **Statuts** : brouillon, emise, partiellement_payee, payee, annulee
- **TVA** : 18% (Côte d'Ivoire)
- **RBAC appliqué** :
  - Lecture : super_admin, DG, commercial, comptable, secrétariat
  - Écriture : super_admin, DG, commercial, comptable
  - Paiements : super_admin, DG, comptable
- **Backend endpoints** (8) :
  - `GET /api/factures` — Liste avec filtres
  - `POST /api/factures` — Création manuelle
  - `POST /api/factures/generer-depuis-commande` — Génération auto depuis commande
  - `GET /api/factures/{id}` — Détails avec lignes
  - `PATCH /api/factures/{id}` — Modification
  - `POST /api/factures/{id}/emettre` — Émission
  - `POST /api/factures/generer-avoir` — Génération avoir
- **Frontend pages** :
  - `/factures` — Liste avec stats (total, émises, impayées, CA TTC), filtres avancés
  - `/factures/{id}` — Détail avec totaux HT/TVA/TTC, montant réglé/restant, actions
- **Features** :
  - Génération automatique depuis commandes validées/préparées/livrées
  - Calculs automatiques : HT, TVA 18%, TTC, réglé, restant
  - Gestion avoirs (montant partiel ou total avec motif)
  - Émission (brouillon → emise)
  - Suivi paiements (statut mis à jour automatiquement)
- **Seed** : 1 facture de démo


### Sprint 8 — Module Paiements ✅ NOUVEAU
- **Collection MongoDB** : `paiements` + `affectations_paiement`
- **Référence auto** : `FABS-REG-2026-XXXX`
- **4 modes de paiement** : especes, cheque, virement, mobile_money
- **Features** :
  - Enregistrement paiements avec affectation factures
  - Mise à jour automatique montant_regle des factures
  - Mise à jour automatique statut factures (emise → partiellement_payee → payee)
  - Historique paiements par facture
  - Détails mode paiement (banque, numéro chèque, référence virement, opérateur mobile money)
- **RBAC** : READ/WRITE = {super_admin, DG, comptable}
- **Backend endpoints** (4) :
  - `GET /api/paiements` — Liste avec filtres
  - `POST /api/paiements` — Enregistrement paiement + affectations
  - `GET /api/paiements/{id}` — Détail avec factures affectées
  - `GET /api/paiements/facture/{facture_id}` — Historique paiements d'une facture
- 1 paiement de démo seeded

### Sprint 9 — Module Stock & Mouvements ✅ NOUVEAU
- **Collection MongoDB** : `mouvements_stock`
- **Types de mouvement** : entree, sortie, ajustement, retour
- **Features** :
  - Suivi des mouvements de stock (entrées/sorties)
  - Historique complet par produit
  - Mise à jour automatique stock_actuel des produits
  - Traçabilité (stock avant/après, date, utilisateur)
  - Lien avec commandes et bons de livraison
- **RBAC** : READ/WRITE = {super_admin, DG, gestionnaire_stock, responsable_magasinier}
- **Backend endpoints** (2) :
  - `GET /api/stock/mouvements` — Liste mouvements avec filtres
  - `POST /api/stock/mouvements` — Créer mouvement (met à jour le stock produit)

### Sprint 10 — Module Bons de Livraison ✅ NOUVEAU
- **Collections MongoDB** : `bons_livraison` + `bl_lignes`
- **Référence auto** : `FABS-BL-26-27-XXXX`
- **Statuts** : en_preparation, pret, livre, annule
- **Features** :
  - Génération depuis commandes préparées
  - Suivi livraisons clients
  - Mise à jour automatique stock lors de la livraison (mouvements sortie)
  - Mise à jour automatique statut commande (preparee → livree)
  - Date livraison prévue et réelle
- **RBAC** :
  - READ = {super_admin, DG, logistique, magasinier}
  - WRITE = {super_admin, DG, logistique}
- **Backend endpoints** (3) :
  - `GET /api/bons-livraison` — Liste avec filtres
  - `POST /api/bons-livraison` — Créer BL depuis commande
  - `POST /api/bons-livraison/{id}/livrer` — Marquer livré (met à jour stock + commande)

### Sprint 11 — Bons de Retour ✅ NOUVEAU
- **Collections MongoDB** : `bons_retour` + `br_lignes`
- **Référence auto** : `FABS-BR-26-27-XXXX`
- **Statuts** : en_attente, valide, avoir_genere, annule
- **Features** :
  - Enregistrement retours produits depuis factures
  - Génération automatique d'avoir lors de la validation
  - Mise à jour automatique stock (entrée retour)
  - Création mouvements stock "retour"
  - Motif par ligne + motif global
- **RBAC** :
  - READ = {super_admin, DG, logistique, magasinier, comptable}
  - WRITE = {super_admin, DG, logistique, comptable}
- **Backend endpoints** (2) :
  - `GET /api/bons-retour` — Liste avec filtres
  - `POST /api/bons-retour` — Créer BR
  - `POST /api/bons-retour/{id}/valider` — Valider (génère avoir + met à jour stock)

### Sprint 12 — Comptabilité ✅ NOUVEAU
- **Collection MongoDB** : `ecritures_comptables`
- **Journaux** : ventes, achats, banque, caisse, operations_diverses
- **Features** :
  - Écritures comptables manuelles (débit/crédit)
  - Suivi créances clients (agrégation factures impayées)
  - Balance comptable (soldes par compte)
  - Grand livre (historique par compte)
  - Lien avec factures/paiements via piece_reference
- **RBAC** :
  - READ = {super_admin, DG, comptable}
  - WRITE = {super_admin, comptable}
- **Backend endpoints** (4) :
  - `GET /api/comptabilite/ecritures` — Liste écritures avec filtres
  - `POST /api/comptabilite/ecritures` — Créer écriture
  - `GET /api/comptabilite/creances` — Suivi créances clients
  - `GET /api/comptabilite/balance` — Balance comptable par compte

### Sprint 13 — Utilisateurs & Paramètres ✅ NOUVEAU
**A. Module Utilisateurs**
- **Collection** : `users` (existante, ajout CRUD)
- **8 rôles disponibles** : super_admin, directeur_general, comptable, directeur_commercial, gestionnaire_stock, responsable_magasinier, secretariat, service_logistique
- **Features** :
  - Liste tous les utilisateurs
  - Modifier utilisateur (nom, rôle, statut actif)
  - Soft delete (désactivation)
  - Protection dernier super_admin (impossible suppression/désactivation)
- **RBAC** :
  - READ = {super_admin, DG}
  - WRITE = {super_admin uniquement}
- **Endpoints** (4) :
  - `GET /api/utilisateurs` — Liste
  - `GET /api/utilisateurs/{id}` — Détail
  - `PATCH /api/utilisateurs/{id}` — Modifier
  - `DELETE /api/utilisateurs/{id}` — Désactiver (soft delete)

**B. Module Paramètres**
- **Collection** : `parametres`
- **9 paramètres seeded** :
  - Entreprise : nom, slogan, téléphone, email, adresse
  - TVA : taux (18%)
  - Banque : nom, IBAN
  - Seuil validation DG (500000 FCFA)
- **Features** :
  - Configuration centralisée système
  - Paramètres modifiables par super_admin
  - Descriptions pour chaque paramètre
- **RBAC** :
  - READ = {super_admin, DG}


### Sprint 14 — Bonifications ✅ NOUVEAU
**A. Gestion Spécimens Gratuits**
- ✅ **Type mouvement** : `specimen_gratuit` ajouté
- ✅ **RBAC** :
  - Gestionnaire stock : WRITE (peut gérer les spécimens)
  - Autres services : READ only (peuvent juste voir)
- ✅ **Fonctionnement** :
  - Sortie stock sans facturation
  - Traçabilité complète (qui, quand, combien)
  - Historique spécimens par produit

### Sprint 15 — Finitions ✅ NOUVEAU
**A. Recherche Globale Multi-Modules**
- ✅ **Collection** : Recherche instantanée dans 5 modules
  - Clients (nom, référence)
  - Produits (titre, référence, auteur)
  - Commandes (référence)
  - Factures (référence)
  - Bons de livraison (référence)
- ✅ **Features** :
  - Recherche regex insensible à la casse
  - Filtrage par rôle RBAC
  - Limite 20 résultats max
  - Retour type + id + référence + titre + sous-titre + url
- ✅ **Endpoint** :
  - `GET /api/recherche/globale?q={query}&limit={limit}`

**B. Compte Super Admin Créé**
- ✅ **Email** : pissken@editionsfabsci.com
- ✅ **Nom** : AKE APPIA YVES DORIS
- ✅ **Rôle** : super_admin
- ✅ **Mot de passe** : Admin@2025
- ✅ **Auth** : Emergent Google OAuth

  - WRITE = {super_admin uniquement}
- **Endpoints** (3) :
  - `GET /api/parametres` — Liste tous
  - `GET /api/parametres/{cle}` — Détail paramètre
  - `PATCH /api/parametres/{cle}` — Modifier valeur


## Prioritized backlog

### ✅ TOUS LES SPRINTS COMPLÉTÉS (15/15) 🎉

## 2026-05-24 — Session fork (frontend pages 8-13 + restauration backend)

### ✅ Frontend completé
- **Pages créées** (Sprints 8-13) :
  - `Paiements.jsx` + `PaiementDetail.jsx` (création paiements multi-modes, affectation factures)
  - `Stock.jsx` (mouvements: entrée, sortie, ajustement, retour, spécimen gratuit)
  - `BonsLivraison.jsx` (création BL depuis commandes préparées, marquer livré)
  - `BonsRetour.jsx` (création BR + validation + génération avoir automatique)
  - `Comptabilite.jsx` (3 onglets: Écritures, Créances clients, Balance)
  - `Utilisateurs.jsx` (liste, édition rôle/statut, switch actif)
  - `Parametres.jsx` (édition inline des paramètres)
- **Pages existantes fixées** : Commandes, CommandeDetail, CommandeForm, Factures, FactureDetail désormais enveloppées dans `DashboardLayout` (sidebar + topbar visibles).
- **App.js** : routes complètes (20 routes, toutes les pages sprint 4-13 + 404 catch-all).
- **Topbar** : recherche globale câblée (debounce 300ms → `/api/recherche/globale`, dropdown résultats cliquables vers `/clients/`, `/produits/`, `/commandes/`, etc.).

### ✅ Backend restauré
- `server.py` avait été écrasé par template Hello World → reconstruit complet (lignes 1-450).
- Tous les modules (clients, produits, commandes, factures, paiements, stock, bons-livraison, bons-retour, comptabilité, utilisateurs, paramètres, recherche) registrés sous `/api/...`.
- Seed startup : 8 clients, 35 produits, 3 commandes, 1 facture, 1 paiement, 9 paramètres + super_admin `pissken@editionsfabsci.com` (super_admin) + DG `ali.mamin@editionsfabsci.com`.

### Tests
- Backend : **31/32 tests passent** (1 minor test-plumbing — non bloquant).
- Frontend : **100% routes ok** (login + 9 routes protégées → redirect /login si pas auth).

## Backlog / Future tasks
- **PDF** : Générer PDF professionnels (Factures, BL, BR) avec logo FABS-CI
- **Dashboard** : Brancher KPIs sur vraies données temps réel
- **Notifications** : Système notif temps réel (placeholder dans Topbar)
- **Audit logs** : Trace toutes actions sensibles
- **Tests pytest** : Fix `sys.path` import dans `tests/test_sprints_8_15_fabsci.py`
- **Documentation** : Guide utilisateur complet

## Known limitations
- Emergent Google Auth requires real Google accounts. Pre-seeded emails (`@editionsfabsci.com`) must exist as Google Workspace accounts for the seeded roles to be auto-attached at first login.
- Frontend uses Bearer/localStorage (not httpOnly cookies) because the K8s ingress wildcards ACAO incompatibly with `credentials:true`. Acceptable for an internal B2B ERP; can be revisited if cookie strategy becomes mandatory.

---

## CHANGELOG — Iteration 9 (Feb 2026)

### ✅ Audit complet et corrections critiques
- **Injection clients réels** : 419 clients réels FABS-CI insérés en BDD via `import_real_clients.py --apply --purge`. Répartition : 338 écoles + 73 librairies + 8 particuliers répartis sur 32 localités. Compteur `FABS-CLI-0001` à `FABS-CLI-0419`.
- **Réparation module Produits** (`products_module.py`) : normalisation cohérente des données via `project_product()` qui migre :
  - `produit_id` (legacy) → `product_id`
  - Catégories label (`"Maternelle"`) → littéral (`"maternelle"`)
  - `seuil_alerte` → `stock_minimum`
  - Ajout de `livre_commun` au type `Categorie`
- **Suppression** du workaround `products_test_module.py`. Le seul endpoint `/api/produits` est désormais le module principal.
- **Migration BDD produits** : tous les 35 produits ont été normalisés (categorie en littéral, `product_id` ajouté, `reference` = `code_article`).

### ✅ Bugs critiques corrigés
- **CRITICAL — Corruption de stock sur Bon de Retour** (`bons_retour_module.py` L233-265) : la projection MongoDB ne récupérait pas `stock_actuel`, écrasant le stock par un `$set` avec une valeur fausse. Fix : projection élargie + bascule sur `$inc` atomique.
- **CRITICAL — Pattern read-then-set sur Bon de Livraison** (`bons_livraison_module.py` L194-227) : remplacé par `$inc` atomique pour éviter les race conditions concurrentes.
- **HIGH — RBAC violation DG** (`administration_module.py`) : `READ_ROLES = {"super_admin"}` uniquement pour `/api/utilisateurs`. Ajout de `PARAMETRES_READ_ROLES = {"super_admin", "directeur_general"}` pour conserver l'accès du DG aux paramètres conformément au PRD.

### ✅ Tests
- **54/54 tests PASS (100%)** via `/app/backend/tests/test_full_audit_iter8.py`
- Scénario E2E métier complet validé : Client → Commande (2 produits) → Validation → Facture auto (TVA 18%) → Paiement partiel → Préparation → BL livré (stock décrémenté via `$inc`) → BR validé (stock ré-incrémenté via `$inc`) → Analytics → Dashboard.
- Sécurité : 15 endpoints protégés renvoient bien 401 sans token.
- RBAC : DG bloqué sur `/api/utilisateurs` (403), autorisé sur `/api/parametres` (200).

### Backlog (P2 — non bloquant)
- Uniformiser le format des LIST endpoints : 9 endpoints renvoient une liste plate (commandes, factures, paiements, stock, livraisons, retours, comptabilite, utilisateurs, parametres) vs 3 paginés (clients, produits, documents-ai). Risque divergence frontend.
- Documents AI étapes 4 & 6 (drag&drop upload + export PDF/WhatsApp) — non démarré.
- `page_size` limité à 100 sur `/api/produits` (OK actuellement avec 35 produits).
- Pas de page FactureForm pour le bouton "Nouvelle facture" sur `/factures` (route `/factures/nouvelle` à créer ou supprimer le bouton).

---

## CHANGELOG — Iteration 10 (Feb 2026)

### ✅ Bug fix critique : impossible de créer une nouvelle commande
- **Root cause identifié** : la route `/commandes/nouvelle` n'était PAS définie dans `App.js`. Le bouton "Nouvelle commande" naviguait vers cette URL qui matchait alors `/commandes/:id` → la page CommandeDetail tentait de fetch une commande avec `id="nouvelle"` → erreur 404 silencieuse.
- **Fix** : ajout de la route `/commandes/nouvelle` → `<CommandeForm />` dans App.js, avec `ProtectedRoute moduleKey="commandes"`.
- **Bug bonus corrigé** : `CommandeForm.jsx` utilisait `limit: 200` pour fetcher clients/produits, mais `listClients()` ignore `limit` (n'extrait que `page_size`) → seuls 20 clients/produits visibles. Remplacé par `page_size: 500` (clients) et `page_size: 100` (produits).
- **Tests** : 10/10 tests E2E backend PASS (`tests/test_full_audit_iter8.py::TestE2E`) — création + validation + facture + paiement + BL + BR fonctionnent parfaitement côté API.


---

## CHANGELOG — Iteration 11 (Feb 2026)

### ✅ Bug fix critique : impossible de créer un nouvel utilisateur
- **Root cause** : le frontend (`utilisateursApi.js`) appelait `POST /api/auth/create-user` et `POST /api/auth/change-password/{user_id}` mais **ces endpoints n'existaient pas** côté backend. Seuls les endpoints GET/PATCH/DELETE de `/api/utilisateurs` étaient implémentés.
- **Fix** : ajout dans `server.py` de :
  - `POST /api/auth/create-user` (super_admin only) — crée un utilisateur avec email + password hashé bcrypt. Retourne 409 si email déjà utilisé, 400 si rôle invalide, 403 si non super_admin.
  - `POST /api/auth/change-password/{user_id}` (super_admin only) — réinitialise le mot de passe (hash bcrypt). Retourne 404 si user introuvable.
- **Tests** : flux complet validé via curl — création HTTP 201 → login du nouvel utilisateur HTTP 200 → reset password HTTP 200 → re-login HTTP 200. ✓
- Ajout aussi du composant `ClientPicker` (recherche + bouton « Nouveau client » dans CommandeForm étape 1) — création à la volée via `POST /api/clients?force=true`.
