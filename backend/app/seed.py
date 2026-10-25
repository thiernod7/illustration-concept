"""Données d'exemple : celles du prototype HTML."""
import json
import sqlite3

CONTENEURS = [
    ("MDNU 482113 0", "40' HC", "Guangzhou, Chine", "2026-07-28", "Vendu", "c1", (290e6, 48e6, 22e6, 6e6),
     [("Riz parfumé 25 kg", "sacs", 1000, 285000, "sac"), ("Huile végétale 20 L", "bidons", 300, 390000, "bidon")]),
    ("MDNU 517390 4", "20' DV", "Mersin, Turquie", "2026-08-21", "Vendu", "c2", (98e6, 28e6, 9e6, 3e6),
     [("Pâtes alimentaires 500 g", "cartons", 800, 95000, "carton"), ("Tomate concentrée", "cartons", 600, 120000, "tomate")]),
    ("MDNU 603218 7", "40' DV", "Jebel Ali, Dubaï", "2026-09-10", "Vendu", "c3", (150e6, 34e6, 14e6, 5e6),
     [("Pneus moto 2.75-17", "pièces", 900, 160000, "pneu"), ("Batteries 12 V", "pièces", 400, 210000, "batterie")]),
    ("MDNU 640055 2", "40' HC", "Ningbo, Chine", "2026-10-18", "En distribution", "c4", (290e6, 46e6, 20e6, 6e6),
     [("Sucre 50 kg", "sacs", 700, 420000, "sucre"), ("Lait en poudre", "cartons", 400, 260000, "lait")]),
]

CLIENTS = [
    ("El Hadj Mamadou Bah", "Madina Marché", {"skin": "#6B4423", "head": "turban", "hc": "#F2EFE6", "cloth": "#E6E0D0", "awn": "#2C7D69"}),
    ("Fatoumata Camara", "Madina Rail", {"skin": "#8A5A3B", "head": "wrap", "hc": "#D9532B", "cloth": "#F0B429", "awn": "#D9532B"}),
    ("Ibrahima Sow", "Koloma", {"skin": "#5A3A22", "head": "kufi", "hc": "#3B5A9C", "cloth": "#4A6BB0", "awn": "#3B5A9C"}),
    ("Mariama Diallo", "Matoto", {"skin": "#7A4E2F", "head": "wrap", "hc": "#7B3FA0", "cloth": "#2E8B7A", "awn": "#7B3FA0"}),
    ("Oumar Kouyaté", "Kaloum", {"skin": "#4E321D", "head": "none", "hc": "#1A1A1A", "cloth": "#C98F1E", "awn": "#C98F1E"}),
    ("Aïssatou Barry", "Madina Dispensaire", {"skin": "#93613F", "head": "wrap", "hc": "#2C7D69", "cloth": "#C4532D", "awn": "#2C7D69"}),
    ("Moussa Keïta", "Bonfi", {"skin": "#62402A", "head": "cap", "hc": "#24323D", "cloth": "#6F7F8A", "awn": "#C4532D"}),
]

# (conteneur, client, produit, quantité, part payée) — indices à partir de 1
VENTES = [
    (1, 1, 0, 300, 1), (1, 2, 0, 250, .6), (1, 2, 1, 90, .6), (1, 3, 0, 250, 1), (1, 6, 0, 200, 1), (1, 4, 1, 200, 0),
    (2, 5, 0, 300, 1), (2, 1, 0, 250, 1), (2, 7, 0, 150, .5), (2, 5, 1, 200, 1), (2, 7, 1, 250, .5), (2, 2, 1, 100, 0),
    (3, 7, 0, 400, .75), (3, 3, 0, 300, 1), (3, 4, 0, 150, 0), (3, 7, 1, 200, .75), (3, 3, 1, 150, 1),
    (4, 1, 0, 200, .5), (4, 6, 0, 150, 0), (4, 2, 0, 120, .3), (4, 6, 1, 100, 0), (4, 4, 1, 80, 0),
]


def seed(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT 1 FROM conteneur LIMIT 1").fetchone():
        return
    produits = {}  # (conteneur, rang) -> (id, prix)
    arrivees = {}
    for code, typ, origine, arrivee, statut, couleur, couts, prods in CONTENEURS:
        cid = conn.execute(
            "INSERT INTO conteneur (code, type, origine, arrivee, statut, couleur, cout_achat, cout_fret,"
            " cout_douane, cout_manutention) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (code, typ, origine, arrivee, statut, couleur, *map(int, couts))).lastrowid
        arrivees[cid] = arrivee
        for i, (nom, unite, qte, prix, illu) in enumerate(prods):
            pid = conn.execute(
                "INSERT INTO produit (conteneur_id, nom, unite, quantite, prix, illustration) VALUES (?,?,?,?,?,?)",
                (cid, nom, unite, qte, prix, illu)).lastrowid
            produits[(cid, i)] = (pid, prix)
    for nom, quartier, look in CLIENTS:
        conn.execute("INSERT INTO client (nom, quartier, apparence) VALUES (?,?,?)", (nom, quartier, json.dumps(look)))
    for cid, kid, rang, qte, part in VENTES:
        pid, prix = produits[(cid, rang)]
        date = arrivees[cid]
        vid = conn.execute("INSERT INTO vente (produit_id, client_id, quantite, prix, date) VALUES (?,?,?,?,?)",
                           (pid, kid, qte, prix, date)).lastrowid
        montant = round(qte * prix * part)
        if montant:
            paid = conn.execute("INSERT INTO paiement (client_id, montant, date) VALUES (?,?,?)",
                                (kid, montant, date)).lastrowid
            conn.execute("INSERT INTO affectation (paiement_id, vente_id, montant) VALUES (?,?,?)", (paid, vid, montant))
    conn.commit()
