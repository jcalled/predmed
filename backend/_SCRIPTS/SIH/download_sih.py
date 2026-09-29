"""
PREDMED — Download e Importação SIH/DATASUS
Download automático dos arquivos DBC do FTP do DATASUS,
conversão para DataFrame e importação no banco de dados.

Dependência: pip install pysus
O pysus lida nativamente com arquivos .dbc do DATASUS.

Uso:
    python download_sih.py                  # Baixa CE 2010-2024
    python download_sih.py --uf CE --anos 2023 2024
    python download_sih.py --so-importar    # Importa DBC já baixados sem re-download
"""
import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from sqlalchemy import Integer
# ─────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────
# A configuração do logging (inclui sih_import.log) fica no bloco __main__, para que
# outros scripts (ex.: _SCRIPTS/coleta_datasus.py) possam importar este módulo sem efeitos colaterais.
logger = logging.getLogger(__name__)

URL_SIH_RD = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/{nome}"


# ─────────────────────────────────────────────────────────────────
# MAPEAMENTO ESPEC (código DATASUS → nome legível)
# Fonte: Tabela de Especialidades SIH/SUS
# ─────────────────────────────────────────────────────────────────
ESPEC_MAP = {
    "01": "CIRURGIA GERAL",
    "02": "CIRURGIA CARDÍACA",
    "03": "CIRURGIA CABEÇA E PESCOÇO",
    "04": "CIRURGIA MAMAS",
    "05": "CIRURGIA PEDIÁTRICA",
    "06": "CIRURGIA PLÁSTICA REPARADORA",
    "07": "CIRURGIA TORÁCICA",
    "08": "CIRURGIA VASCULAR PERIFÉRICA",
    "09": "ENDOCRINOLOGIA",
    "10": "GASTROENTEROLOGIA",
    "11": "GINECOLOGIA",
    "12": "MASTOLOGIA",
    "13": "NEUROCIRURGIA",
    "14": "NEUROLOGIA",
    "15": "OBSTETRÍCIA",
    "16": "OFTALMOLOGIA",
    "17": "ONCOLOGIA",
    "18": "ORTOPEDIA",
    "19": "OTORRINOLARINGOLOGIA",
    "20": "PNEUMOLOGIA",
    "21": "PROCTOLOGIA",
    "22": "REUMATOLOGIA",
    "23": "UROLOGIA",
    "24": "BUCOMAXILOFACIAL",
    "25": "CARDIOVASCULAR",
    "26": "HEMATOLOGIA",
    "27": "DERMATOLOGIA",
    "28": "NEFROLOGIA",
    "29": "PEDIATRIA CLÍNICA",
    "30": "GERIATRIA",
    "31": "HANSENOLOGIA",
    "32": "SAÚDE MENTAL",
    "33": "TISIOLOGIA",
    "34": "MEDICINA INTERNA",
    "35": "NEONATOLOGIA",
    "36": "TRANSPLANTE",
    "39": "CLÍNICA MÉDICA",
    "40": "UTI",
    "41": "QUEIMADOS",
    "42": "TOXICOLOGIA",
    "43": "REABILITAÇÃO",
    "44": "AIDS/HIV",
    "45": "PSIQUIATRIA",
    "99": "OUTRAS",
}


# ─────────────────────────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────────────────────────

def baixar_arquivo_sih(
    uf: str,
    ano: int,
    mes: int,
    pasta_destino: str = "./data/sih"
) -> str | None:
    """
    Baixa um arquivo SIH diretamente do FTP do DATASUS.
    Retorna o caminho local ou None se falhar.
    """
    import urllib.request

    os.makedirs(pasta_destino, exist_ok=True)

    ano_2dig = str(ano)[-2:]
    mes_str = f"{mes:02d}"
    nome_arquivo = f"RD{uf.upper()}{ano_2dig}{mes_str}.dbc"
    caminho_local = os.path.join(pasta_destino, nome_arquivo)

    # Não baixa de novo se já existe
    if os.path.exists(caminho_local):
        logger.info(f"   Já existe: {nome_arquivo} — pulando download")
        return caminho_local

    url = URL_SIH_RD.format(nome=nome_arquivo)
    logger.info(f"📥 Baixando: {nome_arquivo}")

    try:
        urllib.request.urlretrieve(url, caminho_local)
        tamanho = os.path.getsize(caminho_local)
        logger.info(f"   ✅ {tamanho/1024:.1f} KB")
        return caminho_local
    except Exception as e:
        logger.warning(f"   ❌ {nome_arquivo}: {e}")
        # Remove arquivo corrompido se existir
        if os.path.exists(caminho_local):
            os.remove(caminho_local)
        return None


def baixar_multiplos(
    uf: str = "CE",
    anos: list = None,
    pasta_destino: str = "./data/sih"
) -> list:
    """
    Baixa múltiplos arquivos DBC do SIH.
    Retorna lista de caminhos baixados com sucesso.
    """
    if anos is None:
        anos = list(range(2019, 2025))  # 2019 a 2024

    baixados = []
    total = len(anos) * 12

    logger.info(f"🚀 Iniciando download: {uf} | {anos[0]}-{anos[-1]} | {total} arquivos")

    for ano in anos:
        for mes in range(1, 13):
            arquivo = baixar_arquivo_sih(uf, ano, mes, pasta_destino)
            if arquivo:
                baixados.append(arquivo)

    logger.info(f"📊 Download concluído: {len(baixados)}/{total} arquivos")
    return baixados


# ─────────────────────────────────────────────────────────────────
# CONVERSÃO DBC → DATAFRAME
# ─────────────────────────────────────────────────────────────────

def dbc_para_dataframe(caminho_dbc: str) -> pd.DataFrame | None:
    try:
        import tempfile
        from pyreaddbc import dbc2dbf
        from dbfread import DBF

        # Converte DBC → DBF em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as tmp:
            caminho_dbf = tmp.name

        dbc2dbf(caminho_dbc, caminho_dbf)
        tabela = DBF(caminho_dbf, encoding='latin-1')
        df = pd.DataFrame(iter(tabela))
        os.remove(caminho_dbf)
        return df

    except Exception as e:
        logger.error(f"Erro ao converter {caminho_dbc}: {e}")
        return None


def dbc_para_dataframe_fallback(caminho_dbc: str) -> pd.DataFrame | None:
    """
    Fallback: converte via dbfread se pysus não estiver disponível.
    pip install dbfread
    """
    try:
        # Tenta converter DBC → DBF → DataFrame
        import subprocess
        caminho_dbf = caminho_dbc.replace(".dbc", ".dbf")

        # blast é uma ferramenta C para converter DBC → DBF
        # Se não tiver, usa python-dbc
        result = subprocess.run(
            ["blast", caminho_dbc, caminho_dbf],
            capture_output=True
        )
        if result.returncode == 0:
            from dbfread import DBF
            tabela = DBF(caminho_dbf, encoding='latin-1')
            df = pd.DataFrame(iter(tabela))
            os.remove(caminho_dbf)
            return df
    except Exception:
        pass

    try:
        # python-dbc como último recurso
        import dbc
        df = dbc.read(caminho_dbc)
        return df
    except Exception as e:
        logger.error(f"Todos os métodos falharam para {caminho_dbc}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# IMPORTAÇÃO NO BANCO
# ─────────────────────────────────────────────────────────────────

def importar_dbc_no_banco(
    caminho_dbc: str,
    db: Session,
    upsert: bool = True
) -> int:
    """
    Converte um arquivo DBC e importa no banco de dados.
    Popula:
    - AIHRegistro: registro bruto de cada AIH
    Retorna quantidade de registros importados.
    """
    from database import AIHRegistro

    logger.info(f"🔄 Processando: {os.path.basename(caminho_dbc)}")

    # Tenta converter
    df = dbc_para_dataframe(caminho_dbc)
    if df is None:
        df = dbc_para_dataframe_fallback(caminho_dbc)
    if df is None:
        return 0

    # Normaliza colunas
    df.columns = [c.upper().strip() for c in df.columns]
    logger.info(f"   {len(df):,} registros | colunas: {len(df.columns)}")

    # ── Extrai campos relevantes ──────────────────────────────────
    def _get(row, col, default=None):
        """Pega valor de coluna com fallback seguro."""
        val = row.get(col, default)
        if pd.isna(val) if val is not None else True:
            return default
        return val

    def _str(row, col, maxlen=None):
        v = str(_get(row, col, "") or "").strip()
        return v[:maxlen] if maxlen else v

    def _int(row, col):
        try:
            return int(float(str(_get(row, col, 0) or 0)))
        except Exception:
            return 0

    def _float(row, col):
        try:
            return float(str(_get(row, col, 0.0) or 0.0).replace(",", "."))
        except Exception:
            return 0.0

    def _date(row, col):
        """Converte data AAAAMMDD do DATASUS para date Python."""
        try:
            v = str(_get(row, col, "") or "").strip()
            if len(v) == 8 and v.isdigit():
                return datetime.strptime(v, "%Y%m%d").date()
        except Exception:
            pass
        return None

    # Ano/mês de competência
    ano_col = next((c for c in ["ANO_CMPT", "ANOMES"] if c in df.columns), None)
    mes_col = next((c for c in ["MES_CMPT"] if c in df.columns), None)

    batch = []
    for _, row in df.iterrows():
        row = row.to_dict()

        # Mês de competência no formato YYYY-MM
        if ano_col and mes_col:
            ano_val = _int(row, ano_col)
            mes_val = _int(row, mes_col)
            mes_competencia = f"{ano_val:04d}-{mes_val:02d}" if ano_val and mes_val else None
        else:
            mes_competencia = None

        # Especialidade: converte código para nome legível
        espec_cod = _str(row, "ESPEC", 2)
        especialidade = ESPEC_MAP.get(espec_cod, f"ESPEC_{espec_cod}" if espec_cod else "OUTRAS")

        batch.append(AIHRegistro(
            # Identificação
            n_aih=_str(row, "N_AIH", 20),
            cnes=_str(row, "CNES", 10),
            cgc_hosp=_str(row, "CGC_HOSP", 20),

            # Competência
            mes_competencia=mes_competencia,
            ano_cmpt=_int(row, "ANO_CMPT") or None,
            mes_cmpt=_int(row, "MES_CMPT") or None,

            # Especialidade e procedimento
            espec_cod=espec_cod,
            especialidade=especialidade,
            proc_solic=_str(row, "PROC_SOLIC", 20),
            proc_rea=_str(row, "PROC_REA", 20),

            # Localização
            uf_zi=_str(row, "UF_ZI", 6),
            munic_res=_str(row, "MUNIC_RES", 10),
            munic_mov=_str(row, "MUNIC_MOV", 10),
            cep=_str(row, "CEP", 10),

            # Paciente (dados não identificados)
            sexo=_str(row, "SEXO", 1),
            idade=_int(row, "IDADE") or None,
            cod_idade=_str(row, "COD_IDADE", 1),
            nasc=_date(row, "NASC"),
            raca_cor=_str(row, "RACA_COR", 2),

            # Internação
            dt_inter=_date(row, "DT_INTER"),
            dt_saida=_date(row, "DT_SAIDA"),
            dias_perm=_int(row, "DIAS_PERM") or None,
            morte=bool(_int(row, "MORTE")),

            # Diagnóstico
            diag_princ=_str(row, "DIAG_PRINC", 10),
            diag_secun=_str(row, "DIAG_SECUN", 10),
            cid_asso=_str(row, "CID_ASSO", 10),
            cid_morte=_str(row, "CID_MORTE", 10),

            # UTI
            uti_mes_to=_int(row, "UTI_MES_TO") or None,
            uti_int_to=_int(row, "UTI_INT_TO") or None,
            qt_diarias=_int(row, "QT_DIARIAS") or None,

            # Valores financeiros
            val_sh=_float(row, "VAL_SH"),
            val_sp=_float(row, "VAL_SP"),
            val_sadt=_float(row, "VAL_SADT"),
            val_tot=_float(row, "VAL_TOT"),
            val_uti=_float(row, "VAL_UTI"),

            # Gestão
            natureza=_str(row, "NATUREZA", 5),
            gestao=_str(row, "GESTAO", 1),
            complex_=_str(row, "COMPLEX", 2),
            financ=_str(row, "FINANC", 2),

            # Judicialização
            judicializado=bool(_int(row, "CAR_INT") == 4),
        ))

        # Salva em batches de 5000
        if len(batch) >= 5000:
            db.bulk_save_objects(batch)
            db.commit()
            logger.info(f"   💾 {len(batch)} registros salvos...")
            batch = []

    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    total = db.query(AIHRegistro).filter(
        AIHRegistro.mes_competencia == mes_competencia
    ).count() if mes_competencia else 0

    logger.info(f"   ✅ Importado: {os.path.basename(caminho_dbc)}")
    return len(df)


def importar_todos_dbc(
    pasta: str = "./data/sih",
    db: Session = None
) -> int:
    """
    Importa todos os arquivos .dbc de uma pasta.
    """
    arquivos = sorted(Path(pasta).glob("*.dbc"))
    if not arquivos:
        logger.warning(f"Nenhum .dbc encontrado em {pasta}")
        return 0

    logger.info(f"📂 {len(arquivos)} arquivos DBC encontrados")
    total = 0

    for arq in arquivos:
        total += importar_dbc_no_banco(str(arq), db)

    logger.info(f"✅ Total importado: {total:,} registros AIH")
    return total


# ─────────────────────────────────────────────────────────────────
# AGREGAÇÃO → SerieHistorica
# ─────────────────────────────────────────────────────────────────

def recalcular_serie_historica_sih(db: Session):
    """
    Agrega AIHRegistro → SerieHistorica.

    Usa os dados reais do SIH para calcular entradas e saídas mensais
    por especialidade. Com 15 anos de dados (2010-2024), o Holt-Winters
    vai capturar padrões sazonais reais do SUS Ceará.

    O que cada campo significa:
    - fila_total: estimativa da fila acumulada (entradas - saídas)
    - entradas_mes: novos casos internados naquele mês
    - saidas_mes: altas + óbitos naquele mês (= cirurgias realizadas)
    - val_tot_mes: valor total pago pelo SUS naquele mês
    - mortalidade_mes: óbitos naquele mês
    - media_dias_perm: tempo médio de internação
    """
    from database import AIHRegistro, SerieHistorica
    from sqlalchemy import func

    logger.info("📊 Recalculando SerieHistorica a partir do SIH...")

    # Limpa série atual
    db.query(SerieHistorica).delete()
    db.commit()

    # Agrega por mês + especialidade
    rows = db.query(
        AIHRegistro.mes_competencia,
        AIHRegistro.especialidade,
        func.count(AIHRegistro.id).label("total"),
        func.sum(AIHRegistro.val_tot).label("val_tot"),
        func.sum(AIHRegistro.morte.cast(Integer)).label("mortes"),
        func.avg(AIHRegistro.dias_perm).label("media_dias"),
    ).filter(
        AIHRegistro.mes_competencia.isnot(None),
        AIHRegistro.especialidade.isnot(None),
    ).group_by(
        AIHRegistro.mes_competencia,
        AIHRegistro.especialidade,
    ).order_by(
        AIHRegistro.mes_competencia,
        AIHRegistro.especialidade,
    ).all()

    if not rows:
        logger.warning("Nenhum dado AIH encontrado para agregar")
        return

    # Calcula fila acumulada por especialidade
    fila_acum = {}  # especialidade → fila atual
    batch = []

    for mes, esp, total, val_tot, mortes, media_dias in rows:
        if esp not in fila_acum:
            fila_acum[esp] = 0

        # Modelo simplificado: entradas = internações, saídas = altas
        # No SIH, cada registro é uma internação que já saiu (AIH paga)
        # Então: saídas_mes = total, entradas estimadas = total * fator_demanda
        # Fator demanda: no SUS a fila é ~5x maior que a produção mensal
        saidas = int(total)
        entradas = int(total * 1.3)  # 30% mais entram do que saem → fila cresce

        fila_acum[esp] = max(0, fila_acum[esp] + entradas - saidas)

        batch.append(SerieHistorica(
            mes=mes,
            especialidade=esp,
            fila_total=fila_acum[esp],
            entradas_mes=entradas,
            saidas_mes=saidas,
            capacidade_mes=saidas,
            # Campos novos
            val_tot_mes=float(val_tot or 0),
            mortalidade_mes=int(mortes or 0),
            media_dias_perm=float(media_dias or 0),
            total_aih_mes=saidas,
        ))

        if len(batch) >= 1000:
            db.bulk_save_objects(batch)
            db.commit()
            batch = []

    # TOTAL geral por mês
    rows_total = db.query(
        AIHRegistro.mes_competencia,
        func.count(AIHRegistro.id).label("total"),
        func.sum(AIHRegistro.val_tot).label("val_tot"),
    ).filter(
        AIHRegistro.mes_competencia.isnot(None),
    ).group_by(
        AIHRegistro.mes_competencia,
    ).order_by(
        AIHRegistro.mes_competencia,
    ).all()

    fila_total = 0
    for mes, total, val_tot in rows_total:
        saidas = int(total)
        entradas = int(total * 1.3)
        fila_total = max(0, fila_total + entradas - saidas)

        batch.append(SerieHistorica(
            mes=mes,
            especialidade="TOTAL",
            fila_total=fila_total,
            entradas_mes=entradas,
            saidas_mes=saidas,
            capacidade_mes=saidas,
            val_tot_mes=float(val_tot or 0),
        ))

    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    total_registros = db.query(SerieHistorica).count()
    logger.info(f"✅ SerieHistorica: {total_registros} registros gerados")
    logger.info(f"   Período: {rows[0][0]} → {rows[-1][0]}")
    logger.info(f"   Especialidades: {len(fila_acum)}")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("sih_import.log"),
        ]
    )
    parser = argparse.ArgumentParser(description="Download e importação SIH/DATASUS")
    parser.add_argument("--uf", default="CE", help="UF (default: CE)")
    parser.add_argument("--anos", nargs="+", type=int,
                        default=list(range(2010, 2025)),
                        help="Anos para baixar (default: 2010-2024)")
    parser.add_argument("--pasta", default="./data/sih",
                        help="Pasta de destino dos .dbc")
    parser.add_argument("--so-importar", action="store_true",
                        help="Pula download, só importa .dbc já existentes")
    parser.add_argument("--so-serie", action="store_true",
                        help="Só recalcula SerieHistorica (sem reimportar AIH)")
    args = parser.parse_args()

    # Conecta ao banco
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from database import SessionLocal, init_db
    init_db()
    db = SessionLocal()

    try:
        if args.so_serie:
            # Só recalcula a série
            recalcular_serie_historica_sih(db)

        elif args.so_importar:
            # Importa .dbc já baixados
            total = importar_todos_dbc(args.pasta, db)
            recalcular_serie_historica_sih(db)
            logger.info(f"🎉 Concluído: {total:,} AIHs importadas")

        else:
            # Download + importação completa
            logger.info(f"🚀 UF: {args.uf} | Anos: {args.anos}")

            arquivos = baixar_multiplos(args.uf, args.anos, args.pasta)
            logger.info(f"📥 {len(arquivos)} arquivos baixados")

            total = importar_todos_dbc(args.pasta, db)
            recalcular_serie_historica_sih(db)

            logger.info(f"🎉 Concluído!")
            logger.info(f"   AIHs importadas: {total:,}")
            logger.info(f"   Arquivos .dbc: {len(arquivos)}")

    finally:
        db.close()


# # Baixa e importa tudo (2010-2024)
# python download_sih.py

# # Só importa os .dbc já baixados
# python download_sih.py --so-importar

# # Só recalcula a SerieHistorica
# python download_sih.py --so-serie