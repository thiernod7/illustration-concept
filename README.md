# Suivi des conteneurs — Madina (Conakry)

Illustration du concept : pour chaque conteneur arrivé au port de Conakry, à qui le contenu a été distribué, qui n'a pas encore payé, et combien l'importateur a gagné ou perdu. Le besoin et les règles de calcul sont décrits dans [`CLAUDE.md`](CLAUDE.md).

```
frontend/index.html      la page (HTML/CSS/JS sans librairie), lit GET api/tableau
backend/app/db.py        schéma SQLite (montants en GNF entiers)
backend/app/calculs.py   coût de revient, ventes, encaissé, résultat, statuts
backend/app/main.py      API FastAPI ; sert aussi la page
backend/app/seed.py      données d'exemple (celles du prototype)
scripts/export_static.py version statique en lecture seule pour GitHub Pages
```

## Lancer en local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

- Page : http://localhost:8000/
- Documentation interactive de l'API : http://localhost:8000/docs

La base `backend/madina.db` est créée et remplie avec les données d'exemple au premier lancement. Supprimez-la pour repartir de zéro.

Tests : `cd backend && pytest`

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/api/tableau` | totaux, conteneurs, clients et livraisons (ce que la page affiche) |
| GET | `/api/conteneurs`, `/api/conteneurs/{id}` | conteneurs avec leurs calculs |
| POST | `/api/conteneurs` | nouveau conteneur (numéro ISO 6346, coûts, produits) |
| PATCH | `/api/conteneurs/{id}` | changer le statut (`En distribution` / `Vendu`) |
| GET / POST | `/api/clients` | clients avec acheté, payé, reste, statut |
| POST | `/api/ventes` | livrer un produit à un client ; refusé si le stock ne suffit pas ; le prix est figé à la livraison |
| POST | `/api/paiements` | paiement d'un client, réparti sur ses ventes impayées les plus anciennes (ou sur `ventes` indiquées) ; refusé s'il dépasse la dette |

## Déploiement (GitHub Actions)

Le workflow `.github/workflows/ci.yml` lance les tests à chaque push et à chaque pull request. Sur `main`, il publie ensuite la page sur **GitHub Pages**.

GitHub Pages ne sert que des fichiers statiques. Le workflow fige donc la réponse de `api/tableau` (calculée sur les données d'exemple) dans `_site/api/tableau`. La version en ligne est en **lecture seule**.

À faire une fois : *Settings → Pages → Build and deployment → Source : GitHub Actions*.

Pour une version en ligne qui enregistre les ventes et les paiements, il faut héberger le backend sur un serveur Python (Render, Fly.io, Railway, un VPS…). GitHub Actions peut alors déployer vers cet hébergeur.
