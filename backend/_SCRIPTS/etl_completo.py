#!/usr/bin/env python
"""
ETL Completo para o PREDMED
Executa na ordem:
1. Importação do CNES (fonte confiável de estabelecimentos)
2. Importação do DATASUS (capacidade cirúrgica)
3. Importação do IntegraSUS (fila de espera)
4. Correção de municípios de hospitais do DATASUS com base nos pacientes
5. Importação do SIH (dados históricos de internações)
6. Atualização de especialidades a partir do SIH
7. Reconstrução da série histórica

Uso:
    python scripts/etl_completo.py [--cnes /path/CNES.json] [--datasus /path/datasus.csv] [--integrasus /path/integrasus.csv] [--baixar-sih] [--pasta-sih ./data/sih]
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from database import SessionLocal, init_db, Hospital, HospitalCirMap
from services.data_import import (
    import_cnes_json,
    import_datasus,
    import_integrasus,
    _seed_demo_datasus,
    _seed_demo_fila,
)
from services.download_sih import importar_todos_dbc
from services.previsoes import build_serie_historica

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def corrigir_municipios_hospitais_datasus(db: Session, limiar: float = 0.8):
    """
    Atualiza o município de hospitais da fonte 'datasus' com base no
    município mais frequente dos pacientes do IntegraSUS (HospitalCirMap).
    Inclui fuzzy matching para lidar com pequenas variações de nome.
    """
    from services.data_import import norm, get_cir_from_municipio
    from difflib import SequenceMatcher
    logger.info("🔄 Corrigindo municípios de hospitais do DATASUS com base nos pacientes...")

    # Carrega todos os mapas do HospitalCirMap
    cir_maps = db.query(HospitalCirMap).all()
    # Cria dicionário com nomes normalizados
    map_dict = {}
    for cm in cir_maps:
        nome_norm = norm(cm.hospital_nome)
        # Mantém o de maior confiança em caso de duplicidade
        if nome_norm not in map_dict or cm.confianca > map_dict[nome_norm].confianca:
            map_dict[nome_norm] = cm

    hospitais_datasus = db.query(Hospital).filter(Hospital.fonte == 'datasus').all()
    atualizados = 0

    for hosp in hospitais_datasus:
        nome_norm = norm(hosp.nome_fantasia)
        cm = map_dict.get(nome_norm)
        if cm and cm.confianca >= limiar:
            # Encontrou por normalização exata
            if hosp.municipio != cm.municipio or hosp.cir == "DESCONHECIDO":
                logger.info(f"   Corrigindo {hosp.nome_fantasia} (ID {hosp.id}): {hosp.municipio} -> {cm.municipio} (confiança {cm.confianca})")
                hosp.municipio = cm.municipio
                nova_cir = get_cir_from_municipio(cm.municipio)
                hosp.cir = nova_cir if nova_cir != "DESCONHECIDO" else cm.cir
                atualizados += 1
        else:
            # Tenta fuzzy matching
            melhor = None
            melhor_ratio = limiar
            melhor_cm = None
            for nome_norm2, cm2 in map_dict.items():
                ratio = SequenceMatcher(None, nome_norm, nome_norm2).ratio()
                if ratio > melhor_ratio:
                    melhor_ratio = ratio
                    melhor_cm = cm2
            if melhor_cm and melhor_ratio >= limiar:
                logger.info(f"   Corrigindo (fuzzy) {hosp.nome_fantasia} -> {melhor_cm.hospital_nome} (ratio {melhor_ratio:.2f})")
                hosp.municipio = melhor_cm.municipio
                nova_cir = get_cir_from_municipio(melhor_cm.municipio)
                hosp.cir = nova_cir if nova_cir != "DESCONHECIDO" else melhor_cm.cir
                atualizados += 1
            else:
                logger.debug(f"Não encontrado: {hosp.nome_fantasia} (norm: {nome_norm})")

    db.commit()
    logger.info(f"✅ Municípios corrigidos para {atualizados} hospitais do DATASUS.")


def mesclar_hospitais_duplicados(db: Session):
    """
    Identifica hospitais com mesmo nome e município (após normalização) e mescla os pacientes
    do hospital sem CNES para o hospital com CNES, depois deleta o sem CNES.
    Atualiza aliases para apontar para o hospital correto.
    """
    from services.data_import import norm
    logger.info("🔄 Mesclando hospitais duplicados...")

    hospitais = db.query(Hospital).all()
    grupos = {}
    for h in hospitais:
        chave = (norm(h.nome_fantasia), norm(h.municipio))
        grupos.setdefault(chave, []).append(h)

    total_mesclados = 0
    for chave, lista in grupos.items():
        if len(lista) <= 1:
            continue
        com_cnes = [h for h in lista if h.cnes]
        sem_cnes = [h for h in lista if not h.cnes]

        if com_cnes and sem_cnes:
            destino = com_cnes[0]
            for origem in sem_cnes:
                logger.info(f"   Mesclando {origem.nome_fantasia} (ID {origem.id}) em {destino.nome_fantasia} (ID {destino.id}, CNES {destino.cnes})")

                # Migrar pacientes
                db.query(PacienteFila).filter(PacienteFila.hospital_id == origem.id).update(
                    {PacienteFila.hospital_id: destino.id}
                )
                # Migrar capacidades
                db.query(CapacidadeHospital).filter(CapacidadeHospital.hospital_id == origem.id).update(
                    {CapacidadeHospital.hospital_id: destino.id}
                )
                # Migrar especialidades
                db.query(HospitalEspecialidade).filter(HospitalEspecialidade.hospital_id == origem.id).update(
                    {HospitalEspecialidade.hospital_id: destino.id}
                )
                # Atualizar aliases
                db.query(HospitalAlias).filter(
                    (HospitalAlias.alias_nome == origem.nome_fantasia) |
                    (HospitalAlias.hospital_nome == origem.nome_fantasia)
                ).update({
                    HospitalAlias.cnes: destino.cnes,
                    HospitalAlias.hospital_nome: destino.nome_fantasia
                }, synchronize_session=False)

                db.delete(origem)
                total_mesclados += 1
            db.commit()
            logger.info(f"   Mesclado {len(sem_cnes)} hospitais em {destino.nome_fantasia}")

    logger.info(f"✅ Total de hospitais mesclados: {total_mesclados}")


def atualizar_especialidades_sih(db: Session):
    """
    Atualiza a tabela HospitalEspecialidade com a contagem de procedimentos
    realizados por especialidade, a partir dos dados do SIH (AIHRegistro).
    """
    from database import AIHRegistro, HospitalEspecialidade
    from sqlalchemy import func

    logger.info("🔄 Atualizando especialidades a partir do SIH...")

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

    if not rows:
        logger.warning("Nenhum dado encontrado no SIH para atualizar especialidades.")
        return

    count = 0
    for cnes, especialidade, total in rows:
        hospital = db.query(Hospital).filter(Hospital.cnes == cnes).first()
        if not hospital:
            hospital = Hospital(
                cnes=cnes,
                nome_fantasia=f"HOSPITAL CNES {cnes}",
                municipio="DESCONHECIDO",
                uf="CE",
                fonte="sih",
                confiavel=False,
                is_cirurgico=True,
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
        count += 1

        if count % 500 == 0:
            db.commit()

    db.commit()
    logger.info(f"✅ Especialidades do SIH atualizadas para {count} combinações.")


def main():
    parser = argparse.ArgumentParser(description="ETL Completo PREDMED")
    parser.add_argument("--cnes", help="Caminho para o arquivo CNES.json (opcional)")
    parser.add_argument("--datasus", help="Caminho para o CSV do DATASUS (opcional)")
    parser.add_argument("--integrasus", help="Caminho para o CSV do IntegraSUS (opcional)")
    parser.add_argument("--baixar-sih", action="store_true", help="Executar download_sih.py para importar SIH")
    parser.add_argument("--pasta-sih", default="./data/sih", help="Pasta com arquivos DBC (para importação sem download)")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        # 1. CNES
        if args.cnes:
            logger.info("🔄 Importando CNES...")
            import_cnes_json(args.cnes, db)
        else:
            cnes_files = list(Path("data").glob("*cnes*.json"))
            if cnes_files:
                default_cnes = cnes_files[0]
            if default_cnes.exists():
                logger.info(f"🔄 Importando CNES padrão: {default_cnes}")
                import_cnes_json(str(default_cnes), db)
            else:
                logger.warning("Nenhum arquivo CNES fornecido. A base de hospitais ficará incompleta.")

        # 2. DATASUS
        if args.datasus:
            logger.info("🔄 Importando DATASUS (capacidade)...")
            import_datasus(args.datasus, db)
        else:
            default_datasus = Path("data") / "tabnet_internacoes_ceara_datasus.csv"
            if default_datasus.exists():
                logger.info(f"🔄 Importando DATASUS padrão: {default_datasus}")
                import_datasus(str(default_datasus), db)
            else:
                logger.info("[DATASUS] Nenhum arquivo encontrado, usando dados demo...")
                _seed_demo_datasus(db)

        # 3. IntegraSUS
        if args.integrasus:
            logger.info("🔄 Importando IntegraSUS (fila)...")
            import_integrasus(args.integrasus, db)
        else:
            integra_files = list(Path("data").glob("*fila*.csv")) + list(Path("data").glob("*integrasus*.csv"))
            if integra_files:
                logger.info(f"🔄 Importando IntegraSUS padrão: {integra_files[-1]}")
                import_integrasus(str(integra_files[-1]), db)
            else:
                logger.info("[INTEGRASUS] Nenhum arquivo encontrado, usando dados demo...")
                _seed_demo_fila(db)

        # 4. Correção de municípios (após IntegraSUS, usando HospitalCirMap)
        corrigir_municipios_hospitais_datasus(db)
 

        # 5. Mesclar duplicatas (hospitais com mesmo nome e município)
        mesclar_hospitais_duplicados(db)

        # 5. SIH
        if args.baixar_sih:
            logger.info("🔄 Baixando e importando SIH...")
            import subprocess
            subprocess.run([sys.executable, "download_sih.py", "--so-importar"], cwd=os.path.dirname(__file__))
        else:
            if args.pasta_sih and Path(args.pasta_sih).exists():
                logger.info(f"🔄 Importando SIH da pasta {args.pasta_sih}...")
                importar_todos_dbc(args.pasta_sih, db)

        # 6. Atualizar especialidades a partir do SIH
        atualizar_especialidades_sih(db)

        # 7. Reconstruir série histórica
        logger.info("🔄 Reconstruindo série histórica...")
        build_serie_historica(db)

        logger.info("✅ ETL completo executado com sucesso!")

    except Exception as e:
        logger.exception(f"❌ Erro durante ETL: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()