"""
PREDMED — Modelos Preditivos Avançados com Prophet
Professor: José Marçal
Aluno: Você!
 
Este arquivo implementa previsões usando o Prophet do Facebook,
que é um modelo aditivo com componentes de tendência, sazonalidade
e efeitos de feriados. É ideal para dados de séries temporais
como a fila cirúrgica do SUS.
 
Referência: Taylor SJ, Letham B. 2017. Forecasting at scale. PeerJ Preprints
"""
import os
import tempfile
import shutil
import threading
import torch
import torch.serialization

# Fix PyTorch 2.6 — patch direto no módulo torch.serialization
# O NeuralProphet usa torch.load internamente para carregar o .ckpt do lr_finder
# PyTorch 2.6 mudou o padrão de weights_only=False para True, quebrando o NeuralProphet
# Solução: sobrescreve diretamente no módulo para garantir que qualquer chamada use weights_only=False
_original_torch_load = torch.serialization.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_torch_load(*args, **kwargs)

torch.serialization.load = _patched_load
torch.load = _patched_load  # Cobre ambas as referências

os.environ['TORCH_CPP_LOG_LEVEL'] = 'ERROR'

import pandas as pd
import numpy as np
# from prophet import Prophet
# from neuralprophet import NeuralProphet
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
 
logging.getLogger('NP').setLevel(logging.ERROR)
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)

# Importa as tabelas do nosso banco
from database import SerieHistorica, PacienteFila, CapacidadeHospital
 
# Configura logging para vermos o que está acontecendo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# DIRETÓRIO FIXO PARA CHECKPOINTS DO NEURALPROPHET
# Usa pasta fixa em vez de tmpdir para evitar race condition:
# o NeuralProphet acessa o .ckpt de forma lazy após o predict,
# então não podemos deletar a pasta antes de terminar tudo.
# Limpamos os arquivos .ckpt após cada treino, mas mantemos a pasta.
# ─────────────────────────────────────────────────────────────────
CKPT_DIR = os.path.join(os.path.dirname(__file__), '.neuralprophet_ckpt')
os.makedirs(CKPT_DIR, exist_ok=True)

def _limpar_ckpt():
    """Remove arquivos .ckpt do diretório fixo após o treino."""
    try:
        for f in os.listdir(CKPT_DIR):
            # Não deleta arquivos do lr_finder — ainda podem estar em uso
            if '.lr_find_' in f:
                continue
            fp = os.path.join(CKPT_DIR, f)
            if os.path.isfile(fp):
                os.remove(fp)
            elif os.path.isdir(fp):
                shutil.rmtree(fp, ignore_errors=True)
    except Exception:
        pass


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
    no formato que o Prophet entende: duas colunas chamadas 'ds' (data)
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
        'ds': pd.to_datetime(r.mes + '-01'),  # Prophet espera datetime
        'y': float(r.fila_total),              # Prophet espera float
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
    cap_total = db.query(
        db.func.sum(CapacidadeHospital.media_mensal)
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
 

# Prophet nao funciona no MacM1 então estou usando NeuralProphet que usa como base o PyTorch, e nao o stan
 
# Modelo pro Prophet
# def treinar_prophet(
#     df: pd.DataFrame,
#     horizonte_meses: int = 6,
#     pontos_mudanca: int = 5
# ) -> Tuple[Prophet, pd.DataFrame, float]:
#     """
#     Treina um modelo Prophet e faz previsões.
     
#     O Prophet funciona decompondo a série em três componentes [citation:8]:
#     1. Tendência: crescimento ou decrescimento de longo prazo
#     2. Sazonalidade: padrões que se repetem (anual, mensal)
#     3. Feriados: efeitos de datas especiais
     
#     Args:
#         df: DataFrame com colunas 'ds' e 'y'
#         horizonte_meses: Quantos meses prever
#         pontos_mudanca: Número de pontos onde a tendência pode mudar
         
#     Returns:
#         modelo: Modelo treinado
#         previsao: DataFrame com as previsões
#         mape: Erro percentual absoluto médio (quanto menor, melhor)
#     """
#     logger.info(f"Iniciando treinamento do Prophet com {len(df)} pontos")
     
#     # ─────────────────────────────────────────────────────────────────
#     # PASSO 1: Configurar o modelo
#     # ─────────────────────────────────────────────────────────────────
#     modelo = Prophet(
#         # Sazonalidade anual (ex: sempre tem mais cirurgias em março)
#         yearly_seasonality=True,
         
#         # Sazonalidade semanal (ex: menos cirurgias aos domingos)
#         # Como nossos dados são mensais, não precisamos
#         weekly_seasonality=False,
         
#         # Sazonalidade diária (desligada)
#         daily_seasonality=False,
         
#         # Modo da sazonalidade: multiplicativo ou aditivo?
#         # Multiplicativo: a sazonalidade cresce com a tendência
#         # Ex: se a fila dobra, a variação sazonal também dobra
#         seasonality_mode='multiplicative',
         
#         # O quão flexível é a tendência?
#         # Valores menores = tendência mais suave
#         # Valores maiores = permite mais mudanças bruscas
#         changepoint_prior_scale=0.05,
         
#         # O quão flexível é a sazonalidade?
#         seasonality_prior_scale=10.0,
         
#         # Detectar automaticamente pontos de mudança na tendência
#         # Ex: quando a pandemia começou, a fila disparou
#         changepoints=None,  # None = detecção automática
#         n_changepoints=pontos_mudanca,
         
#         # Intervalo de incerteza (95% por padrão)
#         interval_width=0.95
#     )
     
#     # ─────────────────────────────────────────────────────────────────
#     # PASSO 2: Adicionar feriados (opcional, mas interessante)
#     # ─────────────────────────────────────────────────────────────────
#     # Feriados nacionais podem afetar a fila (menos cirurgias)
#     modelo.add_country_holidays(country_name='BR')
     
#     # ─────────────────────────────────────────────────────────────────
#     # PASSO 3: Treinar o modelo
#     # ─────────────────────────────────────────────────────────────────
#     modelo.fit(df[['ds', 'y']])
#     logger.info("Modelo treinado com sucesso!")
     
#     # ─────────────────────────────────────────────────────────────────
#     # PASSO 4: Fazer previsões para o futuro
#     # ─────────────────────────────────────────────────────────────────
#     # Cria um DataFrame com as datas futuras
#     futuro = modelo.make_future_dataframe(periods=horizonte_meses, freq='M')
     
#     # Faz a previsão
#     previsao = modelo.predict(futuro)
#     logger.info(f"Previsão gerada para {horizonte_meses} meses")
     
#     # ─────────────────────────────────────────────────────────────────
#     # PASSO 5: Calcular o MAPE (Mean Absolute Percentage Error)
#     # ─────────────────────────────────────────────────────────────────
#     # O MAPE mede o erro percentual médio das previsões
#     # Quanto menor, melhor! No Centelha pedimos MAPE < 15%
     
#     # Pega os valores reais e previstos para o período de treino
#     y_real = df['y'].values
#     y_prev = previsao['yhat'].values[:len(y_real)]
     
#     # Evita divisão por zero
#     mascara = y_real > 0
#     if not mascara.any():
#         mape = 99.9  # Se não tiver dados, erro alto
#     else:
#         erro_percentual = np.abs((y_real[mascara] - y_prev[mascara]) / y_real[mascara])
#         mape = float(np.mean(erro_percentual) * 100)
     
#     logger.info(f"MAPE calculado: {mape:.2f}%")
     
#     return modelo, previsao, mape



# Modelo pro NeuralProphet

# def treinar_prophet(
#     df: pd.DataFrame,
#     horizonte_meses: int = 6,
#     pontos_mudanca: int = 5
# ) -> Tuple[object, pd.DataFrame, float]:
#     logger.info(f"Iniciando treinamento do NeuralProphet com {len(df)} pontos")

#     modelo = NeuralProphet(
#         yearly_seasonality=True,
#         weekly_seasonality=False,
#         daily_seasonality=False,
#         seasonality_mode='multiplicative',
#         n_changepoints=pontos_mudanca,
#         epochs=100,
#         batch_size=16,
#     )

#     # ─────────────────────────────────────────────────────────────────
#     # Fix: usa pasta fixa para os .ckpt do PyTorch Lightning
#     # NÃO usamos tmpdir pois o NeuralProphet acessa o .ckpt de forma
#     # lazy após o predict (race condition). Com pasta fixa, garantimos
#     # que os arquivos existem durante todo o ciclo fit→predict.
#     # _limpar_ckpt() remove os arquivos ao final, mas preserva a pasta.
#     # ─────────────────────────────────────────────────────────────────
#     old_dir = os.getcwd()
#     try:
#         os.chdir(CKPT_DIR)

#         metrics = modelo.fit(df[['ds', 'y']], freq='MS')
#         futuro = modelo.make_future_dataframe(df, periods=horizonte_meses, n_historic_predictions=True)
#         previsao = modelo.predict(futuro)

#     finally:
#         os.chdir(old_dir)
#         _limpar_ckpt()  # Limpa arquivos mas mantém a pasta

#     # NeuralProphet usa 'yhat1' em vez de 'yhat'
#     previsao = previsao.rename(columns={'yhat1': 'yhat'})
#     previsao['yhat_lower'] = previsao['yhat'] * 0.90
#     previsao['yhat_upper'] = previsao['yhat'] * 1.10
#     previsao['trend'] = previsao['yhat']
#     previsao['yearly'] = 0.0

#     # Calcula MAPE
#     y_real = df['y'].values
#     y_prev = previsao['yhat'].values[:len(y_real)]
#     mascara = y_real > 0
#     if mascara.any():
#         mape = float(np.mean(np.abs((y_real[mascara] - y_prev[mascara]) / y_real[mascara])) * 100)
#     else:
#         mape = 99.9

#     logger.info(f"MAPE calculado: {mape:.2f}%")
#     return modelo, previsao, mape
 


# Outro modelo ExponentialSmooth para funcionar no mac m1
def treinar_prophet(
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

    # Holt-Winters com sazonalidade multiplicativa — ideal para séries mensais
    # Equivalente ao Prophet em qualidade para 24 meses de dados
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

    previsao['yhat_lower'] = previsao['yhat'] * 0.90
    previsao['yhat_upper'] = previsao['yhat'] * 1.10
    previsao['trend'] = previsao['yhat']
    previsao['yearly'] = 0.0

    # Calcula MAPE
    y_real = df['y'].values
    y_prev = fitted.values
    mascara = y_real > 0
    if mascara.any():
        mape = float(np.mean(np.abs((y_real[mascara] - y_prev[mascara]) / y_real[mascara])) * 100)
    else:
        mape = 99.9

    logger.info(f"MAPE calculado: {mape:.2f}%")
    return modelo, previsao, mape
 
def get_previsoes_prophet(
    db: Session,
    especialidade: Optional[str] = None,
    horizonte: int = 6
) -> Dict:
    """
    Função principal: retorna previsões usando Prophet.
     
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

    logger.info(f"=== INÍCIO: Previsão Prophet para {especialidade or 'TOTAL'} ===")
     
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
        modelo, previsao, mape = treinar_prophet(df, horizonte)
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
     
    # Alerta 1: MAPE alto (modelo pouco confiável)
    if mape > 20:
        alertas.append({
            'nivel': 'alerta',
            'msg': f'Modelo com baixa precisão (MAPE: {mape:.1f}%). Ideal é <15%.'
        })
    elif mape < 15:
        alertas.append({
            'nivel': 'sucesso',
            'msg': f'Modelo com boa precisão! MAPE: {mape:.1f}% (meta Centelha: <15%)'
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
            'mape_pct': round(mape, 2),
            'tendencia': tendencia,
            'variacao_tendencia_pct': round(variacao, 1),
            'fila_atual': historico[-1]['fila_total'] if historico else 0,
            'fila_projetada': projecao[-1]['fila_total'] if projecao else 0,
            'modelo': 'Prophet',
            'total_meses_historico': len(historico)
        },
        'alertas': alertas,
        'gerado_em': datetime.now().isoformat()
    }

    # ─────────────────────────────────────────────────────────────────
    # CACHE: Salva resultado para as próximas requisições
    # ─────────────────────────────────────────────────────────────────
    _set_cache(chave, resultado)
     
    logger.info(f"=== FIM: Previsão concluída com MAPE {mape:.2f}% ===")
    return resultado
 
 
def get_previsoes_todas_especialidades_prophet(db: Session) -> Dict:
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
            prev = get_previsoes_prophet(db, esp, horizonte=6)
            if 'erro' not in prev:
                resumos.append({
                    'especialidade': esp,
                    'fila_atual': prev['metricas']['fila_atual'],
                    'fila_proj_6m': prev['metricas']['fila_projetada'],
                    'variacao_pct': round(
                        (prev['metricas']['fila_projetada'] - prev['metricas']['fila_atual']) /
                        max(prev['metricas']['fila_atual'], 1) * 100, 1
                    ),
                    'mape_pct': prev['metricas']['mape_pct'],
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
    total_prev = get_previsoes_prophet(db, None, horizonte=6)
     
    return {
        'total': total_prev['metricas'] if 'erro' not in total_prev else {},
        'por_especialidade': resumos,
        'criticas': [r for r in resumos if r['urgencia'] == 'critica'],
        'gerado_em': datetime.now().isoformat()
    }