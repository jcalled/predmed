"""
PREDMED — Seed de usuários demo (multi-tenant)
Execute: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, SessionLocal, Tenant, Usuario, ConfigVagas, CapacidadeHospital
from auth import hash_password
from services.data_import import auto_import, _seed_demo_datasus


def seed():
    init_db()
    db = SessionLocal()

    # Limpa dados existentes
    db.query(ConfigVagas).delete()
    db.query(Usuario).delete()
    db.query(Tenant).delete()
    db.commit()

    # ── TENANTS ──────────────────────────────────────
    sesa = Tenant(
        nome="SESA — Secretaria de Saúde do Ceará",
        tipo="SESA",
        cir="Ceará (todos)",
        cnpj="06.628.528/0001-72",
    )
    sms_sobral = Tenant(
        nome="SMS — Secretaria Municipal de Saúde de Sobral",
        tipo="SMS",
        cir="CIR Sobral",
        municipio_gestor="SOBRAL",
        cnpj="07.598.143/0001-50",
    )
    hosp_pub = Tenant(
        nome="HGF Hospital Geral de Fortaleza",
        tipo="hospital_publico",
        cir="CIR Fortaleza",
        cnpj="07.954.114/0001-84",
    )
    hosp_part = Tenant(
        nome="Hospital São Raimundo",
        tipo="hospital_particular",
        cir="CIR Fortaleza",
        cnpj="12.345.678/0001-99",
    )
    db.add_all([sesa, sms_sobral, hosp_pub, hosp_part])
    db.commit()

    # ── USUÁRIOS ──────────────────────────────────────
    usuarios = [
        Usuario(
            nome="Ana Gestora", email="sesa@predmed.com",
            senha_hash=hash_password("predmed123"),
            role="sesa", tenant_id=sesa.id,
        ),
        Usuario(
            nome="Dr. João SMS Sobral", email="sms@predmed.com",
            senha_hash=hash_password("predmed123"),
            role="sms", tenant_id=sms_sobral.id,
        ),
        Usuario(
            nome="Dr. Carlos HGF", email="hgf@predmed.com",
            senha_hash=hash_password("predmed123"),
            role="hospital_publico", tenant_id=hosp_pub.id,
        ),
        Usuario(
            nome="Dr. Marcelo Particular", email="particular@predmed.com",
            senha_hash=hash_password("predmed123"),
            role="hospital_particular", tenant_id=hosp_part.id,
        ),
    ]
    db.add_all(usuarios)
    db.commit()

    # ── CONFIG VAGAS INICIAL (particular) ──────────────
    vagas_config = [
        ("ORTOPEDIA", 20, True),
        ("CIR DIGESTIVA", 15, True),
        ("CARDIOVASCULAR", 8, True),
        ("OFTALMOLOGIA", 30, True),
        ("UROLOGIA", 10, True),
        ("GINECOLOGIA", 12, True),
        ("ONCOLOGIA", 5, False),
        ("NEUROLOGIA", 0, False),
    ]
    for esp, qtd, ativo in vagas_config:
        db.add(ConfigVagas(
            tenant_id=hosp_part.id,
            especialidade=esp,
            vagas_mes=qtd,
            ativo=ativo,
        ))
    db.commit()

    # ── DADOS ──────────────────────────────────────────
    # Verifica se DATASUS já foi importado
    cap_count = db.query(CapacidadeHospital).count()
    if cap_count == 0:
        _seed_demo_datasus(db)

    # Auto-import CSVs
    auto_import(db)

    # ─── CONSTRUIR SÉRIE HISTÓRICA ──────────────────────────
    from services.previsoes import build_serie_historica
    build_serie_historica(db)
    print("[SEED] Série histórica reconstruída")

    print()
    print("=" * 55)
    print("  ✅  PREDMED — Seed concluído!")
    print("=" * 55)
    print()
    print("  Usuários de demo:")
    print("  ┌────────────────────────────────────────────────────┐")
    print("  │  SESA        sesa@predmed.com       / predmed123   │")
    print("  │  SMS Sobral  sms@predmed.com        / predmed123   │")
    print("  │  Hosp.Pub.   hgf@predmed.com        / predmed123   │")
    print("  │  Particular  particular@predmed.com / predmed123   │")
    print("  └────────────────────────────────────────────────────┘")
    print()
    print("  ▶  Para colocar seus CSVs reais:")
    print("     backend/data/tabnet_internacoes_ceara_datasus.csv")
    print("     backend/data/consulta-fila-espera_YYYY-MM-DD.csv")
    print()

    db.close()


if __name__ == "__main__":
    seed()
