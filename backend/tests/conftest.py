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


SENHA_TESTE = "senha-sintetica-de-teste"


@pytest.fixture()
def client(db):
    """TestClient sem disparar o evento de startup (que rodaria o seed)."""
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)


def criar_usuario(db, email, role, tenant_kwargs):
    from database import Tenant, Usuario
    from auth import hash_password
    t = Tenant(**tenant_kwargs)
    db.add(t)
    db.flush()
    u = Usuario(nome=email.split("@")[0], email=email, senha_hash=hash_password(SENHA_TESTE),
                role=role, tenant_id=t.id)
    db.add(u)
    db.commit()
    return u, t


def token(client, email):
    r = client.post("/auth/login", json={"email": email, "password": SENHA_TESTE})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
