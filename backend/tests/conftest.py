"""
Configuração dos testes: banco SQLite temporário e dados 100% sintéticos.
Nunca aponta para backend/predmed.db nem predmed-original.db.
"""
import os
import sys
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="predmed-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP_DIR, 'teste.db')}"
os.environ["APP_ENV"] = "teste"
os.environ["SECRET_KEY"] = "segredo-de-teste-" + "x" * 40
os.environ.pop("SEED_SENHA_PADRAO", None)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402

import database  # noqa: E402

# Proteção: os testes só rodam contra o banco temporário.
assert _TMP_DIR in database.DATABASE_URL


@pytest.fixture()
def db():
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    sessao = database.SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()
