# 🎭 Deauville Festival du Rire

Application de gestion du programme du **Festival du Rire de Deauville**, prévu du 10 au 13 juin 2027.

Ce projet est développé en Python dans le cadre du parcours de programmation orientée objet à l'ECE Paris.

L'application permet aux organisateurs de gérer les spectacles, les artistes, les salles et les inscriptions aux ateliers. Les visiteurs peuvent consulter le programme à travers un site web.

## ✨ Fonctionnalités principales

- **Gestion des artistes** : ajouter et consulter les artistes.
- **Gestion des spectacles** : créer, modifier et annuler des spectacles.
- **Gestion des salles** : consulter les salles et vérifier leur disponibilité.
- **Gestion des ateliers** : inscrire des participants et contrôler les places disponibles.
- **Consultation du programme** : filtrer les spectacles par date et par salle.
- **Spectacles en cours** : consulter les spectacles actuellement programmés et les prochains.
- **API REST** : accéder aux fonctionnalités du festival.
- **Interface d'administration** : gérer les spectacles et les artistes.
- **Interface en ligne de commande (CLI)** : utiliser les principales fonctionnalités depuis le terminal.

### Types de spectacles

L'application prend en charge trois types de spectacles :

| Type | Description |
|---|---|
| Solo | Spectacle présenté par un seul artiste. |
| Lineup | Spectacle composé d'un présentateur et de plusieurs artistes. |
| Workshop | Atelier animé par un professeur avec un nombre limité de participants. |

## 🛠️ Technologies utilisées

- **Python 3.12** : langage principal.
- **FastAPI** : développement de l'API REST.
- **Uvicorn** : serveur web.
- **Pytest** : tests automatisés.
- **Ruff** : formatage et vérification du code.
- **JSON** : stockage des données.
- **uv** : gestion de Python et des dépendances.
- **HTML, CSS et JavaScript** : interfaces web.

## 📁 Architecture du projet

```text
ece-poo-track/
│
├── B1/                     # Exercices du bloc 1
├── B2/                     # Exercices du bloc 2
├── B3/                     # Exercices du bloc 3
├── B4/                     # Exercices du bloc 4
├── B5/                     # Exercices du bloc 5
├── Exercices/              # Solution du exercices 
│
├── src/
│   └── deauville/
│       ├── errors.py       # Gestion des erreurs
│       ├── models.py       # Modèles : Venue, Artist, Performance
│       ├── festival.py     # Logique métier et règles du festival
│       ├── storage.py      # Gestion du stockage
│       ├── api.py          # API REST avec FastAPI
│       ├── cli.py          # Commandes en ligne de commande
│       ├── __main__.py     # Point d'entrée du package
│       └── web/            # Site public et interface admin
│
├── data/
│   └── festival.json       # Données du festival
│
├── tests/                  # Tests automatisés
│
├── pyproject.toml          # Configuration du projet
├── uv.lock                 # Versions des dépendances
└── README.md               # Documentation
```

### Rôle des principaux modules

| Module | Responsabilité |
|---|---|
| `models.py` | Définition des salles, artistes et spectacles. |
| `festival.py` | Gestion du programme et application des règles métier. |
| `errors.py` | Définition des différentes erreurs. |
| `storage.py` | Chargement et sauvegarde des données. |
| `api.py` | Gestion des routes de l'API. |
| `cli.py` | Gestion des commandes du terminal. |

L'organisation sépare les règles métier, les modèles, le stockage et les interfaces. Cela facilite la maintenance et les évolutions du projet.

## 🚀 Installation

### Prérequis

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

### Récupérer le projet

```bash
git clone https://github.com/ayoubbelmaati/projet_track_ayoub_belmaati.git
cd projet_track_ayoub_belmaati
```

### Installer les dépendances

```bash
uv sync
```

## ▶️ Lancement de l'application

Les commandes doivent être exécutées depuis le dossier principal du projet.

### Démarrer le serveur

```bash
uv run deauville serve
```

Le serveur est accessible à l'adresse :

http://127.0.0.1:8000

Pour utiliser un autre port :

```bash
uv run deauville serve --port 9000
```

### Accéder aux interfaces

| Adresse | Description |
|---|---|
| http://127.0.0.1:8000/ | Site web public |
| http://127.0.0.1:8000/admin/ | Interface d'administration |
| http://127.0.0.1:8000/docs | Documentation interactive de l'API |

## 🔌 API REST

L'API permet de consulter et de gérer les informations du festival.

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/festival` | Informations générales du festival |
| GET | `/api/venues` | Liste des salles |
| GET | `/api/artists` | Liste des artistes |
| GET | `/api/artists/{slug}` | Détails d'un artiste et de ses spectacles |
| GET | `/api/programme` | Consultation du programme avec filtres |
| GET | `/api/now` | Spectacles en cours et prochains spectacles |
| GET | `/api/performances/{id}` | Détails d'un spectacle |
| POST | `/api/performances` | Ajouter un spectacle |
| PUT | `/api/performances/{id}` | Modifier un spectacle |
| DELETE | `/api/performances/{id}` | Annuler un spectacle |
| POST | `/api/performances/{id}/participants` | Inscrire un participant à un atelier |
| POST | `/api/artists` | Ajouter un artiste |

### Exemple de filtre du programme

```http
GET /api/programme?day=2027-06-11&venue=le-kiosque
```

Les filtres par date et par salle sont facultatifs.

Pour consulter toutes les routes et tester les requêtes, utiliser la documentation Swagger :

http://127.0.0.1:8000/docs

## 💻 Commandes disponibles (CLI)

L'application peut également être utilisée depuis le terminal.

| Commande | Description |
|---|---|
| `uv run deauville venues` | Afficher les salles |
| `uv run deauville artist <slug>` | Consulter un artiste |
| `uv run deauville programme 2027-06-11` | Afficher le programme d'une journée |
| `uv run deauville now 2027-06-11` | Afficher les spectacles en cours |
| `uv run deauville add` | Ajouter un spectacle |
| `uv run deauville cancel <performance-id>` | Annuler un spectacle |
| `uv run deauville serve` | Démarrer le serveur |

Il est également possible d'utiliser le module Python :

```bash
uv run python -m deauville venues
```

L'option `--data <file>` permet d'utiliser un autre fichier JSON.

## ⚙️ Règles de gestion

Le système vérifie plusieurs règles avant d'accepter une opération.

| Règle | Description |
|---|---|
| Type de spectacle | Seuls les types autorisés sont acceptés. |
| Titre | Le titre ne doit pas être vide. |
| Durée | La durée doit être comprise entre 1 et 360 minutes. |
| Solo | Un artiste est obligatoire. |
| Lineup | Un présentateur et au moins deux artistes différents sont nécessaires. |
| Workshop | Un professeur et au moins une place sont nécessaires. |
| Participants | Seuls les ateliers acceptent des inscriptions. |
| Doublons | Un participant ne peut pas s'inscrire deux fois au même atelier. |
| Capacité | Le nombre de participants ne doit pas dépasser la capacité autorisée. |
| Disponibilité | Une salle ou un artiste ne peut pas être utilisé dans deux spectacles simultanés. |
| Dates | Les spectacles doivent respecter les dates du festival. |

### Gestion des erreurs

Les erreurs sont organisées en plusieurs catégories :

- `InvalidError` : données invalides.
- `NotFoundError` : élément introuvable.
- `ConflictError` : conflit avec une règle métier.
- `StorageError` : problème lié au stockage.

L'API retourne des codes HTTP adaptés :

| Code | Signification |
|---|---|
| 400 | Erreur générale |
| 404 | Élément introuvable |
| 409 | Conflit |
| 422 | Erreur de validation |
| 500 | Erreur interne ou problème de stockage |

## 💾 Stockage des données

Les données du festival sont enregistrées dans un fichier JSON.

Le projet utilise une classe abstraite `Storage` qui définit deux méthodes :

- `load()` : charger les données.
- `save()` : sauvegarder les données.

Deux implémentations sont disponibles :

- `JsonStorage` : stockage dans un fichier JSON.
- `MemoryStorage` : stockage en mémoire, notamment pour les tests.

Cette séparation permet de faire évoluer le système de stockage sans modifier les règles métier.

## 🧪 Tests et qualité du code

Le projet utilise Pytest pour vérifier le bon fonctionnement des différentes fonctionnalités.

### Lancer les tests

```bash
uv run pytest
```

### Formater le code

```bash
uv run ruff format .
```

### Vérifier la qualité du code

```bash
uv run ruff check .
```

### Construire le package

```bash
uv build
```

### Organisation des tests

| Fichier | Description |
|---|---|
| `tests/test_festival.py` | Vérification des règles de gestion du programme. |
| `tests/test_admin.py` | Vérification des modifications, annulations et inscriptions. |
| `tests/test_storage.py` | Vérification du stockage et des fichiers JSON. |
| `tests/test_api.py` | Vérification des routes et des réponses de l'API. |

Les tests utilisent des fichiers temporaires afin de ne pas modifier les données réelles du festival.

## 🔄 Améliorations possibles

Plusieurs évolutions peuvent être envisagées :

- Ajouter une base de données SQLite.
- Mettre en place un système d'authentification.
- Améliorer la gestion des utilisateurs et des droits d'accès.
- Optimiser le chargement et la sauvegarde des données.
- Améliorer les interfaces web.

## ⚠️ Limites connues

- Le fichier `data/festival.json` est recherché depuis le dossier principal du projet, sauf si un autre chemin est indiqué avec `--data`.
- Chaque requête recharge actuellement l'ensemble des données.
- Le verrouillage protège un seul processus serveur.
- Les heures sont gérées en heure locale, sans conversion de fuseau horaire.
- L'identifiant d'un spectacle dépend de sa salle et de son heure de début. Un déplacement peut donc modifier son identifiant.
- La commande `deauville now <day>` affiche uniquement le premier spectacle lorsqu'il y en a plusieurs en cours.

## 👨‍💻 Auteur

**Ayoub Belmaati**

Projet réalisé dans le cadre du parcours de programmation Python à l'ECE Paris.

---

*Deauville Festival du Rire – 10 au 13 juin 2027.*