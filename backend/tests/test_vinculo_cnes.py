"""Vínculo nome da fila → CNES e capacidade CNES. Dados 100% sintéticos."""
import csv
import json

from database import CnesCapacidade, Hospital, HospitalAlias, PacienteFila
from services import cnes_vinculo as cv
from services.data_import import import_integrasus


def _linha(nome, conf, cnes, nome_cnes="HOSPITAL SINTETICO CNES", metodo="nome+residencia"):
    return {"competencia_cnes": "2099-01", "nome_fila": nome, "registros_fila": "1",
            "confianca": conf, "metodo": metodo, "cnes": cnes, "nome_cnes": nome_cnes}


def _fila(db, nome, n=2):
    for _ in range(n):
        db.add(PacienteFila(hospital_nome=nome, municipio="MUNICIPIO X",
                            especialidade="ORTOPEDIA", classif_swalis="Categoria B"))
    db.commit()


def test_alta_grava_alias_e_fila_e_e_idempotente(db):
    _fila(db, "HOSPITAL SINTETICO A")
    linhas = [_linha("HOSPITAL SINTETICO A", "ALTA", "9990001")]
    st1 = cv.aplicar_vinculo_cnes(db, linhas)
    assert st1["inseridos"] == 1 and st1["registros_fila_com_cnes"] == 2
    a = db.query(HospitalAlias).filter_by(alias_nome="HOSPITAL SINTETICO A").one()
    assert (a.cnes, a.fonte, a.confianca) == ("9990001", cv.FONTE_VINCULO, "ALTA")
    assert {p.cnes for p in db.query(PacienteFila)} == {"9990001"}
    assert {p.cnes_confianca for p in db.query(PacienteFila)} == {"ALTA"}
    h = db.query(Hospital).filter_by(cnes="9990001").one()
    assert {p.hospital_id for p in db.query(PacienteFila)} == {h.id}

    st2 = cv.aplicar_vinculo_cnes(db, linhas)
    assert st2["inalterados"] == 1 and st2["inseridos"] == 0 and st2["atualizados"] == 0
    assert db.query(HospitalAlias).count() == 1
    assert db.query(Hospital).filter_by(cnes="9990001").count() == 1


def test_nao_sobrescreve_vinculo_manual(db):
    _fila(db, "HOSPITAL SINTETICO B")
    db.add(HospitalAlias(alias_nome="HOSPITAL SINTETICO B", cnes="9990099", fonte="manual"))
    db.commit()
    st = cv.aplicar_vinculo_cnes(db, [_linha("HOSPITAL SINTETICO B", "ALTA", "9990002")])
    assert st["manuais_preservados"] == 1
    a = db.query(HospitalAlias).filter_by(alias_nome="HOSPITAL SINTETICO B").one()
    assert a.cnes == "9990099" and a.fonte == "manual"
    assert {(p.cnes, p.cnes_confianca) for p in db.query(PacienteFila)} == {("9990099", "MANUAL")}


def test_corrige_alias_automatico_errado(db):
    _fila(db, "HOSPITAL SINTETICO C")
    db.add(HospitalAlias(alias_nome="HOSPITAL SINTETICO C", cnes="9990100", fonte="integrasus_auto"))
    db.commit()
    st = cv.aplicar_vinculo_cnes(db, [_linha("HOSPITAL SINTETICO C", "ALTA", "9990003")])
    assert st["atualizados"] == 1
    assert db.query(HospitalAlias).filter_by(alias_nome="HOSPITAL SINTETICO C").one().cnes == "9990003"


def test_provisorio_marcado_e_somente_alta(db):
    _fila(db, "HOSPITAL SINTETICO D")
    linhas = [_linha("HOSPITAL SINTETICO D", "MEDIA", "9990004")]
    cv.aplicar_vinculo_cnes(db, linhas, aceitar_provisorios=False)
    assert db.query(HospitalAlias).count() == 0
    assert {p.cnes for p in db.query(PacienteFila)} == {None}

    cv.aplicar_vinculo_cnes(db, linhas)
    a = db.query(HospitalAlias).one()
    assert (a.fonte, a.confianca) == (cv.FONTE_PROVISORIO, "MEDIA")
    assert {p.cnes_confianca for p in db.query(PacienteFila)} == {"PROVISORIO_MEDIA"}


def test_provavel_erro_fica_marcado(db):
    nome = "HOSPITAL INFANTIL LUCIA DE FATIMA HIF"
    _fila(db, nome, n=1)
    st = cv.aplicar_vinculo_cnes(db, [_linha(nome, "BAIXA", "9990005")])
    assert st["provavel_erro"] == 1
    assert db.query(HospitalAlias).one().metodo == "PROVAVEL_ERRO_REVISAR"


def test_sem_correspondencia_remove_cnes_automatico(db):
    _fila(db, "OUTROS")
    db.add(HospitalAlias(alias_nome="OUTROS", cnes="9990200", fonte="integrasus_auto"))
    db.commit()
    st = cv.aplicar_vinculo_cnes(db, [_linha("OUTROS", "SEM_CORRESPONDENCIA", "")])
    assert st["invalidados_para_revisao"] == 1
    a = db.query(HospitalAlias).one()
    assert a.cnes is None and a.confianca == "REVISAR"
    assert {p.cnes for p in db.query(PacienteFila)} == {None}


def test_rebaixamento_de_alta_para_sem_correspondencia(db):
    _fila(db, "HOSPITAL SINTETICO E")
    cv.aplicar_vinculo_cnes(db, [_linha("HOSPITAL SINTETICO E", "ALTA", "9990006")])
    cv.aplicar_vinculo_cnes(db, [_linha("HOSPITAL SINTETICO E", "SEM_CORRESPONDENCIA", "")])
    assert db.query(HospitalAlias).one().cnes is None
    assert {p.cnes for p in db.query(PacienteFila)} == {None}


def test_importacao_da_coleta_aplica_vinculo(db, tmp_path, monkeypatch):
    monkeypatch.setenv("PREDMED_PSEUDO_KEY", "chave-de-teste")
    db.add(HospitalAlias(alias_nome="HOSPITAL SINTETICO F", cnes="9990007",
                         fonte=cv.FONTE_VINCULO, confianca="ALTA"))
    db.commit()
    arq = tmp_path / "fila_20990101T070000.json"
    arq.write_text(json.dumps([{
        "municipio": "FORTALEZA", "estabelecimento": "HOSPITAL SINTETICO F",
        "procedimento": "PROCEDIMENTO X", "especialidade": "Ortopedia",
        "descSwalis": "Categoria B", "mandadoJudicial": "Não", "posicao": 1,
        "nome": "ZZZ", "codSolicitacao": 9000001, "data": "2098-12-03T10:21:00.000+0000",
    }]))
    assert import_integrasus(str(arq), db) == 1
    p = db.query(PacienteFila).one()
    assert (p.cnes, p.cnes_confianca) == ("9990007", "ALTA")


def test_carregar_capacidade_idempotente(db, tmp_path):
    arq = tmp_path / "cap.csv"
    cols = ["competencia", "cnes", "nome_fantasia", "municipio", "natureza", "vinculo_sus",
            "centro_cirurgico", "salas_cirurgicas", "leitos_cirurgicos_sus", "hab_oncologia"]
    with open(arq, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerow(["2099-01", "9990001", "HOSPITAL SINTETICO", "MUNICIPIO X", "PUBLICO",
                    "True", "True", "4", "20", "False"])
        w.writerow(["2099-01", "123", "CLINICA SINTETICA", "MUNICIPIO Y", "PRIVADO",
                    "False", "False", "0", "", "nan"])
    assert cv.carregar_cnes_capacidade(db, str(arq))["linhas"] == 2
    assert cv.carregar_cnes_capacidade(db, str(arq))["linhas"] == 2
    assert db.query(CnesCapacidade).count() == 2
    h = db.query(CnesCapacidade).filter_by(cnes="9990001").one()
    assert h.salas_cirurgicas == 4 and h.vinculo_sus is True and h.hab_oncologia is False
    assert db.query(CnesCapacidade).filter_by(cnes="0000123").one().leitos_cirurgicos_sus == 0
