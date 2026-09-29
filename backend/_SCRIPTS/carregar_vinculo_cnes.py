"""
Carrega no predmed.db (idempotente):
  1. a capacidade CNES (processado/cnes_capacidade.csv → tabela cnes_capacidade);
  2. o vínculo nome da fila → CNES (processado/vinculo_fila_cnes.csv → hospital_alias
     e pacientes_fila.cnes/cnes_confianca), com as regras de services/cnes_vinculo.py.

Faça backup antes (o script recusa rodar sem --backup-feito ou --sem-backup explícito):
    sqlite3 backend/predmed.db ".backup '$HOME/PredmedDados/backups/predmed_antes_vinculo_cnes_AAAAMMDDHHMM.db'"

Uso:
    backend/venv/bin/python backend/_SCRIPTS/carregar_vinculo_cnes.py --backup-feito
    ... --so-capacidade | --so-vinculo | --somente-alta | --simular

Saída: apenas contagens agregadas (nomes de estabelecimentos, nunca pacientes).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND / 'predmed.db'}")

from sqlalchemy import func, select  # noqa: E402

from database import HospitalAlias, PacienteFila, SessionLocal, init_db  # noqa: E402
from services import cnes_vinculo as cv  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vinculo", default=cv.CSV_VINCULO)
    ap.add_argument("--capacidade", default=cv.CSV_CAPACIDADE)
    ap.add_argument("--so-capacidade", action="store_true")
    ap.add_argument("--so-vinculo", action="store_true")
    ap.add_argument("--somente-alta", action="store_true",
                    help="não grava as sugestões MEDIA/AMBIGUO/BAIXA como provisórias")
    ap.add_argument("--simular", action="store_true", help="executa e faz rollback")
    ap.add_argument("--backup-feito", action="store_true")
    ap.add_argument("--sem-backup", action="store_true")
    a = ap.parse_args()
    if not (a.backup_feito or a.sem_backup or a.simular):
        print("Faça backup do predmed.db e rode com --backup-feito (ou --simular).")
        return 2

    init_db()  # cria cnes_capacidade/serie_producao_cirurgica e acrescenta colunas novas
    db = SessionLocal()
    rel = {}
    try:
        if not a.so_vinculo:
            rel["capacidade"] = cv.carregar_cnes_capacidade(db, a.capacidade, commit=False)
        if not a.so_capacidade:
            linhas = cv.ler_vinculo_csv(a.vinculo)
            rel["vinculo"] = cv.aplicar_vinculo_cnes(
                db, linhas, aceitar_provisorios=not a.somente_alta, commit=False)
            rel["aliases_por_fonte"] = {
                f"{f or '-'}|{c or '-'}": n for f, c, n in db.execute(
                    select(HospitalAlias.fonte, HospitalAlias.confianca, func.count()).group_by(
                        HospitalAlias.fonte, HospitalAlias.confianca)).all()}
            rel["fila_por_confianca_cnes"] = {
                (c or "SEM_CNES"): n for c, n in db.execute(
                    select(PacienteFila.cnes_confianca, func.count()).group_by(PacienteFila.cnes_confianca)).all()}
        if a.simular:
            db.rollback()
            rel["simulacao"] = True
        else:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(json.dumps(rel, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
