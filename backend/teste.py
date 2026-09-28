"""
Teste simples do Prophet para verificar se o erro de permissão foi resolvido
"""
import os
import tempfile
import pandas as pd
import numpy as np
from prophet import Prophet
import logging

# Configuração igual ao seu código
temp_dir = tempfile.mkdtemp(prefix='prophet_test_')
os.environ['PROPHET_REPOMODEL_PATH'] = temp_dir
os.environ['CMDSTANPY_MODEL_PATH'] = temp_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"📁 Diretório temporário: {temp_dir}")

# Cria dados sintéticos simples
dates = pd.date_range(start='2024-01-01', periods=24, freq='M')
values = [100 + i*5 + np.random.normal(0, 10) for i in range(24)]

df = pd.DataFrame({
    'ds': dates,
    'y': values
})

logger.info(f"📊 Dados criados: {len(df)} pontos")

try:
    # Treina modelo
    modelo = Prophet(yearly_seasonality=True)
    modelo.fit(df)
    logger.info("✅ Modelo treinado com sucesso!")
    
    # Faz previsão
    future = modelo.make_future_dataframe(periods=6, freq='M')
    forecast = modelo.predict(future)
    logger.info("✅ Previsão gerada com sucesso!")
    
    print("\n🎉 SUCESSO! Prophet está funcionando!")
    print(f"Último valor real: {df['y'].iloc[-1]:.0f}")
    print(f"Primeiro valor previsto: {forecast['yhat'].iloc[-6]:.0f}")
    
except Exception as e:
    logger.error(f"❌ Erro: {e}")
    print("\n🔍 Detalhes do erro:")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensagem: {e}")
