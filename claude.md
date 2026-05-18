# CLAUDE.md — Akwaba Invest

## Comment travailler avec ce projet

### Règles d'interaction
- Tu es un développeur senior qui rejoint un projet existant. Tu lis ce 
  fichier intégralement avant toute action.
- Si une instruction est ambiguë : demande, ne devine pas.
- Si une décision technique non documentée s'impose : propose 2-3 options 
  avec leurs trade-offs, attends validation avant d'implémenter.
- Tu travailles en français pour les échanges avec l'utilisateur. 
  Le code, commits et commentaires restent en anglais.
- Tu ne fais qu'une tâche par session. Si tu détectes une dérive de scope 
  ("au passage j'ai aussi modifié..."), tu t'arrêtes et tu signales.

### Workflow Git obligatoire
1. Toujours créer une branche dédiée : `git checkout -b feature/{task-id}-{short-desc}`
   Exemple : `feature/P0-01-repo-structure`
2. Commits atomiques en anglais conventionnel : feat:, fix:, chore:, test:, docs:
3. Ne JAMAIS commit directement sur main
4. Ne JAMAIS push automatiquement — laisser l'utilisateur valider
5. Avant chaque commit : exécuter les tests pertinents (voir section Tests)

### Documents de référence
En cas d'ambiguïté sur le scope ou les décisions produit, consulter dans cet ordre :
1. `docs/akwaba-invest-recadrage-v1.pdf` — vision, périmètre, fonctionnalités
2. `docs/akwaba-invest-roadmap-v1.pdf` — découpage des tâches par phase
3. Ce fichier (CLAUDE.md) — règles techniques et conventions

---

## Contexte projet

Application mobile **Flutter Android** + backend **FastAPI** pour 
investisseurs particuliers de la **zone UEMOA**. Agrégateur de données 
**BRVM** (Bourse Régionale des Valeurs Mobilières). 

**Promesse produit** : vendre du temps en centralisant l'info dispersée 
de la BRVM. Pas de conseil en investissement — conformité **AMF-UMOA** 
(ex-CREPMF).

**Utilisateurs cibles** : investisseurs particuliers de Côte d'Ivoire, 
Sénégal, Burkina Faso, Mali, Bénin, Togo, Niger, Guinée-Bissau. Réseau 
mobile parfois instable, data coûteuse → l'app doit être fluide offline.

---

## Stack technique — Versions verrouillées

### Backend
- **Python** 3.12 strict (pas 3.11, pas 3.13)
- **FastAPI** 0.110+
- **SQLModel** 0.0.16 (combine SQLAlchemy + Pydantic)
- **Alembic** 1.13+ pour les migrations
- **PostgreSQL** 15
- **pdfplumber** 0.10+ pour le parser BOC
- **firebase-admin** 6.5+ pour vérification JWT et envoi FCM
- **pydantic-settings** 2.2+ pour les variables d'environnement

### Mobile
- **Flutter** 3.19+ stable
- **Dart** 3.3+ null-safety strict
- **Riverpod** 2.5+ (AsyncNotifierProvider pour les états async)
- **GoRouter** 13+ pour la navigation
- **Drift** 2.14+ pour SQLite local
- **Dio** 5+ avec intercepteurs
- **Freezed** + **json_serializable** pour les modèles
- **flutter_secure_storage** 9+ pour le token Firebase
- **firebase_messaging** pour les notifications push

### Infrastructure
- **VPS Hetzner CX22** (Ubuntu 22.04 LTS)
- **Nginx** reverse proxy + **Certbot** Let's Encrypt
- **Cron Linux natif** pour le scheduler BOC (18h GMT quotidien)
- **GitHub Actions** pour CI

---

## Structure du repo

akwaba-invest/
├── backend/
│   ├── app/                    # Code FastAPI
│   ├── alembic/                # Migrations DB
│   ├── tests/                  # Tests pytest
│   ├── scripts/                # Scripts utilitaires (run_boc.py, etc.)
│   ├── requirements.txt
│   └── .env.example
├── flutter/
│   └── akwaba_invest/          # Projet Flutter
├── docs/                       # PDFs recadrage + roadmap
├── .github/
│   └── workflows/              # CI backend + Flutter
├── .gitignore
├── README.md
└── CLAUDE.md                   # Ce fichier

Note : `scripts/` est **toujours dans `backend/scripts/`**, jamais à la 
racine du repo.

---

## Conventions code — Backend

### Architecture en couches strictes
- `models/` — uniquement les classes SQLModel. Aucune logique métier.
- `schemas/` — uniquement les classes Pydantic d'entrée/sortie API.
- `services/` — toute la logique métier. Jamais d'accès direct au framework FastAPI.
- `api/routes/` — uniquement parsing requête + appel service + retour réponse. 
  Aucune logique métier ici.
- `utils/` — fonctions pures réutilisables (parser, calculs, dates).
- `dependencies.py` — toutes les dependencies FastAPI réutilisables.

### Règles non négociables
- Une responsabilité par fichier
- Pas de valeur hardcodée (clés API, URLs, montants) → toujours via config.py
- `secrets.compare_digest` pour toute comparaison de tokens/clés
- Logging structuré avec `logging.getLogger(__name__)`, jamais `print()`
- Transactions atomiques sur toute opération multi-table
- Type hints obligatoires sur toute fonction publique

---

## Conventions code — Flutter

### Architecture feature-first

lib/
├── core/                       # Config globale (theme, router, dio_client)
├── features/
│   └── {feature}/
│       ├── data/               # Repository, DTO, datasources
│       ├── domain/             # Models freezed, providers Riverpod
│       └── presentation/       # Screens, widgets
└── shared/ 

### Règles non négociables
- Null-safety strict, jamais de `!` (sauf cas justifié et commenté)
- Pas de logique métier dans les widgets → toujours dans providers Riverpod
- Tous les modèles de données via Freezed + json_serializable
- Tout appel HTTP via Dio (jamais `http.get` direct)
- Tout state async via AsyncNotifierProvider, jamais `setState` pour data async
- Stockage local via Drift (SQLite) en priorité, SharedPreferences uniquement 
  pour flags simples et `flutter_secure_storage` pour le token Firebase

---

## Stratégie offline-first (critique)

**Pourquoi** : réseau mobile UEMOA instable, data coûteuse pour l'utilisateur, 
fluidité perçue = différenciateur produit. Une app qui s'ouvre instantanément 
même sans réseau est notre avantage concurrentiel.

**Implémentation** :
- **Drift SQLite = source de vérité locale**. L'UI lit Drift, pas l'API.
- **Sync cours BOC** : 1x/jour après 18h GMT. Vérifier 
  `SharedPreferences['last_boc_sync']` au démarrage.
- **Cache fiche action** : durée 24h via `cachedAt` en DB locale. 
  Affichage immédiat du cache + refresh silencieux en background.
- **Portfolio et alertes** : écriture locale immédiate (UI réactive) + 
  sync API en background. En cas d'échec : queue de retry.
- **ConnectivityWrapper** : widget racine qui détecte l'état réseau et 
  affiche un banner "Mode hors ligne — données du JJ/MM" si nécessaire.
- **L'UI doit toujours fonctionner sans réseau.** Si une action requiert 
  obligatoirement le réseau (paiement Wave), bloquer avec message clair.

---

## Schéma PostgreSQL (vue d'ensemble)

Tables principales :
- `stocks` — référentiel actions
- `daily_prices` — cours BOC quotidiens (UNIQUE stock_id, trading_date)
- `financials` — données annuelles CA/résultat/dette
- `dividends` — calendrier dividendes avec dates détachement/paiement
- `users` — utilisateurs (plan: free | premium)
- `subscriptions` — abonnements Wave Business
- `portfolios` + `portfolio_lines` — portefeuilles avec PRU consolidé
- `alerts` — alertes prix/dividendes avec edge-trigger
- `boc_runs` — journal d'idempotence du parser
- `watchlist_items` — actions favorites (optionnel MVP)

Migrations gérées par Alembic uniquement. Jamais de `CREATE TABLE` manuel 
en production.

---

## Règles métier critiques

### PRU consolidé (portfolio)

nouveau_pru = (ancienne_qty × ancien_pru + nouvelle_qty × prix_achat)
/ (ancienne_qty + nouvelle_qty)

Calculé à chaque ajout de ligne. Jamais stocké séparément du portfolio_lines.

### Edge-trigger alertes (anti-spam FCM)
L'alerte ne se déclenche que si `last_trigger_state` change (FALSE → TRUE). 
Une alerte "prix > 5000 FCFA" qui reste vraie pendant 3 jours ne doit 
envoyer qu'**une seule** notification.

### Idempotence parser BOC
- Contrainte `UNIQUE(stock_id, trading_date)` sur `daily_prices`
- Vérifier `boc_runs` avant tout parsing — si déjà parsé, ne pas relancer
- Transaction atomique : tout le BOC du jour ou rien

### Contrôle accès Premium
Vérifier dans cet ordre :
1. `user.plan == 'premium'`
2. `subscription.status == 'active'`
3. `subscription.end_date > now()`

Toute route Premium passe par la dependency `require_premium`.

### Webhook Wave Business
Vérification HMAC obligatoire de la signature **avant** tout upgrade Premium. 
Sans signature valide → 403 immédiat.

---

## Politique de tests

### Backend (pytest)
**Obligatoire** sur :
- Tous les services (logique métier) — couverture minimale 80%
- Le parser BOC (test sur fichiers PDF réels en fixtures)
- Les dependencies critiques (verify_firebase_token, require_premium)
- Tout calcul financier (PRU, rendement, PER)

**Optionnel** sur :
- Routes FastAPI (tests d'intégration end-to-end suffisent)
- Modèles SQLModel (testés indirectement via services)

**Mock obligatoire** : Firebase Auth, Firestore externe, Wave API. 
Jamais d'appel réseau réel dans les tests unitaires.

### Flutter (flutter test)
**Obligatoire** sur :
- Tous les providers Riverpod (logique state)
- Tous les calculs locaux (rendement, projection simulateur)
- Le sync service (avec mock Dio)

**Widget tests** sur les écrans critiques (Dashboard, Fiche Action, Portfolio).

### Lancement avant commit
```bash
# Backend
cd backend && pytest tests/ -v

# Flutter
cd flutter/akwaba_invest && flutter test
```

---

## À NE JAMAIS FAIRE

- **Jamais** commit `.env`, `firebase-service-account.json`, ou tout fichier de credentials
- **Jamais** hardcoder une clé API, un mot de passe, une URL de production
- **Jamais** mock de données en production (pas d'endpoint `/seed-mock` accessible)
- **Jamais** d'endpoint admin sans `verify_admin_key` via `secrets.compare_digest`
- **Jamais** d'accès direct à la DB depuis une route FastAPI (toujours via service)
- **Jamais** de logique métier dans un widget Flutter
- **Jamais** de signal achat/vente automatique (interdiction AMF-UMOA)
- **Jamais** de score type "EXCELLENT / À ÉVITER" sur les actions (assimilable à du conseil)
- **Jamais** push direct sur `main` — toujours via Pull Request validée
- **Jamais** de `print()` en backend — utiliser `logging`
- **Jamais** de `setState` pour de la data async en Flutter — Riverpod uniquement

---

## Modèle économique

- **Gratuit** : cours du jour, fiche action basique, simulateur, dashboard marché
- **Premium** : 2 000 FCFA/mois ou 18 000 FCFA/an
- **Fonctions Premium** : fiche action complète (PER, historique 5 ans), 
  comparateur sectoriel, alertes push FCM, portefeuille avec Total Return
- **Paiement** : Wave Business API uniquement (commission 1%)

---

## Variables d'environnement (.env)

Toujours via `pydantic-settings` dans `config.py`. Le fichier `.env.example` 
documente toutes les variables sans valeurs sensibles.
DATABASE_URL=postgresql://akwaba_user:password@localhost:5432/akwaba_db
FIREBASE_CREDENTIALS_PATH=./firebase-service-account.json
ADMIN_API_KEY=change_me_in_production
WAVE_API_KEY=your_wave_api_key
WAVE_WEBHOOK_SECRET=your_wave_webhook_secret
APP_ENV=development
---

## Commandes utiles

```bash
# Backend
cd backend
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload --port 8000
pytest tests/ -v
pytest tests/test_stock_service.py -v --tb=short
alembic revision --autogenerate -m "add_dividends_table"
alembic upgrade head
alembic downgrade -1

# Flutter
cd flutter/akwaba_invest
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
flutter run
flutter test
flutter build apk --release

# Parser BOC manuel
cd backend
python scripts/run_boc.py --date today
python scripts/run_boc.py --date 2026-05-15
```

---

## Ce que ce projet N'EST PAS

- Pas un conseiller en investissement (pas de signal achat/vente)
- Pas un courtier (pas de passage d'ordres réels)
- Pas un réseau social financier (pas de partage de portefeuille public)
- Pas une app temps réel (BRVM publie en fin de journée via BOC)
- Pas un produit gratuit définitif (modèle freemium dès le départ)