"""B05 — nenhuma métrica fixa apresentada como medida."""
from database import PacienteFila
from tests.conftest import criar_usuario, token


def test_dashboard_sem_metricas_fixas(db, client):
    criar_usuario(db, "gestor@teste.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    db.add(PacienteFila(hospital_nome="HOSPITAL SINTETICO", municipio="FORTALEZA",
                        especialidade="ORTOPEDIA", classif_swalis="Categoria B"))
    db.commit()
    d = client.get("/dashboard", headers=token(client, "gestor@teste.local")).json()
    assert d["acuracia_mape"] is None and d["acuracia_mape_status"] == "nao_validado"
    assert d["reducao_estimada_pct"] is None and d["reducao_estimada_status"] == "nao_validado"
    assert d["espera_media_oncologia_dias"] is None
    # metas aparecem separadas, como meta
    assert d["meta_mape_pct"] == 15 and d["meta_reducao_espera_pct"] == 40


def test_previsao_rotulada_como_simulada(db, client):
    criar_usuario(db, "gestor@teste.local", "sesa",
                  dict(nome="SESA Teste", tipo="SESA", cir="Ceará (todos)", cnpj="00.000.000/0001-01"))
    for i in range(30):
        db.add(PacienteFila(hospital_nome="HOSPITAL SINTETICO", municipio="FORTALEZA",
                            especialidade="ORTOPEDIA", classif_swalis="Categoria B"))
    db.commit()
    p = client.get("/previsoes", headers=token(client, "gestor@teste.local")).json()
    assert p["origem_serie"] == "simulado"
    assert p["metricas"]["mape_pct"] is None
    assert p["metricas"]["mape_status"] == "nao_validado"
