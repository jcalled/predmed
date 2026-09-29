"""
PREDMED — Previsão operacional da produção cirúrgica SIH (30/60/90 dias) para a tela
"Previsão de demanda". Lê o JSON versionado gerado por _SCRIPTS/prever_producao_cirurgica.py
(backend/avaliacoes/previsao_demanda/previsao_producao_AAAAMMDD.json), que usa o modelo
escolhido na avaliação fora da amostra (docs/dados/previsao-demanda-v1.md).

Alvo: produção cirúrgica registrada no SIH (AIH principais, grupo SIGTAP 04). NÃO é a fila.
Natureza do número: "estimado" (saída de modelo), com o MAPE medido na avaliação ao lado.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Dict, Optional

from services.previsao_avaliacao import PASTA_AVALIACOES, serie_da_especialidade

_CACHE: Dict[str, Dict] = {}


def caminho_previsao_atual(pasta: str = PASTA_AVALIACOES) -> Optional[str]:
    arquivos = sorted(glob.glob(os.path.join(pasta, "previsao_producao_*.json")))
    return arquivos[-1] if arquivos else None


def carregar_previsao_atual(pasta: str = PASTA_AVALIACOES) -> Optional[Dict]:
    caminho = caminho_previsao_atual(pasta)
    if not caminho:
        return None
    chave = f"{caminho}:{os.path.getmtime(caminho)}"
    prev = _CACHE.get(chave)
    if prev is None:
        with open(caminho, encoding="utf-8") as f:
            prev = json.load(f)
        _CACHE.clear()
        _CACHE[chave] = prev
    return prev


def _cabecalho(prev: Dict) -> Dict:
    return {
        "previsao_id": prev["previsao_id"],
        "avaliacao_id": prev["avaliacao_id"],
        "gerado_em": prev["gerado_em"],
        "natureza": "estimado",
        "alvo": prev["alvo"],
        "alvo_resumo": "Produção cirúrgica SUS registrada no SIH (AIH principais do grupo SIGTAP 04). Não é a fila.",
        "ultima_competencia_observada": prev["ultima_competencia_observada"],
        "competencias_provisorias": prev.get("competencias_provisorias", []),
        "intervalo_metodo": prev["intervalo"],
        "horizonte_metodo": prev["horizonte"],
        "meta_mape_pct": 15.0,
    }


def previsao_producao_para_api(especialidade: Optional[str] = None, carater: str = "TODOS",
                               prev: Optional[Dict] = None) -> Dict:
    prev = prev if prev is not None else carregar_previsao_atual()
    if not prev:
        return {"status": "indisponivel", "natureza": "nao_validado",
                "mensagem": "Previsão da produção cirúrgica não gerada (rode _SCRIPTS/prever_producao_cirurgica.py)."}
    nome = serie_da_especialidade(especialidade)
    carater = (carater or "TODOS").upper()
    s = next((x for x in prev["series"] if x["especialidade"] == nome and x["carater"] == carater), None)
    especialidades = sorted({x["especialidade"] for x in prev["series"]
                             if x["carater"] == carater and not x["especialidade"].startswith("TOTAL")})
    base = {**_cabecalho(prev), "especialidade": (especialidade or "TOTAL").upper(), "serie": nome,
            "carater": carater, "especialidades_disponiveis": especialidades}
    if s is None:
        return {**base, "status": "sem_serie", "previsao": [], "historico": []}
    return {
        **base,
        "status": "ok",
        "modelo": s["modelo"],
        "modelo_descricao": s.get("modelo_descricao"),
        "baixo_volume": s.get("baixo_volume"),
        "atinge_meta_15": s.get("atinge_meta_15"),
        "mape_por_horizonte": {p["horizonte"]: p["mape_teste_pct"] for p in s["previsao"]},
        "mape_trimestre_pct": s.get("mape_teste_trimestre_pct"),
        "previsao": s["previsao"],
        "historico": s["historico_24m"],
    }


def resumo_producao_para_api(carater: str = "TODOS", prev: Optional[Dict] = None) -> Dict:
    """Uma linha por especialidade: previsão 30/60/90 dias + MAPE do teste."""
    prev = prev if prev is not None else carregar_previsao_atual()
    if not prev:
        return {"status": "indisponivel", "natureza": "nao_validado", "por_especialidade": []}
    carater = (carater or "TODOS").upper()
    linhas = []
    for s in prev["series"]:
        if s["carater"] != carater:
            continue
        ult = s["historico_24m"][-1]["aihs"] if s["historico_24m"] else None
        linhas.append({
            "especialidade": s["especialidade"],
            "modelo": s["modelo"],
            "baixo_volume": s.get("baixo_volume"),
            "ultimo_mes_observado": ult,
            "previsao": {p["horizonte"]: {k: p[k] for k in ("competencia", "previsto", "intervalo_80_inferior",
                                                              "intervalo_80_superior", "mape_teste_pct")}
                         for p in s["previsao"]},
            "atinge_meta_15": s.get("atinge_meta_15"),
        })
    linhas.sort(key=lambda x: (x["especialidade"].startswith("TOTAL") is False, -(x["ultimo_mes_observado"] or 0)))
    return {**_cabecalho(prev), "status": "ok", "carater": carater, "por_especialidade": linhas}
