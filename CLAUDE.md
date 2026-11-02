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

## Reprise des habitudes d'Invoice Manager
Le client utilisait **Invoice Manager** (application mobile de facturation). La nouvelle application doit garder ses repères, en les rattachant aux conteneurs :

| Invoice Manager | Dans notre application |
|---|---|
| Facture (n°, date, client, articles, total, solde) | **Facture** `FAC-2026-008` : chaque ligne porte son **conteneur d'origine** ; une facture peut mélanger plusieurs conteneurs |
| Paiement (date, montant, remarque, « plein payé maintenant », reçu) | **Paiement** daté, avec mode (Espèces, Orange Money, MTN MoMo, virement) ; plusieurs paiements par facture ; solde de facture |
| Client / Fournisseur, solde d'ouverture (Recevoir / Donner), limite de crédit | **Client** avec limite de crédit (alerte si dépassée) ; **Fournisseur** du conteneur, avec ce qui lui a été versé sur l'achat |
| Produit, inventaire, état des stocks | Produits **du conteneur** : reçu / vendu / en stock |
| Dépenses | Coûts du conteneur : fret, dédouanement, manutention |
| Rapports : factures impayées par client, facture vieillissante, ventes par client / par produit (top 5), profit et perte | Onglet **Rapports** : impayés par ancienneté (0–30, 31–60, 61–90, +90 j), top 5 clients, top 5 produits ; résultat par conteneur |
| Aperçu PDF, signature client, notes / CGV, notes privées | Aperçu de facture avec signature et CGV (modèles PDF, logo : plus tard) |
| Note de crédit, retour des ventes | **Avoir** `AV-2026-001` rattaché à une facture, une vente et donc un **conteneur** (voir « Retours et avoirs ») |
| Estimation, bon de commande, note de livraison | Hors maquette |

Ajouts au modèle de données : **Facture** (n°, client, date, lignes = ventes), **Paiement** (facture, date, montant, mode), **Fournisseur** (nom, montant versé), **Client.limite de crédit**, **Avoir** (n°, facture, vente, quantité, type, date, motif).

## Retours et avoirs
Un avoir porte sur une ligne de facture, donc sur un produit d'un conteneur. Montant = quantité × prix de la vente. Trois types :
- **Repris · remis en stock** : la marchandise revient dans le conteneur. Vendu − q, stock + q, ventes − montant.
- **Repris · mis au rebut** : la marchandise revient mais ne peut pas être revendue. Vendu − q, stock inchangé, ventes − montant (perte pour le conteneur).
- **Avoir sans retour** (remise, marchandise abîmée gardée par le client) : quantités inchangées, ventes − montant.

Imputation : si la facture n'est pas encore payée, l'avoir est **déduit de la facture** (solde = total − avoirs − payé). Si elle est déjà payée, il devient un **crédit client**, à déduire d'une prochaine facture ou à rembourser. Les ventes, le résultat et le stock des conteneurs sont toujours calculés **après avoirs**.

## Langue
Toute l'interface et les textes sont en **français**.

## Stack du développeur
Python, Django, FastAPI, React.js, React Native, Tailwind CSS.
