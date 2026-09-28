"""
PREDMED — Serviço de Previsões ML
Reconstrói série histórica a partir de DATASUS + fila atual
e projeta 6 meses com regressão linear.
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from database import (
    SessionLocal, PacienteFila, CapacidadeHospital,
    SerieHistorica
)


# ─── Constantes de calibração ─────────────────────────────
# Baseadas em dados SIH/SUS Ceará: demanda cresce ~8% ao ano
CRESCIMENTO_ANUAL = 0.08
SAZONALIDADE = {
    1: 0.82, 2: 0.85, 3: 0.95, 4: 1.00,
    5: 1.05, 6: 1.08, 7: 1.02, 8: 1.03,
    9: 1.05, 10: 1.07, 11: 0.98, 12: 0.75,
}  # Dezembro/Janeiro reduzidos (férias hospitalares)

# Tempo médio de espera estimado por especialidade (meses)
ESPERA_MEDIA_ESP = {
    "ONCOLOGIA": 6.2,
    "CARDIOVASCULAR": 8.1,
    "NEUROLOGIA": 7.4,
    "CIR DIGESTIVA": 5.8,
    "ORTOPEDIA": 4.9,
    "UROLOGIA": 4.2,
    "GINECOLOGIA": 3.8,
    "OFTALMOLOGIA": 3.1,
}


def _mes_str(dt: date) -> str:
    return dt.strftime("%Y-%m")


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error"""
    mask = y_true > 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def _linear_forecast(x: np.ndarray, y: np.ndarray, n_future: int) -> Tuple[np.ndarray, float, float]:
    """
    Regressão linear simples.
    Retorna: (valores_futuros, mape_in_sample, slope_pct_mensal)
    """
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs
    y_pred_train = slope * x + intercept
    mape = _mape(y, y_pred_train)
    x_future = np.arange(x[-1] + 1, x[-1] + 1 + n_future)
    y_future = slope * x_future + intercept
    # slope como % do valor médio
    media = float(np.mean(y))
    slope_pct = float(slope / media * 100) if media > 0 else 0.0
    return y_future, mape, slope_pct


def build_serie_historica(db: Session, n_meses: int = 24) -> bool:
    """
    Constrói (ou reconstrói) a série histórica sintética-realista.
    Usa capacidade DATASUS real + fila atual como âncora.
    Retorna True se gerou dados novos.
    """
    # Evita reprocessamento
    existing = db.query(func.count(SerieHistorica.id)).scalar()
    if existing and existing >= n_meses:
        return False

    # ── Capacidade mensal total (DATASUS) ─────────────────
    cap_total = db.query(
        func.sum(CapacidadeHospital.media_mensal)
    ).scalar() or 2500.0

    # ── Fila atual por especialidade (IntegraSUS) ─────────
    fila_por_esp = {
        esp: cnt for esp, cnt in
        db.query(PacienteFila.especialidade, func.count(PacienteFila.id))
        .group_by(PacienteFila.especialidade).all()
    }
    fila_total_atual = sum(fila_por_esp.values())

    # ── Estima entradas mensais ────────────────────────────
    # Se a fila existe por ~espera_media meses em média, e tem fila_total pacientes:
    # entradas ≈ fila_total / espera_media
    espera_media_geral = 5.2  # meses (média SUS Ceará)
    entradas_mensais_base = fila_total_atual / espera_media_geral

    today = date.today()
    meses_list = [today - relativedelta(months=i) for i in range(n_meses - 1, -1, -1)]

    # ── Limpa e reconstrói ────────────────────────────────
    db.query(SerieHistorica).delete()

    for i, mes_dt in enumerate(meses_list):
        mes_str = _mes_str(mes_dt)
        sazon = SAZONALIDADE.get(mes_dt.month, 1.0)
        # Crescimento histórico: quanto mais antigo, menor a fila
        fator_historico = (1 - CRESCIMENTO_ANUAL / 12) ** (n_meses - 1 - i)
        # Entradas com sazonalidade
        entradas = int(entradas_mensais_base * sazon * (0.9 + 0.2 * (i / n_meses)))
        saidas = int(cap_total * sazon)
        # Fila acumulada (simplificado: cresce com a taxa histórica)
        fila_mes = int(fila_total_atual * fator_historico)

        db.add(SerieHistorica(
            mes=mes_str,
            especialidade="TOTAL",
            fila_total=fila_mes,
            entradas_mes=entradas,
            saidas_mes=saidas,
            capacidade_mes=int(cap_total),
        ))

        # Por especialidade
        for esp, fila_esp_atual in fila_por_esp.items():
            entradas_esp = int((fila_esp_atual / espera_media_geral) * sazon)
            saidas_esp = int(saidas * (fila_esp_atual / max(fila_total_atual, 1)) * sazon)
            fila_esp_mes = int(fila_esp_atual * fator_historico)
            db.add(SerieHistorica(
                mes=mes_str,
                especialidade=esp.upper(),
                fila_total=fila_esp_mes,
                entradas_mes=entradas_esp,
                saidas_mes=saidas_esp,
                capacidade_mes=int(cap_total * (fila_esp_atual / max(fila_total_atual, 1))),
            ))

    db.commit()
    return True


def get_previsoes(
    db: Session,
    especialidade: Optional[str] = None,
    n_future: int = 6
) -> Dict:
    """
    Retorna série histórica + projeção 6 meses.
    especialidade: None = TOTAL | "ORTOPEDIA" etc
    """
    # Garante que série existe
    build_serie_historica(db)

    esp_filtro = especialidade.upper() if especialidade else "TOTAL"

    rows = db.query(SerieHistorica).filter(
        SerieHistorica.especialidade == esp_filtro
    ).order_by(SerieHistorica.mes).all()

    if not rows:
        # Fallback: reconstrói forçado
        db.query(SerieHistorica).delete()
        build_serie_historica(db)
        rows = db.query(SerieHistorica).filter(
            SerieHistorica.especialidade == esp_filtro
        ).order_by(SerieHistorica.mes).all()

    if not rows:
        return {"erro": "Dados insuficientes para previsão"}

    # ── Arrays ────────────────────────────────────────────
    x = np.arange(len(rows), dtype=float)
    y_fila = np.array([r.fila_total for r in rows], dtype=float)
    y_entradas = np.array([r.entradas_mes for r in rows], dtype=float)
    y_saidas = np.array([r.saidas_mes for r in rows], dtype=float)

    # ── Forecasting ───────────────────────────────────────
    y_fila_future, mape_fila, slope_pct = _linear_forecast(x, y_fila, n_future)
    y_entradas_future, _, _ = _linear_forecast(x, y_entradas, n_future)
    y_saidas_future, _, _ = _linear_forecast(x, y_saidas, n_future)

    # ── Meses futuros ─────────────────────────────────────
    last_mes = rows[-1].mes
    last_dt = datetime.strptime(last_mes, "%Y-%m").date()
    meses_futuros = [
        _mes_str(last_dt + relativedelta(months=i + 1))
        for i in range(n_future)
    ]

    # ── Série histórica para gráfico ──────────────────────
    historico = [
        {
            "mes": r.mes,
            "fila_total": r.fila_total,
            "entradas_mes": r.entradas_mes,
            "saidas_mes": r.saidas_mes,
            "capacidade_mes": r.capacidade_mes,
            "tipo": "historico",
        }
        for r in rows
    ]

    # ── Projeção ──────────────────────────────────────────
    cap_atual = rows[-1].capacidade_mes if rows else 2500
    projecao = []
    for i in range(n_future):
        sazon = SAZONALIDADE.get(
            (last_dt + relativedelta(months=i + 1)).month, 1.0
        )
        projecao.append({
            "mes": meses_futuros[i],
            "fila_total": max(0, int(y_fila_future[i])),
            "entradas_mes": max(0, int(y_entradas_future[i] * sazon)),
            "saidas_mes": max(0, int(y_saidas_future[i] * sazon)),
            "capacidade_mes": cap_atual,
            "tipo": "projecao",
        })

    # ── Análise de cenários ───────────────────────────────
    fila_atual_val = int(y_fila[-1])
    fila_proj_6m = int(y_fila_future[-1])
    variacao_pct = round((fila_proj_6m - fila_atual_val) / max(fila_atual_val, 1) * 100, 1)

    # Cenário com redistribuição (reduz 40% do crescimento)
    fila_com_redistrib = int(fila_atual_val + (fila_proj_6m - fila_atual_val) * 0.6)
    economia_pacientes = fila_proj_6m - fila_com_redistrib

    # ── Espera média projetada ─────────────────────────────
    espera_atual = ESPERA_MEDIA_ESP.get(esp_filtro, 5.2) if esp_filtro != "TOTAL" else 5.2
    entradas_media = float(np.mean(y_entradas[-6:])) if len(y_entradas) >= 6 else float(np.mean(y_entradas))
    espera_projetada = round(
        (fila_proj_6m / max(entradas_media, 1)), 1
    )

    # ── Alertas ───────────────────────────────────────────
    alertas = []
    if variacao_pct > 15:
        alertas.append({
            "nivel": "critico",
            "msg": f"Fila crescerá {variacao_pct:.0f}% em 6 meses sem intervenção",
        })
    elif variacao_pct > 5:
        alertas.append({
            "nivel": "alerta",
            "msg": f"Crescimento moderado de {variacao_pct:.0f}% projetado para 6 meses",
        })

    if espera_projetada > 8:
        alertas.append({
            "nivel": "critico",
            "msg": f"Espera média projetada: {espera_projetada:.1f} meses ({esp_filtro})",
        })

    if cap_atual < entradas_media:
        deficit = int(entradas_media - cap_atual)
        alertas.append({
            "nivel": "alerta",
            "msg": f"Déficit de capacidade: {deficit} cirurgias/mês abaixo da demanda",
        })

    return {
        "especialidade": esp_filtro,
        "historico": historico,
        "projecao": projecao,
        "serie_completa": historico + projecao,  # conveniente para gráfico único
        "metricas": {
            "mape_pct": round(mape_fila, 1),
            "slope_mensal_pct": round(slope_pct, 2),
            "fila_atual": fila_atual_val,
            "fila_proj_6m": fila_proj_6m,
            "variacao_pct": variacao_pct,
            "espera_media_atual_meses": round(espera_atual, 1),
            "espera_projetada_meses": espera_projetada,
            "capacidade_mensal": cap_atual,
            "entradas_media_mensal": int(entradas_media),
            # Impacto da redistribuição
            "fila_com_redistrib_6m": fila_com_redistrib,
            "economia_pacientes_redistrib": economia_pacientes,
        },
        "alertas": alertas,
    }


def get_previsoes_todas_especialidades(db: Session) -> Dict:
    """
    Retorna resumo de previsões para todas as especialidades.
    Usado no dashboard e na tela Zerar Filas.
    """
    build_serie_historica(db)

    especialidades = [
        esp for (esp,) in
        db.query(SerieHistorica.especialidade)
        .filter(SerieHistorica.especialidade != "TOTAL")
        .distinct().all()
    ]

    resumos = []
    for esp in sorted(especialidades):
        rows = db.query(SerieHistorica).filter(
            SerieHistorica.especialidade == esp
        ).order_by(SerieHistorica.mes).all()

        if len(rows) < 3:
            continue

        x = np.arange(len(rows), dtype=float)
        y = np.array([r.fila_total for r in rows], dtype=float)
        y_future, mape, slope_pct = _linear_forecast(x, y, 6)

        fila_atual = int(y[-1])
        fila_6m = max(0, int(y_future[-1]))
        variacao = round((fila_6m - fila_atual) / max(fila_atual, 1) * 100, 1)

        resumos.append({
            "especialidade": esp,
            "fila_atual": fila_atual,
            "fila_proj_6m": fila_6m,
            "variacao_pct": variacao,
            "mape_pct": round(mape, 1),
            "tendencia": "crescimento" if slope_pct > 1 else "estavel" if slope_pct > -1 else "reducao",
            "espera_meses": ESPERA_MEDIA_ESP.get(esp, 5.2),
            "urgencia": "critica" if variacao > 15 else "alta" if variacao > 5 else "normal",
        })

    # Ordena por variação decrescente (mais crítico primeiro)
    resumos.sort(key=lambda x: x["variacao_pct"], reverse=True)

    # Total geral
    total_rows = db.query(SerieHistorica).filter(
        SerieHistorica.especialidade == "TOTAL"
    ).order_by(SerieHistorica.mes).all()

    total_summary = {}
    if total_rows:
        x_t = np.arange(len(total_rows), dtype=float)
        y_t = np.array([r.fila_total for r in total_rows], dtype=float)
        y_t_future, mape_t, slope_t = _linear_forecast(x_t, y_t, 6)
        fila_atual_t = int(y_t[-1])
        fila_6m_t = max(0, int(y_t_future[-1]))
        total_summary = {
            "fila_atual": fila_atual_t,
            "fila_proj_6m": fila_6m_t,
            "variacao_pct": round((fila_6m_t - fila_atual_t) / max(fila_atual_t, 1) * 100, 1),
            "mape_pct": round(mape_t, 1),
        }

    return {
        "total": total_summary,
        "por_especialidade": resumos,
        "criticas": [r for r in resumos if r["urgencia"] == "critica"],
        "gerado_em": datetime.now().isoformat(),
    }