"""
PREDMED — Previsão de fila com Holt-Winters (statsmodels ExponentialSmoothing)

O modelo em uso é Holt-Winters (tendência aditiva + sazonalidade multiplicativa
anual). Prophet/NeuralProphet NÃO são usados (o código antigo foi removido).

Honestidade (B05):
- A série de fila histórica (SerieHistorica.fila_total) é ESTIMADA — tanto na
  construção a partir da fila atual quanto na derivada do SIH — logo a origem é
  "simulado".
- O erro calculado aqui é de ajuste in-sample sobre essa série; não é validação.
  Por isso mape_pct = None e mape_status = "nao_validado". A validação contra
  dados observados fica em analytics_sih.get_validacao_mape.
"""
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from database import SerieHistorica, PacienteFila, CapacidadeHospital

# O patch global de torch.load (weights_only=False) e o diretório de checkpoints
# do NeuralProphet foram removidos: nenhum dos dois era usado pelo Holt-Winters.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# CACHE EM MEMÓRIA
# Evita retreinar o modelo a cada requisição (seria ~3-4 min por carga).
# O modelo é treinado uma vez e fica em memória por CACHE_TTL_HORAS.
# Após esse tempo, retreina automaticamente na próxima requisição.
# ─────────────────────────────────────────────────────────────────

# Cache global: { "chave": {"resultado": {...}, "expira_em": datetime} }
_cache: Dict = {}
_cache_lock = threading.Lock()
CACHE_TTL_HORAS = 1  # Retreina só a cada 1 hora


def _get_cache(chave: str) -> Optional[Dict]:
    with _cache_lock:
        entrada = _cache.get(chave)
        if entrada and datetime.now() < entrada['expira_em']:
            logger.info(f"Cache HIT para '{chave}' — retornando resultado salvo")
            return entrada['resultado']
        return None


def _set_cache(chave: str, resultado: Dict):
    with _cache_lock:
        _cache[chave] = {
            'resultado': resultado,
            'expira_em': datetime.now() + timedelta(hours=CACHE_TTL_HORAS)
        }
        logger.info(f"Cache SET para '{chave}' (expira em {CACHE_TTL_HORAS}h)")


def limpar_cache():
    """Limpa todo o cache forçando retreinamento na próxima requisição."""
    with _cache_lock:
        _cache.clear()
    logger.info("Cache limpo. Próxima requisição retreinará o modelo.")

 
def construir_serie_temporal(
    db: Session, 
    especialidade: Optional[str] = None
) -> pd.DataFrame:
    """
    Constrói uma série temporal a partir dos dados do banco.
     
    Esta função pega os dados da tabela SerieHistorica e transforma
    no formato ds (data) / y (valor)
    e 'y' (valor a ser previsto).
     
    Args:
        db: Sessão do banco de dados
        especialidade: Se None, pega TOTAL. Se especificada, pega só aquela especialidade
         
    Returns:
        DataFrame com colunas 'ds' (datetime) e 'y' (float)
    """
    logger.info(f"Construindo série temporal para especialidade: {especialidade or 'TOTAL'}")
     
    # Define qual especialidade buscar
    if especialidade:
        esp_filtro = especialidade.upper()
    else:
        esp_filtro = "TOTAL"
     
    # Busca os dados ordenados por mês
    rows = db.query(SerieHistorica).filter(
        SerieHistorica.especialidade == esp_filtro
    ).order_by(SerieHistorica.mes).all()
     
    # Se não tiver dados suficientes, usa fallback sintético
    if len(rows) < 24:
        logger.warning("Poucos dados históricos! Usando dados sintéticos de fallback")
        return _gerar_dados_sinteticos(db, especialidade)
     
    # Converte para DataFrame
    df = pd.DataFrame([{
        'ds': pd.to_datetime(r.mes + '-01'),
        'y': float(r.fila_total),
        'entradas': r.entradas_mes,
        'saidas': r.saidas_mes
    } for r in rows])
     
    logger.info(f"Série temporal criada com {len(df)} meses de dados")
    return df
 
 
def _gerar_dados_sinteticos(
    db: Session, 
    especialidade: Optional[str] = None
) -> pd.DataFrame:
    """
    Gera dados sintéticos realistas quando não há histórico suficiente.
     
    Usa a capacidade real dos hospitais e a fila atual para criar
    uma série plausível. Isso é útil durante o desenvolvimento.
     
    Args:
        db: Sessão do banco
        especialidade: Especialidade alvo
         
    Returns:
        DataFrame com dados sintéticos
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta
     
    # Pega a fila atual como âncora
    if especialidade:
        fila_atual = db.query(PacienteFila).filter(
            PacienteFila.especialidade.ilike(f"%{especialidade}%")
        ).count()
    else:
        fila_atual = db.query(PacienteFila).count()
     
    # Pega capacidade total dos hospitais
    from sqlalchemy import func
    cap_total = db.query(
        func.sum(CapacidadeHospital.media_mensal)
    ).scalar() or 5000
     
    # Estimativa de entradas mensais
    # Fórmula: fila_atual / tempo_médio_espera
    # Tempo médio de espera no SUS Ceará: ~5.2 meses
    entradas_mensais = fila_atual / 5.2 if fila_atual > 0 else 1000
     
    # Gera 24 meses de dados
    hoje = date.today()
    dados = []
     
    # Sazonalidade: meses com mais cirurgias (evita férias)
    sazonalidade = {
        1: 0.85, 2: 0.90, 3: 0.95, 4: 1.00,
        5: 1.05, 6: 1.08, 7: 1.02, 8: 1.00,
        9: 1.03, 10: 1.06, 11: 0.98, 12: 0.80
    }
     
    for i in range(23, -1, -1):  # 24 meses atrás até hoje
        mes_dt = hoje - relativedelta(months=i)
        mes_str = mes_dt.strftime("%Y-%m")
         
        # Fator sazonal
        sazon = sazonalidade.get(mes_dt.month, 1.0)
         
        # Fator histórico: quanto mais antigo, menor a fila (crescimento)
        fator_historico = 1.0 - (i * 0.005)  # Crescimento de 0.5% ao mês
         
        # Calcula fila estimada para este mês
        fila_estimada = max(0, int(fila_atual * fator_historico))
         
        dados.append({
            'ds': pd.to_datetime(mes_str + '-01'),
            'y': float(fila_estimada * sazon),
            'entradas': int(entradas_mensais * sazon),
            'saidas': int(cap_total * sazon)
        })
     
    df = pd.DataFrame(dados)
    logger.info(f"Dados sintéticos gerados: {len(df)} meses")
    return df
 

# Modelo em uso: Holt-Winters (statsmodels)
MODELO_NOME = "Holt-Winters (statsmodels ExponentialSmoothing)"
ORIGEM_SERIE = "simulado"
AVISO_SERIE = ("Série histórica de fila estimada (não observada); previsão não validada. "
               "A faixa exibida é ±10% ilustrativa, não intervalo de confiança.")


def treinar_holt_winters(
    df: pd.DataFrame,
    horizonte_meses: int = 6,
    pontos_mudanca: int = 5
) -> Tuple[object, pd.DataFrame, float]:
    logger.info(f"Iniciando treinamento do Holt-Winters com {len(df)} pontos")


    n = len(df)
    if n >= 24:
        seasonal = 'mul'
        seasonal_periods = 12
    elif n >= 12:
        seasonal = 'add'
        seasonal_periods = 12
    else:
        seasonal = None
        seasonal_periods = None

    # Holt-Winters com sazonalidade multiplicativa anual (séries mensais)
    modelo = ExponentialSmoothing(
        df['y'],
        trend='add',
        seasonal='mul',
        seasonal_periods=12,  # Sazonalidade anual
        initialization_method='estimated'
    ).fit(optimized=True)

    # Previsão histórica (in-sample)
    fitted = modelo.fittedvalues

    # Previsão futura
    forecast = modelo.forecast(horizonte_meses)

    # Monta DataFrame no mesmo formato que o código espera
    datas_futuras = pd.date_range(
        start=df['ds'].max() + pd.DateOffset(months=1),
        periods=horizonte_meses,
        freq='MS'
    )

    previsao = pd.concat([
        pd.DataFrame({'ds': df['ds'], 'yhat': fitted}),
        pd.DataFrame({'ds': datas_futuras, 'yhat': forecast.values})
    ]).reset_index(drop=True)

    # Faixa ILUSTRATIVA de ±10% — não é intervalo de confiança do modelo.
    previsao['yhat_lower'] = previsao['yhat'] * 0.90
    previsao['yhat_upper'] = previsao['yhat'] * 1.10
    previsao['trend'] = previsao['yhat']
    previsao['yearly'] = 0.0

    # Erro de ajuste in-sample (MAPE sobre os próprios dados de treino) — não é validação
    y_real = df['y'].values
    y_prev = fitted.values
    mascara = y_real > 0
    if mascara.any():
        mape = float(np.mean(np.abs((y_real[mascara] - y_prev[mascara]) / y_real[mascara])) * 100)
    else:
        mape = 99.9

    logger.info(f"Erro de ajuste in-sample: {mape:.2f}%")
    return modelo, previsao, mape
 
def get_previsoes_ml(
    db: Session,
    especialidade: Optional[str] = None,
    horizonte: int = 6
) -> Dict:
    """
    Função principal: retorna previsões com Holt-Winters.
     
    Esta é a função que será chamada pela API.
     
    Args:
        db: Sessão do banco
        especialidade: Especialidade desejada
        horizonte: Meses para frente
         
    Returns:
        Dicionário com histórico, previsões e métricas
    """

    # ─────────────────────────────────────────────────────────────────
    # CACHE: Verifica se já temos resultado salvo para essa especialidade
    # Evita retreinar o modelo a cada requisição (seria ~30s por chamada)
    # ─────────────────────────────────────────────────────────────────
    chave = f"{especialidade or 'TOTAL'}_{horizonte}"
    cached = _get_cache(chave)
    if cached:
        return cached

    logger.info(f"=== INÍCIO: Previsão Holt-Winters para {especialidade or 'TOTAL'} ===")
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 1: Construir a série temporal
    # ─────────────────────────────────────────────────────────────────
    df = construir_serie_temporal(db, especialidade)
     
    if df.empty:
        return {"erro": "Dados insuficientes para previsão"}
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 2: Treinar modelo e obter previsões
    # ─────────────────────────────────────────────────────────────────
    try:
        modelo, previsao, mape = treinar_holt_winters(df, horizonte)
    except Exception as e:
        logger.error(f"Erro no treinamento: {e}")
        return {"erro": f"Falha no modelo: {str(e)}"}
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 3: Formatar histórico para o frontend
    # ─────────────────────────────────────────────────────────────────
    historico = []
    for _, row in df.iterrows():
        historico.append({
            'mes': row['ds'].strftime('%Y-%m'),
            'fila_total': int(row['y']),
            'entradas': int(row.get('entradas', 0)),
            'saidas': int(row.get('saidas', 0)),
            'tipo': 'historico'
        })
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 4: Formatar previsões para o frontend
    # ─────────────────────────────────────────────────────────────────
    # Identifica quais linhas são futuras
    ultimo_mes_historico = df['ds'].max()
     
    projecao = []
    for i, row in previsao.iterrows():
        if row['ds'] > ultimo_mes_historico:
            projecao.append({
                'mes': row['ds'].strftime('%Y-%m'),
                'fila_total': max(0, int(row['yhat'])),  # Não pode ser negativo
                'fila_lower': max(0, int(row['yhat_lower'])),  # Limite inferior
                'fila_upper': int(row['yhat_upper']),  # Limite superior
                'tendencia': float(row['trend']),
                'sazonalidade_anual': float(row.get('yearly', 0)),
                'tipo': 'projecao'
            })
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 5: Calcular tendência (crescimento ou queda)
    # ─────────────────────────────────────────────────────────────────
    # Pega os últimos 12 meses para comparar
    ultimos_12 = df.tail(12)
    if len(ultimos_12) >= 6:
        media_6_primeiros = ultimos_12.head(6)['y'].mean()
        media_6_ultimos = ultimos_12.tail(6)['y'].mean()
         
        if media_6_primeiros > 0:
            variacao = ((media_6_ultimos - media_6_primeiros) / media_6_primeiros) * 100
        else:
            variacao = 0
             
        if variacao > 5:
            tendencia = "crescimento"
        elif variacao < -5:
            tendencia = "reducao"
        else:
            tendencia = "estavel"
    else:
        tendencia = "estavel"
        variacao = 0
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 6: Calcular alertas baseados nas previsões
    # ─────────────────────────────────────────────────────────────────
    alertas = []
     
    # Alerta 1: previsão sobre série simulada, sem validação
    alertas.append({
        'nivel': 'alerta',
        'msg': 'Série histórica simulada: previsão não validada (meta do projeto: MAPE < 15% em dados reais).'
    })
     
    # Alerta 2: Fila crescendo muito
    if projecao and len(projecao) >= 3:
        fila_hoje = historico[-1]['fila_total'] if historico else 0
        fila_futura = projecao[-1]['fila_total']
         
        if fila_hoje > 0:
            crescimento = ((fila_futura - fila_hoje) / fila_hoje) * 100
            if crescimento > 20:
                alertas.append({
                    'nivel': 'critico',
                    'msg': f'Fila pode crescer {crescimento:.0f}% nos próximos {horizonte} meses!'
                })
            elif crescimento > 10:
                alertas.append({
                    'nivel': 'alerta',
                    'msg': f'Fila pode crescer {crescimento:.0f}% nos próximos {horizonte} meses'
                })
     
    # ─────────────────────────────────────────────────────────────────
    # PASSO 7: Retornar tudo formatado
    # ─────────────────────────────────────────────────────────────────
    resultado = {
        'especialidade': especialidade or 'TOTAL',
        'historico': historico,
        'projecao': projecao,
        'serie_completa': historico + projecao,  # Conveniente para gráficos
        'metricas': {
            'mape_pct': None,
            'mape_status': 'nao_validado',
            'meta_mape_pct': 15,
            'erro_ajuste_in_sample_pct': round(mape, 2),  # sobre série simulada; não é acurácia
            'tendencia': tendencia,
            'variacao_tendencia_pct': round(variacao, 1),
            'fila_atual': historico[-1]['fila_total'] if historico else 0,
            'fila_projetada': projecao[-1]['fila_total'] if projecao else 0,
            'modelo': MODELO_NOME,
            'total_meses_historico': len(historico)
        },
        'alertas': alertas,
        'origem_serie': ORIGEM_SERIE,
        'faixa_tipo': 'ilustrativa_10pct',
        'aviso': AVISO_SERIE,
        'gerado_em': datetime.now().isoformat()
    }

    # ─────────────────────────────────────────────────────────────────
    # CACHE: Salva resultado para as próximas requisições
    # ─────────────────────────────────────────────────────────────────
    _set_cache(chave, resultado)
     
    logger.info(f"=== FIM: previsão concluída (erro de ajuste in-sample {mape:.2f}%) ===")
    return resultado
 
 
def get_previsoes_ml_todas(db: Session) -> Dict:
    """
    Retorna resumo de previsões para todas as especialidades.
     
    Útil para o dashboard e para a tela "Zerar Filas".
    """
    # Pega todas as especialidades que têm dados
    especialidades = db.query(SerieHistorica.especialidade).filter(
        SerieHistorica.especialidade != "TOTAL"
    ).distinct().all()
     
    especialidades = [e[0] for e in especialidades]
     
    # Se não tiver nenhuma, usa uma lista padrão
    if not especialidades:
        especialidades = [
            "ONCOLOGIA", "CARDIOVASCULAR", "NEUROLOGIA",
            "ORTOPEDIA", "UROLOGIA", "GINECOLOGIA", "OFTALMOLOGIA"
        ]
     
    resumos = []
    for esp in especialidades:
        try:
            prev = get_previsoes_ml(db, esp, horizonte=6)
            if 'erro' not in prev:
                resumos.append({
                    'especialidade': esp,
                    'fila_atual': prev['metricas']['fila_atual'],
                    'fila_proj_6m': prev['metricas']['fila_projetada'],
                    'variacao_pct': round(
                        (prev['metricas']['fila_projetada'] - prev['metricas']['fila_atual']) /
                        max(prev['metricas']['fila_atual'], 1) * 100, 1
                    ),
                    'mape_pct': None,
                    'mape_status': 'nao_validado',
                    'erro_ajuste_in_sample_pct': prev['metricas']['erro_ajuste_in_sample_pct'],
                    'tendencia': prev['metricas']['tendencia'],
                    'urgencia': 'critica' if prev['metricas']['fila_projetada'] > prev['metricas']['fila_atual'] * 1.2
                              else 'alta' if prev['metricas']['fila_projetada'] > prev['metricas']['fila_atual'] * 1.1
                              else 'normal',
                })
        except Exception as e:
            logger.error(f"Erro ao processar {esp}: {e}")
     
    # Ordena por fila atual (maior primeiro)
    resumos.sort(key=lambda x: x['fila_atual'], reverse=True)
     
    # Total geral
    total_prev = get_previsoes_ml(db, None, horizonte=6)
     
    return {
        'total': total_prev['metricas'] if 'erro' not in total_prev else {},
        'por_especialidade': resumos,
        'criticas': [r for r in resumos if r['urgencia'] == 'critica'],
        'modelo': MODELO_NOME,
        'origem_serie': ORIGEM_SERIE,
        'aviso': AVISO_SERIE,
        'gerado_em': datetime.now().isoformat()
    }