"""
Filtro "Somente judicializados" no servidor (GET /priorizacao?apenas_judicializados=true).
Dados 100% sintéticos.

- O filtro é aplicado na query, antes do score: todos os judicializados do escopo
  do perfil voltam, mesmo que tenham score menor que 200 outros pacientes.
- As regras de acesso continuam: hospital particular só vê as próprias linhas.
"""
import pytest

from database import PacienteFila
from tests.conftest import criar_usuario, token

H_ALFA = "HALFA HOSPITAL SINTETICO ALFA"
H_PART = "PARTSINT HOSPITAL PARTICULAR SINTETICO"

N_JUD_ALFA = 240   # mais que o teto antigo de 200
N_JUD_PART = 3
N_NAO_JUD = 250    # A1 com espera longa: score maior que os judicializados "D"


@pytest.fixture()
def cenario(db):
    for i in range(N_NAO_JUD):
        db.add(PacienteFila(iniciais=f"N{i}", hospital_nome=H_ALFA, municipio="FORTALEZA",
                            especialidade="ORTOPEDIA", classif_swalis="Categoria A1",
                            judicializado=False, data_insercao="2020-01-01", data_confiavel=True))
    for i in range(N_JUD_ALFA):
        db.add(PacienteFila(iniciais=f"J{i}", hospital_nome=H_ALFA, municipio="FORTALEZA",
                            especialidade="ORTOPEDIA", classif_swalis="Categoria D",
                            judicializado=True, data_insercao="2026-09-01", data_confiavel=True))
    for i in range(N_JUD_PART):
        db.add(PacienteFila(iniciais=f"P{i}", hospital_nome=H_PART, municipio="FORTALEZA",
                            especialidade="ORTOPEDIA", classif_swalis="Categoria D",
                            judicializado=True, data_insercao="2026-09-01", data_confiavel=True))
    criar_usuario(db, "sesa@t.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    criar_usuario(db, "alfa@t.local", "hospital_publico",
                  dict(nome="HALFA Hospital Sintético Alfa", tipo="hospital_publico",
                       cir="CIR Fortaleza", cnpj="00.000.000/0001-02"))
    criar_usuario(db, "part@t.local", "hospital_particular",
                  dict(nome="PARTSINT Hospital Particular", tipo="hospital_particular",
                       cir="CIR Fortaleza", cnpj="00.000.000/0001-04"))
    db.commit()


def _get(client, email, **params):
    r = client.get("/priorizacao", params=params, headers=token(client, email))
    assert r.status_code == 200, r.text
    return r.json()


def test_sem_filtro_judicializados_de_score_baixo_ficam_fora_do_top(client, cenario):
    d = _get(client, "sesa@t.local", limit=200)
    assert not any(p["judicializado"] for p in d["top_prioritarios"])


def test_judicializados_vem_completos(client, cenario):
    d = _get(client, "sesa@t.local", limit=1000, apenas_judicializados=True)
    linhas = d["top_prioritarios"]
    assert d["total_avaliados"] == N_JUD_ALFA + N_JUD_PART
    assert len(linhas) == N_JUD_ALFA + N_JUD_PART
    assert all(p["judicializado"] for p in linhas)


def test_limite_sem_filtro_continua_200(client, cenario):
    d = _get(client, "sesa@t.local", limit=1000)
    assert len(d["top_prioritarios"]) == 200


def test_publico_ve_judicializados_de_todos_sem_iniciais_alheias(client, cenario):
    linhas = _get(client, "alfa@t.local", limit=1000, apenas_judicializados=True)["top_prioritarios"]
    assert len(linhas) == N_JUD_ALFA + N_JUD_PART
    for p in linhas:
        if p["hospital_nome"] == H_PART:
            assert p["iniciais"] is None
        else:
            assert p["iniciais"]


def test_particular_continua_sem_linhas_alheias(client, cenario):
    d = _get(client, "part@t.local", limit=1000, apenas_judicializados=True)
    linhas = d["top_prioritarios"]
    assert d["total_avaliados"] == N_JUD_PART
    assert {p["hospital_nome"] for p in linhas} == {H_PART}
    assert all(p["iniciais"] for p in linhas)
