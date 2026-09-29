"""
PREDMED — Backend FastAPI
Multi-tenant, role-based, dados reais IntegraSUS + DATASUS
"""
from fastapi import FastAPI, Depends, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, false
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import random
import shutil
import os
import tempfile

from services.previsoes_ml import limpar_cache, get_previsoes_ml, get_previsoes_ml_todas

from contextlib import asynccontextmanager
import threading

import logging
logger = logging.getLogger("main")



from database import (
    get_db, init_db, SessionLocal,
    Usuario, Tenant, PacienteFila, CapacidadeHospital,
    ConfigVagas, Transferencia, HospitalCirMap
)
from config import get_cors_origins
from auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_sesa, require_gestor
)
from services.ia_engine import (
    get_dashboard_kpis, get_hospitais_pressao,
    get_redistribuicao_sugestoes, get_vagas_status_tenant,
    pressao_status, VALOR_AIH_SIMULADO
)
from services.data_import import import_integrasus, import_datasus, ImportacaoInvalida
from services.priorizacao import VERSAO_REGRAS, calcular_score, dias_desde, eh_oncologico

from services.previsoes import (
    get_previsoes, get_previsoes_todas_especialidades,
    build_serie_historica, ESPERA_MEDIA_ESP, ESPERA_MEDIA_ORIGEM
)

from services.analytics_sih import (
    get_resumo_analytics, get_sazonalidade_real,
    get_mortalidade_por_hospital, get_pressao_historica,
    get_receita_aih_real, get_simulador_receita,
    get_validacao_mape, get_espera_media_real
)


def _treinar_em_background(db):
    logger.info("🔄 Retreinando modelos ML após upload...")
    from database import SerieHistorica

    especialidades = db.query(SerieHistorica.especialidade).distinct().all()
    especialidades = [e[0] for e in especialidades] or [
        "ONCOLOGIA", "CARDIOVASCULAR", "NEUROLOGIA",
        "ORTOPEDIA", "UROLOGIA", "GINECOLOGIA", "OFTALMOLOGIA", "TOTAL"
    ]

    horizontes = [3, 6, 12, 18, 24]

    for esp in especialidades:
        for h in horizontes:
            try:
                get_previsoes_ml(db, esp, horizonte=h)
                logger.info(f"✅ {esp} — {h} meses treinado")
            except Exception as e:
                logger.error(f"❌ {esp} {h}m: {e}")

    logger.info("✅ Todos os modelos prontos!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Roda ao iniciar o servidor
    db = next(get_db())
    thread = threading.Thread(target=_treinar_em_background, args=(db,), daemon=True)
    thread.start()
    yield
    # Roda ao encerrar (pode deixar vazio)


# ─── App ──────────────────────────────────────────────────
# app = FastAPI(title="PREDMED API", version="1.0.0", lifespan=lifespan)
app = FastAPI(title="PREDMED API", version="1.0.0") # Sem retreino

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),  # CORS_ORIGINS (vírgula); padrão localhost só em dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    # Se banco vazio, roda seed automaticamente
    db = SessionLocal()
    if db.query(Usuario).count() == 0:
        db.close()
        import subprocess, sys
        subprocess.run([sys.executable, "seed.py"], cwd=os.path.dirname(__file__))
    else:
        db.close()


# ─── SCHEMAS ──────────────────────────────────────────────
class LoginInput(BaseModel):
    email: str
    password: str


class VagaUpdate(BaseModel):
    especialidade: str
    vagas_mes: int
    ativo: bool = True


class AprovacaoInput(BaseModel):
    hospital_origem: str
    hospital_destino: str
    tenant_destino_id: Optional[int] = None
    especialidade: str
    qtd_pacientes: int


# ─── AUTH ─────────────────────────────────────────────────
@app.post("/auth/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.ativo == True
    ).first()
    if not user or not verify_password(data.password, user.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    token = create_token({
        "sub": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "tenant_nome": tenant.nome if tenant else "",
        "tenant_cir": tenant.cir if tenant else "",
        "user_nome": user.nome,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "tenant_nome": tenant.nome if tenant else "",
            "tenant_cir": tenant.cir if tenant else "",
        }
    }


@app.get("/auth/me")
def me(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return {
        "id": user.id, "nome": user.nome, "email": user.email,
        "role": user.role, "tenant_id": user.tenant_id,
        "tenant_nome": tenant.nome if tenant else "",
        "tenant_cir": tenant.cir if tenant else "",
    }


# ─── DASHBOARD ────────────────────────────────────────────
@app.get("/dashboard")
def dashboard(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_dashboard_kpis(db, user.role, user.tenant_id)


# ─── ESCOPO DE DADOS POR INSTITUIÇÃO ───────────────────────
# Regras decididas pelo proponente em 28/09/2026 (README, "Quem vê o quê"):
# - SESA e SMS: veem o estado inteiro.
# - hospital_publico: fila detalhada só do próprio hospital; priorização e
#   judicializados de todas as instituições, com iniciais ocultas nas linhas
#   de outros hospitais (LGPD).
# - hospital_particular: linhas individuais só do próprio hospital; do resto
#   do estado, apenas dados agregados (contagens).
# O vínculo tenant → hospital ainda é feito pelo 1º termo do nome do tenant
# (ex.: "HGF ..." → hospital_nome ILIKE '%HGF%'). Enquanto não houver vínculo
# por CNES, falhamos fechado quando a chave é genérica ou ausente.
_ROLES_HOSPITAL = ("hospital_publico", "hospital_particular")
_CHAVES_GENERICAS = {
    "HOSPITAL", "HOSP", "HOSP.", "INSTITUTO", "CENTRO", "CLINICA", "CLÍNICA",
    "SECRETARIA", "SMS", "SESA", "UNIDADE", "MATERNIDADE", "SANTA", "SAO", "SÃO",
}


def _chave_hospital_do_tenant(db: Session, user: Usuario) -> Optional[str]:
    """Chave de nome do hospital do usuário, ou None se não for seguro filtrar."""
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    if not tenant or not tenant.nome or not tenant.nome.split():
        return None
    chave = tenant.nome.upper().split()[0]
    if len(chave) < 3 or chave in _CHAVES_GENERICAS:
        logger.warning("Tenant %s com nome genérico: escopo de hospital não resolvido", tenant.id)
        return None
    return chave


def _filtrar_pacientes_por_escopo(q, db: Session, user: Usuario):
    """Restringe uma query de PacienteFila às linhas do próprio hospital (perfis hospitalares)."""
    if user.role in _ROLES_HOSPITAL:
        chave = _chave_hospital_do_tenant(db, user)
        if chave is None:
            return q.filter(false())  # falha fechado: sem vínculo confiável, nada é exibido
        return q.filter(PacienteFila.hospital_nome.ilike(f"%{chave}%"))
    return q


def _escopo_linhas_compartilhadas(q, db: Session, user: Usuario):
    """Priorização/judicializados: hospital público vê todas as instituições;
    hospital particular só as próprias linhas (o resto apenas agregado)."""
    if user.role == "hospital_particular":
        return _filtrar_pacientes_por_escopo(q, db, user)
    return q


def _mascara_iniciais(db: Session, user: Usuario):
    """Função que oculta as iniciais de pacientes de outros hospitais (perfis hospitalares)."""
    if user.role not in _ROLES_HOSPITAL:
        return lambda p: p.iniciais
    chave = _chave_hospital_do_tenant(db, user)
    return lambda p: p.iniciais if chave and chave in (p.hospital_nome or "").upper() else None


def _data_referencia() -> date:
    """Hoje. A fila é coletada 2x/dia, então a espera é contada até a data atual."""
    return date.today()


def _dias_espera(data_insercao: Optional[str]) -> Optional[int]:
    if not data_insercao:
        return None
    try:
        return (_data_referencia() - date.fromisoformat(data_insercao[:10])).days
    except ValueError:
        return None


# ─── FILA CIRÚRGICA ───────────────────────────────────────
@app.get("/fila")
def fila(
    page: int = 1,
    limit: int = 50,
    especialidade: Optional[str] = None,
    swalis: Optional[str] = None,
    hospital: Optional[str] = None,
    judicializado: Optional[bool] = None,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Perfis hospitalares veem linhas só do próprio hospital
    q = _filtrar_pacientes_por_escopo(db.query(PacienteFila), db, user)
    # Estatísticas agregadas: hospital público no próprio escopo;
    # particular, SMS e SESA no estado inteiro (só contagens)
    if user.role == "hospital_publico":
        escopo = q
        agg_esp = _filtrar_pacientes_por_escopo(
            db.query(PacienteFila.especialidade, func.count(PacienteFila.id)), db, user)
    else:
        escopo = db.query(PacienteFila)
        agg_esp = db.query(PacienteFila.especialidade, func.count(PacienteFila.id))

    if especialidade:
        q = q.filter(PacienteFila.especialidade.ilike(f"%{especialidade}%"))
    if swalis:
        q = q.filter(PacienteFila.classif_swalis == swalis)
    if hospital:
        q = q.filter(PacienteFila.hospital_nome.ilike(f"%{hospital}%"))
    if judicializado is not None:
        q = q.filter(PacienteFila.judicializado == judicializado)

    total = q.count()

    # Ordenação por prioridade SWALIS
    from sqlalchemy import case
    swalis_order = case(
        {"Categoria A1": 0, "Categoria A2": 1, "Categoria B": 2,
         "Categoria C": 3, "Categoria D": 4},
        value=PacienteFila.classif_swalis, else_=5
    )
    # Dentro da mesma categoria SWALIS, quem espera há mais tempo vem primeiro
    rows = q.order_by(swalis_order, PacienteFila.data_insercao.asc()) \
        .offset((page - 1) * limit).limit(limit).all()

    # Mediana só com datas confiáveis (numerações atuais)
    datas = sorted(d for (d,) in escopo.with_entities(PacienteFila.data_insercao)
                   .filter(PacienteFila.data_insercao.isnot(None),
                           PacienteFila.data_confiavel.isnot(False)).all())
    stats = {
        "total": total,
        "total_escopo_agregado": escopo.count(),
        # Espera medida desde a data da solicitação informada pelo IntegraSUS
        "espera_mediana_dias": _dias_espera(datas[len(datas) // 2]) if datas else None,
        "datas_a_confirmar": escopo.filter(PacienteFila.data_confiavel.is_(False)).count(),
        "data_referencia": _data_referencia(),
        "a1": escopo.filter(PacienteFila.classif_swalis == "Categoria A1").count(),
        "judicializados": escopo.filter(PacienteFila.judicializado == True).count(),
        "especialidades": [
            {"nome": e, "total": n}
            for e, n in agg_esp
            .group_by(PacienteFila.especialidade)
            .order_by(func.count(PacienteFila.id).desc()).limit(10).all()
        ],
    }

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "stats": stats,
        "pacientes": [
            {
                "id": r.id,
                "iniciais": r.iniciais,
                "municipio": r.municipio,
                "hospital_nome": r.hospital_nome,
                "especialidade": r.especialidade,
                "classif_swalis": r.classif_swalis,
                "judicializado": r.judicializado,
                "procedimento": r.procedimento,
                "data_insercao": r.data_insercao,
                "dias_espera": _dias_espera(r.data_insercao),
                "data_confiavel": r.data_confiavel,
            }
            for r in rows
        ]
    }


# ─── HOSPITAIS ────────────────────────────────────────────
@app.get("/hospitais")
def hospitais(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    hosp_list = get_hospitais_pressao(db)

    # Particular só vê hospitais públicos da sua CIR
    if user.role == "hospital_particular":
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        cir_user = tenant.cir if tenant else "CIR Fortaleza"
        hosp_list = [h for h in hosp_list if h["cir"] == cir_user or h["cir"] == "CIR Fortaleza"]

    # hospital_publico vê só sua CIR
    elif user.role == "hospital_publico":
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        cir_user = tenant.cir if tenant else "CIR Fortaleza"
        hosp_list = [h for h in hosp_list if h["cir"] == cir_user]

    return {"hospitais": hosp_list, "total": len(hosp_list)}


# ─── REDISTRIBUIÇÃO ───────────────────────────────────────
def _cir_do_tenant(db: Session, user: Usuario) -> Optional[str]:
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first() if user.tenant_id else None
    return tenant.cir if tenant and tenant.cir else None


def _cir_do_hospital(db: Session, hospital_nome: str) -> Optional[str]:
    m = db.query(HospitalCirMap).filter(HospitalCirMap.hospital_nome == hospital_nome).first()
    return m.cir if m else None


@app.get("/redistribuicao")
def redistribuicao(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # data = get_redistribuicao_sugestoes(db)
    data = get_redistribuicao_sugestoes(db)  # ← MODIFICADO

    # SESA aprova em todo o estado; SMS aprova transferências da própria CIR
    # (decisão de 29/09/2026). Hospitais só leem.
    data["pode_aprovar"] = user.role in ("sesa", "sms")
    data["escopo_aprovacao"] = "estado" if user.role == "sesa" else (
        _cir_do_tenant(db, user) if user.role == "sms" else None)
    return data


@app.post("/redistribuicao/aprovar")
def aprovar_redistribuicao(
    data: AprovacaoInput,
    user: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db)
):
    if user.role == "sms":
        cir = _cir_do_tenant(db, user)
        cir_origem = _cir_do_hospital(db, data.hospital_origem)
        cir_destino = _cir_do_hospital(db, data.hospital_destino)
        if not cir or cir_origem != cir or cir_destino != cir:
            raise HTTPException(403, "A SMS aprova apenas transferências entre hospitais da própria CIR")

    # Verifica vagas se destino for particular
    if data.tenant_destino_id:
        vagas = get_vagas_status_tenant(db, data.tenant_destino_id)
        vaga_esp = next(
            (v for v in vagas if v["especialidade"] == data.especialidade.upper()),
            None
        )
        if not vaga_esp or not vaga_esp["ativo"]:
            raise HTTPException(400, f"{data.especialidade} não configurada para este hospital")
        if vaga_esp["disponivel"] < data.qtd_pacientes:
            raise HTTPException(400,
                f"Vagas insuficientes: solicitado {data.qtd_pacientes}, disponível {vaga_esp['disponivel']}")

    protocolo = f"PRED-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    trans = Transferencia(
        protocolo=protocolo,
        hospital_origem=data.hospital_origem,
        hospital_destino=data.hospital_destino,
        tenant_destino_id=data.tenant_destino_id,
        especialidade=data.especialidade.upper(),
        qtd_pacientes=data.qtd_pacientes,
        aprovado_por_id=user.id,
        status="aprovado",
    )
    db.add(trans)
    db.commit()
    db.refresh(trans)

    return {
        "protocolo": protocolo,
        "status": "aprovado",
        "aih_estimada": data.qtd_pacientes * VALOR_AIH_SIMULADO,
        "aih_estimada_origem": "simulado",
        "message": f"✅ {data.qtd_pacientes} pacientes alocados para {data.hospital_destino}",
    }


@app.get("/redistribuicao/historico")
def historico_transferencias(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Transferencia)
    if user.role == "hospital_particular":
        q = q.filter(Transferencia.tenant_destino_id == user.tenant_id)
    elif user.role == "hospital_publico":
        chave = _chave_hospital_do_tenant(db, user)
        if chave is None:
            q = q.filter(false())
        else:
            q = q.filter(Transferencia.hospital_origem.ilike(f"%{chave}%"))

    rows = q.order_by(Transferencia.data_aprovacao.desc()).limit(50).all()
    return {
        "transferencias": [
            {
                "protocolo": t.protocolo,
                "data_aprovacao": t.data_aprovacao.isoformat() if t.data_aprovacao else None,
                "hospital_origem": t.hospital_origem,
                "hospital_destino": t.hospital_destino,
                "especialidade": t.especialidade,
                "qtd_pacientes": t.qtd_pacientes,
                "status": t.status,
                "aih_estimada": t.qtd_pacientes * VALOR_AIH_SIMULADO,
                "aih_estimada_origem": "simulado",
            }
            for t in rows
        ]
    }


# ─── CONFIGURAÇÕES (Particular) ───────────────────────────
@app.get("/configuracoes/vagas")
def get_vagas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role not in ["hospital_particular", "sesa"]:
        raise HTTPException(403, "Apenas hospitais particulares podem acessar esta rota")
    return {"vagas": get_vagas_status_tenant(db, user.tenant_id)}


@app.put("/configuracoes/vagas")
def update_vaga(
    data: VagaUpdate,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role != "hospital_particular":
        raise HTTPException(403, "Apenas hospitais particulares podem configurar vagas")

    cfg = db.query(ConfigVagas).filter(
        ConfigVagas.tenant_id == user.tenant_id,
        ConfigVagas.especialidade == data.especialidade.upper()
    ).first()

    if cfg:
        cfg.vagas_mes = data.vagas_mes
        cfg.ativo = data.ativo
        cfg.atualizado_em = datetime.utcnow()
    else:
        cfg = ConfigVagas(
            tenant_id=user.tenant_id,
            especialidade=data.especialidade.upper(),
            vagas_mes=data.vagas_mes,
            ativo=data.ativo,
        )
        db.add(cfg)

    db.commit()
    return {"ok": True, "especialidade": data.especialidade, "vagas_mes": data.vagas_mes}


# ─── IMPORTAÇÃO DE DADOS ──────────────────────────────────
def _importar_upload(file: UploadFile, importador, db: Session) -> int:
    """
    Grava o upload num arquivo temporário com nome gerado (não usa file.filename),
    chama o importador (transacional) e apaga o temporário.
    Arquivo inválido → 400 e a base anterior é preservada.
    """
    fd, path = tempfile.mkstemp(prefix="predmed-upload-", suffix=".csv")
    try:
        with os.fdopen(fd, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return importador(path, db)
    except ImportacaoInvalida as e:
        raise HTTPException(400, f"Importação rejeitada: {e}. Dados anteriores preservados.")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@app.post("/admin/import/integrasus")
def upload_integrasus(
    file: UploadFile = File(...),
    user: Usuario = Depends(require_sesa),
    db: Session = Depends(get_db)
):
    count = _importar_upload(file, import_integrasus, db)

    # Após salvar os dados, limpa cache e retreina em background
    limpar_cache()
    thread = threading.Thread(
        target=_treinar_em_background, 
        args=(db,), 
        daemon=True
    )
    thread.start()

    return {"ok": True, "pacientes_importados": count}


@app.post("/admin/import/datasus")
def upload_datasus(
    file: UploadFile = File(...),
    user: Usuario = Depends(require_sesa),
    db: Session = Depends(get_db)
):
    count = _importar_upload(file, import_datasus, db)
    return {"ok": True, "hospitais_importados": count}


# ─── PRIORIZACAO ──────────────────────────────────────────
@app.get("/priorizacao")
def priorizacao(
    limit: int = 50,
    especialidade: Optional[str] = None,
    apenas_oncologia: bool = False,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fila ordenada pelo score explicável (services/priorizacao.py, regras v0.1)."""
    limit = max(1, min(limit, 200))
    hoje = _data_referencia()
    iniciais = _mascara_iniciais(db, user)

    q = _escopo_linhas_compartilhadas(db.query(PacienteFila), db, user).with_entities(
        PacienteFila.id, PacienteFila.iniciais, PacienteFila.hospital_nome,
        PacienteFila.municipio, PacienteFila.especialidade, PacienteFila.classif_swalis,
        PacienteFila.judicializado, PacienteFila.procedimento,
        PacienteFila.data_insercao, PacienteFila.data_confiavel,
    )
    if especialidade:
        q = q.filter(PacienteFila.especialidade.ilike(f"%{especialidade}%"))

    avaliados = []
    for p in q.all():
        if apenas_oncologia and not eh_oncologico(p.especialidade, p.procedimento):
            continue
        r = calcular_score(
            classif_swalis=p.classif_swalis, data_insercao=p.data_insercao,
            data_confiavel=p.data_confiavel, judicializado=bool(p.judicializado),
            especialidade=p.especialidade, procedimento=p.procedimento, hoje=hoje,
        )
        avaliados.append((r.score, dias_desde(p.data_insercao, hoje) or 0, p, r))
    # Desempate: maior espera primeiro
    avaliados.sort(key=lambda t: (t[0], t[1]), reverse=True)

    # Distribuição SWALIS é agregada: estado inteiro para todos os perfis
    dist = db.query(
        PacienteFila.classif_swalis,
        func.count(PacienteFila.id).label("n")
    ).group_by(PacienteFila.classif_swalis).all()

    return {
        "versao_regras": VERSAO_REGRAS,
        "data_referencia": hoje,
        "total_avaliados": len(avaliados),
        "resumo": {
            "score_70_ou_mais": sum(1 for t in avaliados if t[0] >= 70),
            "oncologia_acima_60_dias": sum(
                1 for t in avaliados if any("Oncologia com mais" in a for a in t[3].alertas)),
            "datas_a_confirmar": sum(1 for t in avaliados if t[2].data_confiavel is False),
        },
        "top_prioritarios": [
            {
                "id": p.id, "iniciais": iniciais(p),
                "hospital_nome": p.hospital_nome,
                "municipio": p.municipio,
                "especialidade": p.especialidade,
                "classif_swalis": p.classif_swalis,
                "judicializado": p.judicializado,
                "procedimento": p.procedimento,
                "dias_espera": dias,
                "data_confiavel": p.data_confiavel,
                "score": score,
                "componentes": r.componentes,
                "alertas": r.alertas,
            }
            for score, dias, p, r in avaliados[:limit]
        ],
        "distribuicao_swalis": {row[0]: row[1] for row in dist},
    }


# ─── JUDICIALIZADOS ───────────────────────────────────────
@app.get("/judicializados")
def judicializados(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    iniciais = _mascara_iniciais(db, user)
    # Total é agregado (estado inteiro); linhas conforme o perfil
    total = db.query(PacienteFila).filter(PacienteFila.judicializado == True).count()
    rows = _escopo_linhas_compartilhadas(db.query(PacienteFila), db, user).filter(
        PacienteFila.judicializado == True
    ).limit(100).all()

    return {
        "total": total,
        "pacientes": [
            {
                "id": p.id, "iniciais": iniciais(p),
                "municipio": p.municipio, "hospital_nome": p.hospital_nome,
                "especialidade": p.especialidade, "classif_swalis": p.classif_swalis,
                "procedimento": p.procedimento,
            }
            for p in rows
        ]
    }


# ─── RELATORIOS ───────────────────────────────────────────
@app.get("/relatorios/resumo")
def relatorio_resumo(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    kpis = get_dashboard_kpis(db, user.role, user.tenant_id)
    hosp = get_hospitais_pressao(db)

    # Filtra hospitais por role
    if user.role == "hospital_publico":
        chave = _chave_hospital_do_tenant(db, user)
        hosp = [h for h in hosp if chave and chave in h["hospital_nome"].upper()]

    return {
        "kpis": kpis,
        "hospitais_criticos": [h for h in hosp if h["pressao_status"] == "critico"][:5],
        "gerado_em": datetime.now().isoformat(),
        "role": user.role,
    }



# ─── PREVISÕES ML ─────────────────────────────────────────
@app.get("/previsoes")
def previsoes(
    especialidade: Optional[str] = None,
    horizonte: int = 6,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna série histórica (24 meses) + projeção ML (6 meses).
    especialidade: vazio = TOTAL | "ORTOPEDIA" | "ONCOLOGIA" etc
    """
    horizonte = min(max(horizonte, 1), 12)
    return get_previsoes(db, especialidade=especialidade, n_future=horizonte)


@app.get("/previsoes/todas")
def previsoes_todas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resumo de previsões para todas as especialidades — usado no dashboard"""
    return get_previsoes_todas_especialidades(db)


@app.post("/previsoes/recalcular")
def recalcular_previsoes(
    user: Usuario = Depends(require_sesa),
    db: Session = Depends(get_db),
):
    """Força reprocessamento da série histórica (após novos dados importados)"""
    from database import SerieHistorica
    db.query(SerieHistorica).delete()
    db.commit()
    build_serie_historica(db)
    return {"ok": True, "message": "Série histórica recalculada com sucesso"}


# --- PREVISÕES ML (Holt-Winters; série histórica simulada, não validada) ---

@app.get("/previsoes/ml")
def previsoes_ml(
    especialidade: Optional[str] = None,
    horizonte: int = 6,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from services.previsoes_ml import _get_cache
    
    # Só retorna do cache — nunca treina aqui
    chave = f"{especialidade or 'TOTAL'}_{horizonte}"
    cached = _get_cache(chave)
    
    if cached:
        return cached
    
    # Cache vazio = ainda treinando em background
    return {
        "status": "treinando",
        "msg": "Modelos sendo preparados. Tente novamente em 1-2 minutos."
    }


@app.get("/previsoes/ml/todas")
def previsoes_ml_todas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from services.previsoes_ml import _get_cache

    # Verifica se pelo menos TOTAL está no cache
    # Se estiver, o treinamento já completou
    cached = _get_cache("TOTAL_6")

    if not cached:
        return {
            "status": "treinando",
            "msg": "Faça upload do IntegraSUS para iniciar o treinamento."
        }

    # Cache populado — chama normalmente (retorna tudo do cache, não retreina)
    return get_previsoes_ml_todas(db)

# ─── ZERAR FILAS ──────────────────────────────────────────
@app.get("/zerarfilas")
def zerar_filas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Módulo Programa Zerar Filas:
    Combina previsões + redistribuição para calcular plano de eliminação da fila.
    """
    todas = get_previsoes_todas_especialidades(db)
    redistrib = get_redistribuicao_sugestoes(db)

    plano = []
    for esp in todas["por_especialidade"]:
        nome = esp["especialidade"]
        fila_atual = esp["fila_atual"]
        fila_6m_sem = esp["fila_proj_6m"]
        espera_meses = ESPERA_MEDIA_ESP.get(nome, 5.2)

        # Pacientes redistribuíveis nesta especialidade
        redistrib_esp = sum(
            s["qtd_sugerida"] for s in redistrib["sugestoes"]
            if s["especialidade"].upper() == nome
        )

        fila_6m_com = max(0, fila_6m_sem - redistrib_esp)
        reducao_pct = round((fila_6m_sem - fila_6m_com) / max(fila_6m_sem, 1) * 100, 1)
        meses_zeramento = round(fila_6m_com / max(fila_atual / espera_meses, 1)) if fila_atual > 0 else 0

        plano.append({
            "especialidade": nome,
            "fila_atual": fila_atual,
            "fila_6m_sem_acao": fila_6m_sem,
            "fila_6m_com_redistrib": fila_6m_com,
            "pacientes_redistribuiveis": redistrib_esp,
            "reducao_redistrib_pct": reducao_pct,
            "espera_media_meses": espera_meses,
            "meses_para_zeramento": meses_zeramento,
            "aih_estimada_redistrib": redistrib_esp * VALOR_AIH_SIMULADO,
            "espera_media_origem": ESPERA_MEDIA_ORIGEM,
            "urgencia": esp["urgencia"],
            "tendencia": esp["tendencia"],
        })

    plano.sort(key=lambda x: x["fila_atual"], reverse=True)

    total_redistribuiveis = sum(p["pacientes_redistribuiveis"] for p in plano)
    total_aih = sum(p["aih_estimada_redistrib"] for p in plano)
    fila_total_atual = todas["total"].get("fila_atual", 0)
    fila_total_6m_sem = todas["total"].get("fila_proj_6m", 0)
    fila_total_6m_com = max(0, fila_total_6m_sem - total_redistribuiveis)

    return {
        "resumo": {
            "fila_total_atual": fila_total_atual,
            "fila_total_6m_sem_acao": fila_total_6m_sem,
            "fila_total_6m_com_redistrib": fila_total_6m_com,
            "total_pacientes_redistribuiveis": total_redistribuiveis,
            "total_aih_estimada": total_aih,
            "aih_estimada_origem": "simulado",
            "reducao_total_pct": round(
                (fila_total_6m_sem - fila_total_6m_com) / max(fila_total_6m_sem, 1) * 100, 1
            ),
        },
        "plano_por_especialidade": plano,
        "sugestoes_redistribuicao": redistrib["sugestoes"],
        "origem": "simulado",
        "aviso": "Plano simulado: série histórica estimada, espera média e valor de AIH são parâmetros fixos não validados.",
        "gerado_em": datetime.now().isoformat(),
    }




# ─── ANALYTICS SIH ────────────────────────────────────────────────

@app.get("/analytics/resumo")
def analytics_resumo(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resumo executivo da base AIH para SESA."""
    from services.analytics_sih import get_resumo_analytics
    return get_resumo_analytics(db)


@app.get("/analytics/sazonalidade")
def analytics_sazonalidade(
    especialidade: Optional[str] = None,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Índice sazonal real por mês e especialidade.
    Mostra quais meses têm mais/menos internações historicamente.
    """
    from services.analytics_sih import get_sazonalidade_real
    return get_sazonalidade_real(db, especialidade=especialidade)


@app.get("/analytics/mortalidade")
def analytics_mortalidade(
    especialidade: Optional[str] = None,
    ano: Optional[int] = None,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ranking de mortalidade por hospital e especialidade.
    Proxy de qualidade assistencial.
    """
    from services.analytics_sih import get_mortalidade_por_hospital
    return get_mortalidade_por_hospital(db, especialidade=especialidade, ano=ano)


@app.get("/analytics/pressao-historica")
def analytics_pressao_historica(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evolução histórica do volume de internações com detecção de picos."""
    from services.analytics_sih import get_pressao_historica
    return get_pressao_historica(db)


@app.get("/analytics/receita-aih")
def analytics_receita_aih(
    especialidade: Optional[str] = None,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Valores reais de AIH pagos pelo SUS por especialidade e complexidade."""
    from services.analytics_sih import get_receita_aih_real
    return get_receita_aih_real(db, especialidade=especialidade)


@app.post("/analytics/simulador-receita")
def analytics_simulador_receita(
    vagas: dict = Body(..., example={"ORTOPEDIA": 10, "CARDIOVASCULAR": 5}),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Simula receita mensal de um hospital particular
    se aceitar pacientes redistribuídos pelo PREDMED.
    Usa valores reais de AIH como base — não é estimativa fixa.
    """
    from services.analytics_sih import get_simulador_receita
    return get_simulador_receita(db, especialidades_vagas=vagas)


@app.get("/analytics/validacao-mape")
def analytics_validacao_mape(
    especialidade: Optional[str] = None,
    meses: int = 6,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    MAPE calculado: compara previsão do modelo vs dados SIH realizados.
    Meta do projeto (proposta Centelha): MAPE < 15%.
    """
    from services.analytics_sih import get_validacao_mape
    return get_validacao_mape(db, especialidade=especialidade, meses_validacao=meses)


@app.get("/analytics/espera-media")
def analytics_espera_media(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanência hospitalar média por especialidade (SIH, em meses).
    Não é tempo de espera na fila; ESPERA_MEDIA_ESP continua sendo parâmetro fixo.
    """
    from services.analytics_sih import get_espera_media_real
    return get_espera_media_real(db)

# ─── HEALTH CHECK ─────────────────────────────────────────
@app.get("/health")
def health(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "pacientes_na_fila": db.query(func.count(PacienteFila.id)).scalar(),
        "hospitais": db.query(func.count(CapacidadeHospital.id)).scalar(),
        "usuarios": db.query(func.count(Usuario.id)).scalar(),
        "timestamp": datetime.now().isoformat(),
    }




