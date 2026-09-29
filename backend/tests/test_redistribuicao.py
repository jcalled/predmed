"""Redistribuição v1 e simulação de mutirão — regras e limites. Dados 100% sintéticos.

Regras testadas (docs/dados/redistribuicao-v1.md):
- só dentro da mesma CIR;
- destino compatível (produção SIH na especialidade, habilitação para onco/cardio/neuro,
  fila própria baixa, centro cirúrgico e vínculo SUS);
- capacidade: soma recebida por destino ≤ ociosidade estimada; origem transfere ≤ excedente ≤ fila;
- mutirão: 0 ≤ redistribuíveis ≤ fila e 0 ≤ redução ≤ 100%.
"""
import pytest

from services import redistribuicao as rd

COMPS = [f"2024-{m:02d}" for m in range(7, 13)] + [f"2025-{m:02d}" for m in range(1, 13)] + \
        [f"2026-{m:02d}" for m in range(1, 7)]


def _est(cir, salas=4, leitos=60, hab=None, natureza="PUBLICO", centro=True, sus=True):
    d = {"cir_ads_predmed": cir, "municipio": "MUNICIPIO SINTETICO", "natureza": natureza,
         "vinculo_sus": sus, "centro_cirurgico": centro, "salas_cirurgicas": salas,
         "leitos_cirurgicos_exist": leitos, "leitos_cirurgicos_sus": leitos,
         "nome_fantasia": None}
    for h in hab or []:
        d[h] = True
    return d


def _prod(por_esp_recente, por_esp_pico=None):
    """Produção mensal: pico (3 meses no início) e depois nível recente."""
    por_esp_pico = por_esp_pico or por_esp_recente
    out = {}
    for i, c in enumerate(COMPS):
        out[c] = dict(por_esp_pico if i < 3 else por_esp_recente)
    return out


def _base(estabs, prods, filas, nomes=None, vinculo=None):
    return rd.Base(estabelecimentos=estabs, producao=prods, competencias=COMPS, fila=filas,
                   nome_fila=nomes or {c: f"HOSPITAL SINTETICO {c}" for c in estabs},
                   vinculo=vinculo or {}, competencia_cnes="2026-08")


def _cenario(**kw):
    """Origem O sobrecarregada em ORTOPEDIA; destino D (mesma CIR) com folga; X em outra CIR com folga."""
    estabs = {
        "O": _est("CIR A"),
        "D": _est("CIR A", salas=4, leitos=60),
        "X": _est("CIR B", salas=4, leitos=60),
    }
    prods = {
        "O": _prod({"ORTOPEDIA": 40}),
        # D e X: recente 100/mês, pico 160/mês → folga demonstrada 60
        "D": _prod({"ORTOPEDIA": 40, "CIR DIGESTIVA": 60}, {"ORTOPEDIA": 70, "CIR DIGESTIVA": 90}),
        "X": _prod({"ORTOPEDIA": 40, "CIR DIGESTIVA": 60}, {"ORTOPEDIA": 70, "CIR DIGESTIVA": 90}),
    }
    filas = {"O": {"ORTOPEDIA": 1000}, "D": {"ORTOPEDIA": 10}, "X": {"ORTOPEDIA": 5}}
    estabs.update(kw.get("estabs", {}))
    prods.update(kw.get("prods", {}))
    filas.update(kw.get("filas", {}))
    return rd.estimar_hospitais(_base(estabs, prods, filas, vinculo=kw.get("vinculo")))


def _por_cnes(hosps):
    return {h["cnes"]: h for h in hosps}


# ── estimativa de ociosidade ──────────────────────────────
def test_ociosidade_e_o_menor_dos_tres_limites():
    h = _por_cnes(_cenario())["D"]
    # demonstrada: 160 - 100 = 60; salas: 4 × 88 = 352 - 100; leitos: 60 × 30/3 × 0,85 = 510 - 100
    assert h["capacidade_demonstrada_mes"] == pytest.approx(160)
    assert h["ociosidade_estimada_mes"] == 60
    assert h["ociosidade_limitada_por"] == "demonstrada"


def test_sem_salas_ou_sem_vinculo_sus_nao_tem_ociosidade():
    hs = _por_cnes(_cenario(estabs={"D": _est("CIR A", salas=0), "X": _est("CIR B", sus=False)}))
    assert hs["D"]["ociosidade_estimada_mes"] == 0 and not hs["D"]["apto_receber"]
    assert hs["X"]["ociosidade_estimada_mes"] == 0


def test_queda_forte_de_producao_nao_vira_ociosidade():
    hs = _por_cnes(_cenario(prods={"D": _prod({"ORTOPEDIA": 10}, {"ORTOPEDIA": 200})}))
    assert hs["D"]["queda_producao_recente"] is True
    assert hs["D"]["ociosidade_estimada_mes"] == 0


def test_status_ocioso_exige_ociosidade_estimada():
    hs = _por_cnes(_cenario(prods={"D": _prod({"ORTOPEDIA": 100})}))  # sem pico → sem folga demonstrada
    assert hs["D"]["ociosidade_estimada_mes"] == 0
    assert hs["D"]["pressao_status"] != "ocioso"


# ── regras das sugestões ──────────────────────────────────
def test_sugestoes_so_na_mesma_cir():
    sug = rd.sugerir_redistribuicao(_cenario())
    assert sug, "deveria haver sugestão O → D"
    assert all(s["origem"]["cir"] == s["destino"]["cir"] for s in sug)
    assert {s["cnes_destino"] for s in sug} == {"D"}
    assert all(s["tipo_transferencia"] == "mesma_regiao" for s in sug)


def test_destino_sem_producao_na_especialidade_nao_recebe():
    hs = _cenario(prods={"D": _prod({"CIR DIGESTIVA": 100}, {"CIR DIGESTIVA": 160})})
    assert rd.sugerir_redistribuicao(hs) == []


def test_habilitacao_exigida_para_oncologia():
    base = dict(
        filas={"O": {"ONCOLOGIA": 500}, "D": {}},
        prods={"O": _prod({"ONCOLOGIA": 20}),
               "D": _prod({"ONCOLOGIA": 40, "CIR DIGESTIVA": 60}, {"ONCOLOGIA": 70, "CIR DIGESTIVA": 90})},
    )
    sem_hab = rd.sugerir_redistribuicao(_cenario(**base))
    assert sem_hab == []
    com_hab = rd.sugerir_redistribuicao(_cenario(estabs={"D": _est("CIR A", hab=["hab_oncologia"])}, **base))
    assert com_hab and all(s["especialidade"] == "ONCOLOGIA" for s in com_hab)


def test_destino_com_fila_propria_alta_nao_recebe():
    hs = _cenario(filas={"D": {"ORTOPEDIA": 400}})
    assert all(s["cnes_destino"] != "D" for s in rd.sugerir_redistribuicao(hs))


def test_capacidade_do_destino_e_limite_da_origem_respeitados():
    hs = _cenario(filas={"O": {"ORTOPEDIA": 1000, "CIR DIGESTIVA": 900}},
                  prods={"O": _prod({"ORTOPEDIA": 40, "CIR DIGESTIVA": 40})})
    sug = rd.sugerir_redistribuicao(hs)
    oc = _por_cnes(hs)["D"]["ociosidade_estimada_mes"]
    assert sum(s["qtd_sugerida"] for s in sug if s["cnes_destino"] == "D") <= oc
    for s in sug:
        # por especialidade: no máximo +50% da produção do destino
        assert s["qtd_sugerida"] <= 0.5 * s["producao_especialidade_destino_mes"] + 1e-9
        assert s["qtd_sugerida"] <= s["excedente_origem"] <= s["fila_especialidade_origem"]
        assert s["qtd_sugerida"] >= rd.PARAMS["qtd_minima_sugestao"]


def test_excedente_pequeno_nao_gera_sugestao():
    # fila = 1,5 mês de produção → nada acima do que a origem retém
    hs = _cenario(filas={"O": {"ORTOPEDIA": 60}})
    assert rd.sugerir_redistribuicao(hs) == []


def test_transferencias_do_mes_consomem_capacidade():
    hs = _cenario()
    nome_d = _por_cnes(hs)["D"]["hospital_nome"]
    assert rd.sugerir_redistribuicao(hs, ja_transferido={nome_d: 60}) == []


def test_vagas_declaradas_precedem_e_respeitam_limite():
    hs = _cenario()
    vagas = [{"tenant_id": 9, "hospital_nome": "PARTICULAR SINTETICO", "cir": "CIR A",
              "especialidade": "ORTOPEDIA", "disponivel": 7},
             {"tenant_id": 8, "hospital_nome": "PARTICULAR OUTRA CIR", "cir": "CIR B",
              "especialidade": "ORTOPEDIA", "disponivel": 50}]
    sug = rd.sugerir_redistribuicao(hs, vagas_declaradas=vagas)
    decl = [s for s in sug if s["capacidade_natureza"] == "declarada"]
    assert len(decl) == 1 and decl[0]["qtd_sugerida"] == 7 and decl[0]["tenant_destino_id"] == 9
    assert sug[0]["capacidade_natureza"] == "declarada"


def test_vinculo_provisorio_sinalizado():
    hs = _cenario(vinculo={"O": "PROVISORIO_BAIXA", "D": "ALTA", "X": "ALTA"})
    sug = rd.sugerir_redistribuicao(hs)
    assert sug and all(s["vinculo_provisorio"] for s in sug)
    assert _por_cnes(hs)["O"]["vinculo_provisorio"] is True


def test_especialidade_da_fila_mapeada_para_serie():
    assert rd.especialidade_serie("OTORRINO MÉDIA COMPLEXIDADE") == "OTORRINO"
    assert rd.especialidade_serie("Ortopedia") == "ORTOPEDIA"


# ── mutirão ────────────────────────────────────────────────
def _sug(origem, esp, qtd, excedente):
    return {"origem": {"hospital_nome": origem}, "especialidade": esp, "qtd_sugerida": qtd,
            "excedente_origem": excedente}


def test_mutirao_redistribuiveis_nunca_excedem_fila():
    # sugestões infladas: 500/mês com excedente 10.000 numa fila de 100
    cen = rd.plano_mutirao({"ORTOPEDIA": 100, "UROLOGIA": 50},
                           [_sug("H1", "ORTOPEDIA", 500, 10000), _sug("H2", "UROLOGIA", 1, 5)],
                           horizonte_meses=6)
    for p in cen["plano"]:
        assert 0 <= p["pacientes_redistribuiveis"] <= p["fila_atual"]
        assert 0 <= p["reducao_pct"] <= 100
        assert p["fila_com_redistribuicao"] == p["fila_atual"] - p["pacientes_redistribuiveis"] >= 0
    assert cen["total_pacientes_redistribuiveis"] <= cen["fila_total_atual"]
    assert 0 <= cen["reducao_total_pct"] <= 100


def test_mutirao_limitado_ao_excedente_da_origem():
    cen = rd.plano_mutirao({"ORTOPEDIA": 1000}, [_sug("H1", "ORTOPEDIA", 40, 70)], horizonte_meses=3)
    assert cen["total_pacientes_redistribuiveis"] == 70   # 40 × 3 = 120, mas excedente = 70


def test_mutirao_fila_vazia_e_sem_sugestoes():
    cen = rd.plano_mutirao({"ORTOPEDIA": 0}, [_sug("H1", "ORTOPEDIA", 10, 10)])
    assert cen["reducao_total_pct"] == 0.0 and cen["total_pacientes_redistribuiveis"] == 0
    assert rd.plano_mutirao({}, [])["reducao_total_pct"] == 0.0


def test_endpoint_zerarfilas_limites_e_rotulo(db, client):
    from database import PacienteFila
    from tests.conftest import criar_usuario, token
    criar_usuario(db, "sesa@z.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-09"))
    for i in range(20):
        db.add(PacienteFila(hospital_nome="HOSPITAL SINTETICO", municipio="FORTALEZA",
                            especialidade="ORTOPEDIA", classif_swalis="Categoria B"))
    db.commit()
    z = client.get("/zerarfilas", headers=token(client, "sesa@z.local")).json()
    r = z["resumo"]
    assert z["natureza"] == "simulado" and z["origem"] == "simulado"
    assert r["fila_total_atual"] == 20
    assert 0 <= r["total_pacientes_redistribuiveis"] <= r["fila_total_atual"]
    assert 0 <= r["reducao_total_pct"] <= 100
    red = client.get("/redistribuicao", headers=token(client, "sesa@z.local")).json()
    assert red["natureza"] == "estimado" and red["regra_regional"] == "mesma_cir"
    assert red["metodologia"]["hipoteses"]


# ── previsão da produção (tela Previsão) ─────────────────
def test_previsao_producao_api_com_json_sintetico():
    from services.previsao_producao import previsao_producao_para_api, resumo_producao_para_api
    pontos = [{"horizonte": f"h{k}", "horizonte_dias": 30 * k, "competencia": f"2026-0{6 + k}",
               "previsto": 100, "intervalo_80_inferior": 90, "intervalo_80_superior": 115,
               "mape_teste_pct": 5.0 + k, "n_erros_intervalo": 12, "mape_recalculado_pct": 5.0 + k}
              for k in (1, 2, 3)]
    prev = {"previsao_id": "p-sint", "avaliacao_id": "a-sint", "gerado_em": "2026-09-29T00:00:00",
            "alvo": "producao sintetica", "ultima_competencia_observada": "2026-06",
            "competencias_provisorias": ["2026-05", "2026-06"], "intervalo": "x", "horizonte": "y",
            "series": [{"especialidade": "OTORRINO", "carater": "TODOS", "modelo": "naive_ultimo",
                        "previsao": pontos, "historico_24m": [{"competencia": "2026-06", "aihs": 100}],
                        "atinge_meta_15": {"h1": True}, "baixo_volume": False}]}
    r = previsao_producao_para_api("OTORRINO MÉDIA COMPLEXIDADE", "TODOS", prev=prev)
    assert r["status"] == "ok" and r["natureza"] == "estimado" and r["avaliacao_id"] == "a-sint"
    assert r["mape_por_horizonte"] == {"h1": 6.0, "h2": 7.0, "h3": 8.0}
    assert all(p["intervalo_80_inferior"] <= p["previsto"] <= p["intervalo_80_superior"] for p in r["previsao"])
    assert "Não é a fila" in r["alvo_resumo"]
    assert previsao_producao_para_api("INEXISTENTE", prev=prev)["status"] == "sem_serie"
    assert resumo_producao_para_api(prev=prev)["por_especialidade"][0]["especialidade"] == "OTORRINO"
