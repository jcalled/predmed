"""
PREDMED — Database Layer (SQLAlchemy + SQLite for MVP)
Em produção: trocar DATABASE_URL por PostgreSQL
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, DateTime, ForeignKey, Text, Index, Date
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

import config  # noqa: F401  (carrega backend/.env antes de ler DATABASE_URL)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./predmed.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ──────────────────────────────────────────────
# TENANTS (hospitais assinantes)
# ──────────────────────────────────────────────
class Tenant(Base):
    __tablename__       = "tenants"
    id                  = Column(Integer, primary_key=True, index=True)
    nome                = Column(String, nullable=False)
    tipo                = Column(String, nullable=False)  # SESA | SMS | hospital_publico | hospital_particular
    cir                 = Column(String, default="CIR Fortaleza")
    municipio_gestor    = Column(String, nullable=True)   # Para SMS: município que gerencia (ex: "SOBRAL")
    cnpj                = Column(String, unique=True)
    ativo               = Column(Boolean, default=True)
    criado_em           = Column(DateTime, default=datetime.utcnow)
    usuarios            = relationship("Usuario", back_populates="tenant")
    config_vagas        = relationship("ConfigVagas", back_populates="tenant")


# ──────────────────────────────────────────────
# USUARIOS
# ──────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"
    id          = Column(Integer, primary_key=True, index=True)
    nome        = Column(String, nullable=False)
    email       = Column(String, unique=True, index=True, nullable=False)
    senha_hash  = Column(String, nullable=False)
    role        = Column(String, nullable=False)  # sesa | sms | hospital_publico | hospital_particular
    tenant_id   = Column(Integer, ForeignKey("tenants.id"))
    ativo       = Column(Boolean, default=True)
    tenant      = relationship("Tenant", back_populates="usuarios")


# ──────────────────────────────────────────────
# DADOS DA FILA CIRÚRGICA (IntegraSUS)
# ──────────────────────────────────────────────
class PacienteFila(Base):
    __tablename__ = "pacientes_fila"
    id               = Column(Integer, primary_key=True, index=True)
    iniciais         = Column(String)
    municipio        = Column(String)
    hospital_nome    = Column(String, index=True)
    cnes = Column(String(10), index=True, nullable=True)
    especialidade    = Column(String, index=True)
    classif_swalis   = Column(String, index=True)
    judicializado    = Column(Boolean, default=False)
    procedimento     = Column(String)
    data_insercao    = Column(String)
    data_atualizacao = Column(String)  # data do CSV importado
    
    hospital_id = Column(Integer, ForeignKey("hospitais.id"), nullable=True, index=True)
    hospital = relationship("Hospital", back_populates="pacientes")

    


# ──────────────────────────────────────────────
# CAPACIDADE HOSPITALAR (DATASUS)
# ──────────────────────────────────────────────
class CapacidadeHospital(Base):
    __tablename__ = "capacidade_hospitais"
    id               = Column(Integer, primary_key=True, index=True)
    cnes = Column(String(10), index=True, nullable=True)
    hospital_nome    = Column(String, index=True)
    municipio        = Column(String)
    cir              = Column(String, default="CIR Fortaleza")
    tipo             = Column(String, default="publico")  # publico | particular
    total_cirurgias  = Column(Integer, default=0)
    meses            = Column(Integer, default=1)
    media_mensal     = Column(Float, default=0)

    hospital_id = Column(Integer, ForeignKey("hospitais.id"), nullable=True, index=True)
    hospital = relationship("Hospital", back_populates="capacidades")


# ──────────────────────────────────────────────
# CONFIGURAÇÃO DE VAGAS (Particular)
# ──────────────────────────────────────────────
class ConfigVagas(Base):
    __tablename__ = "config_vagas"
    id            = Column(Integer, primary_key=True, index=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"))
    especialidade = Column(String, nullable=False)
    vagas_mes     = Column(Integer, default=0)
    ativo         = Column(Boolean, default=True)
    atualizado_em = Column(DateTime, default=datetime.utcnow)
    tenant        = relationship("Tenant", back_populates="config_vagas")


# ──────────────────────────────────────────────
# TRANSFERÊNCIAS APROVADAS
# ──────────────────────────────────────────────
class Transferencia(Base):
    __tablename__ = "transferencias"
    id                  = Column(Integer, primary_key=True, index=True)
    protocolo           = Column(String, unique=True, index=True)
    data_aprovacao      = Column(DateTime, default=datetime.utcnow)
    hospital_origem     = Column(String)
    hospital_destino    = Column(String)
    tenant_destino_id   = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    especialidade       = Column(String)
    qtd_pacientes       = Column(Integer)
    aprovado_por_id     = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    status              = Column(String, default="aprovado")  # aprovado | recusado | pendente


# ──────────────────────────────────────────────
# HOSPITAL CIR MAP
# CIR inferida de cada hospital pelo IntegraSUS.
# Atualizada a cada importação do CSV.
# ──────────────────────────────────────────────
class HospitalCirMap(Base):
    __tablename__ = "hospital_cir_map"
    id            = Column(Integer, primary_key=True, index=True)
    hospital_nome = Column(String, unique=True, index=True)
    municipio     = Column(String)
    cir           = Column(String)
    confianca     = Column(Float)   # % dos pacientes do município dominante
    atualizado_em = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# HOSPITAL ESPECIALIDADE
# Mapeamento de quais especialidades cada hospital atende.
# Fontes: CNES, SIH, IntegraSUS
# ──────────────────────────────────────────────
class HospitalEspecialidade(Base):
    __tablename__ = "hospital_especialidades"
    id                  = Column(Integer, primary_key=True, index=True)
    hospital_nome       = Column(String, nullable=True, index=True)
    hospital_cnes       = Column(String, index=True)
    especialidade       = Column(String, nullable=False, index=True)
    total_procedimentos = Column(Integer, default=0)
    leitos_disponiveis  = Column(Integer, default=0)
    pacientes_na_fila   = Column(Integer, default=0)
    fonte               = Column(String)   # 'cnes' | 'sih' | 'integrasus' | 'combinado'
    ultima_atualizacao  = Column(DateTime, default=datetime.utcnow)

    hospital_id = Column(Integer, ForeignKey("hospitais.id"), nullable=False, index=True)
    hospital = relationship("Hospital", back_populates="especialidades")


# ──────────────────────────────────────────────────────────────────
# AIH REGISTRO — Dados brutos do SIH/DATASUS (2010–2024)
# Fonte de verdade para série histórica, analytics e pagamentos.
# Populado pelo download_sih.py
# ──────────────────────────────────────────────────────────────────
class AIHRegistro(Base):
    __tablename__ = "aih_registro"

    id = Column(Integer, primary_key=True, index=True)

    # ── Identificação ────────────────────────────────────────────
    n_aih           = Column(String(20), index=True)    # Número da AIH
    cnes            = Column(String(10), index=True)    # Código CNES do hospital
    cgc_hosp        = Column(String(20))                # CNPJ do hospital

    # ── Competência ─────────────────────────────────────────────
    mes_competencia = Column(String(7), index=True)     # "2024-03"
    ano_cmpt        = Column(Integer, index=True)       # 2024
    mes_cmpt        = Column(Integer)                   # 3

    # ── Especialidade e Procedimento ────────────────────────────
    espec_cod       = Column(String(2), index=True)     # Código DATASUS (ex: "18")
    especialidade   = Column(String(50), index=True)    # Nome legível (ex: "ORTOPEDIA")
    proc_solic      = Column(String(20))                # Procedimento solicitado
    proc_rea        = Column(String(20), index=True)    # Procedimento realizado

    # ── Localização ─────────────────────────────────────────────
    uf_zi           = Column(String(6))                 # UF de internação
    munic_res       = Column(String(10), index=True)    # Município de residência (IBGE)
    munic_mov       = Column(String(10))                # Município de atendimento
    cep             = Column(String(10))

    # ── Paciente (não identificável) ─────────────────────────────
    sexo            = Column(String(1))                 # M/F
    idade           = Column(Integer)
    cod_idade       = Column(String(1))                 # A=anos, M=meses, D=dias
    nasc            = Column(Date)
    raca_cor        = Column(String(2))                 # 01=Branca 02=Preta 03=Parda...

    # ── Internação ──────────────────────────────────────────────
    dt_inter        = Column(Date, index=True)          # Data de internação
    dt_saida        = Column(Date)                      # Data de saída (alta/óbito)
    dias_perm       = Column(Integer)                   # Dias de permanência
    morte           = Column(Boolean, default=False)    # Óbito durante internação

    # ── Diagnóstico (CID-10) ─────────────────────────────────────
    diag_princ      = Column(String(10), index=True)    # CID principal
    diag_secun      = Column(String(10))                # CID secundário
    cid_asso        = Column(String(10))                # CID associado
    cid_morte       = Column(String(10))                # CID de óbito

    # ── UTI ──────────────────────────────────────────────────────
    uti_mes_to      = Column(Integer)                   # Dias de UTI no mês
    uti_int_to      = Column(Integer)                   # Dias UTI intermediária
    qt_diarias      = Column(Integer)                   # Quantidade de diárias

    # ── Valores Financeiros (R$) ─────────────────────────────────
    val_sh          = Column(Float, default=0)          # Serviços hospitalares
    val_sp          = Column(Float, default=0)          # Serviços profissionais
    val_sadt        = Column(Float, default=0)          # SADT (exames)
    val_tot         = Column(Float, default=0, index=True)  # Valor total pago
    val_uti         = Column(Float, default=0)          # Valor UTI

    # ── Gestão ──────────────────────────────────────────────────
    natureza        = Column(String(5))                 # Natureza jurídica
    gestao          = Column(String(1))                 # M=Municipal E=Estadual F=Federal
    complex_        = Column(String(2))                 # MA=Média AL=Alta complexidade
    financ          = Column(String(2))                 # Fonte de financiamento

    # ── Casos Especiais ──────────────────────────────────────────
    judicializado   = Column(Boolean, default=False)    # Internação por ordem judicial

    # ── Metadados ────────────────────────────────────────────────
    criado_em       = Column(DateTime, default=datetime.utcnow)

    hospital_id = Column(Integer, ForeignKey("hospitais.id"), nullable=True, index=True)
    hospital = relationship("Hospital", back_populates="aihs")


    __table_args__ = (
        Index("ix_aih_mes_esp",  "mes_competencia", "especialidade"),
        Index("ix_aih_cnes_mes", "cnes", "mes_competencia"),
        Index("ix_aih_diag",     "diag_princ", "mes_competencia"),

        # ── NOVOS ÍNDICES (performance analytics + validação) ──
        Index("idx_aih_especialidade", "especialidade"),
        Index("idx_aih_cnes", "cnes"),
        Index("idx_aih_ano", "ano_cmpt"),
        Index("idx_aih_mes", "mes_cmpt"),
        Index("idx_aih_dias_perm", "dias_perm"),
    )


# ──────────────────────────────────────────────────────────────────
# SÉRIE HISTÓRICA — Snapshots mensais agregados
# Alimentada por:
#   - IntegraSUS (fila atual): via import_integrasus()
#   - SIH/DATASUS (histórico 2010-2024): via recalcular_serie_historica_sih()
# ──────────────────────────────────────────────────────────────────
class SerieHistorica(Base):
    __tablename__ = "serie_historica"

    id              = Column(Integer, primary_key=True, index=True)
    mes             = Column(String, index=True)        # "2024-01"
    especialidade   = Column(String, index=True)        # "ORTOPEDIA" | "TOTAL"

    # ── Fila ─────────────────────────────────────────────────────
    fila_total      = Column(Integer, default=0)        # Pacientes na fila
    entradas_mes    = Column(Integer, default=0)        # Novos casos naquele mês
    saidas_mes      = Column(Integer, default=0)        # Cirurgias realizadas
    capacidade_mes  = Column(Integer, default=0)        # Capacidade instalada

    # ── Financeiro ───────────────────────────────────────────────
    val_tot_mes     = Column(Float, default=0)          # Valor total pago pelo SUS (R$)
    total_aih_mes   = Column(Integer, default=0)        # Número de AIHs pagas

    # ── Clínico ──────────────────────────────────────────────────
    mortalidade_mes = Column(Integer, default=0)        # Óbitos naquele mês
    media_dias_perm = Column(Float, default=0)          # Tempo médio de internação (dias)

    criado_em       = Column(DateTime, default=datetime.utcnow)



# Tabela Hospital unificada (use HospitalCNES como base, renomeando se preferir)
class Hospital(Base):
    __tablename__ = "hospitais"

    id = Column(Integer, primary_key=True, index=True)
    cnes = Column(String(10), unique=True, index=True, nullable=True)
    is_cirurgico = Column(Boolean, default=False)
    nome_fantasia = Column(String, nullable=False)
    razao_social = Column(String, nullable=True)
    municipio = Column(String, nullable=False)
    uf = Column(String(2), default="CE")
    gestao = Column(String(1), nullable=True)
    natureza_juridica = Column(String, nullable=True)
    atende_sus = Column(Boolean, default=True)
    esfera_administrativa = Column(String, nullable=True)
    tipo = Column(String, default="publico")      # inferido
    cir = Column(String, nullable=True)
    fonte = Column(String, default="cnes")        # cnes, integrasus, datasus, combinado
    confiavel = Column(Boolean, default=True)     # true se veio do CNES
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    pacientes = relationship("PacienteFila", back_populates="hospital")
    capacidades = relationship("CapacidadeHospital", back_populates="hospital")
    especialidades = relationship("HospitalEspecialidade", back_populates="hospital")
    aihs = relationship("AIHRegistro", back_populates="hospital")


# Melhorar o matching
class HospitalAlias(Base):
    __tablename__ = "hospital_alias"

    id = Column(Integer, primary_key=True, index=True)

    # Texto que vem nos arquivos (integrasus/datasus)
    alias_nome      = Column(String, unique=True, index=True, nullable=False)

    # Para onde isso aponta
    cnes            = Column(String(10), index=True, nullable=True)   # link direto com HospitalCNES.cnes
    hospital_nome   = Column(String, index=True, nullable=True)       # nome canônico (se você quiser)

    fonte           = Column(String, nullable=True)  # "integrasus" | "datasus" | "manual"
    atualizado_em   = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)