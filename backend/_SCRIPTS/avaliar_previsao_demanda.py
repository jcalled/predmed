"""
Avaliação fora da amostra da previsão de demanda v1 (backtesting com corte temporal).

Entrada: ~/PredmedDados/datasus/processado/serie_producao_cirurgica.csv
         (gerada por serie_producao_cirurgica.py; só agregados mensais)
Saída:   backend/avaliacoes/previsao_demanda/avaliacao_AAAAMMDD.json  (versionada no git;
         lida pela API /analytics/validacao-mape e pelo relatório docs/dados/previsao-demanda-v1.md)

Desenho (sem vazamento temporal):
  - origem móvel mensal de 2023-12 a 2026-05: em cada origem o modelo é treinado só com
    competências ≤ origem e prevê 1, 2 e 3 meses à frente (≈ 30/60/90 dias);
  - janela de VALIDAÇÃO (alvos 2024-01..2025-06): usada para ESCOLHER o modelo de cada série;
  - janela de TESTE (alvos 2025-07..2026-06): usada só para REPORTAR o erro do modelo escolhido;
  - origem fixa 2025-06 (treino até 2025-06, previsão de 2025-07..2026-06) como conferência.

Uso:
    backend/venv/bin/python backend/_SCRIPTS/avaliar_previsao_demanda.py [--sem-prophet] [--workers 6]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from services import previsao_avaliacao as pa  # noqa: E402

SERIE_CSV = Path.home() / "PredmedDados" / "datasus" / "processado" / "serie_producao_cirurgica.csv"
ORIGENS = [str(p) for p in pd.period_range("2023-12", "2026-05", freq="M")]
VALIDACAO = ("2024-01", "2025-06")
TESTE = ("2025-07", "2026-06")
ORIGEM_FIXA = "2025-06"
CARATERES = ("TODOS", "ELETIVO")
VOLUME_MINIMO = 30  # média mensal abaixo disso = série de baixo volume (MAPE instável)


def _avaliar_serie(args):
    esp, carater, valores, modelos = args
    y = pd.Series(valores)
    y.index = y.index.astype(str)
    t0 = time.time()
    bt = pa.backtest_origem_movel(y, ORIGENS, modelos, h_max=3, fim=TESTE[1])
    val = pa.resumir(bt, *VALIDACAO)
    tes = pa.resumir(bt, *TESTE)
    # origem fixa
    fixa = []
    treino = y[y.index <= ORIGEM_FIXA]
    alvos = [str(pd.Period(ORIGEM_FIXA, freq="M") + k) for k in range(1, 13)]
    for mod in modelos:
        try:
            prev = pa.prever(mod, treino, 12)
        except Exception:
            continue
        real = [float(y[a]) for a in alvos]
        fixa.append({"modelo": mod, **pa.metricas(real, prev),
                     "mape_h1_3": pa.metricas(real[:3], prev[:3])["mape"],
                     "comparacao_mensal": [{"mes": a, "previsto": int(round(p)), "realizado": int(r)}
                                           for a, p, r in zip(alvos, prev, real)]})
    h1_teste = bt[(bt["h"] == 1) & (bt["alvo"] >= TESTE[0]) & (bt["alvo"] <= TESTE[1])]
    comp_h1 = {mod: [{"mes": r.alvo, "origem": r.origem, "previsto": int(round(r.previsto)),
                      "realizado": int(r.real)} for r in g.itertuples() if not np.isnan(r.previsto)]
               for mod, g in h1_teste.groupby("modelo")}
    return {"especialidade": esp, "carater": carater, "validacao": val, "teste": tes,
            "origem_fixa": fixa, "comparacao_h1_teste": comp_h1,
            "media_mensal_2025": float(y[(y.index >= "2025-01") & (y.index <= "2025-12")].mean()),
            "segundos": round(time.time() - t0, 1)}


def _escolher(val_rows, modelos):
    """Menor MAPE médio (h1..h3) na validação; sMAPE se MAPE indisponível."""
    melhor, melhor_v = None, float("inf")
    for mod in modelos:
        rs = [r for r in val_rows if r["modelo"] == mod and r["horizonte"] in ("h1", "h2", "h3")]
        if len(rs) < 3:
            continue
        vals = [r["mape"] if r["mape"] is not None else r["smape"] for r in rs]
        v = float(np.mean(vals))
        if v < melhor_v:
            melhor, melhor_v = mod, v
    return melhor, round(melhor_v, 2) if melhor else None


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(BACKEND), "rev-parse", "--short", "HEAD"],
                                       text=True, timeout=10).strip()
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", default=str(SERIE_CSV))
    ap.add_argument("--sem-prophet", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--saida", default=pa.PASTA_AVALIACOES)
    ap.add_argument("--so", nargs="*", help="avaliar só estas especialidades (teste rápido)")
    a = ap.parse_args()

    modelos = [m for m in pa.MODELOS if not (a.sem_prophet and m.startswith("prophet"))]
    serie = pd.read_csv(a.serie, dtype={"competencia": str})
    sha = hashlib.sha256(Path(a.serie).read_bytes()).hexdigest()
    serie = serie[serie["carater"].isin(CARATERES)]
    tarefas = []
    for (esp, car), g in serie.groupby(["especialidade", "carater"]):
        if a.so and esp not in a.so:
            continue
        v = g.set_index("competencia")["aihs"].sort_index().astype(float)
        tarefas.append((esp, car, v.to_dict(), modelos))
    print(f"{len(tarefas)} séries × {len(modelos)} modelos × {len(ORIGENS)} origens", flush=True)

    resultados = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(_avaliar_serie, t): t[:2] for t in tarefas}
        for f in as_completed(futs):
            r = f.result()
            resultados.append(r)
            print(f"  {r['especialidade']}/{r['carater']} em {r['segundos']}s", flush=True)

    series_out = []
    for r in sorted(resultados, key=lambda x: (x["carater"], x["especialidade"])):
        escolhido, val_score = _escolher(r["validacao"], modelos)
        teste_esc = {t["horizonte"]: t for t in r["teste"] if t["modelo"] == escolhido}
        base = {t["horizonte"]: t for t in r["teste"] if t["modelo"] == "naive_sazonal"}
        melhor_teste = {}
        for hz in ("h1", "h2", "h3", "trimestre"):
            cands = [t for t in r["teste"] if t["horizonte"] == hz and t["mape"] is not None]
            if cands:
                b = min(cands, key=lambda t: t["mape"])
                melhor_teste[hz] = {"modelo": b["modelo"], "mape": b["mape"]}
        baixo_volume = r["media_mensal_2025"] < VOLUME_MINIMO
        series_out.append({
            "especialidade": r["especialidade"], "carater": r["carater"],
            "media_mensal_2025": round(r["media_mensal_2025"], 1), "baixo_volume": baixo_volume,
            "modelo_escolhido": escolhido, "criterio_escolha_mape_medio_validacao": val_score,
            "teste_modelo_escolhido": {hz: {k: t[k] for k in ("mape", "smape", "mae", "n", "n_real_zero")}
                                       for hz, t in teste_esc.items()},
            "teste_baseline_sazonal": {hz: {k: t[k] for k in ("mape", "smape", "mae", "n")} for hz, t in base.items()},
            "atinge_meta_15": {hz: (t["mape"] is not None and t["mape"] < pa.META_MAPE_PCT)
                               for hz, t in teste_esc.items()},
            "melhor_no_teste_informativo": melhor_teste,
            "validacao": r["validacao"], "teste": r["teste"], "origem_fixa": r["origem_fixa"],
            "comparacao_h1_teste": {k: v for k, v in r["comparacao_h1_teste"].items()
                                    if k in (escolhido, "naive_sazonal")},
        })

    # resumo agregado por modelo (média simples entre séries, só séries sem baixo volume)
    resumo_modelos = []
    for car in CARATERES:
        ss = [s for s in series_out if s["carater"] == car and not s["baixo_volume"]
              and not s["especialidade"].startswith("TOTAL")]
        for mod in modelos:
            for hz in ("h1", "h2", "h3", "trimestre"):
                vals = [t["mape"] for s in ss for t in s["teste"]
                        if t["modelo"] == mod and t["horizonte"] == hz and t["mape"] is not None]
                if vals:
                    resumo_modelos.append({"carater": car, "modelo": mod, "horizonte": hz,
                                           "mape_mediano_especialidades": round(float(np.median(vals)), 2),
                                           "especialidades_abaixo_15": int(sum(v < 15 for v in vals)),
                                           "especialidades": len(vals)})

    hoje = datetime.now()
    saida = {
        "avaliacao_id": f"previsao-demanda-v1-{hoje:%Y%m%d}",
        "versao_metodo": "v1",
        "gerado_em": hoje.isoformat(timespec="seconds"),
        "codigo_git": _git_commit(),
        "status": "avaliacao_fora_da_amostra",
        "alvo": ("Produção cirúrgica mensal SUS no Ceará: nº de AIH principais (IDENT=1) pagas com "
                 "procedimento realizado do grupo SIGTAP 04, por competência de processamento, por "
                 "especialidade da fila. Não é a entrada na fila nem o estoque da fila."),
        "fonte": {"sistema": "SIH-RD/DATASUS (RDCEaamm.dbc)", "serie_csv": str(a.serie).replace(str(Path.home()), "~"),
                  "serie_sha256": sha, "competencias": [serie["competencia"].min(), serie["competencia"].max()],
                  "provisorias": sorted(serie.loc[serie["provisoria"], "competencia"].unique().tolist())},
        "desenho": {"origens": [ORIGENS[0], ORIGENS[-1]], "janela_validacao": list(VALIDACAO),
                    "janela_teste": list(TESTE), "origem_fixa": ORIGEM_FIXA, "horizontes_meses": [1, 2, 3],
                    "horizontes_dias": [30, 60, 90], "trimestre": "erro da soma dos 3 meses seguintes",
                    "selecao": "modelo com menor MAPE médio h1–h3 na janela de validação; teste só reporta",
                    "pandemia": (f"{pa.PANDEMIA_INICIO}..{pa.PANDEMIA_FIM}: variantes 'pos2022' (treino a partir de "
                                 f"{pa.INICIO_POS_PANDEMIA}) e 'imputada' (média do mesmo mês de 2019 e 2022)"),
                    "volume_minimo_mensal": VOLUME_MINIMO},
        "meta_mape_pct": pa.META_MAPE_PCT,
        "modelos": {m: {"descricao": pa.MODELOS[m]["descricao"], "baseline": pa.MODELOS[m]["baseline"]} for m in modelos},
        "resumo_modelos": resumo_modelos,
        "series": series_out,
    }
    Path(a.saida).mkdir(parents=True, exist_ok=True)
    arq = Path(a.saida) / f"avaliacao_{hoje:%Y%m%d}.json"
    arq.write_text(json.dumps(saida, ensure_ascii=False, indent=1))
    print(f"gravado {arq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
