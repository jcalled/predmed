"""
Previsão operacional (30/60/90 dias) da PRODUÇÃO CIRÚRGICA SIH com o modelo VALIDADO de cada série.

Usa a avaliação versionada mais recente (backend/avaliacoes/previsao_demanda/avaliacao_*.json):
  - o modelo de cada série (especialidade × caráter) é o `modelo_escolhido` na janela de validação;
  - a série é a MESMA da avaliação (o sha256 do CSV é conferido; divergência aborta, salvo --forcar);
  - o modelo é treinado com todas as competências disponíveis e prevê os 3 meses seguintes
    (h = 1, 2, 3 meses ≈ 30, 60, 90 dias a partir da última competência consolidada).

Intervalo de previsão (80%, empírico): o modelo escolhido é re-executado com origem móvel sobre a
janela de TESTE da avaliação (alvos fora da amostra); para cada horizonte h calcula-se a razão
real/previsto e o intervalo é previsão × [quantil 10%, quantil 90%] dessas razões (n ≈ 12).
Também confere se o MAPE recalculado bate com o da avaliação.

Alvo: produção cirúrgica registrada no SIH (AIH principais, grupo SIGTAP 04). NÃO é a fila.
Saída: backend/avaliacoes/previsao_demanda/previsao_producao_AAAAMMDD.json (só agregados).

Uso:
    backend/venv/bin/python backend/_SCRIPTS/prever_producao_cirurgica.py [--sem-prophet] [--forcar]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from services import previsao_avaliacao as pa  # noqa: E402

SERIE_CSV = Path.home() / "PredmedDados" / "datasus" / "processado" / "serie_producao_cirurgica.csv"
QUANTIS = (0.10, 0.90)


def _intervalo_empirico(y: pd.Series, modelo: str, janela_teste: list[str]) -> dict:
    """Razões real/previsto do modelo por horizonte, só com alvos da janela de teste."""
    ini, fim = janela_teste
    primeira_origem = str(pd.Period(ini, freq="M") - 3)
    ultima_origem = str(pd.Period(fim, freq="M") - 1)
    origens = [str(p) for p in pd.period_range(primeira_origem, ultima_origem, freq="M")]
    bt = pa.backtest_origem_movel(y, origens, [modelo], h_max=3, fim=fim)
    bt = bt[(bt["alvo"] >= ini) & (bt["alvo"] <= fim)].dropna(subset=["previsto"])
    out = {}
    for h, g in bt.groupby("h"):
        g = g[g["previsto"] > 0]
        razoes = (g["real"] / g["previsto"]).to_numpy()
        m = pa.metricas(g["real"], g["previsto"])
        out[f"h{h}"] = {
            "n": int(len(razoes)),
            "razao_q10": round(float(np.quantile(razoes, QUANTIS[0])), 4) if len(razoes) else None,
            "razao_q90": round(float(np.quantile(razoes, QUANTIS[1])), 4) if len(razoes) else None,
            "mape_recalculado": m["mape"],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", default=str(SERIE_CSV))
    ap.add_argument("--sem-prophet", action="store_true", help="pula séries cujo modelo escolhido é Prophet")
    ap.add_argument("--forcar", action="store_true", help="aceita CSV com sha256 diferente da avaliação")
    a = ap.parse_args()

    aval = pa.carregar_avaliacao_atual()
    if not aval:
        print("ERRO: nenhuma avaliação versionada encontrada")
        return 1
    sha = hashlib.sha256(Path(a.serie).read_bytes()).hexdigest()
    mesma_serie = sha == aval["fonte"]["serie_sha256"]
    if not mesma_serie and not a.forcar:
        print("ERRO: a série atual não é a mesma da avaliação (sha256 diferente). "
              "Rode de novo avaliar_previsao_demanda.py ou use --forcar.")
        return 1

    serie = pd.read_csv(a.serie, dtype={"competencia": str})
    ultima = serie["competencia"].max()
    alvos = [str(pd.Period(ultima, freq="M") + k) for k in (1, 2, 3)]
    janela_teste = aval["desenho"]["janela_teste"]

    saida_series = []
    for s in aval["series"]:
        esp, car, mod = s["especialidade"], s["carater"], s["modelo_escolhido"]
        if not mod or (a.sem_prophet and mod.startswith("prophet")):
            continue
        g = serie[(serie["especialidade"] == esp) & (serie["carater"] == car)]
        y = g.set_index("competencia")["aihs"].sort_index().astype(float)
        prev = pa.prever(mod, y, 3)
        ic = _intervalo_empirico(y, mod, janela_teste)
        pontos = []
        for k, (alvo, p) in enumerate(zip(alvos, prev), 1):
            hz = f"h{k}"
            r = ic.get(hz, {})
            q10, q90 = r.get("razao_q10"), r.get("razao_q90")
            pontos.append({
                "horizonte": hz, "horizonte_dias": pa.HORIZONTE_DIAS[k], "competencia": alvo,
                "previsto": int(round(p)),
                "intervalo_80_inferior": None if q10 is None else int(round(p * min(q10, 1.0))),
                "intervalo_80_superior": None if q90 is None else int(round(p * max(q90, 1.0))),
                "mape_teste_pct": (s["teste_modelo_escolhido"].get(hz) or {}).get("mape"),
                "n_erros_intervalo": r.get("n"),
                "mape_recalculado_pct": r.get("mape_recalculado"),
            })
        hist = y[y.index >= str(pd.Period(ultima, freq="M") - 23)]
        saida_series.append({
            "especialidade": esp, "carater": car, "modelo": mod,
            "modelo_descricao": aval["modelos"].get(mod, {}).get("descricao"),
            "baixo_volume": s.get("baixo_volume"),
            "atinge_meta_15": s.get("atinge_meta_15"),
            "mape_teste_trimestre_pct": (s["teste_modelo_escolhido"].get("trimestre") or {}).get("mape"),
            "previsao": pontos,
            "historico_24m": [{"competencia": c, "aihs": int(v)} for c, v in hist.items()],
        })
        print(f"{esp}/{car} ({mod}): " + ", ".join(f"{p['competencia']}={p['previsto']}" for p in pontos), flush=True)

    hoje = datetime.now()
    out = {
        "previsao_id": f"previsao-producao-v1-{hoje:%Y%m%d}",
        "avaliacao_id": aval["avaliacao_id"],
        "gerado_em": hoje.isoformat(timespec="seconds"),
        "natureza": "estimado",
        "alvo": aval["alvo"],
        "ultima_competencia_observada": ultima,
        "competencias_provisorias": aval["fonte"].get("provisorias", []),
        "serie_sha256": sha, "mesma_serie_da_avaliacao": mesma_serie,
        "intervalo": ("80% empírico: previsão × quantis 10% e 90% da razão real/previsto do mesmo modelo "
                      f"na janela de teste {janela_teste[0]}..{janela_teste[1]} (origem móvel, fora da amostra); "
                      "limites nunca excluem a própria previsão"),
        "horizonte": ("h1/h2/h3 = 1, 2 e 3 competências após a última observada (≈ 30, 60 e 90 dias); "
                      "competência de processamento SIH, não data da cirurgia"),
        "series": saida_series,
    }
    arq = Path(pa.PASTA_AVALIACOES) / f"previsao_producao_{hoje:%Y%m%d}.json"
    arq.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"gravado {arq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
