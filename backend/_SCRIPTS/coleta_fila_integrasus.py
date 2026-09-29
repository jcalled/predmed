"""
Coleta diária da fila de espera pública do IntegraSUS (painel 214 — "Consulta da Fila de Espera").

Fonte: o mesmo endpoint JSON que o painel público usa para exibir a fila
(`/api/consulta-fila-espera/consulta-nome-fila-espera`). Diferente do CSV do botão
"Baixar Dados", o JSON traz o campo `data` (data da solicitação), que permite
calcular o tempo de espera. Ver docs/dados/nota-tecnica-integrasus.md.

O que o script faz a cada execução:
1. Baixa a fila completa (uma requisição, com retentativas).
2. Valida o formato (lista de registros com as chaves esperadas).
3. Guarda o JSON bruto compactado (xz) e CRIPTOGRAFADO (Fernet), fora do repositório,
   porque ele contém iniciais e nº de solicitação (dados pessoais — LGPD).
4. Registra um manifesto (JSONL) só com números agregados: total, entradas e saídas
   em relação à coleta anterior, contagem por SWALIS, judicializados, datas mín./máx.

Nunca imprime nem registra linhas de pacientes.

Configuração (variáveis de ambiente):
    PREDMED_DADOS_DIR   pasta de destino (padrão: ~/PredmedDados)
    PREDMED_COLETA_KEY  chave Fernet; se ausente, usa/gera ~/.predmed/coleta.key (chmod 600)

Uso:
    backend/venv/bin/python backend/_SCRIPTS/coleta_fila_integrasus.py
    backend/venv/bin/python backend/_SCRIPTS/coleta_fila_integrasus.py --verificar   # só testa, não grava
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import lzma
import os
import stat
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.fernet import Fernet

URL = ("https://integrasus.saude.ce.gov.br/api/consulta-fila-espera/"
       "consulta-nome-fila-espera?municipio=&procedimento=&especialidade=&estabelecimento=")
CHAVES_ESPERADAS = {"municipio", "estabelecimento", "procedimento", "especialidade",
                    "descSwalis", "mandadoJudicial", "posicao", "nome", "codSolicitacao", "data"}
MINIMO_REGISTROS = 1000  # abaixo disso, a resposta é tratada como falha da fonte
USER_AGENT = "PREDMED-coleta/0.1 (coleta diaria de dados publicos; 1 requisicao/dia)"

DADOS_DIR = Path(os.getenv("PREDMED_DADOS_DIR", Path.home() / "PredmedDados"))
DESTINO = DADOS_DIR / "integrasus" / "fila"
MANIFESTO = DESTINO / "manifesto.jsonl"
CHAVE_PADRAO = Path.home() / ".predmed" / "coleta.key"

log = logging.getLogger("coleta_integrasus")


class ColetaInvalida(Exception):
    pass


# ── Criptografia ────────────────────────────────────────────────
def carregar_chave() -> Fernet:
    chave = os.getenv("PREDMED_COLETA_KEY")
    if chave:
        return Fernet(chave.encode())
    if not CHAVE_PADRAO.exists():
        CHAVE_PADRAO.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(CHAVE_PADRAO.parent, stat.S_IRWXU)
        CHAVE_PADRAO.write_bytes(Fernet.generate_key())
        os.chmod(CHAVE_PADRAO, stat.S_IRUSR | stat.S_IWUSR)
        log.warning("Chave de criptografia criada em %s — faça backup dela: sem a chave, "
                    "as coletas não podem ser lidas.", CHAVE_PADRAO)
    return Fernet(CHAVE_PADRAO.read_bytes().strip())


def ler_snapshot(caminho: Path, fernet: Fernet) -> list[dict]:
    return json.loads(lzma.decompress(fernet.decrypt(caminho.read_bytes())))


# ── Download e validação ────────────────────────────────────────
def baixar(tentativas: int = 3) -> bytes:
    ultimo_erro: Exception | None = None
    for i in range(1, tentativas + 1):
        try:
            r = httpx.get(URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                          timeout=120)
            r.raise_for_status()
            return r.content
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            ultimo_erro = e
            log.warning("Tentativa %d/%d falhou: %s", i, tentativas, type(e).__name__)
            if i < tentativas:
                time.sleep(30 * i)
    raise ColetaInvalida(f"download falhou após {tentativas} tentativas: {ultimo_erro!r}")


def validar(bruto: bytes) -> list[dict]:
    try:
        registros = json.loads(bruto)
    except json.JSONDecodeError as e:
        raise ColetaInvalida(f"resposta não é JSON ({e.msg})") from None
    if not isinstance(registros, list):
        raise ColetaInvalida("resposta não é uma lista")
    if len(registros) < MINIMO_REGISTROS:
        raise ColetaInvalida(f"apenas {len(registros)} registros (mínimo {MINIMO_REGISTROS})")
    faltando = CHAVES_ESPERADAS - set(registros[0])
    if faltando:
        raise ColetaInvalida(f"formato mudou; chaves ausentes: {sorted(faltando)}")
    return registros


# ── Resumo agregado (sem dados pessoais) ────────────────────────
def resumir(registros: list[dict], anterior: list[dict] | None) -> dict:
    datas = sorted(str(r["data"])[:10] for r in registros if r.get("data"))
    resumo = {
        "total": len(registros),
        "com_data": len(datas),
        "data_min": datas[0] if datas else None,
        "data_mediana": datas[len(datas) // 2] if datas else None,
        "data_max": datas[-1] if datas else None,
        "judicializados": sum(1 for r in registros if str(r.get("mandadoJudicial", "")).upper().startswith("S")),
        "por_swalis": dict(Counter(r.get("descSwalis") or "sem classificação" for r in registros)),
        "especialidades": len({r.get("especialidade") for r in registros}),
        "estabelecimentos": len({r.get("estabelecimento") for r in registros}),
    }
    if anterior is not None:
        atuais = {r["codSolicitacao"] for r in registros}
        antes = {r["codSolicitacao"] for r in anterior}
        resumo["entradas"] = len(atuais - antes)
        resumo["saidas"] = len(antes - atuais)
    return resumo


def ultimo_snapshot() -> Path | None:
    arquivos = sorted(DESTINO.glob("*/*/fila_*.json.xz.enc"))
    return arquivos[-1] if arquivos else None


# ── Execução ────────────────────────────────────────────────────
def coletar(verificar: bool = False) -> dict:
    inicio = datetime.now(timezone.utc).astimezone()
    bruto = baixar()
    registros = validar(bruto)

    fernet = carregar_chave()
    anterior_path = ultimo_snapshot()
    anterior = None
    if anterior_path:
        try:
            anterior = ler_snapshot(anterior_path, fernet)
        except Exception as e:  # snapshot anterior ilegível não impede a coleta atual
            log.warning("Não foi possível ler a coleta anterior (%s): %s", anterior_path.name, type(e).__name__)

    resumo = resumir(registros, anterior)
    registro_manifesto = {
        "coletado_em": inicio.isoformat(timespec="seconds"),
        "sha256_bruto": hashlib.sha256(bruto).hexdigest(),
        "bytes_bruto": len(bruto),
        **resumo,
    }

    if verificar:
        log.info("Verificação OK (nada gravado): %s", json.dumps(resumo, ensure_ascii=False))
        return registro_manifesto

    pasta = DESTINO / inicio.strftime("%Y") / inicio.strftime("%m")
    pasta.mkdir(parents=True, exist_ok=True)
    os.chmod(DADOS_DIR, stat.S_IRWXU)
    destino = pasta / f"fila_{inicio.strftime('%Y%m%dT%H%M%S')}.json.xz.enc"
    cifrado = fernet.encrypt(lzma.compress(bruto, preset=6))
    tmp = destino.with_suffix(".tmp")
    tmp.write_bytes(cifrado)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    tmp.rename(destino)  # grava atômico: nunca fica um arquivo pela metade

    registro_manifesto["arquivo"] = str(destino.relative_to(DESTINO))
    registro_manifesto["bytes_gravados"] = len(cifrado)
    with MANIFESTO.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro_manifesto, ensure_ascii=False) + "\n")

    log.info("Coleta gravada: %s (%d registros, %.1f MB) entradas=%s saidas=%s",
             destino.name, resumo["total"], len(cifrado) / 1e6,
             resumo.get("entradas", "-"), resumo.get("saidas", "-"))
    return registro_manifesto


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verificar", action="store_true", help="baixa e valida sem gravar nada")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        coletar(verificar=args.verificar)
    except ColetaInvalida as e:
        log.error("Coleta falhou: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
