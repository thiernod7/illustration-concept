"""Calculs du suivi : coût de revient, ventes, encaissé, résultat, statuts.

Les règles sont celles de CLAUDE.md ; le frontend ne fait qu'afficher.
"""
import json
import sqlite3
from collections import defaultdict

POSTES = {"achat": "cout_achat", "fret": "cout_fret", "douane": "cout_douane", "manutention": "cout_manutention"}


def statut_paiement(montant: int, paye: int) -> str:
    if paye >= montant:
        return "Soldé"
    return "Partiel" if paye > 0 else "Impayé"


def ventes_avec_paye(conn: sqlite3.Connection, client_id: int | None = None) -> list[sqlite3.Row]:
    """Ventes, avec leur conteneur, leur montant et ce qui en a été payé."""
    sql = """
      SELECT v.*, p.conteneur_id, v.quantite * v.prix AS montant,
             COALESCE((SELECT SUM(a.montant) FROM affectation a WHERE a.vente_id = v.id), 0) AS paye
      FROM vente v JOIN produit p ON p.id = v.produit_id
    """
    if client_id is None:
        return conn.execute(sql + " ORDER BY v.date, v.id").fetchall()
    return conn.execute(sql + " WHERE v.client_id = ? ORDER BY v.date, v.id", (client_id,)).fetchall()


def tableau(conn: sqlite3.Connection) -> dict:
    """Tout ce que l'écran affiche, calculé en une fois."""
    produits = defaultdict(list)
    vendu = defaultdict(int)
    vendu_montant = defaultdict(int)
    ventes = ventes_avec_paye(conn)
    for v in ventes:
        vendu[v["produit_id"]] += v["quantite"]
        vendu_montant[v["produit_id"]] += v["montant"]
    for p in conn.execute("SELECT * FROM produit ORDER BY id"):
        stock = p["quantite"] - vendu[p["id"]]
        produits[p["conteneur_id"]].append({
            "id": p["id"], "nom": p["nom"], "unite": p["unite"], "quantite": p["quantite"],
            "prix": p["prix"], "illustration": p["illustration"],
            "vendu": vendu[p["id"]], "stock": stock, "montant_vendu": vendu_montant[p["id"]],
        })

    # Livraisons : regroupement des ventes par (conteneur, client).
    livraisons: dict[tuple[int, int], dict] = {}
    for v in ventes:
        cle = (v["conteneur_id"], v["client_id"])
        liv = livraisons.setdefault(cle, {
            "conteneur_id": cle[0], "client_id": cle[1], "montant": 0, "paye": 0, "lignes": []})
        liv["montant"] += v["montant"]
        liv["paye"] += v["paye"]
        liv["lignes"].append({"vente_id": v["id"], "produit_id": v["produit_id"],
                              "quantite": v["quantite"], "montant": v["montant"], "date": v["date"]})
    for liv in livraisons.values():
        liv["reste"] = liv["montant"] - liv["paye"]
        liv["statut"] = statut_paiement(liv["montant"], liv["paye"])

    conteneurs = []
    for c in conn.execute("SELECT * FROM conteneur ORDER BY arrivee, id"):
        couts = {k: c[col] for k, col in POSTES.items()}
        prods = produits[c["id"]]
        livs = [l for l in livraisons.values() if l["conteneur_id"] == c["id"]]
        cout = sum(couts.values())
        total_ventes = sum(l["montant"] for l in livs)
        encaisse = sum(l["paye"] for l in livs)
        resultat = total_ventes - cout
        valeur_stock = sum(p["stock"] * p["prix"] for p in prods)
        conteneurs.append({
            "id": c["id"], "code": c["code"], "type": c["type"], "origine": c["origine"],
            "arrivee": c["arrivee"], "statut": c["statut"], "couleur": c["couleur"],
            "couts": couts, "cout_revient": cout, "ventes": total_ventes, "encaisse": encaisse,
            "reste": total_ventes - encaisse, "resultat": resultat,
            "valeur_stock": valeur_stock, "resultat_prevu": resultat + valeur_stock,
            "clients_en_retard": sum(1 for l in livs if l["reste"] > 0),
            "produits": prods,
        })

    clients = []
    for k in conn.execute("SELECT * FROM client ORDER BY id"):
        livs = [l for l in livraisons.values() if l["client_id"] == k["id"]]
        achete = sum(l["montant"] for l in livs)
        paye = sum(l["paye"] for l in livs)
        clients.append({
            "id": k["id"], "nom": k["nom"], "quartier": k["quartier"],
            "apparence": json.loads(k["apparence"]) if k["apparence"] else None,
            "achete": achete, "paye": paye, "reste": achete - paye,
            "statut": statut_paiement(achete, paye),
        })

    totaux = {
        "investi": sum(c["cout_revient"] for c in conteneurs),
        "ventes": sum(c["ventes"] for c in conteneurs),
        "encaisse": sum(c["encaisse"] for c in conteneurs),
        "reste": sum(c["reste"] for c in conteneurs),
        "resultat": sum(c["resultat"] for c in conteneurs),
    }
    return {"totaux": totaux, "conteneurs": conteneurs, "clients": clients,
            "livraisons": list(livraisons.values())}
