"""
PREDMED — Configuração por variáveis de ambiente.

Regras (B04):
- APP_ENV=dev é o único modo em que existem valores padrão para segredos.
  Se APP_ENV não estiver definida, o app assume "producao" e exige SECRET_KEY.
- Em dev sem SECRET_KEY, gera um segredo aleatório e o guarda em
  backend/.dev-secret-key (ignorado pelo git), para que tokens sobrevivam ao --reload.
- CORS_ORIGINS: lista separada por vírgula. Em dev, padrão localhost:3000.

As variáveis podem vir do ambiente ou de backend/.env (ver .env.example).
O ambiente tem precedência sobre o .env.
"""
import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger("config")

BACKEND_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env", override=False)
except ImportError:  # python-dotenv é opcional
    pass


class ConfiguracaoInvalida(RuntimeError):
    """Configuração obrigatória ausente fora do modo dev."""


APP_ENV = (os.getenv("APP_ENV") or "producao").strip().lower()
MODO_DEV = APP_ENV in ("dev", "desenvolvimento", "development", "local")

# Senha padrão dos usuários de demonstração — usada SOMENTE em APP_ENV=dev.
SENHA_DEMO_DEV = "predmed123"

_DEV_SECRET_FILE = BACKEND_DIR / ".dev-secret-key"


def _segredo_dev() -> str:
    try:
        if _DEV_SECRET_FILE.exists():
            valor = _DEV_SECRET_FILE.read_text().strip()
            if valor:
                return valor
        valor = secrets.token_urlsafe(48)
        _DEV_SECRET_FILE.write_text(valor)
        try:
            _DEV_SECRET_FILE.chmod(0o600)
        except OSError:
            pass
        return valor
    except OSError:
        # Sem permissão de escrita: segredo só deste processo
        return secrets.token_urlsafe(48)


def get_secret_key() -> str:
    valor = os.getenv("SECRET_KEY", "").strip()
    if valor:
        if len(valor) < 32:
            logger.warning("SECRET_KEY tem menos de 32 caracteres; use um valor mais longo.")
        return valor
    if MODO_DEV:
        logger.warning(
            "SECRET_KEY não definida: usando segredo de desenvolvimento gerado localmente "
            "(backend/.dev-secret-key). Nunca use APP_ENV=dev fora da máquina local."
        )
        return _segredo_dev()
    raise ConfiguracaoInvalida(
        "SECRET_KEY é obrigatória fora do modo dev. Defina SECRET_KEY no ambiente "
        "(ex.: python -c \"import secrets; print(secrets.token_urlsafe(48))\") "
        "ou use APP_ENV=dev apenas em desenvolvimento local."
    )


def get_cors_origins() -> list[str]:
    bruto = os.getenv("CORS_ORIGINS", "").strip()
    if bruto:
        return [o.strip() for o in bruto.split(",") if o.strip()]
    if MODO_DEV:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Fora de dev, sem configuração explícita: nenhuma origem cruzada liberada.
    logger.warning("CORS_ORIGINS não definida: nenhuma origem cruzada será permitida.")
    return []


def get_senha_seed(chave: str) -> str | None:
    """
    Senha de um usuário de seed. Ordem: SEED_SENHA_<CHAVE> → SEED_SENHA_PADRAO →
    padrão de dev (só em APP_ENV=dev). Fora de dev sem variável, retorna None
    (o seed não cria o usuário).
    """
    especifica = os.getenv(f"SEED_SENHA_{chave.upper()}", "").strip()
    if especifica:
        return especifica
    padrao = os.getenv("SEED_SENHA_PADRAO", "").strip()
    if padrao:
        return padrao
    if MODO_DEV:
        return SENHA_DEMO_DEV
    return None
