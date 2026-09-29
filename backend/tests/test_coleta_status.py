"""
GET /coleta/status — lê só agregados dos manifestos (sintéticos, em tmp_path).
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import criar_usuario, token

AGORA = datetime.now(timezone.utc)


def _escrever(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        for l in linhas:
            f.write((l if isinstance(l, str) else json.dumps(l)) + "\n")


def _linha_fila(horas_atras, total, entradas=None, saidas=None):
    d = {
        "coletado_em": (AGORA - timedelta(hours=horas_atras)).astimezone(
            timezone(timedelta(hours=-3))).isoformat(timespec="seconds"),
        "sha256_bruto": "a" * 64, "total": total, "data_max": "2026-09-28",
        "judicializados": 7, "especialidades": 3, "estabelecimentos": 5,
        "por_swalis": {"Categoria A1": 1},
        "arquivo": "2026/09/fila_SINTETICO.json.xz.enc",
        # campo inesperado que nunca deve sair na resposta
        "paciente_exemplo": "ZZ 123456",
    }
    if entradas is not None:
        d["entradas"], d["saidas"] = entradas, saidas
    return d


@pytest.fixture()
def dados(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDMED_DADOS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def usuarios(db):
    criar_usuario(db, "sesa@t.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    criar_usuario(db, "sms@t.local", "sms",
                  dict(nome="SMS Teste", tipo="SMS", cir="CIR Sobral", cnpj="00.000.000/0001-05"))
    criar_usuario(db, "alfa@t.local", "hospital_publico",
                  dict(nome="HALFA Hospital", tipo="hospital_publico", cir="CIR Fortaleza",
                       cnpj="00.000.000/0001-02"))
    criar_usuario(db, "part@t.local", "hospital_particular",
                  dict(nome="PARTSINT Hospital", tipo="hospital_particular", cir="CIR Fortaleza",
                       cnpj="00.000.000/0001-04"))


def _status(client, email="sesa@t.local", **params):
    r = client.get("/coleta/status", params=params, headers=token(client, email))
    assert r.status_code == 200, r.text
    return r.json()


def test_ultima_coleta_e_historico(client, usuarios, dados):
    _escrever(dados / "integrasus" / "fila" / "manifesto.jsonl", [
        _linha_fila(24, 100),
        "{linha corrompida",
        _linha_fila(12, 105, 10, 5),
        _linha_fila(2, 110, 8, 3),
    ])
    _escrever(dados / "datasus" / "manifesto.jsonl", [
        {"registrado_em": "2026-09-01T05:00:00+00:00", "fonte": "SIH-RD", "arquivo": "RDCE2606.dbc",
         "competencia": "2026-06", "acao": "baixado", "registros": 50, "sha256": "b" * 64},
        {"registrado_em": "2026-09-02T05:00:00+00:00", "fonte": "SIH-RD", "arquivo": "RDCE2607.dbc",
         "competencia": "2026-07", "acao": "baixado", "registros": 60, "sha256": "c" * 64},
        {"registrado_em": "2026-09-01T06:00:00+00:00", "fonte": "CNES-LT", "arquivo": "LTCE2608.dbc",
         "competencia": "2026-08", "acao": "validado_existente", "registros": 9},
    ])
    d = _status(client, n=2)
    fila = d["fila"]
    assert fila["atrasada"] is False
    assert fila["total_coletas"] == 3
    assert fila["ultima"]["total"] == 110
    assert fila["ultima"]["entradas"] == 8 and fila["ultima"]["saidas"] == 3
    assert fila["ultima"]["data_max"] == "2026-09-28"
    assert [c["total"] for c in fila["ultimas"]] == [110, 105]
    assert fila["ultimas"][1]["entradas"] == 10
    assert 1.5 < fila["horas_desde_ultima"] < 2.5

    ds = d["datasus"]
    assert ds["total_registros"] == 3
    fontes = {f["fonte"]: f for f in ds["por_fonte"]}
    assert fontes["SIH-RD"]["competencia"] == "2026-07"
    assert fontes["CNES-LT"]["acao"] == "validado_existente"

    # Nada de arquivo, hash, caminho ou dado de paciente na resposta
    texto = json.dumps(d)
    for proibido in ("arquivo", ".dbc", ".enc", "sha256", str(dados), "ZZ 123456", "paciente"):
        assert proibido not in texto


def test_atrasada_quando_ultima_coleta_tem_mais_de_14h(client, usuarios, dados):
    _escrever(dados / "integrasus" / "fila" / "manifesto.jsonl", [_linha_fila(15, 100)])
    fila = _status(client, "sms@t.local")["fila"]
    assert fila["atrasada"] is True
    assert fila["horas_desde_ultima"] > 14


def test_sem_manifestos_conta_como_atrasada(client, usuarios, dados):
    d = _status(client)
    assert d["fila"]["atrasada"] is True
    assert d["fila"]["ultima"] is None and d["fila"]["ultimas"] == []
    assert d["datasus"]["por_fonte"] == []


@pytest.mark.parametrize("email", ["alfa@t.local", "part@t.local"])
def test_hospitais_nao_acessam(client, usuarios, dados, email):
    r = client.get("/coleta/status", headers=token(client, email))
    assert r.status_code == 403


def test_sem_token_negado(client, usuarios, dados):
    assert client.get("/coleta/status").status_code in (401, 403)
