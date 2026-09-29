"""Cenários da meta de −40% (simulado) — regras e limites. Dados 100% sintéticos.

Garantias testadas (docs/dados/meta-40-caminho.md):
- redução entre 0 e 100% e igual a atendimentos adicionais ÷ estoque;
- priorização não altera a espera média;
- saneamento é só contagem (não entra na redução);
- destinos só contam se compatíveis e na região do cenário;
- a saída agregada não carrega idades individuais nem chaves.
"""
from datetime import date

from services import cenarios_meta40 as cm
from tests.test_redistribuicao import _cenario

REF = date(2026, 9, 28)


def _regs(cnes, esp, n, dias_atras, swalis="Categoria D", jud=False, onco=False, conf=True, chave=None):
    d = date.fromordinal(REF.toordinal() - dias_atras).isoformat()
    return [(cnes, esp, d, swalis, jud, onco, conf, chave) for _ in range(n)]


def test_reducao_limites():
    assert cm.reducao(0, 50, 3) == 0.0
    assert cm.reducao(100, 0, 3) == 0.0
    assert cm.reducao(300, 40, 3) == 0.4
    assert cm.reducao(100, 1000, 3) == 1.0
    assert cm.reducao(100, -5, 3) == 0.0


def test_estatisticas_contam_entradas_saneamento_e_duplicidade():
    regs = (_regs("O", "ORTOPEDIA", 20, 5) + _regs("O", "ORTOPEDIA", 80, 400)
            + _regs("O", "ORTOPEDIA", 10, 900, conf=False) + _regs("O", "ORTOPEDIA", 3, 100, chave="k1"))
    est = cm.estatisticas_fila(regs, REF)
    e = est[("O", "ORTOPEDIA")]
    assert e.L == 113
    assert e.n_recentes == 20
    assert e.n_legado == 10
    assert e.n_antigos == 10
    assert e.n_dup_extra == 2
    r = e.resumo(cm.PARAMS)
    assert r["fila"] == 113 and r["entradas_mes_est"] > 0
    # só agregados: nenhuma lista de idades ou chave no resumo
    assert all(not isinstance(v, (list, dict)) for v in r.values())


def test_priorizacao_nao_muda_media():
    ef = cm.efeito_priorizacao(L=1000, lam=100, L_prio=200, lam_prio=20, p=cm.PARAMS)
    assert ef["reducao_media_geral_pct"] == 0.0
    assert 0 <= ef["reducao_prioritarios_pct"] <= 100
    assert ef["aumento_estoque_nao_prioritarios"] >= 0


def test_capacidade_destinos_respeita_regiao_e_compatibilidade():
    hosp = _cenario()
    por = {h["cnes"]: h for h in hosp}
    mesma_cir = [h for h in hosp if h["cir"] == "CIR A"]
    cap_cir = cm.capacidade_destinos(por["O"], "ORTOPEDIA", mesma_cir)
    cap_todos = cm.capacidade_destinos(por["O"], "ORTOPEDIA", hosp)
    assert cap_cir > 0
    assert cap_todos >= cap_cir            # estado inclui a CIR
    assert cm.capacidade_destinos(por["O"], "NEUROLOGIA", hosp) == 0   # sem produção nem habilitação


def test_cenarios_recortes_limites_e_saneamento_fora():
    hosp = _cenario()
    regs = _regs("O", "ORTOPEDIA", 60, 10) + _regs("O", "ORTOPEDIA", 540, 300) + \
        _regs("O", "ORTOPEDIA", 400, 1000, conf=False)
    est = cm.estatisticas_fila(regs, REF)
    macro = {"CIR A": "MACRO 1", "CIR B": "MACRO 1"}
    out = cm.cenarios_recortes(hosp, est, {}, macro)
    assert len(out) == 1
    r = out[0]
    assert r["natureza_dado"] == "simulado"
    for c in r["cenarios"].values():
        assert 0 <= c["reducao_pct"] <= 100
        assert c["reducao_robusta_pct"] <= c["reducao_pct"]
    # cenários acumulam alavancas (S1 ⊂ S2 ⊂ S3 ⊂ S4 ⊂ S5 ⊂ S6)
    seq = ["S1_cir", "S2_cir_proprio", "S3_cir_proprio_turno", "S4_macro", "S5_macro_privado", "S6_estado_privado"]
    vals = [r["cenarios"][c]["extra_mes"] for c in seq]
    assert vals == sorted(vals)
    # saneamento só é contado, não reduz: a redução usa o estoque inteiro como denominador
    assert r["saneamento_legado"] == 400
    extra = r["cenarios"]["S1_cir"]["extra_mes"]
    assert abs(r["cenarios"]["S1_cir"]["reducao_pct"] - round(100 * min(1, extra * 3 / 1000), 1)) < 0.11
    # macro inclui a CIR B (X tem folga): b_macro ≥ 0
    assert r["alavancas_mes"]["b_macro"] >= 0


def test_cenarios_cir():
    hosp = _cenario()
    est = cm.estatisticas_fila(_regs("O", "ORTOPEDIA", 1000, 200), REF)
    out = cm.cenarios_cir(hosp, est, {}, {"CIR A": "M", "CIR B": "M"})
    assert out and out[0]["cir"] == "CIR A"
    for c in out[0]["cenarios"].values():
        assert 0 <= c["reducao_pct"] <= 100


# ─── Endpoint /meta40/cenarios (acesso e escopo) ──────────────
import json  # noqa: E402

import pytest  # noqa: E402

from tests.conftest import criar_usuario, token  # noqa: E402


@pytest.fixture()
def arquivo_cenarios(tmp_path, monkeypatch):
    from routers import meta40
    dados = {
        "versao": cm.VERSAO, "gerado_em": "2026-09-29T10:00:00", "data_referencia": "2026-09-28",
        "natureza": "simulado", "metodologia": {}, "fontes": {}, "estadual": {"fila": 30},
        "mapa": {}, "sistema_simultaneo": {},
        "recortes": [{"cir": "CIR Sobral", "especialidade": "ORTOPEDIA", "fila": 10},
                     {"cir": "CIR Fortaleza", "especialidade": "ORTOPEDIA", "fila": 20}],
        "cir_especialidade": [{"cir": "CIR Sobral", "especialidade": "ORTOPEDIA", "fila": 10},
                              {"cir": "CIR Fortaleza", "especialidade": "ORTOPEDIA", "fila": 20}],
        "candidatos_piloto": [{"cir": "CIR Fortaleza", "especialidade": "ORTOPEDIA", "fila": 20}],
    }
    (tmp_path / "cenarios_20260929.json").write_text(json.dumps(dados))
    monkeypatch.setattr(meta40, "DIR", tmp_path)
    meta40._CACHE.clear()
    return tmp_path


@pytest.fixture()
def usuarios_meta40(db):
    criar_usuario(db, "sesa@t.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    criar_usuario(db, "sms@t.local", "sms",
                  dict(nome="SMS Teste", tipo="SMS", cir="CIR Sobral", cnpj="00.000.000/0001-05"))
    criar_usuario(db, "alfa@t.local", "hospital_publico",
                  dict(nome="HALFA Hospital", tipo="hospital_publico", cir="CIR Fortaleza",
                       cnpj="00.000.000/0001-02"))


def test_endpoint_acesso_e_escopo(client, usuarios_meta40, arquivo_cenarios):
    r = client.get("/meta40/cenarios", headers=token(client, "alfa@t.local"))
    assert r.status_code == 403
    r = client.get("/meta40/cenarios", headers=token(client, "sesa@t.local"))
    assert r.status_code == 200
    d = r.json()
    assert d["natureza"] == "simulado" and len(d["recortes"]) == 2 and d["escopo"] == "estado"
    # SMS só vê a própria CIR, mesmo pedindo outra
    r = client.get("/meta40/cenarios", params={"cir": "CIR Fortaleza"}, headers=token(client, "sms@t.local"))
    d = r.json()
    assert r.status_code == 200 and d["escopo"] == "cir"
    assert {x["cir"] for x in d["recortes"]} == {"CIR Sobral"}
    assert d["candidatos_piloto"] == []
