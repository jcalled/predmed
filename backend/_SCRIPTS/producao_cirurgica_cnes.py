"""
Produção cirúrgica SIH-RD por ESTABELECIMENTO (CNES) — insumo da redistribuição v1
(docs/dados/redistribuicao-v1.md).

Mesmas regras da série estadual (serie_producao_cirurgica.py): AIH principal (IDENT = 1),
PROC_REA do grupo SIGTAP 04, competência de processamento (ANO_CMPT/MES_CMPT), especialidade
pelo mapa SUBGRUPO_PARA_ESPECIALIDADE, caráter ELETIVO (CAR_INT 01) ou URGENCIA (demais).

Fontes (somente leitura): backend/data/sih/RDCEaamm.dbc e ~/PredmedDados/datasus/sih/RD/.
Saídas (só contagens agregadas; nenhum dado individual sai do .dbc):
  - ~/PredmedDados/datasus/processado/cache_sih_cnes/RDCEaamm.csv (cache por arquivo, sha256)
  - ~/PredmedDados/datasus/processado/producao_cirurgica_cnes.csv
  - tabela producao_cirurgica_cnes do predmed.db (substituída por inteiro; --sem-banco evita)

Uso:
    backend/venv/bin/python backend/_SCRIPTS/producao_cirurgica_cnes.py \
        [--inicio 2024-07] [--ultima-competencia 2026-06] [--sem-banco]
Faça backup do predmed.db antes de gravar (ver docs/dados/datasus-cnes-sih.md).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import serie_producao_cirurgica as spc  # noqa: E402

CACHE = spc.PROCESSADO / "cache_sih_cnes"
SAIDA_CSV = spc.PROCESSADO / "producao_cirurgica_cnes.csv"


def agregar_arquivo(caminho: Path) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    sha = spc._sha256(caminho)
    cache = CACHE / f"{caminho.stem}.csv"
    meta = CACHE / f"{caminho.stem}.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()).get("sha256") == sha:
        return pd.read_csv(cache, dtype={"cnes": str})
    df = spc._ler_dbc(caminho, ["ANO_CMPT", "MES_CMPT", "CNES", "PROC_REA", "CAR_INT", "IDENT"])
    df = df[df["PROC_REA"].astype(str).str.startswith("04") & (df["IDENT"].astype(str) == "1")].copy()
    df["competencia"] = df["ANO_CMPT"].astype(str).str.zfill(4) + "-" + df["MES_CMPT"].astype(str).str.zfill(2)
    df["cnes"] = df["CNES"].astype(str).str.strip().str.zfill(7)
    df["especialidade"] = df["PROC_REA"].astype(str).map(spc.especialidade_do_proc)
    df["carater"] = df["CAR_INT"].astype(str).str.zfill(2).map(lambda c: "ELETIVO" if c == "01" else "URGENCIA")
    ag = (df.groupby(["competencia", "cnes", "especialidade", "carater"]).size()
            .rename("aihs").reset_index())
    ag.to_csv(cache, index=False)
    meta.write_text(json.dumps({"arquivo": caminho.name, "sha256": sha, "linhas_grupo04_ident1": int(len(df)),
                                "gerado_em": datetime.now().isoformat(timespec="seconds")}))
    return ag


def gravar_banco(ag: pd.DataFrame):
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND / 'predmed.db'}")
    from database import ProducaoCirurgicaCnes, SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        db.query(ProducaoCirurgicaCnes).delete(synchronize_session=False)
        agora = datetime.utcnow()
        db.bulk_save_objects([ProducaoCirurgicaCnes(
            competencia=r.competencia, cnes=r.cnes, especialidade=r.especialidade, carater=r.carater,
            aihs=int(r.aihs), provisoria=bool(r.provisoria), gerado_em=agora) for r in ag.itertuples()])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default="2024-07")
    ap.add_argument("--ultima-competencia", default="2026-06")
    ap.add_argument("--sem-banco", action="store_true")
    a = ap.parse_args()

    arquivos = {c: p for c, p in spc.arquivos_dbc().items() if a.inicio <= c <= a.ultima_competencia}
    faltam = [c for c in pd.period_range(a.inicio, a.ultima_competencia, freq="M").strftime("%Y-%m")
              if c not in arquivos]
    if faltam:
        print(f"ERRO: competências sem arquivo: {faltam}")
        return 1
    partes = []
    for i, (comp, p) in enumerate(arquivos.items(), 1):
        partes.append(agregar_arquivo(p))
        print(f"[{i}/{len(arquivos)}] {comp} ok", flush=True)
    ag = pd.concat(partes, ignore_index=True)
    ag = ag[(ag["competencia"] >= a.inicio) & (ag["competencia"] <= a.ultima_competencia)]
    comps = sorted(ag["competencia"].unique())
    ag["provisoria"] = ag["competencia"].isin(comps[-2:])
    spc.PROCESSADO.mkdir(parents=True, exist_ok=True)
    ag.to_csv(SAIDA_CSV, index=False)

    # Conferência com a série estadual (mesmas regras → mesmo total por competência)
    conf = {}
    if spc.SAIDA_CSV.exists():
        est = pd.read_csv(spc.SAIDA_CSV)
        est = est[(est["carater"] == "TODOS") & (est["especialidade"] == "TOTAL")].set_index("competencia")["aihs"]
        por_comp = ag.groupby("competencia")["aihs"].sum()
        dif = (por_comp - est.reindex(por_comp.index)).abs()
        conf = {"competencias": int(len(dif)), "iguais_serie_estadual": int((dif == 0).sum()),
                "maior_diferenca_abs": int(dif.max()) if len(dif) else None}
    resumo = {"competencias": len(comps), "inicio": comps[0], "fim": comps[-1],
              "estabelecimentos": int(ag["cnes"].nunique()), "aihs": int(ag["aihs"].sum()),
              "conferencia_serie_estadual": conf}
    if not a.sem_banco:
        gravar_banco(ag)
        resumo["gravado_no_banco"] = True
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
