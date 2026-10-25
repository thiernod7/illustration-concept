"""Base SQLite : schéma et connexion.

Tous les montants sont des entiers en francs guinéens (GNF, sans centimes).
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("MADINA_DB", Path(__file__).resolve().parents[1] / "madina.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS conteneur (
  id               INTEGER PRIMARY KEY,
  code             TEXT NOT NULL UNIQUE,          -- ISO 6346, ex. « MDNU 482113 0 »
  type             TEXT NOT NULL,                 -- 20' DV, 40' DV, 40' HC
  origine          TEXT NOT NULL,
  arrivee          TEXT NOT NULL,                 -- date ISO
  statut           TEXT NOT NULL DEFAULT 'En distribution'
                   CHECK (statut IN ('En distribution', 'Vendu')),
  couleur          TEXT NOT NULL,                 -- jeton CSS : c1 … c4
  cout_achat       INTEGER NOT NULL DEFAULT 0 CHECK (cout_achat >= 0),
  cout_fret        INTEGER NOT NULL DEFAULT 0 CHECK (cout_fret >= 0),
  cout_douane      INTEGER NOT NULL DEFAULT 0 CHECK (cout_douane >= 0),
  cout_manutention INTEGER NOT NULL DEFAULT 0 CHECK (cout_manutention >= 0)
);

CREATE TABLE IF NOT EXISTS produit (
  id           INTEGER PRIMARY KEY,
  conteneur_id INTEGER NOT NULL REFERENCES conteneur(id),
  nom          TEXT NOT NULL,
  unite        TEXT NOT NULL,                     -- sacs, bidons, cartons, pièces
  quantite     INTEGER NOT NULL CHECK (quantite >= 0),
  prix         INTEGER NOT NULL CHECK (prix >= 0), -- prix de vente unitaire actuel
  illustration TEXT                               -- sac, bidon, carton, pneu…
);

CREATE TABLE IF NOT EXISTS client (
  id        INTEGER PRIMARY KEY,
  nom       TEXT NOT NULL,
  quartier  TEXT NOT NULL,
  apparence TEXT                                  -- JSON : dessin du personnage
);

-- Une vente = une livraison d'un produit (donc d'un conteneur) à un client.
CREATE TABLE IF NOT EXISTS vente (
  id         INTEGER PRIMARY KEY,
  produit_id INTEGER NOT NULL REFERENCES produit(id),
  client_id  INTEGER NOT NULL REFERENCES client(id),
  quantite   INTEGER NOT NULL CHECK (quantite > 0),
  prix       INTEGER NOT NULL CHECK (prix >= 0),  -- figé au moment de la livraison
  date       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paiement (
  id        INTEGER PRIMARY KEY,
  client_id INTEGER NOT NULL REFERENCES client(id),
  montant   INTEGER NOT NULL CHECK (montant > 0),
  date      TEXT NOT NULL
);

-- Répartition d'un paiement sur les ventes qu'il règle.
CREATE TABLE IF NOT EXISTS affectation (
  paiement_id INTEGER NOT NULL REFERENCES paiement(id),
  vente_id    INTEGER NOT NULL REFERENCES vente(id),
  montant     INTEGER NOT NULL CHECK (montant > 0),
  PRIMARY KEY (paiement_id, vente_id)
);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
