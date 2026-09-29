"""
Série mensal de PRODUÇÃO CIRÚRGICA do SUS no Ceará (SIH-RD, grupo SIGTAP 04), por
especialidade da fila — alvo da previsão de demanda v1 (docs/dados/previsao-demanda-v1.md).

Fontes (somente leitura):
  - backend/data/sih/RDCEaamm.dbc            2019-01 → 2024-12 (mesmos arquivos que geraram
                                             predmed-original.db)
  - ~/PredmedDados/datasus/sih/RD/RDCEaamm.dbc  2025-01 → última baixada (coleta_datasus.py)
  - backend/predmed-original.db (aberto com mode=ro) só para CONFERÊNCIA 2019–2024: a contagem
    mensal do grupo 04 lida dos .dbc deve bater com aih_registro. O banco não tem CAR_INT/IDENT,
    por isso a série é montada a partir dos .dbc.

Regras:
  - competência = ANO_CMPT/MES_CMPT (competência de processamento/pagamento), não DT_INTER;
  - conta AIH com IDENT = 1 (AIH principal); IDENT 5 (longa permanência) é continuação e
    duplicaria a internação; o total de linhas de todas as IDENT é guardado para conferência;
  - cirúrgico = PROC_REA começando por "04" (grupo 04 — procedimentos cirúrgicos);
  - carater: ELETIVO = CAR_INT 01; URGENCIA = demais (02 urgência, 03–06 acidentes/lesões);
  - especialidade = mapa SUBGRUPO_PARA_ESPECIALIDADE (hipótese documentada);
  - competências mais recentes que --ultima-competencia são descartadas (padrão 2026-06:
    2026-07 ainda está sendo complementada) e as 2 últimas mantidas são marcadas provisórias.

Saídas (só agregados, sem nenhum dado individual):
  - ~/PredmedDados/datasus/processado/cache_sih_agregado/RDCEaamm.csv  (cache por arquivo)
  - ~/PredmedDados/datasus/processado/serie_producao_cirurgica.csv
  - tabela serie_producao_cirurgica do predmed.db (substituída por inteiro; --sem-banco evita)

Uso:
    backend/venv/bin/python backend/_SCRIPTS/serie_producao_cirurgica.py [--sem-banco]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

PASTAS_DBC = [BACKEND / "data" / "sih", Path.home() / "PredmedDados" / "datasus" / "sih" / "RD"]
PROCESSADO = Path.home() / "PredmedDados" / "datasus" / "processado"
CACHE = PROCESSADO / "cache_sih_agregado"
SAIDA_CSV = PROCESSADO / "serie_producao_cirurgica.csv"
ORIGINAL_DB = BACKEND / "predmed-original.db"

# SIGTAP grupo 04 — subgrupo (4 dígitos) ou forma de organização (6 dígitos) → especialidade
# da fila IntegraSUS. Hipótese de mapeamento: ver docs/dados/previsao-demanda-v1.md.
SUBGRUPO_PARA_ESPECIALIDADE = {
    "0401": "PEQUENAS CIRURGIAS",        # pele, tecido subcutâneo e mucosa
    "0402": "ENDOCRINOLOGIA",            # glândulas endócrinas (tireoide, paratireoide, adrenal)
    "0403": "NEUROLOGIA",                # sistema nervoso central e periférico (neurocirurgia)
    "0404": "OTORRINO",                  # vias aéreas superiores, face, cabeça e pescoço
    "0405": "OFTALMOLOGIA",              # aparelho da visão
    "0406": "CARDIOVASCULAR",            # aparelho circulatório
    "0407": "CIR DIGESTIVA",             # aparelho digestivo, anexos e parede abdominal
    "0408": "ORTOPEDIA",                 # sistema osteomuscular
    "040901": "UROLOGIA",                # rim, ureter, bexiga
    "040902": "UROLOGIA",                # uretra
    "040903": "UROLOGIA",                # próstata e vesícula seminal
    "040904": "UROLOGIA",                # bolsa escrotal, testículos, cordão espermático
    "040905": "UROLOGIA",                # pênis
    "040906": "GINECOLOGIA",             # útero e anexos
    "040907": "GINECOLOGIA",             # vagina, vulva e períneo
    "0410": "GINECOLOGIA",               # mama (mastologia) — hipótese
    "0411": "OBSTETRICIA",               # cirurgia obstétrica (parto cesáreo etc.) — fora da fila
    "0412": "OUTRAS",                    # torácica
    "0413": "CIR PLASTICA REPARADORA",   # cirurgia reparadora
    "0414": "BUCO MAXILO-FACIAL",        # bucomaxilofacial
    "0415": "OUTRAS",                    # múltiplas / politraumatizado / sequenciais
    "0416": "ONCOLOGIA",                 # cirurgia em oncologia
    "0417": "OUTRAS",                    # anestesiologia
    "0418": "OUTRAS",                    # nefrologia (acesso para diálise)
}
# Especialidades da fila agrupadas para comparar com o SIH.
FILA_PARA_SERIE = {
    "OTORRINO MÉDIA COMPLEXIDADE": "OTORRINO",
    "OTORRINO E PNEUMOLOGIA": "OTORRINO",
}


def especialidade_do_proc(proc: str) -> str:
    proc = (proc or "").strip()
    return SUBGRUPO_PARA_ESPECIALIDADE.get(proc[:6]) or SUBGRUPO_PARA_ESPECIALIDADE.get(proc[:4], "OUTRAS")


def _ler_dbc(caminho: Path, colunas: list[str]) -> pd.DataFrame:
    from dbfread import DBF
    from pyreaddbc import dbc2dbf
    fd, dbf = tempfile.mkstemp(suffix=".dbf")
    os.close(fd)
    try:
        dbc2dbf(str(caminho), dbf)
        tab = DBF(dbf, encoding="latin-1", load=False)
        usar = [c for c in colunas if c in tab.field_names]
        return pd.DataFrame(({c: r[c] for c in usar} for r in tab), columns=usar)
    finally:
        os.remove(dbf)


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def agregar_arquivo(caminho: Path) -> pd.DataFrame:
    """Agregado de um RDCEaamm.dbc (com cache por sha256)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    sha = _sha256(caminho)
    cache = CACHE / f"{caminho.stem}.csv"
    meta = CACHE / f"{caminho.stem}.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text()).get("sha256") == sha:
        return pd.read_csv(cache, dtype={"subgrupo6": str, "car_int": str, "ident": str})
    df = _ler_dbc(caminho, ["ANO_CMPT", "MES_CMPT", "PROC_REA", "CAR_INT", "IDENT", "VAL_TOT"])
    aamm = caminho.stem[-4:]
    esperado = f"20{aamm[:2]}-{aamm[2:]}"
    df["competencia"] = df["ANO_CMPT"].astype(str).str.zfill(4) + "-" + df["MES_CMPT"].astype(str).str.zfill(2)
    fora = int((df["competencia"] != esperado).sum())
    df["subgrupo6"] = df["PROC_REA"].astype(str).str.slice(0, 6)
    df["cirurgico"] = df["PROC_REA"].astype(str).str.startswith("04")
    total_linhas = len(df)
    total_04 = int(df["cirurgico"].sum())
    df = df[df["cirurgico"]]
    ag = (df.groupby(["competencia", "subgrupo6", "CAR_INT", "IDENT"], dropna=False)
            .agg(n=("PROC_REA", "size"), val_tot=("VAL_TOT", "sum")).reset_index()
            .rename(columns={"CAR_INT": "car_int", "IDENT": "ident"}))
    ag.to_csv(cache, index=False)
    meta.write_text(json.dumps({"arquivo": caminho.name, "sha256": sha, "linhas": total_linhas,
                                "linhas_grupo04": total_04, "fora_da_competencia": fora,
                                "gerado_em": datetime.now().isoformat(timespec="seconds")}))
    return ag


def arquivos_dbc() -> dict[str, Path]:
    """competência → arquivo; a pasta de 2025+ tem precedência se houver repetição."""
    achados: dict[str, Path] = {}
    for pasta in PASTAS_DBC:
        for p in sorted(pasta.glob("RDCE*.dbc")):
            aamm = p.stem[-4:]
            achados[f"20{aamm[:2]}-{aamm[2:]}"] = p
    return dict(sorted(achados.items()))


def montar_serie(ag: pd.DataFrame, ultima: str) -> pd.DataFrame:
    ag = ag[(ag["competencia"] <= ultima) & (ag["ident"].astype(str) == "1")].copy()
    ag["especialidade"] = ag["subgrupo6"].map(especialidade_do_proc)
    ag["carater"] = ag["car_int"].astype(str).str.zfill(2).map(lambda c: "ELETIVO" if c == "01" else "URGENCIA")
    partes = []
    for car_nome, filtro in (("TODOS", None), ("ELETIVO", "ELETIVO"), ("URGENCIA", "URGENCIA")):
        base = ag if filtro is None else ag[ag["carater"] == filtro]
        por_esp = base.groupby(["competencia", "especialidade"]).agg(aihs=("n", "sum"), valor_total=("val_tot", "sum")).reset_index()
        tot = base.groupby("competencia").agg(aihs=("n", "sum"), valor_total=("val_tot", "sum")).reset_index()
        tot["especialidade"] = "TOTAL"
        sem_obst = base[base["especialidade"] != "OBSTETRICIA"].groupby("competencia").agg(
            aihs=("n", "sum"), valor_total=("val_tot", "sum")).reset_index()
        sem_obst["especialidade"] = "TOTAL_SEM_OBSTETRICIA"
        s = pd.concat([por_esp, tot, sem_obst], ignore_index=True)
        s["carater"] = car_nome
        partes.append(s)
    serie = pd.concat(partes, ignore_index=True)
    # completa zeros para combinações ausentes (série regular)
    comps = sorted(serie["competencia"].unique())
    idx = pd.MultiIndex.from_product([comps, sorted(serie["especialidade"].unique()), ["TODOS", "ELETIVO", "URGENCIA"]],
                                     names=["competencia", "especialidade", "carater"])
    serie = serie.set_index(["competencia", "especialidade", "carater"]).reindex(idx, fill_value=0).reset_index()
    serie["aihs"] = serie["aihs"].astype(int)
    serie["valor_total"] = serie["valor_total"].round(2)
    serie["fonte"] = serie["competencia"].map(lambda c: "SIH-RD RDCE .dbc (backend/data/sih)" if c < "2025-01"
                                              else "SIH-RD RDCE .dbc (~/PredmedDados/datasus/sih/RD)")
    provis = comps[-2:]
    serie["provisoria"] = serie["competencia"].isin(provis)
    return serie.sort_values(["carater", "especialidade", "competencia"]).reset_index(drop=True)


def conferir_original(ag: pd.DataFrame) -> dict:
    """Compara linhas grupo 04 (todas as IDENT) com predmed-original.db, aberto só para leitura."""
    if not ORIGINAL_DB.exists():
        return {"status": "predmed-original.db ausente"}
    con = sqlite3.connect(f"file:{ORIGINAL_DB}?mode=ro", uri=True)
    try:
        orig = pd.read_sql("SELECT mes_competencia AS competencia, COUNT(*) AS n_original "
                           "FROM aih_registro WHERE substr(proc_rea,1,2)='04' GROUP BY 1", con)
    finally:
        con.close()
    dbc = ag.groupby("competencia")["n"].sum().rename("n_dbc").reset_index()
    m = orig.merge(dbc, on="competencia", how="left")
    m["dif"] = m["n_dbc"] - m["n_original"]
    return {"competencias_comparadas": int(len(m)), "competencias_iguais": int((m["dif"] == 0).sum()),
            "maior_diferenca_abs": int(m["dif"].abs().max()) if len(m) else None,
            "total_original": int(m["n_original"].sum()), "total_dbc": int(m["n_dbc"].sum())}


def gravar_banco(serie: pd.DataFrame):
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND / 'predmed.db'}")
    from database import SerieProducaoCirurgica, SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        db.query(SerieProducaoCirurgica).delete(synchronize_session=False)
        agora = datetime.utcnow()
        db.bulk_save_objects([SerieProducaoCirurgica(
            competencia=r.competencia, especialidade=r.especialidade, carater=r.carater,
            aihs=int(r.aihs), valor_total=float(r.valor_total), fonte=r.fonte,
            provisoria=bool(r.provisoria), gerado_em=agora) for r in serie.itertuples()])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default="2019-01")
    ap.add_argument("--ultima-competencia", default="2026-06")
    ap.add_argument("--sem-banco", action="store_true")
    a = ap.parse_args()

    arquivos = {c: p for c, p in arquivos_dbc().items() if a.inicio <= c <= a.ultima_competencia}
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
    serie = montar_serie(ag, a.ultima_competencia)
    PROCESSADO.mkdir(parents=True, exist_ok=True)
    serie.to_csv(SAIDA_CSV, index=False)
    conf = conferir_original(ag)
    resumo = {"competencias": serie["competencia"].nunique(),
              "inicio": serie["competencia"].min(), "fim": serie["competencia"].max(),
              "aihs_grupo04_ident1": int(serie.query("carater=='TODOS' and especialidade=='TOTAL'")["aihs"].sum()),
              "conferencia_predmed_original": conf}
    (PROCESSADO / "serie_producao_cirurgica_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2))
    if not a.sem_banco:
        gravar_banco(serie)
        resumo["gravado_no_banco"] = True
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
