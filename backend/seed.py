"""
PREDMED — Seed de tenants e usuários demo (multi-tenant)

Idempotente: cria apenas o que falta. Não apaga nem sobrescreve usuários,
tenants, configurações de vagas ou dados já existentes.

Uso:
    APP_ENV=dev python seed.py              # cria o que falta
    APP_ENV=dev python seed.py --reimportar # reimporta CSVs de backend/data/
                                            # (a fila só é substituída se o novo
                                            #  arquivo for válido; ver import_integrasus)
    SEED_SENHA_PADRAO=... python seed.py --redefinir-senhas   # rotação de senhas demo

Senhas: SEED_SENHA_<SESA|SMS|HGF|PARTICULAR> ou SEED_SENHA_PADRAO.
Em APP_ENV=dev, sem variável, usa a senha de demonstração de dev.
Fora de dev, usuário sem senha definida NÃO é criado.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_ENV, MODO_DEV, get_senha_seed  # noqa: E402
from database import (  # noqa: E402
    init_db, SessionLocal, Tenant, Usuario, ConfigVagas,
    CapacidadeHospital, PacienteFila, SerieHistorica,
)
from auth import hash_password  # noqa: E402
from services.data_import import auto_import  # noqa: E402

TENANTS = [
    # chave, dados
    ("sesa", dict(
        nome="SESA — Secretaria de Saúde do Ceará", tipo="SESA",
        cir="Ceará (todos)", cnpj="06.628.528/0001-72",
    )),
    ("sms_sobral", dict(
        nome="SMS — Secretaria Municipal de Saúde de Sobral", tipo="SMS",
        cir="CIR Sobral", municipio_gestor="SOBRAL", cnpj="07.598.143/0001-50",
    )),
    ("hosp_pub", dict(
        nome="HGF Hospital Geral de Fortaleza", tipo="hospital_publico",
        cir="CIR Fortaleza", cnpj="07.954.114/0001-84",
    )),
    ("hosp_part", dict(
        nome="Hospital São Raimundo", tipo="hospital_particular",
        cir="CIR Fortaleza", cnpj="12.345.678/0001-99",
    )),
]

USUARIOS = [
    # chave de senha, nome, email, role, tenant
    ("SESA", "Ana Gestora", "sesa@predmed.com", "sesa", "sesa"),
    ("SMS", "Dr. João SMS Sobral", "sms@predmed.com", "sms", "sms_sobral"),
    ("HGF", "Dr. Carlos HGF", "hgf@predmed.com", "hospital_publico", "hosp_pub"),
    ("PARTICULAR", "Dr. Marcelo Particular", "particular@predmed.com",
     "hospital_particular", "hosp_part"),
]

VAGAS_PARTICULAR = [
    ("ORTOPEDIA", 20, True),
    ("CIR DIGESTIVA", 15, True),
    ("CARDIOVASCULAR", 8, True),
    ("OFTALMOLOGIA", 30, True),
    ("UROLOGIA", 10, True),
    ("GINECOLOGIA", 12, True),
    ("ONCOLOGIA", 5, False),
    ("NEUROLOGIA", 0, False),
]


def _senha_de_ambiente(chave: str) -> str | None:
    return (os.getenv(f"SEED_SENHA_{chave}", "").strip()
            or os.getenv("SEED_SENHA_PADRAO", "").strip() or None)


def _obter_ou_criar_tenant(db, dados: dict) -> tuple[Tenant, bool]:
    t = db.query(Tenant).filter(Tenant.cnpj == dados["cnpj"]).first()
    if t:
        return t, False
    t = Tenant(**dados)
    db.add(t)
    db.flush()
    return t, True


def seed_usuarios(db, redefinir_senhas: bool = False) -> dict:
    """
    Cria tenants, usuários e vagas que faltam. Retorna contagens.
    redefinir_senhas=True troca a senha dos usuários demo existentes, mas só com
    senha vinda de variável de ambiente (nunca com o padrão de dev) — rotação.
    """
    criados = {"tenants": 0, "usuarios": 0, "vagas": 0, "vinculos_completados": 0,
               "senhas_redefinidas": 0,
               "usuarios_sem_senha": []}
    tenants = {}
    for chave, dados in TENANTS:
        t, novo = _obter_ou_criar_tenant(db, dados)
        tenants[chave] = t
        criados["tenants"] += int(novo)

    for chave_senha, nome, email, role, tenant_chave in USUARIOS:
        existente = db.query(Usuario).filter(Usuario.email == email).first()
        if existente:
            # Nunca altera usuário existente (nem senha nem papel). Só completa o
            # vínculo com a instituição se ele estiver vazio.
            if existente.tenant_id is None:
                existente.tenant_id = tenants[tenant_chave].id
                criados["vinculos_completados"] += 1
            if redefinir_senhas:
                nova = _senha_de_ambiente(chave_senha)
                if nova:
                    existente.senha_hash = hash_password(nova)
                    criados["senhas_redefinidas"] += 1
            continue
        senha = get_senha_seed(chave_senha)
        if not senha:
            criados["usuarios_sem_senha"].append(email)
            continue
        db.add(Usuario(
            nome=nome, email=email, senha_hash=hash_password(senha),
            role=role, tenant_id=tenants[tenant_chave].id,
        ))
        criados["usuarios"] += 1

    part = tenants["hosp_part"]
    for esp, qtd, ativo in VAGAS_PARTICULAR:
        existe = db.query(ConfigVagas).filter(
            ConfigVagas.tenant_id == part.id, ConfigVagas.especialidade == esp
        ).first()
        if not existe:
            db.add(ConfigVagas(tenant_id=part.id, especialidade=esp, vagas_mes=qtd, ativo=ativo))
            criados["vagas"] += 1

    db.commit()
    return criados


def seed(reimportar: bool = False, redefinir_senhas: bool = False):
    init_db()
    db = SessionLocal()
    try:
        criados = seed_usuarios(db, redefinir_senhas=redefinir_senhas)
        if redefinir_senhas:
            print(f"[SEED] {criados['senhas_redefinidas']} senhas redefinidas a partir das variáveis SEED_SENHA_*")
        print(f"[SEED] APP_ENV={APP_ENV} — criados: {criados['tenants']} tenants, "
              f"{criados['usuarios']} usuários, {criados['vagas']} configs de vagas, "
              f"{criados['vinculos_completados']} vínculos usuário→tenant completados "
              "(existentes foram preservados)")
        for email in criados["usuarios_sem_senha"]:
            print(f"[SEED] ⚠️  {email} não criado: defina SEED_SENHA_PADRAO ou a senha específica.")

        # ── DADOS ─────────────────────────────────────────
        tem_capacidade = db.query(CapacidadeHospital).count() > 0
        tem_fila = db.query(PacienteFila).count() > 0
        if reimportar or not (tem_capacidade and tem_fila):
            auto_import(db, importar_datasus=reimportar or not tem_capacidade,
                        importar_fila=reimportar or not tem_fila)
        else:
            print("[SEED] Fila e capacidade já existem — nada reimportado "
                  "(use --reimportar para carregar novos CSVs).")

        if reimportar or db.query(SerieHistorica).count() == 0:
            from services.previsoes import build_serie_historica
            build_serie_historica(db)
            print("[SEED] Série histórica construída")

        print()
        print("  ✅  PREDMED — Seed concluído.")
        if MODO_DEV and not os.getenv("SEED_SENHA_PADRAO"):
            print("  Usuários de demo (dev): sesa@, sms@, hgf@, particular@predmed.com")
            print("  Senha: padrão de desenvolvimento (ver README) — só vale para usuários "
                  "criados agora; usuários existentes mantêm a senha atual.")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed idempotente do PREDMED")
    parser.add_argument("--reimportar", action="store_true",
                        help="Reimporta os CSVs de backend/data/ (fila substituída só se válida)")
    parser.add_argument("--redefinir-senhas", action="store_true",
                        help="Rotação: troca a senha dos usuários demo existentes pela de "
                             "SEED_SENHA_<CHAVE>/SEED_SENHA_PADRAO (exige a variável)")
    args = parser.parse_args()
    seed(reimportar=args.reimportar, redefinir_senhas=args.redefinir_senhas)
