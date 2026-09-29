"""Importação da coleta JSON do IntegraSUS (painel 214). Dados 100% sintéticos."""
import json

from database import PacienteFila
from services.data_import import import_integrasus


def _registro(i, **extra):
    base = {
        "municipio": "FORTALEZA", "estabelecimento": "HOSPITAL SINTETICO",
        "procedimento": "PROCEDIMENTO X", "especialidade": "Ortopedia",
        "descSwalis": "Categoria B", "mandadoJudicial": "Não", "posicao": i,
        "nome": "ZZZ", "codSolicitacao": 9000000 + i,
        "data": "2025-12-03T10:21:00.000+0000",
    }
    base.update(extra)
    return base


def test_coleta_json_preenche_data_posicao_e_pseudonimiza(db, tmp_path, monkeypatch):
    monkeypatch.setenv("PREDMED_PSEUDO_KEY", "chave-de-teste")
    arq = tmp_path / "fila_20260928T070000.json"
    arq.write_text(json.dumps([
        _registro(1),
        _registro(2, descSwalis=None, mandadoJudicial="Sim"),
    ]))

    assert import_integrasus(str(arq), db) == 2

    pacientes = db.query(PacienteFila).order_by(PacienteFila.posicao_fila).all()
    assert [p.data_insercao for p in pacientes] == ["2025-12-03", "2025-12-03"]
    assert [p.posicao_fila for p in pacientes] == [1, 2]
    assert pacientes[0].data_atualizacao == "2026-09-28"
    # SWALIS ausente não vira "Categoria D"
    assert pacientes[1].classif_swalis == "Não Informada"
    assert pacientes[1].judicializado is True
    # nº de solicitação nunca é gravado em claro
    for p in pacientes:
        assert p.solicitacao_hash and len(p.solicitacao_hash) == 64
        assert "900000" not in p.solicitacao_hash
    assert pacientes[0].solicitacao_hash != pacientes[1].solicitacao_hash
    # numeração atual (7 dígitos) → data confiável
    assert all(p.data_confiavel is True for p in pacientes)


def test_numeracao_legada_marca_data_a_confirmar(db, tmp_path, monkeypatch):
    monkeypatch.setenv("PREDMED_PSEUDO_KEY", "chave-de-teste")
    arq = tmp_path / "fila_20260928T070000.json"
    arq.write_text(json.dumps([_registro(1, codSolicitacao=12345, data="2008-05-02T00:00:00.000+0000")]))
    import_integrasus(str(arq), db)
    p = db.query(PacienteFila).one()
    assert p.data_confiavel is False and p.data_insercao == "2008-05-02"
