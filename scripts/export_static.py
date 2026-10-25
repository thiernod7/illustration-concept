"""Exporte une version statique (lecture seule) pour GitHub Pages.

Copie frontend/ dans le dossier de sortie et y écrit api/tableau, calculé par le
backend sur les données d'exemple. La page fonctionne alors sans serveur.

Usage : python scripts/export_static.py _site
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend"))

from app import db  # noqa: E402
from app.calculs import tableau  # noqa: E402
from app.seed import seed  # noqa: E402

sortie = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
shutil.rmtree(sortie, ignore_errors=True)
shutil.copytree(RACINE / "frontend", sortie)
with tempfile.TemporaryDirectory() as tmp:
    conn = db.connect(Path(tmp) / "export.db")
    db.init(conn)
    seed(conn)
    (sortie / "api").mkdir()
    (sortie / "api" / "tableau").write_text(json.dumps(tableau(conn), ensure_ascii=False), encoding="utf-8")
    conn.close()
(sortie / ".nojekyll").touch()
print(f"Site statique écrit dans {sortie}/")
