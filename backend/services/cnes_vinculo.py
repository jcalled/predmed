"""
PREDMED — Vínculo nome do estabelecimento (fila IntegraSUS) → CNES e capacidade CNES.

Fontes (geradas fora do banco, em ~/PredmedDados/datasus/processado/):
  - vinculo_fila_cnes.csv   → _SCRIPTS/casar_estabelecimentos_cnes.py
  - cnes_capacidade.csv     → _SCRIPTS/cnes_capacidade.py

Regras do vínculo (docs/dados/datasus-cnes-sih.md e vinculo-fila-cnes-revisao.md;
decisão do responsável de 29/09/2026):
  - ALTA grava o CNES como vínculo automático definitivo (fonte = FONTE_VINCULO);
  - MEDIA, AMBIGUO e BAIXA gravam o 1º candidato como PROVISÓRIO
    (fonte = FONTE_PROVISORIO, confiança original preservada) para revisão posterior;
  - SEM_CORRESPONDENCIA não recebe CNES; alias automático antigo com CNES perde o
    link e fica como REVISAR;
  - vínculo manual (fonte "manual"/"revisao_manual") nunca é sobrescrito;
  - PROVAVEL_ERRO: nomes cuja sugestão foi apontada como provavelmente errada;
    continuam provisórios, com metodo marcado, para revisão prioritária;
  - pacientes_fila.cnes / cnes_confianca são derivados dos aliases a cada carga.
Tudo é idempotente: rodar de novo com o mesmo arquivo não muda nada.
Nenhum dado de paciente é lido além do nome do estabelecimento.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from sqlalchemy import update
from sqlalchemy.orm import Session

from database import CnesCapacidade, Hospital, HospitalAlias, PacienteFila

FONTE_VINCULO = "cnes_casamento_v1"
FONTE_PROVISORIO = "cnes_auto_provisorio"
FONTES_MANUAIS = ("manual", "revisao_manual")
FONTES_AUTOMATICAS_ANTIGAS = ("integrasus_auto",)
CONFIANCAS_DEFINITIVAS = ("ALTA",)
CONFIANCAS_PROVISORIAS = ("MEDIA", "AMBIGUO", "BAIXA")
# Sugestões que o responsável apontou como provável erro (29/09/2026).
PROVAVEL_ERRO = {
    "HOSPITAL INFANTIL LUCIA DE FATIMA HIF": "sugestao SOPAI parece errada",
    "HOSPITAL SAO RAIMUNDO": "homonimo Crato x Varzea Alegre",
}

PASTA_PROCESSADO = os.path.expanduser(
    os.getenv("PREDMED_DATASUS_PROCESSADO", "~/PredmedDados/datasus/processado"))
CSV_VINCULO = os.path.join(PASTA_PROCESSADO, "vinculo_fila_cnes.csv")
CSV_CAPACIDADE = os.path.join(PASTA_PROCESSADO, "cnes_capacidade.csv")


def eh_manual(alias: Optional[HospitalAlias]) -> bool:
    return bool(alias and alias.fonte and alias.fonte.lower().startswith(FONTES_MANUAIS))


def alias_confiavel(alias: HospitalAlias, incluir_provisorios: bool = True) -> bool:
    """Alias cujo CNES pode ser propagado para a fila."""
    if not alias.cnes:
        return False
    if eh_manual(alias):
        return True
    if alias.fonte == FONTE_VINCULO and alias.confianca in CONFIANCAS_DEFINITIVAS:
        return True
    return incluir_provisorios and alias.fonte == FONTE_PROVISORIO


def rotulo_confianca(alias: HospitalAlias) -> str:
    if eh_manual(alias):
        return "MANUAL"
    if alias.fonte == FONTE_PROVISORIO:
        return f"PROVISORIO_{alias.confianca}"
    return alias.confianca or "ALTA"


def ler_vinculo_csv(caminho: str = CSV_VINCULO) -> List[Dict]:
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    obrig = {"nome_fila", "confianca", "cnes", "nome_cnes"}
    if linhas and not obrig.issubset(linhas[0].keys()):
        raise ValueError(f"vinculo_fila_cnes.csv sem colunas {obrig - set(linhas[0].keys())}")
    return linhas


def _cnes7(valor) -> Optional[str]:
    v = (valor or "").strip()
    if not v or v.lower() == "nan":
        return None
    return v.zfill(7) if v.isdigit() else v


def aplicar_vinculo_cnes(db: Session, linhas: Iterable[Dict],
                         aceitar_provisorios: bool = True,
                         commit: bool = True) -> Dict[str, int]:
    """Grava o vínculo em hospital_alias e propaga para pacientes_fila. Idempotente."""
    st = {"inseridos": 0, "atualizados": 0, "inalterados": 0, "manuais_preservados": 0,
          "definitivos_alta": 0, "provisorios": 0, "provavel_erro": 0,
          "invalidados_para_revisao": 0, "sem_cnes": 0}
    agora = datetime.utcnow()
    for ln in linhas:
        nome = (ln.get("nome_fila") or "").strip()
        if not nome:
            continue
        conf = (ln.get("confianca") or "").strip().upper()
        cnes = _cnes7(ln.get("cnes"))
        alias = db.query(HospitalAlias).filter(HospitalAlias.alias_nome == nome).first()

        if eh_manual(alias):
            st["manuais_preservados"] += 1
            continue

        if cnes and (conf in CONFIANCAS_DEFINITIVAS or
                     (aceitar_provisorios and conf in CONFIANCAS_PROVISORIAS)):
            definitivo = conf in CONFIANCAS_DEFINITIVAS
            metodo = (ln.get("metodo") or "") or None
            if not definitivo and nome in PROVAVEL_ERRO:
                metodo = "PROVAVEL_ERRO_REVISAR"
                st["provavel_erro"] += 1
            novo = dict(cnes=cnes, hospital_nome=(ln.get("nome_cnes") or None),
                        fonte=FONTE_VINCULO if definitivo else FONTE_PROVISORIO,
                        confianca=conf, metodo=metodo,
                        competencia_cnes=(ln.get("competencia_cnes") or None))
            st["definitivos_alta" if definitivo else "provisorios"] += 1
            if alias is None:
                db.add(HospitalAlias(alias_nome=nome, atualizado_em=agora, **novo))
                st["inseridos"] += 1
            elif all(getattr(alias, k) == v for k, v in novo.items()):
                st["inalterados"] += 1
            else:
                for k, v in novo.items():
                    setattr(alias, k, v)
                alias.atualizado_em = agora
                st["atualizados"] += 1
            continue

        # SEM_CORRESPONDENCIA (ou provisórios recusados): não grava CNES e desfaz
        # link automático existente, que não foi confirmado.
        st["sem_cnes"] += 1
        if alias is None:
            continue
        automatico = alias.fonte in FONTES_AUTOMATICAS_ANTIGAS + (FONTE_VINCULO, FONTE_PROVISORIO)
        if automatico and alias.cnes:
            alias.cnes = None
            alias.confianca = "REVISAR"
            alias.metodo = f"sugestao_{conf.lower()}:{cnes or '-'}"
            alias.competencia_cnes = ln.get("competencia_cnes") or None
            alias.atualizado_em = agora
            st["invalidados_para_revisao"] += 1
        elif automatico and alias.confianca not in (conf, "REVISAR"):
            alias.confianca = conf
            alias.atualizado_em = agora
    db.flush()
    st.update(aplicar_cnes_na_fila(db))
    if commit:
        db.commit()
    return st


def _hospital_para_cnes(db: Session, cnes: str, nome: Optional[str]) -> Hospital:
    """Hospital da tabela unificada com esse CNES; cria a partir de cnes_capacidade se faltar."""
    h = db.query(Hospital).filter(Hospital.cnes == cnes).first()
    if h:
        return h
    cap = (db.query(CnesCapacidade).filter(CnesCapacidade.cnes == cnes)
           .order_by(CnesCapacidade.competencia.desc()).first())
    h = Hospital(
        cnes=cnes,
        nome_fantasia=(cap.nome_fantasia if cap and cap.nome_fantasia else nome) or cnes,
        razao_social=cap.razao_social if cap else None,
        municipio=(cap.municipio if cap else None) or "DESCONHECIDO",
        cir=cap.cir_ads_predmed if cap else None,
        natureza_juridica=cap.natureza if cap else None,
        atende_sus=bool(cap.vinculo_sus) if cap else True,
        is_cirurgico=bool(cap.centro_cirurgico) if cap else False,
        fonte="cnes", confiavel=cap is not None,
    )
    db.add(h)
    db.flush()
    return h


def aplicar_cnes_na_fila(db: Session) -> Dict[str, int]:
    """Recalcula pacientes_fila.cnes (e hospital_id) a partir dos aliases confiáveis.
    Não faz commit: pode ser chamada dentro da transação de import_integrasus."""
    nomes_fila = {n for (n,) in db.query(PacienteFila.hospital_nome).distinct()}
    aliases = {a.alias_nome: a for a in db.query(HospitalAlias)
               .filter(HospitalAlias.alias_nome.in_(nomes_fila)).all()} if nomes_fila else {}
    vinculados = registros = provisorios = 0
    for nome in nomes_fila:
        a = aliases.get(nome)
        if a is not None and alias_confiavel(a):
            h = _hospital_para_cnes(db, a.cnes, a.hospital_nome)
            rotulo = rotulo_confianca(a)
            n = db.execute(update(PacienteFila).where(PacienteFila.hospital_nome == nome)
                           .values(cnes=a.cnes, cnes_confianca=rotulo, hospital_id=h.id)).rowcount
            vinculados += 1
            registros += n or 0
            if rotulo.startswith("PROVISORIO"):
                provisorios += n or 0
        else:
            db.execute(update(PacienteFila).where(PacienteFila.hospital_nome == nome)
                       .values(cnes=None, cnes_confianca=None))
    return {"estabelecimentos_fila": len(nomes_fila), "estabelecimentos_com_cnes": vinculados,
            "registros_fila_com_cnes": registros, "registros_fila_cnes_provisorio": provisorios}


# ──────────────────────────────────────────────
# Capacidade CNES
# ──────────────────────────────────────────────
_BOOL = {"true": True, "false": False, "1": True, "0": False, "": None}
_COLS_BOOL = {c.name for c in CnesCapacidade.__table__.columns if str(c.type) == "BOOLEAN"}
_COLS_INT = {c.name for c in CnesCapacidade.__table__.columns
             if str(c.type) == "INTEGER" and c.name != "id"}
_COLS = {c.name for c in CnesCapacidade.__table__.columns} - {"id", "carregado_em"}


def _converter(col: str, v):
    v = (v or "").strip()
    if v.lower() == "nan":
        v = ""
    if col in _COLS_BOOL:
        return _BOOL.get(v.lower())
    if col in _COLS_INT:
        return int(float(v)) if v else 0
    if col == "cnes":
        return _cnes7(v)
    return v or None


def carregar_cnes_capacidade(db: Session, caminho: str = CSV_CAPACIDADE,
                             commit: bool = True) -> Dict[str, int]:
    """Substitui as linhas das competências presentes no CSV (idempotente)."""
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        raise ValueError("cnes_capacidade.csv vazio")
    faltam = {"competencia", "cnes", "salas_cirurgicas"} - set(linhas[0].keys())
    if faltam:
        raise ValueError(f"cnes_capacidade.csv sem colunas {faltam}")
    competencias = sorted({ln["competencia"] for ln in linhas})
    db.query(CnesCapacidade).filter(CnesCapacidade.competencia.in_(competencias)) \
        .delete(synchronize_session=False)
    agora = datetime.utcnow()
    objs = [CnesCapacidade(carregado_em=agora,
                           **{c: _converter(c, ln.get(c)) for c in _COLS if c in ln})
            for ln in linhas]
    db.bulk_save_objects(objs)
    if commit:
        db.commit()
    return {"competencias": len(competencias), "linhas": len(objs),
            "competencia_mais_recente": competencias[-1]}
