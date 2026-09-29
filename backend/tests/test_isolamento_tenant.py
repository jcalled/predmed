"""
Isolamento entre instituições (antecipação de B23 / T07). Dados 100% sintéticos.

Referência: README, tabela "Multi-tenant — Quem vê o quê" (regras decididas em 28/09/2026).
- SESA e SMS: veem o estado inteiro.
- hospital_publico: fila detalhada só do próprio hospital; priorização e
  judicializados de todas as instituições, sem iniciais de outros hospitais.
- hospital_particular: linhas só do próprio hospital; do resto, apenas agregados.
"""
import pytest

from database import PacienteFila
from tests.conftest import criar_usuario, token

H_ALFA = "HALFA HOSPITAL SINTETICO ALFA"
H_BETA = "HOSPITAL SINTETICO BETA"


@pytest.fixture()
def cenario(db):
    """Dois hospitais, pacientes sintéticos, um usuário por perfil."""
    pacientes = [
        # hospital, município, SWALIS, judicializado
        (H_ALFA, "FORTALEZA", "Categoria A1", True),
        (H_ALFA, "FORTALEZA", "Categoria B", False),
        (H_BETA, "SOBRAL", "Categoria A1", True),
        (H_BETA, "SOBRAL", "Categoria A2", True),
        (H_BETA, "SOBRAL", "Categoria C", False),
    ]
    for i, (h, m, sw, jud) in enumerate(pacientes):
        db.add(PacienteFila(iniciais=f"X{i}", hospital_nome=h, municipio=m,
                            especialidade="ORTOPEDIA", classif_swalis=sw, judicializado=jud))
    criar_usuario(db, "sesa@t.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    criar_usuario(db, "alfa@t.local", "hospital_publico",
                  dict(nome="HALFA Hospital Sintético Alfa", tipo="hospital_publico",
                       cir="CIR Fortaleza", cnpj="00.000.000/0001-02"))
    criar_usuario(db, "generico@t.local", "hospital_publico",
                  dict(nome="Hospital Genérico", tipo="hospital_publico",
                       cir="CIR Fortaleza", cnpj="00.000.000/0001-03"))
    criar_usuario(db, "part@t.local", "hospital_particular",
                  dict(nome="Clínica Particular Teste", tipo="hospital_particular",
                       cir="CIR Fortaleza", cnpj="00.000.000/0001-04"))
    criar_usuario(db, "sms@t.local", "sms",
                  dict(nome="SMS Teste Sobral", tipo="SMS", cir="CIR Sobral",
                       municipio_gestor="SOBRAL", cnpj="00.000.000/0001-05"))
    db.commit()


def _hospitais(lista):
    return {p["hospital_nome"] for p in lista}


# ── SESA ─────────────────────────────────────────────────────
def test_sesa_ve_tudo(client, cenario):
    h = token(client, "sesa@t.local")
    fila = client.get("/fila", headers=h).json()
    assert fila["total"] == 5 and fila["stats"]["a1"] == 2
    assert _hospitais(client.get("/judicializados", headers=h).json()["pacientes"]) == {H_ALFA, H_BETA}


# ── Hospital público ─────────────────────────────────────────
def test_publico_fila_so_do_proprio_hospital(client, cenario):
    fila = client.get("/fila", headers=token(client, "alfa@t.local")).json()
    assert fila["total"] == 2
    assert _hospitais(fila["pacientes"]) == {H_ALFA}


def test_publico_estatisticas_da_fila_respeitam_escopo(client, cenario):
    stats = client.get("/fila", headers=token(client, "alfa@t.local")).json()["stats"]
    assert stats["a1"] == 1
    assert stats["judicializados"] == 1
    assert sum(e["total"] for e in stats["especialidades"]) == 2


def test_publico_filtro_de_hospital_nao_fura_escopo(client, cenario):
    fila = client.get("/fila", params={"hospital": "BETA"}, headers=token(client, "alfa@t.local")).json()
    assert fila["total"] == 0


def test_publico_ve_priorizacao_e_judicializados_de_todos_sem_iniciais_alheias(client, cenario):
    h = token(client, "alfa@t.local")
    prio = client.get("/priorizacao", headers=h).json()
    assert _hospitais(prio["top_prioritarios"]) == {H_ALFA, H_BETA}
    assert sum(prio["distribuicao_swalis"].values()) == 5
    jud = client.get("/judicializados", headers=h).json()
    assert jud["total"] == 3 and _hospitais(jud["pacientes"]) == {H_ALFA, H_BETA}
    for lista in (prio["top_prioritarios"], jud["pacientes"]):
        for p in lista:
            if p["hospital_nome"] == H_ALFA:
                assert p["iniciais"] is not None
            else:
                assert p["iniciais"] is None


def test_publico_com_nome_generico_falha_fechado(client, cenario):
    """'Hospital Genérico' → 1º termo 'HOSPITAL' casaria com todos: fila vazia e nenhuma inicial."""
    h = token(client, "generico@t.local")
    assert client.get("/fila", headers=h).json()["total"] == 0
    jud = client.get("/judicializados", headers=h).json()["pacientes"]
    prio = client.get("/priorizacao", headers=h).json()["top_prioritarios"]
    assert all(p["iniciais"] is None for p in jud + prio)


# ── Hospital particular: só agregados de outras instituições ─
def test_particular_sem_linhas_de_outros_hospitais(client, cenario):
    h = token(client, "part@t.local")
    fila = client.get("/fila", headers=h).json()
    assert fila["pacientes"] == []
    assert fila["stats"]["total_escopo_agregado"] == 5 and fila["stats"]["a1"] == 2
    prio = client.get("/priorizacao", headers=h).json()
    assert prio["top_prioritarios"] == [] and sum(prio["distribuicao_swalis"].values()) == 5
    jud = client.get("/judicializados", headers=h).json()
    assert jud["pacientes"] == [] and jud["total"] == 3


# ── SMS: estado inteiro ─────────────────────────────────────
def test_sms_ve_estado_inteiro(client, cenario):
    h = token(client, "sms@t.local")
    fila = client.get("/fila", headers=h).json()
    assert fila["total"] == 5
    assert {p["municipio"] for p in fila["pacientes"]} == {"FORTALEZA", "SOBRAL"}
    assert all(p["iniciais"] for p in fila["pacientes"])


# ── Dashboard (README: "Ceará todo" para todos) ─────────────
def test_dashboard_agregado_igual_para_todos(client, cenario):
    totais = {e: client.get("/dashboard", headers=token(client, e)).json()["total_fila"]
              for e in ["sesa@t.local", "alfa@t.local", "part@t.local", "sms@t.local"]}
    assert set(totais.values()) == {5}


# ── RBAC de escrita ──────────────────────────────────────────
@pytest.mark.parametrize("email", ["alfa@t.local", "part@t.local"])
def test_hospitais_nao_aprovam_redistribuicao(client, cenario, email):
    r = client.post("/redistribuicao/aprovar", headers=token(client, email), json={
        "hospital_origem": H_BETA, "hospital_destino": H_ALFA,
        "especialidade": "ORTOPEDIA", "qtd_pacientes": 1})
    assert r.status_code == 403


def _mapear_cir(db):
    from database import HospitalCirMap
    for h, cir in [(H_ALFA, "CIR Fortaleza"), (H_BETA, "CIR Sobral"), ("HOSPITAL GAMA SOBRAL", "CIR Sobral")]:
        db.add(HospitalCirMap(hospital_nome=h, municipio="X", cir=cir, confianca=1.0))
    db.commit()


def test_sms_aprova_dentro_da_propria_cir(client, cenario, db):
    _mapear_cir(db)
    r = client.post("/redistribuicao/aprovar", headers=token(client, "sms@t.local"), json={
        "hospital_origem": H_BETA, "hospital_destino": "HOSPITAL GAMA SOBRAL",
        "especialidade": "ORTOPEDIA", "qtd_pacientes": 1})
    assert r.status_code == 200, r.text


def test_sms_nao_aprova_fora_da_propria_cir(client, cenario, db):
    _mapear_cir(db)
    r = client.post("/redistribuicao/aprovar", headers=token(client, "sms@t.local"), json={
        "hospital_origem": H_BETA, "hospital_destino": H_ALFA,
        "especialidade": "ORTOPEDIA", "qtd_pacientes": 1})
    assert r.status_code == 403


def test_sesa_aprova_em_todo_o_estado(client, cenario, db):
    _mapear_cir(db)
    r = client.post("/redistribuicao/aprovar", headers=token(client, "sesa@t.local"), json={
        "hospital_origem": H_BETA, "hospital_destino": H_ALFA,
        "especialidade": "ORTOPEDIA", "qtd_pacientes": 1})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("email", ["alfa@t.local", "part@t.local", "sms@t.local"])
def test_somente_sesa_importa(client, cenario, email):
    r = client.post("/admin/import/integrasus", headers=token(client, email),
                    files={"file": ("x.csv", b"UNIDADE;ESPECIALIDADE\nA;B\n", "text/csv")})
    assert r.status_code == 403


def test_sem_token_negado(client, cenario):
    assert client.get("/fila").status_code in (401, 403)
