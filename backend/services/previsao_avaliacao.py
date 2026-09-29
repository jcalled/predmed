"""
PREDMED — Avaliação fora da amostra da previsão de demanda (v1).

Alvo: produção cirúrgica mensal do SUS no Ceará (SIH-RD, grupo SIGTAP 04, AIH principal),
por especialidade da fila — série gerada por _SCRIPTS/serie_producao_cirurgica.py.
Relatório: docs/dados/previsao-demanda-v1.md. Execução: _SCRIPTS/avaliar_previsao_demanda.py.

Este módulo tem:
  - os modelos comparados (baselines ingênuos, Holt-Winters, SARIMA e Prophet);
  - o backtesting com origem móvel (janela expansível), sem vazamento temporal;
  - as métricas (MAPE, sMAPE, MAE);
  - a leitura da avaliação versionada (JSON em backend/avaliacoes/previsao_demanda/),
    usada pela API /analytics/validacao-mape para exibir a MESMA avaliação do relatório.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import warnings
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

META_MAPE_PCT = 15.0
PANDEMIA_INICIO, PANDEMIA_FIM = "2020-03", "2021-12"
INICIO_POS_PANDEMIA = "2022-01"
PASTA_AVALIACOES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "avaliacoes", "previsao_demanda")
HORIZONTE_DIAS = {1: 30, 2: 60, 3: 90}


# ──────────────────────────────────────────────
# Métricas
# ──────────────────────────────────────────────
def metricas(real, previsto) -> Dict[str, Optional[float]]:
    r = np.asarray(real, dtype=float)
    p = np.asarray(previsto, dtype=float)
    if r.size == 0:
        return {"mape": None, "smape": None, "mae": None, "n": 0, "n_real_zero": 0}
    nz = r > 0
    mape = float(np.mean(np.abs(p[nz] - r[nz]) / r[nz]) * 100) if nz.any() else None
    den = np.abs(r) + np.abs(p)
    ok = den > 0
    smape = float(np.mean(2 * np.abs(p[ok] - r[ok]) / den[ok]) * 100) if ok.any() else 0.0
    mae = float(np.mean(np.abs(p - r)))
    return {"mape": None if mape is None else round(mape, 2), "smape": round(smape, 2),
            "mae": round(mae, 1), "n": int(r.size), "n_real_zero": int((~nz).sum())}


# ──────────────────────────────────────────────
# Tratamento da pandemia
# ──────────────────────────────────────────────
def imputar_pandemia(y: pd.Series) -> pd.Series:
    """Substitui 2020-03..2021-12 pela média do mesmo mês em 2019 e 2022 (contrafactual simples).
    Usa só meses anteriores a qualquer origem de previsão avaliada (≥ 2023-12)."""
    y = y.copy()
    for comp in pd.period_range(PANDEMIA_INICIO, PANDEMIA_FIM, freq="M"):
        refs = [str(pd.Period(f"{a}-{comp.month:02d}", freq="M")) for a in (2019, 2022)]
        vals = [y[r] for r in refs if r in y.index]
        if vals and str(comp) in y.index:
            y[str(comp)] = float(np.mean(vals))
    return y


def _preparar(y: pd.Series, variante: str) -> pd.Series:
    if variante == "pos2022":
        return y[y.index >= INICIO_POS_PANDEMIA]
    if variante == "imputada":
        return imputar_pandemia(y)
    return y


# ──────────────────────────────────────────────
# Modelos: f(y_treino: pd.Series indexada 'AAAA-MM', h) -> np.ndarray (h,)
# ──────────────────────────────────────────────
def m_naive_ultimo(y: pd.Series, h: int) -> np.ndarray:
    return np.repeat(float(y.iloc[-1]), h)


def m_naive_sazonal(y: pd.Series, h: int) -> np.ndarray:
    return np.array([float(y.iloc[-12 + (i % 12)]) for i in range(h)])


def m_naive_sazonal_nivel(y: pd.Series, h: int) -> np.ndarray:
    """Sazonal ingênuo ajustado pelo nível: y[t-12] × (média últimos 3 / média dos mesmos 3 um ano antes)."""
    base = m_naive_sazonal(y, h)
    ant = y.iloc[-15:-12].mean()
    fator = (y.iloc[-3:].mean() / ant) if ant > 0 else 1.0
    return base * fator


def _hw(y: pd.Series, h: int) -> np.ndarray:
    """Holt-Winters com a mesma configuração do módulo atual (analytics_sih/previsoes_ml)."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    v = y.values.astype(float)
    n = len(v)
    seasonal = "mul" if (n >= 24 and (v > 0).all()) else ("add" if n >= 24 else None)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(v, trend="add", seasonal=seasonal,
                                   seasonal_periods=12 if seasonal else None,
                                   initialization_method="estimated").fit(optimized=True)
        return np.asarray(fit.forecast(h))


def _sarima(y: pd.Series, h: int) -> np.ndarray:
    """SARIMA 'airline' (0,1,1)(0,1,1)12 em log(1+y)."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    v = np.log1p(y.values.astype(float))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = SARIMAX(v, order=(0, 1, 1), seasonal_order=(0, 1, 1, 12),
                      enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        return np.expm1(np.asarray(fit.forecast(h)))


def _prophet(y: pd.Series, h: int) -> np.ndarray:
    import logging as _lg
    _lg.getLogger("cmdstanpy").setLevel(_lg.ERROR)
    _lg.getLogger("prophet").setLevel(_lg.ERROR)
    from prophet import Prophet
    df = pd.DataFrame({"ds": pd.PeriodIndex(y.index, freq="M").to_timestamp(), "y": y.values.astype(float)})
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                seasonality_mode="multiplicative")
    m.fit(df)
    fut = m.make_future_dataframe(periods=h, freq="MS")
    return m.predict(fut)["yhat"].values[-h:]


def _com_variante(fn: Callable, variante: str) -> Callable:
    return lambda y, h: fn(_preparar(y, variante), h)


MODELOS: Dict[str, Dict] = {
    "naive_ultimo": {"fn": m_naive_ultimo, "descricao": "Ingênuo: repete o último mês observado", "baseline": True},
    "naive_sazonal": {"fn": m_naive_sazonal, "descricao": "Sazonal ingênuo: mesmo mês do ano anterior", "baseline": True},
    "naive_sazonal_nivel": {"fn": m_naive_sazonal_nivel, "baseline": True,
                            "descricao": "Sazonal ingênuo × razão de nível (últimos 3 meses / mesmos meses do ano anterior)"},
    "holt_winters_pos2022": {"fn": _com_variante(_hw, "pos2022"), "baseline": False,
                             "descricao": "Holt-Winters (config. atual do PREDMED), treino a partir de 2022-01"},
    "holt_winters_imputada": {"fn": _com_variante(_hw, "imputada"), "baseline": False,
                              "descricao": "Holt-Winters, treino 2019+ com 2020-03..2021-12 imputados"},
    "sarima_pos2022": {"fn": _com_variante(_sarima, "pos2022"), "baseline": False,
                       "descricao": "SARIMA(0,1,1)(0,1,1)12 em log, treino a partir de 2022-01"},
    "sarima_imputada": {"fn": _com_variante(_sarima, "imputada"), "baseline": False,
                        "descricao": "SARIMA(0,1,1)(0,1,1)12 em log, treino 2019+ com pandemia imputada"},
    "prophet_imputada": {"fn": _com_variante(_prophet, "imputada"), "baseline": False,
                         "descricao": "Prophet (sazonalidade anual multiplicativa), treino 2019+ com pandemia imputada"},
}


def prever(modelo: str, y_treino: pd.Series, h: int) -> np.ndarray:
    p = MODELOS[modelo]["fn"](y_treino, h)
    return np.clip(np.asarray(p, dtype=float), 0, None)


# ──────────────────────────────────────────────
# Backtesting com origem móvel
# ──────────────────────────────────────────────
def backtest_origem_movel(y: pd.Series, origens: List[str], modelos: List[str],
                          h_max: int = 3, fim: Optional[str] = None) -> pd.DataFrame:
    """Para cada origem o (último mês de treino), treina só com y[:o] e prevê o+1..o+h_max.
    Retorna linhas (modelo, origem, alvo, h, real, previsto). Alvos após `fim` são descartados."""
    fim = fim or y.index.max()
    linhas = []
    for o in origens:
        treino = y[y.index <= o]
        alvos = [str(pd.Period(o, freq="M") + k) for k in range(1, h_max + 1)]
        for mod in modelos:
            try:
                prev = prever(mod, treino, h_max)
            except Exception as e:  # registra falha, não interrompe a avaliação
                logger.warning("falha %s origem %s: %s", mod, o, e)
                prev = [np.nan] * h_max
            for k, (alvo, pv) in enumerate(zip(alvos, prev), 1):
                if alvo > fim or alvo not in y.index:
                    continue
                linhas.append({"modelo": mod, "origem": o, "alvo": alvo, "h": k,
                               "real": float(y[alvo]), "previsto": float(pv)})
    return pd.DataFrame(linhas)


def resumir(bt: pd.DataFrame, alvo_ini: str, alvo_fim: str) -> List[Dict]:
    """Métricas por modelo e horizonte (h=1,2,3) e para o total trimestral (soma dos 3 meses)."""
    out = []
    j = bt[(bt["alvo"] >= alvo_ini) & (bt["alvo"] <= alvo_fim)].dropna(subset=["previsto"])
    for mod, g in j.groupby("modelo"):
        for h, gh in g.groupby("h"):
            out.append({"modelo": mod, "horizonte": f"h{h}", "horizonte_dias": HORIZONTE_DIAS.get(h),
                        **metricas(gh["real"], gh["previsto"])})
        # trimestre: origens cujos 3 alvos estão todos na janela
        tri = g.groupby("origem").filter(lambda x: len(x) == 3 and x["alvo"].min() >= alvo_ini)
        if len(tri):
            s = tri.groupby("origem")[["real", "previsto"]].sum()
            out.append({"modelo": mod, "horizonte": "trimestre", "horizonte_dias": 90,
                        **metricas(s["real"], s["previsto"])})
    return out


# ──────────────────────────────────────────────
# Leitura da avaliação versionada (API/telas)
# ──────────────────────────────────────────────
def caminho_avaliacao_atual(pasta: str = PASTA_AVALIACOES) -> Optional[str]:
    arquivos = sorted(glob.glob(os.path.join(pasta, "avaliacao_*.json")))
    return arquivos[-1] if arquivos else None


_CACHE: Dict[str, Dict] = {}


def carregar_avaliacao_atual(pasta: str = PASTA_AVALIACOES) -> Optional[Dict]:
    caminho = caminho_avaliacao_atual(pasta)
    if not caminho:
        return None
    chave = f"{caminho}:{os.path.getmtime(caminho)}"
    if chave not in _CACHE:
        with open(caminho, encoding="utf-8") as f:
            _CACHE.clear()
            _CACHE[chave] = json.load(f)
    return _CACHE[chave]


# Especialidades da fila → nome da série SIH (ver _SCRIPTS/serie_producao_cirurgica.py)
_FILA_PARA_SERIE = {
    "TOTAL": "TOTAL_SEM_OBSTETRICIA",
    "OTORRINO MEDIA COMPLEXIDADE": "OTORRINO",
    "OTORRINO E PNEUMOLOGIA": "OTORRINO",
}


def _sem_acento(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper().strip()


def serie_da_especialidade(especialidade: Optional[str]) -> str:
    e = _sem_acento(especialidade or "TOTAL")
    return _FILA_PARA_SERIE.get(e, e)


def validacao_para_api(especialidade: Optional[str] = None, carater: str = "TODOS",
                       aval: Optional[Dict] = None) -> Optional[Dict]:
    """Resposta de /analytics/validacao-mape a partir da avaliação versionada.
    Mantém as chaves antigas e acrescenta as da avaliação fora da amostra.
    Retorna None se não houver avaliação gravada."""
    aval = aval if aval is not None else carregar_avaliacao_atual()
    if not aval:
        return None
    esp_pedida = (especialidade or "TOTAL").upper()
    nome = serie_da_especialidade(especialidade)
    carater = (carater or "TODOS").upper()
    s = next((x for x in aval["series"] if x["especialidade"] == nome and x["carater"] == carater), None)
    base = {
        "especialidade": esp_pedida,
        "meta_projeto_mape_pct": aval.get("meta_mape_pct", META_MAPE_PCT),
        "alvo_validado": aval["alvo"],
        "fonte_avaliacao": "avaliacao_versionada",
        "avaliacao_id": aval["avaliacao_id"],
        "avaliacao_gerada_em": aval["gerado_em"],
        "serie_avaliada": nome,
        "carater": carater,
        "janela_teste": aval["desenho"]["janela_teste"],
        "desenho_avaliacao": aval["desenho"],
        "base_real_ultima_competencia": aval["fonte"]["competencias"][1],
        "competencias_provisorias": aval["fonte"].get("provisorias", []),
        "periodo_validado": " → ".join(aval["desenho"]["janela_teste"]),
    }
    if s is None or not s.get("modelo_escolhido"):
        return {**base, "mape_real": None, "dentro_da_meta": None, "status": "nao_validado",
                "comparacao_mensal": [], "meses_comparados": 0, "meses_sem_dados_reais": 0,
                "resumo": {"melhor_mes": None, "pior_mes": None, "meses_dentro_meta": 0},
                "interpretacao": f"Sem série avaliada para '{esp_pedida}' ({carater}).",
                "modelo": None, "mape_por_horizonte": {}}
    t = s["teste_modelo_escolhido"]
    mape_h1 = (t.get("h1") or {}).get("mape")
    comp = []
    for c in s["comparacao_h1_teste"].get(s["modelo_escolhido"], []):
        r, p = c["realizado"], c["previsto"]
        if r > 0:
            e = abs(p - r) / r * 100
            comp.append({"mes": c["mes"], "previsto": p, "realizado": r, "erro_absoluto": abs(p - r),
                         "erro_pct": round(e, 2), "dentro_meta": e < META_MAPE_PCT})
    meta = aval.get("meta_mape_pct", META_MAPE_PCT)
    por_h = {hz: (t.get(hz) or {}).get("mape") for hz in ("h1", "h2", "h3", "trimestre")}
    rotulos = {"h1": "30 dias", "h2": "60 dias", "h3": "90 dias", "trimestre": "total trimestral"}
    atinge = [rotulos[hz] for hz, v in por_h.items() if v is not None and v < meta]
    fmt = lambda v: "—" if v is None else f"{v:.1f}%".replace(".", ",")  # noqa: E731
    interp = (f"Produção cirúrgica SIH (não a fila). Teste fora da amostra "
              f"({' a '.join(aval['desenho']['janela_teste'])}), modelo {s['modelo_escolhido']} escolhido "
              f"na validação. MAPE 30/60/90 dias: " + " / ".join(fmt(por_h[h]) for h in ("h1", "h2", "h3"))
              + f". Meta < {meta:.0f}% " + ("atingida em: " + ", ".join(atinge) if atinge else "não atingida")
              + (". Série de baixo volume: erro percentual instável." if s.get("baixo_volume") else "."))
    return {
        **base,
        "mape_real": mape_h1,
        "dentro_da_meta": (mape_h1 < meta) if mape_h1 is not None else None,
        "status": "calculado" if mape_h1 is not None else "nao_validado",
        "comparacao_mensal": comp,
        "meses_comparados": len(comp),
        "meses_sem_dados_reais": 0,
        "resumo": {
            "melhor_mes": min(comp, key=lambda x: x["erro_pct"]) if comp else None,
            "pior_mes": max(comp, key=lambda x: x["erro_pct"]) if comp else None,
            "meses_dentro_meta": sum(1 for c in comp if c["dentro_meta"]),
        },
        "interpretacao": interp,
        "modelo": s["modelo_escolhido"],
        "modelo_descricao": aval["modelos"].get(s["modelo_escolhido"], {}).get("descricao"),
        "mape_por_horizonte": por_h,
        "metricas_teste": t,
        "baseline_sazonal_teste": s.get("teste_baseline_sazonal"),
        "atinge_meta_por_horizonte": s.get("atinge_meta_15"),
        "baixo_volume": s.get("baixo_volume"),
    }
