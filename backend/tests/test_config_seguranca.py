"""B04 — segredo JWT obrigatório fora de dev, CORS configurável."""
import os
import subprocess
import sys

from tests.conftest import BACKEND_DIR, _TMP_DIR


def _importar_auth(env_extra: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items()
           if k not in ("SECRET_KEY", "APP_ENV", "CORS_ORIGINS")}
    env["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP_DIR, 'sub.db')}"
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", "import auth; print('ok')"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=60,
    )


def test_sem_secret_key_e_sem_app_env_falha():
    r = _importar_auth({})
    assert r.returncode != 0
    assert "SECRET_KEY" in r.stderr


def test_producao_sem_secret_key_falha():
    r = _importar_auth({"APP_ENV": "producao"})
    assert r.returncode != 0
    assert "ConfiguracaoInvalida" in r.stderr


def test_producao_com_secret_key_inicia():
    r = _importar_auth({"APP_ENV": "producao", "SECRET_KEY": "k" * 48})
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_dev_sem_secret_key_inicia_com_segredo_gerado():
    r = _importar_auth({"APP_ENV": "dev"})
    assert r.returncode == 0, r.stderr


def test_cors_configuravel(monkeypatch):
    import config
    monkeypatch.setenv("CORS_ORIGINS", "https://a.exemplo.gov.br, https://b.exemplo.gov.br")
    assert config.get_cors_origins() == ["https://a.exemplo.gov.br", "https://b.exemplo.gov.br"]
    monkeypatch.delenv("CORS_ORIGINS")
    monkeypatch.setattr(config, "MODO_DEV", False)
    assert config.get_cors_origins() == []
    monkeypatch.setattr(config, "MODO_DEV", True)
    assert "http://localhost:3000" in config.get_cors_origins()


def test_senha_seed_fora_de_dev_exige_variavel(monkeypatch):
    import config
    monkeypatch.setattr(config, "MODO_DEV", False)
    monkeypatch.delenv("SEED_SENHA_PADRAO", raising=False)
    monkeypatch.delenv("SEED_SENHA_SESA", raising=False)
    assert config.get_senha_seed("SESA") is None
    monkeypatch.setenv("SEED_SENHA_SESA", "senha-especifica-teste")
    assert config.get_senha_seed("SESA") == "senha-especifica-teste"
