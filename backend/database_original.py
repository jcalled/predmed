"""
PREDMED — Database Layer (SQLAlchemy + SQLite for MVP)
Em produção: trocar DATABASE_URL por PostgreSQL
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, DateTime, ForeignKey, Text, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

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
    role        = Column(String, nullable=False)  # sesa | hospital_publico | hospital_particular
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
    especialidade    = Column(String, index=True)
    classif_swalis   = Column(String, index=True)
    judicializado    = Column(Boolean, default=False)
    procedimento     = Column(String)
    data_insercao    = Column(String)
    data_atualizacao = Column(String)  # data do CSV importado


# ──────────────────────────────────────────────
# CAPACIDADE HOSPITALAR (DATASUS)
# ──────────────────────────────────────────────
class CapacidadeHospital(Base):
    __tablename__ = "capacidade_hospitais"
    id               = Column(Integer, primary_key=True, index=True)
    hospital_nome    = Column(String, index=True)
    municipio        = Column(String)
    cir              = Column(String, default="CIR Fortaleza")
    tipo             = Column(String, default="publico")  # publico | particular
    total_cirurgias  = Column(Integer, default=0)         # total histórico
    meses            = Column(Integer, default=1)
    media_mensal     = Column(Float, default=0)


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


class HospitalCirMap(Base):
    """
    CIR inferida de cada hospital pelo IntegraSUS.
    Atualizada a cada importação do CSV.
    Mais precisa que inferência por nome.
    """
    __tablename__ = "hospital_cir_map"
    id            = Column(Integer, primary_key=True, index=True)
    hospital_nome = Column(String, unique=True, index=True)
    municipio     = Column(String)
    cir           = Column(String)
    confianca     = Column(Float)   # % dos pacientes do município dominante
    atualizado_em = Column(DateTime, default=datetime.utcnow)



class HospitalEspecialidade(Base):
    """
    Mapeamento de quais especialidades cada hospital atende
    Fontes: CNES (leitos), SIH (procedimentos), IntegraSUS (fila)
    """
    __tablename__ = "hospital_especialidades"
    
    id = Column(Integer, primary_key=True, index=True)
    hospital_nome = Column(String, nullable=False, index=True)
    hospital_cnes = Column(String, index=True)  # Código CNES para match preciso
    especialidade = Column(String, nullable=False, index=True)
    total_procedimentos = Column(Integer, default=0)  # Quantos procedimentos realizados
    leitos_disponiveis = Column(Integer, default=0)   # Leitos específicos da especialidade
    pacientes_na_fila = Column(Integer, default=0)    # Pacientes aguardando
    fonte = Column(String)  # 'cnes', 'sih', 'integrasus', 'combinado'
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow)
    
    # Índice composto para busca rápida
    __table_args__ = (
        Index('idx_hospital_especialidade_unique', 'hospital_cnes', 'especialidade', unique=True),
    )


# ──────────────────────────────────────────────
# SÉRIE HISTÓRICA (snapshots mensais calculados)
# ──────────────────────────────────────────────
class SerieHistorica(Base):
    __tablename__ = "serie_historica"
    id              = Column(Integer, primary_key=True, index=True)
    mes             = Column(String, index=True)          # "2024-01"
    especialidade   = Column(String, index=True)          # "ORTOPEDIA" | "TOTAL"
    fila_total      = Column(Integer, default=0)          # pacientes na fila
    entradas_mes    = Column(Integer, default=0)          # novos casos
    saidas_mes      = Column(Integer, default=0)          # cirurgias realizadas
    capacidade_mes  = Column(Integer, default=0)          # capacidade instalada
    criado_em       = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
