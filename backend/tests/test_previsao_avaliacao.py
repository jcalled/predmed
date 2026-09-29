"""Avaliação fora da amostra da previsão de demanda. Séries 100% sintéticas."""
import numpy as np
import pandas as pd

from services import previsao_avaliacao as pa


def _serie(inicio="2019-01", fim="2026-06", nivel=1000.0):
    idx = [str(p) for p in pd.period_range(inicio, fim, freq="M")]
    meses = np.array([int(i[-2:]) for i in idx])
    return pd.Series(nivel + 100 * np.sin(2 * np.pi * meses / 12), index=idx)


def test_metricas_mape_smape_mae_e_zeros():
    m = pa.metricas([100, 200, 0], [110, 180, 5])
    assert m["mape"] == 10.0  # (10% + 10%) / 2; o zero fica fora do MAPE
    assert m["n_real_zero"] == 1 and m["n"] == 3
    assert m["mae"] == round((10 + 20 + 5) / 3, 1)
    assert m["smape"] > 0


def test_sazonal_ingenuo_perfeito_em_serie_sazonal_pura():
    y = _serie()
    bt = pa.backtest_origem_movel(y, ["2025-06", "2025-07"], ["naive_sazonal"], h_max=3)
    assert np.allclose(bt["real"], bt["previsto"])


def test_backtest_nao_usa_dados_apos_a_origem():
    y = _serie()
    vistos = []

    def espiao(treino, h):
        vistos.append(treino.index.max())
        return np.repeat(float(treino.iloc[-1]), h)

    pa.MODELOS["_espiao"] = {"fn": espiao, "descricao": "teste", "baseline": True}
    try:
        bt = pa.backtest_origem_movel(y, ["2025-06", "2025-09"], ["_espiao"], h_max=3)
    finally:
        del pa.MODELOS["_espiao"]
    assert vistos == ["2025-06", "2025-09"]
    assert (bt["alvo"] > bt["origem"]).all()


def test_imputacao_da_pandemia_nao_altera_fora_do_periodo():
    y = _serie()
    y["2020-04"] = 10.0
    yi = pa.imputar_pandemia(y)
    assert yi["2020-04"] == (y["2019-04"] + y["2022-04"]) / 2
    assert yi["2019-04"] == y["2019-04"] and yi["2022-06"] == y["2022-06"]


def test_holt_winters_e_sarima_rodam():
    y = _serie()[:"2025-06"]
    for mod in ("holt_winters_pos2022", "sarima_imputada"):
        p = pa.prever(mod, y, 3)
        assert p.shape == (3,) and (p >= 0).all()


def _avaliacao_sintetica():
    comp = [{"mes": "2099-01", "origem": "2098-12", "previsto": 110, "realizado": 100}]
    return {
        "avaliacao_id": "previsao-demanda-v1-teste", "gerado_em": "2099-01-01T00:00:00",
        "meta_mape_pct": 15, "alvo": "alvo sintético",
        "fonte": {"competencias": ["2090-01", "2099-01"], "provisorias": []},
        "desenho": {"janela_teste": ["2099-01", "2099-01"]},
        "modelos": {"naive_sazonal": {"descricao": "x", "baseline": True}},
        "series": [{
            "especialidade": "OTORRINO", "carater": "TODOS", "baixo_volume": False,
            "modelo_escolhido": "naive_sazonal",
            "teste_modelo_escolhido": {"h1": {"mape": 10.0}, "h2": {"mape": 16.0},
                                       "h3": {"mape": 20.0}, "trimestre": {"mape": 12.0}},
            "atinge_meta_15": {"h1": True, "h2": False, "h3": False, "trimestre": True},
            "comparacao_h1_teste": {"naive_sazonal": comp},
        }],
    }


def test_api_usa_avaliacao_versionada_e_mapeia_especialidade_da_fila():
    r = pa.validacao_para_api("OTORRINO MÉDIA COMPLEXIDADE", aval=_avaliacao_sintetica())
    assert r["fonte_avaliacao"] == "avaliacao_versionada"
    assert r["serie_avaliada"] == "OTORRINO"
    assert r["mape_real"] == 10.0 and r["dentro_da_meta"] is True and r["status"] == "calculado"
    assert r["mape_por_horizonte"]["h2"] == 16.0
    assert r["comparacao_mensal"][0]["erro_pct"] == 10.0
    # chaves antigas preservadas
    for k in ("meses_comparados", "meses_sem_dados_reais", "resumo", "interpretacao",
              "base_real_ultima_competencia", "periodo_validado", "meta_projeto_mape_pct"):
        assert k in r


def test_api_sem_serie_nao_inventa_numero():
    r = pa.validacao_para_api("ESPECIALIDADE INEXISTENTE", aval=_avaliacao_sintetica())
    assert r["mape_real"] is None and r["status"] == "nao_validado"


def test_endpoint_devolve_a_mesma_avaliacao_versionada(db, client, monkeypatch):
    from tests.conftest import criar_usuario, token
    monkeypatch.setattr(pa, "carregar_avaliacao_atual", lambda pasta=pa.PASTA_AVALIACOES: _avaliacao_sintetica())
    criar_usuario(db, "gestor@teste.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    r = client.get("/analytics/validacao-mape", params={"especialidade": "OTORRINO E PNEUMOLOGIA"},
                   headers=token(client, "gestor@teste.local")).json()
    assert r["avaliacao_id"] == "previsao-demanda-v1-teste" and r["mape_real"] == 10.0
