"""
Pseudonimização de identificadores de pacientes (LGPD).

O nº de solicitação do IntegraSUS identifica o pedido de um paciente. Guardamos
apenas um HMAC-SHA256 dele: permite acompanhar o mesmo pedido entre coletas
(entrada, saída, tempo de espera) sem armazenar o número original.

Chave: variável PREDMED_PSEUDO_KEY ou arquivo ~/.predmed/pseudo.key (criado na
primeira execução, permissão 600). Trocar a chave quebra o vínculo com os
hashes já gravados — guarde-a junto com a chave das coletas.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import stat
from functools import lru_cache
from pathlib import Path

CHAVE_PADRAO = Path.home() / ".predmed" / "pseudo.key"


@lru_cache(maxsize=1)
def _chave() -> bytes:
    chave = os.getenv("PREDMED_PSEUDO_KEY")
    if chave:
        return chave.encode()
    if not CHAVE_PADRAO.exists():
        CHAVE_PADRAO.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(CHAVE_PADRAO.parent, stat.S_IRWXU)
        CHAVE_PADRAO.write_text(secrets.token_hex(32))
        os.chmod(CHAVE_PADRAO, stat.S_IRUSR | stat.S_IWUSR)
    return CHAVE_PADRAO.read_text().strip().encode()


def pseudonimizar(valor) -> str | None:
    """HMAC-SHA256 hexadecimal do identificador, ou None se vazio."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return hmac.new(_chave(), texto.encode(), hashlib.sha256).hexdigest()
