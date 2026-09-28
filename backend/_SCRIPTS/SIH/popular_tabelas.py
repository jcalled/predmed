#!/usr/bin/env python
"""
Script para popular as tabelas auxiliares do PREDMED
- serie_historica: dados mensais para previsões
- hospital_especialidades: quais hospitais atendem quais especialidades

Uso: python scripts/popular_tabelas.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, SerieHistorica, HospitalEspecialidade
from services.previsoes import build_serie_historica
from services.data_import import build_hospital_especialidades
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def popular_tabelas():
    """Popula todas as tabelas auxiliares"""
    
    db = SessionLocal()
    
    try:
        # ─────────────────────────────────────────────────────────
        # PASSO 1: Verificar se há dados no IntegraSUS
        # ─────────────────────────────────────────────────────────
        from database import PacienteFila
        total_pacientes = db.query(func.count(PacienteFila.id)).scalar() or 0
        
        if total_pacientes == 0:
            logger.error("❌ Nenhum paciente encontrado no IntegraSUS!")
            logger.error("   Primeiro faça upload do CSV do IntegraSUS")
            return
        
        logger.info(f"📊 Encontrados {total_pacientes} pacientes no IntegraSUS")
        
        # ─────────────────────────────────────────────────────────
        # PASSO 2: Popular série histórica
        # ─────────────────────────────────────────────────────────
        logger.info("🔄 Populando série histórica...")
        
        # Limpa dados antigos
        db.query(SerieHistorica).delete()
        db.commit()
        
        # Constrói nova série
        build_serie_historica(db)
        
        # Verifica
        total_serie = db.query(func.count(SerieHistorica.id)).scalar()
        logger.info(f"✅ Série histórica populada com {total_serie} registros")
        
        # Mostra resumo
        from sqlalchemy import text
        resumo = db.execute(text("""
            SELECT 
                especialidade,
                COUNT(*) as meses,
                MIN(fila_total) as min_fila,
                MAX(fila_total) as max_fila,
                AVG(fila_total) as avg_fila
            FROM serie_historica 
            GROUP BY especialidade
            ORDER BY especialidade
        """)).fetchall()
        
        for r in resumo:
            logger.info(f"   {r[0]}: {r[1]} meses | fila: {r[2]:.0f}-{r[3]:.0f}")
        
        # ─────────────────────────────────────────────────────────
        # PASSO 3: Popular especialidades dos hospitais
        # ─────────────────────────────────────────────────────────
        logger.info("🔄 Populando especialidades dos hospitais...")
        
        # Limpa dados antigos
        db.query(HospitalEspecialidade).delete()
        db.commit()
        
        # Constrói mapa de especialidades
        build_hospital_especialidades(db)
        
        # Verifica
        total_esp = db.query(func.count(HospitalEspecialidade.id)).scalar()
        logger.info(f"✅ Especialidades populadas com {total_esp} registros")
        
        # Mostra top hospitais
        top_hospitais = db.execute(text("""
            SELECT hospital_nome, COUNT(*) as esp_count
            FROM hospital_especialidades
            GROUP BY hospital_nome
            ORDER BY esp_count DESC
            LIMIT 5
        """)).fetchall()
        
        for h in top_hospitais:
            logger.info(f"   {h[0]}: {h[1]} especialidades")
        
        logger.info("🎉 Todas as tabelas populadas com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    popular_tabelas()