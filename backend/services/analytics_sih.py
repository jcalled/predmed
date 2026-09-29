"""
PREDMED — Analytics SIH
Todas as análises derivadas do AIHRegistro (dados reais SIH/DATASUS 2020-2024).

Funções:
  - get_espera_media_real()         → substitui ESPERA_MEDIA_ESP hardcoded
  - get_sazonalidade_real()         → índice sazonal por especialidade/mês
  - get_mortalidade_por_hospital()  → ranking qualidade hospitalar
  - get_pressao_historica()         → evolução da pressão por CIR
  - get_receita_aih_real()          → valores reais de AIH por especialidade
  - get_simulador_receita()         → simulador de receita para hospital particular
  - get_validacao_mape()            → MAPE real: previsto vs realizado
  - get_resumo_analytics()          → resumo geral para dashboard
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case, cast, Integer
from typing import Dict, List, Optional
from datetime import datetime, date
import logging

from database import AIHRegistro, SerieHistorica, CapacidadeHospital, HospitalEspecialidade

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# 1. ESPERA MÉDIA REAL (substitui ESPERA_MEDIA_ESP hardcoded)
# ══════════════════════════════════════════════════════════════════

# def get_espera_media_real(db: Session) -> Dict[str, float]:
#     """
#     Calcula tempo médio de permanência por especialidade a partir do SIH real.
#     Retorna dicionário compatível com ESPERA_MEDIA_ESP existente.

#     Nota: dias_perm no SIH = dias de internação (proxy do tempo de espera
#     para cirurgias eletivas no SUS).
#     """
#     rows = db.query(
#         AIHRegistro.especialidade,
#         func.avg(AIHRegistro.dias_perm).label("media_dias"),
#         func.count(AIHRegistro.id).label("total"),
#         func.percentile_cont(0.5).within_group(
#             AIHRegistro.dias_perm
#         ).label("mediana_dias") if hasattr(func, 'percentile_cont') else func.avg(AIHRegistro.dias_perm).label("mediana_dias"),
#     ).filter(
#         AIHRegistro.especialidade.isnot(None),
#         AIHRegistro.dias_perm.isnot(None),
#         AIHRegistro.dias_perm > 0,
#         AIHRegistro.dias_perm < 365,  # Remove outliers
#     ).group_by(
#         AIHRegistro.especialidade
#     ).all()

#     resultado = {}
#     for esp, media, total, mediana in rows:
#         if esp and media:
#             # Converte dias para meses (proxy de espera)
#             espera_meses = round(float(media) / 30, 1)
#             resultado[esp] = max(espera_meses, 1.0)  # Mínimo 1 mês

#     # Fallback para especialidades sem dados
#     fallback = {
#         "ONCOLOGIA": 6.2,
#         "CARDIOVASCULAR": 4.8,
#         "NEUROLOGIA": 5.1,
#         "ORTOPEDIA": 5.5,
#         "UROLOGIA": 3.8,
#         "GINECOLOGIA": 3.2,
#         "OFTALMOLOGIA": 4.1,
#         "CIR DIGESTIVA": 4.5,
#         "BUCOMAXILOFACIAL": 3.0,
#         "CIR PLASTICA REPARADORA": 5.8,
#         "OTORRINOLARINGOLOGIA": 3.5,
#         "TOTAL": 5.2,
#     }
#     for k, v in fallback.items():
#         if k not in resultado:
#             resultado[k] = v

#     logger.info(f"Espera média calculada para {len(resultado)} especialidades")
#     return resultado

def get_espera_media_real(db: Session) -> Dict[str, float]:
    """
    Permanência hospitalar média (dias_perm do SIH, em meses) por especialidade.
    ATENÇÃO: é tempo de internação, NÃO tempo de espera na fila. Só retorna
    especialidades com dado calculado (sem valores fixos de fallback).
    SQLite NÃO suporta percentile_cont/within_group.
    """
    dialect = db.get_bind().dialect.name  # "sqlite", "postgresql", etc.

    q = db.query(
        AIHRegistro.especialidade,
        func.avg(AIHRegistro.dias_perm).label("media_dias"),
        func.count(AIHRegistro.id).label("total"),
    ).filter(
        AIHRegistro.especialidade.isnot(None),
        AIHRegistro.dias_perm.isnot(None),
        AIHRegistro.dias_perm > 0,
        AIHRegistro.dias_perm < 365,
    ).group_by(AIHRegistro.especialidade)

    rows = q.all()

    resultado: Dict[str, float] = {}
    for esp, media, total in rows:
        if esp and media:
            resultado[esp] = round(float(media) / 30, 2)

    logger.info(f"Espera média calculada para {len(resultado)} especialidades (dialect={dialect})")
    return resultado


# ══════════════════════════════════════════════════════════════════
# 2. SAZONALIDADE REAL
# ══════════════════════════════════════════════════════════════════

def get_sazonalidade_real(
    db: Session,
    especialidade: Optional[str] = None
) -> Dict:
    """
    Calcula índice sazonal real por mês a partir do SIH histórico.
    Índice > 1.0 = mês com mais internações que a média anual.
    Índice < 1.0 = mês com menos internações.

    Útil para SESA planejar cirurgias eletivas nos meses de baixa.
    """
    q = db.query(
        AIHRegistro.mes_cmpt,
        AIHRegistro.especialidade,
        func.count(AIHRegistro.id).label("total"),
        func.avg(AIHRegistro.val_tot).label("ticket_medio"),
    ).filter(
        AIHRegistro.mes_cmpt.isnot(None),
        AIHRegistro.especialidade.isnot(None),
    )

    if especialidade:
        q = q.filter(AIHRegistro.especialidade == especialidade.upper())

    rows = q.group_by(
        AIHRegistro.mes_cmpt,
        AIHRegistro.especialidade,
    ).all()

    if not rows:
        return {"erro": "Sem dados SIH para calcular sazonalidade"}

    # Agrupa por especialidade → mês
    por_esp: Dict[str, Dict[int, list]] = {}
    for mes, esp, total, ticket in rows:
        if not mes or not esp:
            continue
        por_esp.setdefault(esp, {})
        por_esp[esp].setdefault(mes, []).append(total)

    nomes_meses = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }

    resultado = {}
    for esp, meses in por_esp.items():
        medias_mes = {}
        for mes, totais in meses.items():
            medias_mes[mes] = sum(totais) / len(totais)

        media_anual = sum(medias_mes.values()) / len(medias_mes) if medias_mes else 1

        indices = []
        for mes in range(1, 13):
            media_m = medias_mes.get(mes, media_anual)
            indice = round(media_m / media_anual, 3) if media_anual > 0 else 1.0
            indices.append({
                "mes": mes,
                "nome_mes": nomes_meses[mes],
                "indice": indice,
                "media_internacoes": round(medias_mes.get(mes, 0), 0),
                "classificacao": "alta" if indice > 1.1 else "baixa" if indice < 0.9 else "normal",
            })

        # Meses ideais para programar cirurgias eletivas (baixa demanda)
        meses_ideais = sorted(
            [i for i in indices if i["classificacao"] == "baixa"],
            key=lambda x: x["indice"]
        )

        resultado[esp] = {
            "especialidade": esp,
            "indices_mensais": indices,
            "media_anual": round(media_anual, 0),
            "meses_criticos": [i["nome_mes"] for i in indices if i["classificacao"] == "alta"],
            "meses_ociosos": [i["nome_mes"] for i in indices if i["classificacao"] == "baixa"],
            "recomendacao": f"Programar cirurgias eletivas em {', '.join([m['nome_mes'] for m in meses_ideais[:3]])}" if meses_ideais else "Demanda estável",
        }

    return {
        "por_especialidade": resultado,
        "especialidades_disponiveis": list(resultado.keys()),
        "anos_analisados": _get_anos_disponiveis(db),
    }


# ══════════════════════════════════════════════════════════════════
# 3. MORTALIDADE E QUALIDADE POR HOSPITAL
# ══════════════════════════════════════════════════════════════════

def get_mortalidade_por_hospital(
    db: Session,
    especialidade: Optional[str] = None,
    ano: Optional[int] = None
) -> Dict:
    """
    Ranking de mortalidade por hospital e especialidade.
    Taxa de mortalidade = óbitos / total de internações.

    Proxy de qualidade assistencial — dado que não existe de forma
    acessível no SUS Ceará hoje.
    """
    q = db.query(
        AIHRegistro.cnes,
        AIHRegistro.especialidade,
        func.count(AIHRegistro.id).label("total_internacoes"),
        func.sum(case((AIHRegistro.morte == True, 1), else_=0)).label("total_obitos"),
        func.avg(AIHRegistro.dias_perm).label("media_dias"),
        func.avg(AIHRegistro.val_tot).label("ticket_medio"),
    ).filter(
        AIHRegistro.cnes.isnot(None),
        AIHRegistro.especialidade.isnot(None),
    )

    if especialidade:
        q = q.filter(AIHRegistro.especialidade == especialidade.upper())
    if ano:
        q = q.filter(AIHRegistro.ano_cmpt == ano)

    rows = q.group_by(
        AIHRegistro.cnes,
        AIHRegistro.especialidade,
    ).having(
        func.count(AIHRegistro.id) >= 10  # Mínimo 10 internações para ser significativo
    ).all()

    
    # Busca nomes dos hospitais pelo CNES (fonte: HospitalEspecialidade)
    cnes_nomes = {
        cnes: nome
        for (cnes, nome) in db.query(
            HospitalEspecialidade.hospital_cnes,
            HospitalEspecialidade.hospital_nome,
        ).filter(
            HospitalEspecialidade.hospital_cnes.isnot(None),
            HospitalEspecialidade.hospital_nome.isnot(None),
        ).distinct().all()
    }

    ranking = []
    for cnes, esp, total, obitos, media_dias, ticket in rows:
        taxa = round((int(obitos or 0) / int(total)) * 100, 2)
        ranking.append({
            "cnes": cnes,
            "hospital_nome": cnes_nomes.get(cnes, f"CNES {cnes}"),
            "especialidade": esp,
            "total_internacoes": int(total),
            "total_obitos": int(obitos or 0),
            "taxa_mortalidade_pct": taxa,
            "media_dias_perm": round(float(media_dias or 0), 1),
            "ticket_medio_aih": round(float(ticket or 0), 2),
            "classificacao": "critico" if taxa > 5 else "alerta" if taxa > 2 else "normal",
        })

    ranking.sort(key=lambda x: x["taxa_mortalidade_pct"], reverse=True)

    return {
        "ranking": ranking[:50],
        "total_hospitais": len(ranking),
        "media_geral": round(
            sum(r["taxa_mortalidade_pct"] for r in ranking) / len(ranking), 2
        ) if ranking else 0,
        "criticos": [r for r in ranking if r["classificacao"] == "critico"],
        "filtros": {"especialidade": especialidade, "ano": ano},
    }


# ══════════════════════════════════════════════════════════════════
# 4. PRESSÃO HISTÓRICA POR CIR
# ══════════════════════════════════════════════════════════════════

def get_pressao_historica(
    db: Session,
    cir: Optional[str] = None
) -> Dict:
    """
    Evolução histórica do volume de internações por mês/ano.
    Mostra picos de pressão (pandemia, epidemias, sazonalidade).
    """
    rows = db.query(
        AIHRegistro.mes_competencia,
        AIHRegistro.especialidade,
        func.count(AIHRegistro.id).label("total"),
        func.sum(AIHRegistro.val_tot).label("val_total"),
        func.sum(case((AIHRegistro.morte == True, 1), else_=0)).label("obitos"),
        func.avg(AIHRegistro.dias_perm).label("media_dias"),
    ).filter(
        AIHRegistro.mes_competencia.isnot(None),
    ).group_by(
        AIHRegistro.mes_competencia,
        AIHRegistro.especialidade,
    ).order_by(
        AIHRegistro.mes_competencia,
    ).all()

    if not rows:
        return {"erro": "Sem dados históricos disponíveis"}

    # Agrega por mês (TOTAL)
    por_mes: Dict[str, Dict] = {}
    for mes, esp, total, val, obitos, media_dias in rows:
        if mes not in por_mes:
            por_mes[mes] = {
                "mes": mes,
                "total_internacoes": 0,
                "val_total": 0,
                "obitos": 0,
                "por_especialidade": {}
            }
        por_mes[mes]["total_internacoes"] += int(total)
        por_mes[mes]["val_total"] += float(val or 0)
        por_mes[mes]["obitos"] += int(obitos or 0)
        por_mes[mes]["por_especialidade"][esp] = int(total)

    # Calcula média móvel de 3 meses para detectar picos
    serie = sorted(por_mes.values(), key=lambda x: x["mes"])
    for i, ponto in enumerate(serie):
        if i >= 2:
            media_3m = (
                serie[i-2]["total_internacoes"] +
                serie[i-1]["total_internacoes"] +
                ponto["total_internacoes"]
            ) / 3
            ponto["media_movel_3m"] = round(media_3m, 0)
        else:
            ponto["media_movel_3m"] = ponto["total_internacoes"]

    # Identifica eventos notáveis
    media_geral = sum(p["total_internacoes"] for p in serie) / len(serie)
    for ponto in serie:
        desvio = (ponto["total_internacoes"] - media_geral) / media_geral * 100
        if desvio > 20:
            ponto["evento"] = "pico"
        elif desvio < -20:
            ponto["evento"] = "colapso"
        else:
            ponto["evento"] = "normal"
        ponto["desvio_media_pct"] = round(desvio, 1)

    return {
        "serie_temporal": serie,
        "total_meses": len(serie),
        "media_mensal": round(media_geral, 0),
        "pico_maximo": max(serie, key=lambda x: x["total_internacoes"]),
        "pico_minimo": min(serie, key=lambda x: x["total_internacoes"]),
        "periodo": f"{serie[0]['mes']} → {serie[-1]['mes']}" if serie else "N/A",
    }


# ══════════════════════════════════════════════════════════════════
# 5. RECEITA AIH REAL POR ESPECIALIDADE
# ══════════════════════════════════════════════════════════════════

def get_receita_aih_real(
    db: Session,
    especialidade: Optional[str] = None,
    anos: Optional[List[int]] = None
) -> Dict:
    """
    Valores reais de AIH pagos pelo SUS por especialidade e complexidade.
    Substitui o R$ 1.500 fixo hardcoded.

    Retorna:
    - ticket_medio: valor médio de AIH
    - ticket_p25/p75: intervalo de confiança
    - por_complexidade: MA (média) vs AL (alta complexidade)
    """
    q = db.query(
        AIHRegistro.especialidade,
        AIHRegistro.complex_,
        func.count(AIHRegistro.id).label("total"),
        func.avg(AIHRegistro.val_tot).label("media"),
        func.min(AIHRegistro.val_tot).label("minimo"),
        func.max(AIHRegistro.val_tot).label("maximo"),
        func.sum(AIHRegistro.val_tot).label("total_pago"),
        func.avg(AIHRegistro.val_sh).label("media_sh"),
        func.avg(AIHRegistro.val_sp).label("media_sp"),
    ).filter(
        AIHRegistro.val_tot > 0,
        AIHRegistro.especialidade.isnot(None),
    )

    if especialidade:
        q = q.filter(AIHRegistro.especialidade == especialidade.upper())
    if anos:
        q = q.filter(AIHRegistro.ano_cmpt.in_(anos))

    rows = q.group_by(
        AIHRegistro.especialidade,
        AIHRegistro.complex_,
    ).all()

    # Agrupa por especialidade
    por_esp: Dict[str, Dict] = {}
    for esp, complex_, total, media, minimo, maximo, total_pago, media_sh, media_sp in rows:
        if not esp:
            continue

        if esp not in por_esp:
            por_esp[esp] = {
                "especialidade": esp,
                "total_aih": 0,
                "ticket_medio": 0,
                "total_pago_sus": 0,
                "por_complexidade": {},
                "_soma_ponderada": 0,
            }

        por_esp[esp]["total_aih"] += int(total)
        por_esp[esp]["total_pago_sus"] += float(total_pago or 0)
        por_esp[esp]["_soma_ponderada"] += float(media or 0) * int(total)

        if complex_:
            complex_nome = {
                "01": "Atenção Básica",
                "02": "Média Complexidade",
                "03": "Alta Complexidade",
            }.get(str(complex_), f"Complexidade {complex_}")

            por_esp[esp]["por_complexidade"][complex_nome] = {
                "total_aih": int(total),
                "ticket_medio": round(float(media or 0), 2),
                "minimo": round(float(minimo or 0), 2),
                "maximo": round(float(maximo or 0), 2),
                "media_sh": round(float(media_sh or 0), 2),
                "media_sp": round(float(media_sp or 0), 2),
            }

    # Calcula ticket médio ponderado
    resultado = []
    for esp, dados in por_esp.items():
        if dados["total_aih"] > 0:
            dados["ticket_medio"] = round(
                dados["_soma_ponderada"] / dados["total_aih"], 2
            )
        del dados["_soma_ponderada"]
        resultado.append(dados)

    resultado.sort(key=lambda x: x["ticket_medio"], reverse=True)

    return {
        "por_especialidade": resultado,
        "total_especialidades": len(resultado),
        "ticket_medio_geral": round(
            sum(r["ticket_medio"] for r in resultado) / len(resultado), 2
        ) if resultado else 0,
        "anos_base": anos or _get_anos_disponiveis(db),
    }


# ══════════════════════════════════════════════════════════════════
# 6. SIMULADOR DE RECEITA — HOSPITAL PARTICULAR
# ══════════════════════════════════════════════════════════════════

def get_simulador_receita(
    db: Session,
    especialidades_vagas: Dict[str, int],  # {"ORTOPEDIA": 10, "CARDIOVASCULAR": 5}
    anos_base: Optional[List[int]] = None
) -> Dict:
    """
    Simula receita mensal de um hospital particular se aceitar
    pacientes redistribuídos pelo PREDMED.

    Usa valores reais de AIH dos últimos anos como base.

    Args:
        especialidades_vagas: dict com especialidade → nº de vagas disponíveis
        anos_base: anos para calcular o ticket médio (default: últimos 3 anos)
    """
    if not anos_base:
        anos_disponiveis = _get_anos_disponiveis(db)
        anos_base = anos_disponiveis[-3:] if len(anos_disponiveis) >= 3 else anos_disponiveis

    receita_real = get_receita_aih_real(db, anos=anos_base)
    tickets = {
        r["especialidade"]: r["ticket_medio"]
        for r in receita_real["por_especialidade"]
    }

    simulacao = []
    total_receita_mes = 0
    total_pacientes = 0

    for esp, vagas in especialidades_vagas.items():
        esp_upper = esp.upper()
        ticket = tickets.get(esp_upper, 1500)  # Fallback R$ 1.500

        receita_esp = vagas * ticket
        total_receita_mes += receita_esp
        total_pacientes += vagas

        # Busca dados de complexidade para essa especialidade
        dados_esp = next(
            (r for r in receita_real["por_especialidade"] if r["especialidade"] == esp_upper),
            None
        )

        simulacao.append({
            "especialidade": esp_upper,
            "vagas_mes": vagas,
            "ticket_medio_real": round(ticket, 2),
            "receita_mes": round(receita_esp, 2),
            "receita_ano": round(receita_esp * 12, 2),
            "fonte": "SIH real" if esp_upper in tickets else "estimativa",
            "intervalo_confianca": {
                "baixo": round(receita_esp * 0.85, 2),
                "alto": round(receita_esp * 1.15, 2),
            },
            "por_complexidade": dados_esp["por_complexidade"] if dados_esp else {},
        })

    simulacao.sort(key=lambda x: x["receita_mes"], reverse=True)

    return {
        "simulacao_por_especialidade": simulacao,
        "resumo": {
            "total_vagas_mes": total_pacientes,
            "receita_total_mes": round(total_receita_mes, 2),
            "receita_total_ano": round(total_receita_mes * 12, 2),
            "ticket_medio_geral": round(total_receita_mes / total_pacientes, 2) if total_pacientes else 0,
            "receita_conservadora_mes": round(total_receita_mes * 0.85, 2),
            "receita_otimista_mes": round(total_receita_mes * 1.15, 2),
        },
        "anos_base": anos_base,
        "nota": f"Valores baseados em {len(anos_base)} anos de dados reais SIH/DATASUS Ceará",
    }


# ══════════════════════════════════════════════════════════════════
# 7. VALIDAÇÃO MAPE REAL (robusto: últimos meses reais + fallback)
# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════
# 7. VALIDAÇÃO MAPE REAL (SIH) — usando ÚLTIMOS MESES DISPONÍVEIS
# ══════════════════════════════════════════════════════════════════

from typing import Tuple
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def _interpretar_mape(mape: Optional[float]) -> str:
    if mape is None:
        return "Sem dados suficientes para validação"
    if mape < 10:
        return f"MAPE de {mape:.1f}% no holdout — abaixo da meta do projeto (15%)."
    if mape < 15:
        return f"MAPE de {mape:.1f}% no holdout — dentro da meta do projeto (15%)."
    if mape < 25:
        return f"Precisão moderada ({mape:.1f}%). Abaixo da meta. Considere mais dados históricos."
    return f"Precisão baixa ({mape:.1f}%). Necessita ajuste do modelo."


def _get_serie_sih_mensal(
    db: Session,
    especialidade: Optional[str] = None,
) -> Tuple[List[str], List[int]]:
    """
    Retorna (meses, y) onde y = total de AIHs no SIH por mês.
    Meses no formato 'YYYY-MM', ordenados.
    """
    q = db.query(
        AIHRegistro.mes_competencia,
        func.count(AIHRegistro.id).label("total_aih"),
    ).filter(
        AIHRegistro.mes_competencia.isnot(None),
    )

    esp = (especialidade or "TOTAL").upper()
    if esp != "TOTAL":
        q = q.filter(AIHRegistro.especialidade == esp)

    rows = (
        q.group_by(AIHRegistro.mes_competencia)
         .order_by(AIHRegistro.mes_competencia)
         .all()
    )

    meses = [r[0] for r in rows if r[0]]
    y = [int(r[1]) for r in rows]

    return meses, y


def get_validacao_mape(
    db: Session,
    especialidade: Optional[str] = None,
    meses_validacao: int = 6,
    carater: str = "TODOS",
) -> Dict:
    """
    MAPE fora da amostra da previsão de demanda.

    1) Se existir avaliação versionada (backend/avaliacoes/previsao_demanda/avaliacao_*.json,
       gerada por _SCRIPTS/avaliar_previsao_demanda.py), devolve ESSA avaliação — a mesma do
       relatório docs/dados/previsao-demanda-v1.md (backtesting com origem móvel, h = 1..3 meses).
       Nesse caso `meses_validacao` é ignorado: a janela de teste é a da avaliação.
    2) Sem avaliação gravada: cálculo ad hoc (holdout dos últimos N meses de aih_registro).
    """
    from services.previsao_avaliacao import validacao_para_api
    versionada = validacao_para_api(especialidade, carater=carater)
    if versionada is not None:
        return versionada

    esp = (especialidade or "TOTAL").upper()

    meses, y = _get_serie_sih_mensal(db, esp)

    if not meses or len(y) < (meses_validacao + 12):
        # 12 meses mínimo pra sazonalidade fazer sentido; ajuste se quiser
        ultima = meses[-1] if meses else None
        return {
            "especialidade": esp,
            "mape_real": None,
            "meta_projeto_mape_pct": 15,
            "alvo_validado": "contagem mensal de AIH no SIH (produção hospitalar), não a fila",
            "dentro_da_meta": None,
            "status": "nao_validado",
            "comparacao_mensal": [],
            "meses_comparados": 0,
            "meses_sem_dados_reais": meses_validacao,
            "resumo": {"melhor_mes": None, "pior_mes": None, "meses_dentro_meta": 0},
            "interpretacao": "Sem dados suficientes para validação",
            "base_real_ultima_competencia": ultima,
            "periodo_validado": None,
        }

    ultima_comp = meses[-1]
    periodo_validado = f"{meses[-meses_validacao]} → {meses[-1]}"

    # HOLDOUT
    train_y = y[:-meses_validacao]
    test_y = y[-meses_validacao:]
    test_meses = meses[-meses_validacao:]

    # Configura sazonalidade conforme tamanho do treino
    n_train = len(train_y)
    if n_train >= 24:
        seasonal = "mul"
        seasonal_periods = 12
    elif n_train >= 12:
        seasonal = "add"
        seasonal_periods = 12
    else:
        seasonal = None
        seasonal_periods = None

    try:
        model = ExponentialSmoothing(
            train_y,
            trend="add",
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit(optimized=True)

        forecast = model.forecast(meses_validacao)
        prev_y = [int(round(max(0, v))) for v in forecast.tolist()]
    except Exception as e:
        logger.exception("Falha ao treinar/forecast Holt-Winters no SIH")
        return {
            "especialidade": esp,
            "mape_real": None,
            "meta_projeto_mape_pct": 15,
            "alvo_validado": "contagem mensal de AIH no SIH (produção hospitalar), não a fila",
            "dentro_da_meta": None,
            "status": "nao_validado",
            "comparacao_mensal": [],
            "meses_comparados": 0,
            "meses_sem_dados_reais": meses_validacao,
            "resumo": {"melhor_mes": None, "pior_mes": None, "meses_dentro_meta": 0},
            "interpretacao": f"Erro no modelo: {str(e)}",
            "base_real_ultima_competencia": ultima_comp,
            "periodo_validado": periodo_validado,
        }

    # COMPARAÇÃO + MAPE
    comparacao = []
    erros = []

    for mes, previsto, real in zip(test_meses, prev_y, test_y):
        if real and real > 0:
            erro_pct = abs(previsto - real) / real * 100
            erros.append(erro_pct)
            comparacao.append({
                "mes": mes,
                "previsto": int(previsto),
                "realizado": int(real),
                "erro_absoluto": int(abs(previsto - real)),
                "erro_pct": round(float(erro_pct), 2),
                "dentro_meta": erro_pct < 15,
            })

    mape = round(sum(erros) / len(erros), 2) if erros else None

    return {
        "especialidade": esp,
        "mape_real": mape,
        "meta_projeto_mape_pct": 15,
            "alvo_validado": "contagem mensal de AIH no SIH (produção hospitalar), não a fila",
        "dentro_da_meta": (mape < 15) if mape is not None else None,
        "status": "calculado" if mape is not None else "nao_validado",
        "comparacao_mensal": comparacao,
        "meses_comparados": len(comparacao),
        "meses_sem_dados_reais": meses_validacao - len(comparacao),
        "resumo": {
            "melhor_mes": min(comparacao, key=lambda x: x["erro_pct"]) if comparacao else None,
            "pior_mes": max(comparacao, key=lambda x: x["erro_pct"]) if comparacao else None,
            "meses_dentro_meta": sum(1 for c in comparacao if c["dentro_meta"]),
        },
        "interpretacao": _interpretar_mape(mape),
        "base_real_ultima_competencia": ultima_comp,
        "periodo_validado": periodo_validado,
    }

# ══════════════════════════════════════════════════════════════════
# 8. RESUMO GERAL ANALYTICS
# ══════════════════════════════════════════════════════════════════

def get_resumo_analytics(db: Session) -> Dict:
    """
    Resumo executivo de todos os analytics para o dashboard SESA.
    """
    total_aih = db.query(func.count(AIHRegistro.id)).scalar() or 0
    total_valor = db.query(func.sum(AIHRegistro.val_tot)).scalar() or 0
    total_obitos = db.query(func.sum(
        case((AIHRegistro.morte == True, 1), else_=0)
    )).scalar() or 0

    anos = _get_anos_disponiveis(db)
    especialidades = db.query(AIHRegistro.especialidade).filter(
        AIHRegistro.especialidade.isnot(None)
    ).distinct().count()

    # Espera média real
    espera_real = get_espera_media_real(db)
    espera_media_geral = round(
        sum(espera_real.values()) / len(espera_real), 1
    ) if espera_real else 5.2

    return {
        "base_dados": {
            "total_aih": total_aih,
            "total_valor_pago": round(float(total_valor), 2),
            "total_obitos": int(total_obitos),
            "taxa_mortalidade_geral": round(int(total_obitos) / max(total_aih, 1) * 100, 2),
            "anos_disponiveis": anos,
            "especialidades": especialidades,
            "periodo": f"{anos[0]}-{anos[-1]}" if anos else "N/A",
        },
        "espera_media_real": espera_real,
        "espera_media_geral_meses": espera_media_geral,
        "gerado_em": datetime.now().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════

def _get_anos_disponiveis(db: Session) -> List[int]:
    rows = db.query(AIHRegistro.ano_cmpt).filter(
        AIHRegistro.ano_cmpt.isnot(None)
    ).distinct().order_by(AIHRegistro.ano_cmpt).all()
    return [r[0] for r in rows if r[0]]


def atualizar_especialidades_sih(db: Session):
  """Atualiza contagem de procedimentos realizados por especialidade no SIH."""
  from database import AIHRegistro, Hospital, HospitalEspecialidade
  from sqlalchemy import func

  rows = db.query(
      AIHRegistro.cnes,
      AIHRegistro.especialidade,
      func.count(AIHRegistro.id).label("total")
  ).filter(
      AIHRegistro.cnes.isnot(None),
      AIHRegistro.especialidade.isnot(None)
  ).group_by(
      AIHRegistro.cnes,
      AIHRegistro.especialidade
  ).all()

  for cnes, especialidade, total in rows:
      hospital = db.query(Hospital).filter(Hospital.cnes == cnes).first()
      if not hospital:
          # Cria um hospital mínimo (improvável, mas seguro)
          hospital = Hospital(
              cnes=cnes,
              nome_fantasia=f"HOSPITAL CNES {cnes}",
              municipio="DESCONHECIDO",
              uf="CE",
              fonte="sih",
              confiavel=False,
          )
          db.add(hospital)
          db.flush()

      esp_rel = db.query(HospitalEspecialidade).filter_by(
          hospital_id=hospital.id,
          especialidade=especialidade
      ).first()
      if esp_rel:
          esp_rel.total_procedimentos_sih = total
          esp_rel.ultima_atualizacao = datetime.utcnow()
      else:
          esp_rel = HospitalEspecialidade(
              hospital_id=hospital.id,
              hospital_cnes=cnes,
              especialidade=especialidade,
              total_procedimentos_sih=total,
              fonte="sih",
          )
          db.add(esp_rel)

  db.commit()
  logger.info(f"[SIH] Especialidades atualizadas para {len(rows)} combinações.")