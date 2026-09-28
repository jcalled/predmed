"""
PREDMED — Backend FastAPI
Multi-tenant, role-based, dados reais IntegraSUS + DATASUS
"""
from fastapi import FastAPI, Depends, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import random
import shutil
import os

from services.previsoes_ml import limpar_cache, get_previsoes_todas_especialidades_prophet

from contextlib import asynccontextmanager
import threading

import logging
logger = logging.getLogger("main")



from database import (
    get_db, init_db, SessionLocal,
    Usuario, Tenant, PacienteFila, CapacidadeHospital,
    ConfigVagas, Transferencia
)
from auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_sesa
)
from services.ia_engine import (
    get_dashboard_kpis, get_hospitais_pressao,
    get_redistribuicao_sugestoes, get_vagas_status_tenant,
    pressao_status
)
from services.data_import import import_integrasus, import_datasus

from services.previsoes import (
    get_previsoes, get_previsoes_todas_especialidades,
    build_serie_historica, ESPERA_MEDIA_ESP
)

from services.previsoes_ml import get_previsoes_prophet, get_previsoes_todas_especialidades_prophet

from services.analytics_sih import (
    get_resumo_analytics, get_sazonalidade_real,
    get_mortalidade_por_hospital, get_pressao_historica,
    get_receita_aih_real, get_simulador_receita,
    get_validacao_mape, get_espera_media_real
)

# def _treinar_em_background(db):
#     """Treina todos os modelos ao subir o servidor."""
#     logger.info("🔄 Iniciando pré-treinamento dos modelos ML...")
#     get_previsoes_todas_especialidades_prophet(db)
#     logger.info("✅ Modelos ML prontos!")

def _treinar_em_background(db):
    logger.info("🔄 Retreinando modelos ML após upload...")
    from services.previsoes_ml import get_previsoes_prophet
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
                get_previsoes_prophet(db, esp, horizonte=h)
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    q = db.query(PacienteFila)

    # hospital_publico vê só a fila do seu próprio hospital
    if user.role == "hospital_publico":
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant:
            hosp_key = tenant.nome.upper().split()[0]
            q = q.filter(PacienteFila.hospital_nome.ilike(f"%{hosp_key}%"))

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
    rows = q.order_by(swalis_order).offset((page - 1) * limit).limit(limit).all()

    # Stats gerais
    stats = {
        "total": total,
        "a1": db.query(func.count(PacienteFila.id)).filter(
            PacienteFila.classif_swalis == "Categoria A1").scalar() or 0,
        "judicializados": db.query(func.count(PacienteFila.id)).filter(
            PacienteFila.judicializado == True).scalar() or 0,
        "especialidades": [
            {"nome": e, "total": n}
            for e, n in db.query(PacienteFila.especialidade, func.count(PacienteFila.id))
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
@app.get("/redistribuicao")
def redistribuicao(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # data = get_redistribuicao_sugestoes(db)
    data = get_redistribuicao_sugestoes(db)  # ← MODIFICADO

    # particular e hospital_publico veem, mas SÓ SESA pode aprovar
    data["pode_aprovar"] = user.role == "sesa"
    return data


@app.post("/redistribuicao/aprovar")
def aprovar_redistribuicao(
    data: AprovacaoInput,
    user: Usuario = Depends(require_sesa),
    db: Session = Depends(get_db)
):
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
        "aih_estimada": data.qtd_pacientes * 1500,
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
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if tenant:
            q = q.filter(Transferencia.hospital_origem.ilike(f"%{tenant.nome.split()[0]}%"))

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
                "aih_estimada": t.qtd_pacientes * 1500,
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
@app.post("/admin/import/integrasus")
def upload_integrasus(
    file: UploadFile = File(...),
    user: Usuario = Depends(require_sesa),
    db: Session = Depends(get_db)
):
    path = f"/tmp/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    count = import_integrasus(path, db)


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
    path = f"/tmp/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    count = import_datasus(path, db)
    return {"ok": True, "hospitais_importados": count}


# ─── PRIORIZACAO ──────────────────────────────────────────
@app.get("/priorizacao")
def priorizacao(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import case
    swalis_order = case(
        {"Categoria A1": 0, "Categoria A2": 1, "Categoria B": 2,
         "Categoria C": 3, "Categoria D": 4},
        value=PacienteFila.classif_swalis, else_=5
    )
    top = db.query(PacienteFila).order_by(swalis_order).limit(20).all()

    dist = db.query(
        PacienteFila.classif_swalis,
        func.count(PacienteFila.id).label("n")
    ).group_by(PacienteFila.classif_swalis).all()

    return {
        "top_prioritarios": [
            {
                "id": p.id, "iniciais": p.iniciais,
                "hospital_nome": p.hospital_nome,
                "especialidade": p.especialidade,
                "classif_swalis": p.classif_swalis,
                "judicializado": p.judicializado,
                "procedimento": p.procedimento,
                "score_ia": 100 - ["Categoria A1", "Categoria A2", "Categoria B",
                                    "Categoria C", "Categoria D"].index(
                                        p.classif_swalis) * 20 if p.classif_swalis in [
                                        "Categoria A1", "Categoria A2", "Categoria B",
                                        "Categoria C", "Categoria D"] else 0,
            }
            for p in top
        ],
        "distribuicao_swalis": {row[0]: row[1] for row in dist},
    }


# ─── JUDICIALIZADOS ───────────────────────────────────────
@app.get("/judicializados")
def judicializados(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rows = db.query(PacienteFila).filter(
        PacienteFila.judicializado == True
    ).limit(100).all()

    return {
        "total": db.query(func.count(PacienteFila.id)).filter(
            PacienteFila.judicializado == True).scalar() or 0,
        "pacientes": [
            {
                "id": p.id, "iniciais": p.iniciais,
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
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        nome_key = tenant.nome.split()[0] if tenant else ""
        hosp = [h for h in hosp if nome_key.upper() in h["hospital_nome"].upper()]

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


# --- PREVISOES PROPHET (MACHINE LEARNING) ---────────────────────────────────────────

# @app.get("/previsoes/prophet")
# def previsoes_prophet(
#     especialidade: Optional[str] = None,
#     horizonte: int = 6,
#     user: Usuario = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Previsões usando Prophet (Facebook) - MAPE < 15%
     
#     Este é o modelo principal para o Programa Centelha.
#     """
#     return get_previsoes_prophet(db, especialidade, horizonte)

@app.get("/previsoes/prophet")
def previsoes_prophet(
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


@app.get("/previsoes/prophet/todas")
def previsoes_prophet_todas(
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
    return get_previsoes_todas_especialidades_prophet(db)

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
            "aih_estimada_redistrib": redistrib_esp * 1500,
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
            "reducao_total_pct": round(
                (fila_total_6m_sem - fila_total_6m_com) / max(fila_total_6m_sem, 1) * 100, 1
            ),
        },
        "plano_por_especialidade": plano,
        "sugestoes_redistribuicao": redistrib["sugestoes"],
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
    MAPE real: compara previsão do modelo vs dados SIH realizados.
    Prova técnica para o Programa Centelha (exige MAPE < 15%).
    """
    from services.analytics_sih import get_validacao_mape
    return get_validacao_mape(db, especialidade=especialidade, meses_validacao=meses)


@app.get("/analytics/espera-media")
def analytics_espera_media(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tempo médio de espera real por especialidade — calculado do SIH.
    Substitui os valores hardcoded em ESPERA_MEDIA_ESP.
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




