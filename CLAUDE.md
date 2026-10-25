# Suivi des conteneurs — Madina (Conakry)

## Le besoin, en une phrase
Un importateur de Madina (Conakry, Guinée) fait venir des conteneurs par bateau. Il veut savoir, **pour chaque conteneur** : à quels clients le contenu a été distribué, qui n'a pas encore payé, combien il a gagné ou perdu.

## Le concept
- Un **bateau** arrive au Port autonome de Conakry avec des **conteneurs**.
- Chaque conteneur contient des **produits** (riz, huile, sucre, pâtes, pneus, batteries…), avec une quantité reçue.
- Le contenu d'un conteneur est **distribué à plusieurs clients** (commerçants de Madina, Koloma, Matoto, Kaloum, Bonfi…).
- Un **client peut recevoir des produits de plusieurs conteneurs**, à des moments différents ou en même temps. La relation conteneur ↔ client est donc **plusieurs à plusieurs**.
- Chaque client paie tout, une partie ou rien : il faut suivre les **impayés**.
- L'importateur (le propriétaire des conteneurs) voit le **résultat** de chaque conteneur : bénéfice ou perte.

## Modèle de données
- **Conteneur** : numéro (format ISO 6346, ex. `MDNU 482113 0`), type (20' DV, 40' DV, 40' HC), port d'origine, date d'arrivée, statut (`En distribution` / `Vendu`).
  - Coûts : achat marchandise, fret maritime, dédouanement, manutention & transport.
- **Produit du conteneur** : nom, unité (sacs, bidons, cartons, pièces), quantité reçue, prix de vente unitaire.
- **Client** : nom, quartier / marché.
- **Vente (livraison)** : conteneur, client, produit, quantité, montant = quantité × prix.
- **Paiement** : client, vente(s) concernée(s), montant, date.

## Calculs
- Coût de revient du conteneur = achat + fret + dédouanement + manutention.
- Ventes = Σ des montants vendus du conteneur.
- Encaissé = Σ des paiements reçus. Reste à percevoir = ventes − encaissé.
- **Résultat = ventes − coût de revient**. Il est provisoire tant que le conteneur n'est pas entièrement vendu.
- Valeur du stock restant = Σ (quantité reçue − vendue) × prix.
- Résultat prévu = résultat + valeur du stock restant.
- Statut d'un client : `Soldé` (tout payé), `Partiel`, `Impayé`.
- Monnaie : franc guinéen (GNF), format français (`1 250 000 GNF`, abrégé `1,3 M` / `1,25 Md`).

## Le prototype existant : `suivi-conteneurs.html`
C'est la **référence visuelle et fonctionnelle**. C'est une page HTML autonome (HTML/CSS/JS, sans librairie) avec des données d'exemple.

- Une bande « comment lire » en 4 étapes illustrées : le bateau arrive → on vide le conteneur → les clients sont servis → on suit l'argent.
- Des totaux globaux : investi, ventes, encaissé, reste à percevoir, résultat.
- Une **scène SVG animée** :
  - le navire accoste ;
  - la grue décharge 4 conteneurs sur le quai ;
  - de petits camions (de la couleur du conteneur) partent vers les boutiques des clients.
  - Les clients sont dessinés en personnages (boubou, foulard, turban, kufi) dans des boutiques à auvent, avec leur statut de paiement.
  - L'importateur est représenté sur le quai.
  - Un encadré montre le contenu du conteneur sélectionné, ou ce qu'un client a reçu.
- Onglet **Par conteneur** :
  - la liste des conteneurs ;
  - le détail du conteneur choisi : indicateurs, barre de répartition des coûts, table des produits (reçu / vendu / stock) et table distribution & paiements.
- Onglet **Par client** :
  - chaque client avec les conteneurs dont il a reçu des produits, ce qu'il a acheté, payé et ce qu'il doit encore.
  - Cliquer un client dessine dans la scène tous les conteneurs qui l'ont livré.
- Design :
  - polices Big Shoulders Display (titres), IBM Plex Sans (texte) et IBM Plex Mono (numéros de conteneur) ;
  - une couleur par conteneur ;
  - couleurs de statut vert / orange / rouge ;
  - thème clair et sombre ;
  - respect de `prefers-reduced-motion`.

## Langue
Toute l'interface et les textes sont en **français**.

## Stack du développeur
Python, Django, FastAPI, React.js, React Native, Tailwind CSS.

## Stack du projet (illustration du concept)
- **Backend** : FastAPI + SQLite (`backend/`). Toutes les règles de calcul vivent dans `backend/app/calculs.py` ; montants en GNF **entiers**.
- **Frontend** : la page du prototype (`frontend/index.html`), sans build ; elle lit `GET api/tableau` et ne fait qu'afficher.
- **Paiements** : un paiement est réparti sur les ventes via la table `affectation` (les plus anciennes d'abord). Le prix est figé sur la vente.
- **CI / déploiement** : GitHub Actions lance `pytest`, puis publie une version statique en lecture seule sur GitHub Pages (`scripts/export_static.py`).
