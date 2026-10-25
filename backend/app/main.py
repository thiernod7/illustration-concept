"""API du suivi des conteneurs — Madina (Conakry).

Lancement : uvicorn app.main:app --reload  (depuis backend/)
"""
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date as Date
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .calculs import tableau, ventes_avec_paye
from .seed import seed

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
CODE_ISO = r"^[A-Z]{3}[UJZ] \d{6} \d$"


# ---- schémas d'entrée

class Couts(BaseModel):
    achat: int = Field(0, ge=0)
    fret: int = Field(0, ge=0)
    douane: int = Field(0, ge=0)
    manutention: int = Field(0, ge=0)


class ProduitIn(BaseModel):
    nom: str = Field(min_length=1)
    unite: str = Field(min_length=1)
    quantite: int = Field(ge=0)
    prix: int = Field(ge=0)
    illustration: str | None = None


class ConteneurIn(BaseModel):
    code: str = Field(pattern=CODE_ISO, examples=["MDNU 482113 0"])
    type: Literal["20' DV", "40' DV", "40' HC"]
    origine: str = Field(min_length=1)
    arrivee: Date
    couts: Couts = Couts()
    produits: list[ProduitIn] = []


class StatutIn(BaseModel):
    statut: Literal["En distribution", "Vendu"]


class ClientIn(BaseModel):
    nom: str = Field(min_length=1)
    quartier: str = Field(min_length=1)
    apparence: dict | None = None


class VenteIn(BaseModel):
    produit_id: int
    client_id: int
    quantite: int = Field(gt=0)
    date: Date = Field(default_factory=Date.today)


class PaiementIn(BaseModel):
    client_id: int
    montant: int = Field(gt=0)
    date: Date = Field(default_factory=Date.today)
    ventes: list[int] | None = Field(None, description="Ventes à régler ; par défaut, les plus anciennes d'abord")


# ---- application

def create_app(db_path: Path | str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = db.connect(app.state.db_path)
        db.init(conn)
        seed(conn)
        conn.close()
        yield

    app = FastAPI(title="Suivi des conteneurs — Madina", lifespan=lifespan)
    app.state.db_path = db_path or db.DB_PATH

    def get_conn(request: Request):
        conn = db.connect(request.app.state.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def existe(conn: sqlite3.Connection, table: str, id: int, quoi: str) -> sqlite3.Row:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id,)).fetchone()
        if not row:
            raise HTTPException(404, f"{quoi} introuvable")
        return row

    @app.get("/api/tableau")
    def lire_tableau(conn=Depends(get_conn)):
        """Totaux, conteneurs, clients et livraisons : tout ce que l'écran affiche."""
        return tableau(conn)

    @app.get("/api/conteneurs")
    def lister_conteneurs(conn=Depends(get_conn)):
        return tableau(conn)["conteneurs"]

    @app.get("/api/conteneurs/{conteneur_id}")
    def lire_conteneur(conteneur_id: int, conn=Depends(get_conn)):
        t = tableau(conn)
        for c in t["conteneurs"]:
            if c["id"] == conteneur_id:
                return {**c, "livraisons": [l for l in t["livraisons"] if l["conteneur_id"] == conteneur_id]}
        raise HTTPException(404, "Conteneur introuvable")

    @app.post("/api/conteneurs", status_code=201)
    def creer_conteneur(body: ConteneurIn, conn=Depends(get_conn)):
        n = conn.execute("SELECT COUNT(*) FROM conteneur").fetchone()[0]
        try:
            cid = conn.execute(
                "INSERT INTO conteneur (code, type, origine, arrivee, couleur, cout_achat, cout_fret, cout_douane,"
                " cout_manutention) VALUES (?,?,?,?,?,?,?,?,?)",
                (body.code, body.type, body.origine, body.arrivee.isoformat(), f"c{n % 4 + 1}",
                 body.couts.achat, body.couts.fret, body.couts.douane, body.couts.manutention)).lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Ce numéro de conteneur existe déjà")
        for p in body.produits:
            conn.execute(
                "INSERT INTO produit (conteneur_id, nom, unite, quantite, prix, illustration) VALUES (?,?,?,?,?,?)",
                (cid, p.nom, p.unite, p.quantite, p.prix, p.illustration))
        conn.commit()
        return lire_conteneur(cid, conn)

    @app.patch("/api/conteneurs/{conteneur_id}")
    def changer_statut(conteneur_id: int, body: StatutIn, conn=Depends(get_conn)):
        existe(conn, "conteneur", conteneur_id, "Conteneur")
        conn.execute("UPDATE conteneur SET statut = ? WHERE id = ?", (body.statut, conteneur_id))
        conn.commit()
        return lire_conteneur(conteneur_id, conn)

    @app.get("/api/clients")
    def lister_clients(conn=Depends(get_conn)):
        return tableau(conn)["clients"]

    @app.post("/api/clients", status_code=201)
    def creer_client(body: ClientIn, conn=Depends(get_conn)):
        kid = conn.execute("INSERT INTO client (nom, quartier, apparence) VALUES (?,?,?)",
                           (body.nom, body.quartier, json.dumps(body.apparence) if body.apparence else None)).lastrowid
        conn.commit()
        return next(k for k in tableau(conn)["clients"] if k["id"] == kid)

    @app.post("/api/ventes", status_code=201)
    def creer_vente(body: VenteIn, conn=Depends(get_conn)):
        """Livre un produit d'un conteneur à un client, au prix actuel du produit."""
        produit = existe(conn, "produit", body.produit_id, "Produit")
        existe(conn, "client", body.client_id, "Client")
        deja = conn.execute("SELECT COALESCE(SUM(quantite), 0) FROM vente WHERE produit_id = ?",
                            (body.produit_id,)).fetchone()[0]
        stock = produit["quantite"] - deja
        if body.quantite > stock:
            raise HTTPException(409, f"Stock insuffisant : il reste {stock} {produit['unite']}")
        vid = conn.execute("INSERT INTO vente (produit_id, client_id, quantite, prix, date) VALUES (?,?,?,?,?)",
                           (body.produit_id, body.client_id, body.quantite, produit["prix"],
                            body.date.isoformat())).lastrowid
        conn.commit()
        return {"id": vid, "produit_id": body.produit_id, "client_id": body.client_id, "quantite": body.quantite,
                "prix": produit["prix"], "montant": body.quantite * produit["prix"], "date": body.date.isoformat()}

    @app.post("/api/paiements", status_code=201)
    def creer_paiement(body: PaiementIn, conn=Depends(get_conn)):
        """Enregistre un paiement et le répartit sur les ventes impayées, les plus anciennes d'abord."""
        existe(conn, "client", body.client_id, "Client")
        dues = [v for v in ventes_avec_paye(conn, body.client_id)
                if v["montant"] > v["paye"] and (body.ventes is None or v["id"] in body.ventes)]
        du = sum(v["montant"] - v["paye"] for v in dues)
        if body.montant > du:
            raise HTTPException(422, f"Le paiement dépasse ce que le client doit ({du} GNF)")
        pid = conn.execute("INSERT INTO paiement (client_id, montant, date) VALUES (?,?,?)",
                           (body.client_id, body.montant, body.date.isoformat())).lastrowid
        reste, affectations = body.montant, []
        for v in dues:
            part = min(reste, v["montant"] - v["paye"])
            conn.execute("INSERT INTO affectation (paiement_id, vente_id, montant) VALUES (?,?,?)", (pid, v["id"], part))
            affectations.append({"vente_id": v["id"], "montant": part})
            reste -= part
            if not reste:
                break
        conn.commit()
        return {"id": pid, "client_id": body.client_id, "montant": body.montant, "date": body.date.isoformat(),
                "affectations": affectations}

    if FRONTEND.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
    return app


app = create_app()
