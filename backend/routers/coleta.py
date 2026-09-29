"""
Status da coleta automática (IntegraSUS e DATASUS).

Lê SOMENTE agregados dos manifestos gravados pelos scripts de coleta
(backend/_SCRIPTS/coleta_fila_integrasus.py e coleta_datasus.py):

- $PREDMED_DADOS_DIR/integrasus/fila/manifesto.jsonl
- $PREDMED_DADOS_DIR/datasus/manifesto.jsonl

Nunca devolve nomes de arquivo/caminhos nem dados de pacientes: os campos são
copiados por lista de permissão (whitelist), não pelo conteúdo bruto da linha.
Acesso: gestores (SESA e SMS).
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query

from auth import require_gestor
from database import Usuario

logger = logging.getLogger("coleta")

router = APIRouter(prefix="/coleta", tags=["coleta"])

# A fila é coletada às 7h e às 19h (launchd): 12 h entre coletas + margem.
LIMITE_ATRASO_HORAS = 14

# Campos agregados permitidos (nada de arquivo, sha256 ou caminhos).
_CAMPOS_FILA = ("total", "entradas", "saidas", "data_max", "data_min",
                "judicializados", "especialidades", "estabelecimentos")
_CAMPOS_DATASUS = ("fonte", "competencia", "acao", "registros")


def _dados_dir() -> Path:
    return Path(os.getenv("PREDMED_DADOS_DIR", str(Path.home() / "PredmedDados")))


def _parse_data_hora(valor) -> Optional[datetime]:
    if not isinstance(valor, str) or not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor)
    except ValueError:
        return None
    if dt.tzinfo is None:  # sem fuso: assume UTC para não quebrar a comparação
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _ler_manifesto(caminho: Path, campo_data: str) -> list:
    """Linhas válidas do manifesto (JSON por linha), ordenadas pela data. Linhas
    corrompidas são ignoradas (e contadas no log, sem conteúdo)."""
    if not caminho.is_file():
        return []
    linhas, invalidas = [], 0
    try:
        with caminho.open(encoding="utf-8") as f:
            for bruta in f:
                bruta = bruta.strip()
                if not bruta:
                    continue
                try:
                    reg = json.loads(bruta)
                except json.JSONDecodeError:
                    invalidas += 1
                    continue
                dt = _parse_data_hora(reg.get(campo_data)) if isinstance(reg, dict) else None
                if dt is None:
                    invalidas += 1
                    continue
                linhas.append((dt, reg))
    except OSError:
        logger.warning("Manifesto de coleta ilegível (%s)", caminho.name)
        return []
    if invalidas:
        logger.warning("Manifesto %s: %d linha(s) inválida(s) ignorada(s)", caminho.name, invalidas)
    linhas.sort(key=lambda t: t[0])
    return linhas


def _resumo_fila(dt: datetime, reg: dict) -> dict:
    out = {"coletado_em": dt.isoformat()}
    for campo in _CAMPOS_FILA:
        v = reg.get(campo)
        out[campo] = v if isinstance(v, (int, float, str)) and not isinstance(v, bool) else None
    return out


def _resumo_datasus(dt: datetime, reg: dict) -> dict:
    out = {"registrado_em": dt.isoformat()}
    for campo in _CAMPOS_DATASUS:
        v = reg.get(campo)
        out[campo] = v if isinstance(v, (int, float, str)) and not isinstance(v, bool) else None
    return out


def status_coleta(dados_dir: Path, agora: datetime, n: int = 10) -> dict:
    fila = _ler_manifesto(dados_dir / "integrasus" / "fila" / "manifesto.jsonl", "coletado_em")
    datasus = _ler_manifesto(dados_dir / "datasus" / "manifesto.jsonl", "registrado_em")

    ultima = _resumo_fila(*fila[-1]) if fila else None
    if fila:
        horas = round((agora - fila[-1][0]).total_seconds() / 3600, 1)
        atrasada = horas > LIMITE_ATRASO_HORAS
    else:
        horas, atrasada = None, True

    # DATASUS: último registro por fonte (SIH-RD, CNES-*), mais recente primeiro
    por_fonte: dict = {}
    for dt, reg in datasus:
        fonte = reg.get("fonte")
        if isinstance(fonte, str):
            por_fonte[fonte] = _resumo_datasus(dt, reg)

    return {
        "verificado_em": agora.isoformat(),
        "fila": {
            "limite_atraso_horas": LIMITE_ATRASO_HORAS,
            "atrasada": atrasada,
            "horas_desde_ultima": horas,
            "total_coletas": len(fila),
            "ultima": ultima,
            "ultimas": [_resumo_fila(dt, reg) for dt, reg in reversed(fila[-n:])],
        },
        "datasus": {
            "total_registros": len(datasus),
            "ultimo_registro_em": datasus[-1][0].isoformat() if datasus else None,
            "por_fonte": sorted(por_fonte.values(), key=lambda r: r["registrado_em"], reverse=True),
        },
    }


@router.get("/status")
def get_status_coleta(
    n: int = Query(10, ge=1, le=60, description="Quantidade de coletas recentes da fila"),
    user: Usuario = Depends(require_gestor),
):
    """Situação da coleta automática (apenas agregados dos manifestos)."""
    return status_coleta(_dados_dir(), datetime.now(timezone.utc), n=n)
