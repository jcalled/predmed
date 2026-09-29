"""
Não-destruição de dados (achado D04 do arquiteto):
- seed idempotente: não apaga nem recria usuários/tenants existentes;
- importação IntegraSUS: valida antes, substitui em transação, rollback em falha.
Todos os dados são sintéticos.
"""
import pytest

import config
from database import Usuario, Tenant, ConfigVagas, PacienteFila
from services import data_import
from services.data_import import import_integrasus, ImportacaoInvalida

CABECALHO = "POSICAO_FILA;MUNICIPIO;UNIDADE;PROCEDIMENTO;ESPECIALIDADE;INIC_NOME_PACIENTE;JUDICIALIZADO;CLASSIF_SWALIS\n"


def _csv(tmp_path, nome, linhas, cabecalho=CABECALHO):
    p = tmp_path / nome
    p.write_text(cabecalho + "".join(linhas), encoding="utf-8")
    return str(p)


def _linhas_sinteticas(n, hospital="HOSPITAL SINTETICO ALFA", mun="FORTALEZA"):
    return [f"{i};{mun};{hospital};PROC TESTE;ORTOPEDIA;ZZ;NAO;Categoria B\n" for i in range(n)]


# ── Seed ─────────────────────────────────────────────────────
def test_seed_idempotente_preserva_usuarios(db, monkeypatch):
    import seed
    monkeypatch.setattr(config, "MODO_DEV", True)
    monkeypatch.setattr(seed, "get_senha_seed", config.get_senha_seed)

    c1 = seed.seed_usuarios(db)
    assert c1["usuarios"] == 4 and c1["tenants"] == 4

    # Simula troca de senha e um usuário extra criado depois
    u = db.query(Usuario).filter(Usuario.email == "sesa@predmed.com").one()
    u.senha_hash = "hash-alterado"
    extra_tenant = db.query(Tenant).first()
    db.add(Usuario(nome="Extra", email="extra@teste.local", senha_hash="h",
                   role="sesa", tenant_id=extra_tenant.id))
    db.commit()
    ids_antes = sorted(x.id for x in db.query(Usuario).all())

    c2 = seed.seed_usuarios(db)
    assert c2["usuarios"] == 0 and c2["tenants"] == 0 and c2["vagas"] == 0
    assert sorted(x.id for x in db.query(Usuario).all()) == ids_antes
    assert db.query(Usuario).filter(Usuario.email == "sesa@predmed.com").one().senha_hash == "hash-alterado"
    assert db.query(Tenant).count() == 4
    assert db.query(ConfigVagas).count() == 8


def test_seed_redefine_senha_so_com_variavel(db, monkeypatch):
    import seed
    from auth import verify_password
    monkeypatch.setattr(config, "MODO_DEV", True)
    seed.seed_usuarios(db)
    monkeypatch.delenv("SEED_SENHA_PADRAO", raising=False)
    c = seed.seed_usuarios(db, redefinir_senhas=True)
    assert c["senhas_redefinidas"] == 0  # padrão de dev nunca é usado para rotação
    monkeypatch.setenv("SEED_SENHA_PADRAO", "nova-senha-sintetica-123")
    c = seed.seed_usuarios(db, redefinir_senhas=True)
    assert c["senhas_redefinidas"] == 4
    u = db.query(Usuario).filter(Usuario.email == "hgf@predmed.com").one()
    assert verify_password("nova-senha-sintetica-123", u.senha_hash)


def test_seed_fora_de_dev_sem_senha_nao_cria_usuario(db, monkeypatch):
    import seed
    monkeypatch.setattr(config, "MODO_DEV", False)
    monkeypatch.delenv("SEED_SENHA_PADRAO", raising=False)
    monkeypatch.setattr(seed, "get_senha_seed", config.get_senha_seed)
    c = seed.seed_usuarios(db)
    assert c["usuarios"] == 0
    assert len(c["usuarios_sem_senha"]) == 4
    assert db.query(Usuario).count() == 0


# ── Importação IntegraSUS ────────────────────────────────────
def test_importacao_valida_substitui_fila(db, tmp_path):
    assert import_integrasus(_csv(tmp_path, "a.csv", _linhas_sinteticas(5)), db) == 5
    assert import_integrasus(_csv(tmp_path, "b.csv", _linhas_sinteticas(3)), db) == 3
    assert db.query(PacienteFila).count() == 3


def test_arquivo_invalido_preserva_fila(db, tmp_path):
    import_integrasus(_csv(tmp_path, "a.csv", _linhas_sinteticas(5)), db)
    sem_hospital = "POSICAO_FILA;MUNICIPIO;ESPECIALIDADE\n1;FORTALEZA;ORTOPEDIA\n"
    with pytest.raises(ImportacaoInvalida):
        import_integrasus(_csv(tmp_path, "ruim.csv", [], cabecalho=sem_hospital), db)
    with pytest.raises(ImportacaoInvalida):
        import_integrasus(_csv(tmp_path, "vazio.csv", []), db)
    assert db.query(PacienteFila).count() == 5


def test_falha_no_meio_faz_rollback(db, tmp_path, monkeypatch):
    import_integrasus(_csv(tmp_path, "a.csv", _linhas_sinteticas(5)), db)

    def explode(*a, **k):
        raise RuntimeError("falha simulada depois de inserir")

    monkeypatch.setattr(data_import, "build_hospital_especialidades", explode)
    with pytest.raises(RuntimeError):
        import_integrasus(_csv(tmp_path, "b.csv", _linhas_sinteticas(9, hospital="OUTRO HOSP")), db)
    db.expire_all()
    assert db.query(PacienteFila).count() == 5
    assert {p.hospital_nome for p in db.query(PacienteFila).all()} == {"HOSPITAL SINTETICO ALFA"}
