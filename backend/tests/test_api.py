import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as c:
        yield c


def conteneur(t, code):
    return next(c for c in t["conteneurs"] if c["code"] == code)


def test_totaux_des_donnees_d_exemple(client):
    t = client.get("/api/tableau").json()
    assert len(t["conteneurs"]) == 4 and len(t["clients"]) == 7
    assert t["totaux"]["investi"] == 1_069_000_000
    assert t["totaux"]["ventes"] == t["totaux"]["encaisse"] + t["totaux"]["reste"]


def test_calculs_d_un_conteneur(client):
    c1 = conteneur(client.get("/api/tableau").json(), "MDNU 482113 0")
    assert c1["cout_revient"] == 290e6 + 48e6 + 22e6 + 6e6
    # riz : 1000 sacs vendus × 285 000 ; huile : 290 bidons × 390 000
    assert c1["ventes"] == 1000 * 285000 + 290 * 390000
    assert c1["resultat"] == c1["ventes"] - c1["cout_revient"]
    assert c1["valeur_stock"] == 10 * 390000
    assert c1["resultat_prevu"] == c1["resultat"] + c1["valeur_stock"]
    huile = c1["produits"][1]
    assert (huile["vendu"], huile["stock"]) == (290, 10)


def test_statuts_clients(client):
    clients = {k["nom"]: k for k in client.get("/api/clients").json()}
    assert clients["Ibrahima Sow"]["statut"] == "Soldé"
    assert clients["Fatoumata Camara"]["statut"] == "Partiel"
    assert clients["Aïssatou Barry"]["statut"] == "Partiel"  # soldé sur C1, rien payé sur C4
    assert clients["Oumar Kouyaté"]["reste"] == 0


def test_vente_refusee_si_stock_insuffisant(client):
    c1 = conteneur(client.get("/api/tableau").json(), "MDNU 482113 0")
    huile = c1["produits"][1]
    r = client.post("/api/ventes", json={"produit_id": huile["id"], "client_id": 1, "quantite": 11})
    assert r.status_code == 409
    r = client.post("/api/ventes", json={"produit_id": huile["id"], "client_id": 1, "quantite": 10})
    assert r.status_code == 201 and r.json()["montant"] == 3_900_000


def test_paiement_reparti_sur_les_ventes_les_plus_anciennes(client):
    avant = {k["id"]: k for k in client.get("/api/clients").json()}[4]  # Mariama Diallo, rien payé
    assert avant["statut"] == "Impayé"
    r = client.post("/api/paiements", json={"client_id": 4, "montant": 80_000_000})
    assert r.status_code == 201
    aff = r.json()["affectations"]
    assert aff[0]["montant"] == 78_000_000  # 200 bidons d'huile du C1, réglés en entier
    assert sum(a["montant"] for a in aff) == 80_000_000
    apres = {k["id"]: k for k in client.get("/api/clients").json()}[4]
    assert apres["statut"] == "Partiel" and apres["paye"] == 80_000_000


def test_paiement_superieur_a_la_dette_refuse(client):
    du = {k["id"]: k for k in client.get("/api/clients").json()}[2]["reste"]
    assert client.post("/api/paiements", json={"client_id": 2, "montant": du + 1}).status_code == 422
    assert client.post("/api/paiements", json={"client_id": 2, "montant": du}).status_code == 201
    assert {k["id"]: k for k in client.get("/api/clients").json()}[2]["statut"] == "Soldé"


def test_nouveau_conteneur(client):
    r = client.post("/api/conteneurs", json={
        "code": "MDNU 700001 3", "type": "20' DV", "origine": "Anvers, Belgique", "arrivee": "2026-11-02",
        "couts": {"achat": 100_000_000, "fret": 20_000_000},
        "produits": [{"nom": "Ciment 50 kg", "unite": "sacs", "quantite": 500, "prix": 90000}]})
    assert r.status_code == 201
    c = r.json()
    assert c["statut"] == "En distribution" and c["couleur"] == "c1"
    assert c["resultat"] == -120_000_000 and c["resultat_prevu"] == 500 * 90000 - 120_000_000
    assert client.post("/api/conteneurs", json={"code": "MDNU 700001 3", "type": "20' DV", "origine": "x",
                                                "arrivee": "2026-11-02"}).status_code == 409
    assert client.post("/api/conteneurs", json={"code": "ABC", "type": "20' DV", "origine": "x",
                                                "arrivee": "2026-11-02"}).status_code == 422


def test_le_frontend_est_servi(client):
    r = client.get("/")
    assert r.status_code == 200 and "Du bateau" in r.text
