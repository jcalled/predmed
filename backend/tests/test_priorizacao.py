"""Regras de priorização v0.1 (services/priorizacao.py). Cenários sintéticos."""
from datetime import date, timedelta

from services.priorizacao import calcular_score

HOJE = date(2026, 9, 28)


def _score(**kw):
    base = dict(classif_swalis="Categoria B", data_insercao=None, data_confiavel=True,
                judicializado=False, especialidade="ORTOPEDIA", procedimento="X", hoje=HOJE)
    base.update(kw)
    return calcular_score(**base)


def _dias_atras(n):
    return (HOJE - timedelta(days=n)).isoformat()


def test_swalis_ordena_categorias():
    pts = [_score(classif_swalis=c, data_insercao=_dias_atras(0)).score
           for c in ["Categoria A1", "Categoria A2", "Categoria B", "Categoria C", "Categoria D"]]
    assert pts == sorted(pts, reverse=True) and pts[0] == 40 and pts[-1] == 4


def test_espera_cresce_e_satura_em_dois_anos():
    s0 = _score(data_insercao=_dias_atras(0)).score
    s1 = _score(data_insercao=_dias_atras(365)).score
    s2 = _score(data_insercao=_dias_atras(730)).score
    s3 = _score(data_insercao=_dias_atras(3000)).score
    assert s0 < s1 < s2 == s3
    assert s2 - s0 == 30


def test_judicial_oncologia_e_cardio_somam_pontos():
    base = _score(data_insercao=_dias_atras(0)).score
    assert _score(data_insercao=_dias_atras(0), judicializado=True).score == base + 15
    assert _score(data_insercao=_dias_atras(0), especialidade="ONCOLOGIA").score == base + 10
    assert _score(data_insercao=_dias_atras(0), procedimento="RESSECCAO DE TUMOR MALIGNO").score == base + 10
    a1 = _score(classif_swalis="Categoria A1", data_insercao=_dias_atras(0)).score
    assert _score(classif_swalis="Categoria A1", data_insercao=_dias_atras(0),
                  especialidade="CARDIOVASCULAR").score == a1 + 5
    # cardiovascular sem gravidade não soma
    assert _score(data_insercao=_dias_atras(0), especialidade="CARDIOVASCULAR").score == base


def test_score_limitado_a_100():
    r = _score(classif_swalis="Categoria A1", data_insercao=_dias_atras(5000), judicializado=True,
               especialidade="ONCOLOGIA")
    assert r.score == 95  # 40 + 30 + 15 + 10
    assert _score(classif_swalis="Categoria A1", data_insercao=_dias_atras(5000), judicializado=True,
                  especialidade="CARDIOVASCULAR", procedimento="MALIGNO").score == 100


def test_alertas_explicam_dados_faltantes_e_prazos():
    r = _score(classif_swalis=None, data_insercao=None)
    assert "Classificação SWALIS não informada" in r.alertas
    assert "Sem data de solicitação" in r.alertas
    r = _score(data_insercao=_dias_atras(90), data_confiavel=False, especialidade="ONCOLOGIA")
    assert any("a confirmar" in a for a in r.alertas)
    assert any("Oncologia com mais de 60 dias" in a for a in r.alertas)
    assert not any("Oncologia" in a for a in _score(data_insercao=_dias_atras(30),
                                                     especialidade="ONCOLOGIA").alertas)


def test_componentes_somam_o_score():
    r = _score(classif_swalis="Categoria A2", data_insercao=_dias_atras(200), judicializado=True)
    assert sum(c["pontos"] for c in r.componentes) == r.score
