"""
Casamento nome do estabelecimento (fila IntegraSUS) → CNES, com nível de confiança.

O IntegraSUS publica o NOME do estabelecimento executante, não o CNES. Este script:
1. Lê os nomes distintos da fila e contagens AGREGADAS (predmed.db, somente leitura):
   total de registros por estabelecimento e distribuição do município de RESIDÊNCIA dos pacientes
   (o campo `municipio` da fila é o município do paciente, não o do hospital).
2. Normaliza nomes (acentos, pontuação, abreviações HOSP/MATERN/MUNIC/DR/STA...).
3. Compara com os estabelecimentos ativos do CNES-CE (cnes_capacidade.csv: nome fantasia e razão social).
4. Restrição por município:
   - se o nome da fila contém o nome de um município do CE (ex.: "... DE SOBRAL"), só concorrem
     estabelecimentos desse município (restrição dura);
   - caso contrário, estabelecimentos localizados nos municípios de residência mais frequentes
     da fila daquele estabelecimento recebem um bônus pequeno (restrição suave).
5. Classifica: ALTA / MEDIA / BAIXA / SEM_CORRESPONDENCIA, com margem para o 2º candidato.

Saídas (só nomes de ESTABELECIMENTOS e contagens — nenhuma linha de paciente):
    ~/PredmedDados/datasus/processado/vinculo_fila_cnes.csv
    docs/dados/vinculo-fila-cnes-revisao.md   (com --relatorio)

Uso:
    backend/venv/bin/python backend/_SCRIPTS/casar_estabelecimentos_cnes.py --relatorio
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
REPO = AQUI.parent.parent
DB_PADRAO = AQUI.parent / "predmed.db"
DADOS_DIR = Path(os.getenv("PREDMED_DADOS_DIR", Path.home() / "PredmedDados"))
PROC = DADOS_DIR / "datasus" / "processado"
RELATORIO = REPO / "docs" / "dados" / "vinculo-fila-cnes-revisao.md"

ABREV = {
    "HOSP": "HOSPITAL", "HOSPIT": "HOSPITAL", "MAT": "MATERNIDADE", "MATERN": "MATERNIDADE",
    "MUN": "MUNICIPAL", "MUNIC": "MUNICIPAL", "DR": "DOUTOR", "DRA": "DOUTORA", "STA": "SANTA",
    "STO": "SANTO", "SEC": "SECRETARIA", "SECRET": "SECRETARIA", "N": "NOSSA", "SRA": "SENHORA",
    "PE": "PADRE", "GOV": "GOVERNADOR", "DEP": "DEPUTADO", "PREF": "PREFEITO", "INST": "INSTITUTO",
    "CEN": "CENTRO", "POLICL": "POLICLINICA", "UNID": "UNIDADE", "ANT": "ANTONIO", "RAIM": "RAIMUNDO",
    "IZABEL": "ISABEL", "LUIZA": "LUISA",
}
PARADAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "LTDA", "S", "A", "SA", "ME", "EIRELI", "EPP"}
COMUNS = {"HOSPITAL", "MUNICIPAL", "MATERNIDADE", "SAUDE", "CENTRO", "SECRETARIA", "DOUTOR", "DOUTORA",
          "REGIONAL", "GERAL", "POSTO", "UNIDADE", "BASICA", "INSTITUTO", "CLINICA", "POLICLINICA", "CASA",
          "SAO", "SANTA", "SANTO", "NOSSA", "SENHORA", "DISTRITAL", "UBS", "FUNDO", "OLHOS"}
GENERICOS = {"OUTROS", "SECRETARIA MUNICIPAL SAUDE", "SECRETARIA MUNICIPAL SAUDE", "SECRETARIA SAUDE"}

log = logging.getLogger("casar_cnes")


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = [ABREV.get(t, t) for t in s.split()]
    return " ".join(t for t in toks if t not in PARADAS)


def _tok_igual(a: str, b: str) -> bool:
    if a == b:
        return True
    return len(a) >= 5 and len(b) >= 5 and SequenceMatcher(None, a, b).ratio() >= 0.85


def similaridade(a: str, b: str) -> float:
    """Combina razão de sequência e cobertura de tokens (tolerante a erro de digitação)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = a.split(), b.split()
    comuns = sum(1 for t in ta if any(_tok_igual(t, u) for u in tb))
    dice = 2 * comuns / (len(ta) + len(tb))
    cobertura = comuns / min(len(ta), len(tb))
    seq = SequenceMatcher(None, a, b).ratio()
    return round(0.4 * seq + 0.4 * dice + 0.2 * cobertura, 4)


def ler_fila(db: Path) -> pd.DataFrame:
    """Só agregados: registros por estabelecimento e por (estabelecimento, município de residência)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query(
            "SELECT hospital_nome AS nome, municipio, COUNT(*) AS n FROM pacientes_fila "
            "GROUP BY hospital_nome, municipio", con)
    finally:
        con.close()
    return df


def _texto(s: str) -> str:
    """Maiúsculas sem acento/pontuação, mantendo preposições (para achar 'DE <MUNICÍPIO>')."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s).split())


def candidatos() -> tuple[pd.DataFrame, str]:
    """Estabelecimentos ativos na competência (ST) + cadastrados no CADGERCE e ausentes do ST
    (inativos/sem envio na competência; só pessoa jurídica)."""
    cap = pd.read_csv(PROC / "cnes_capacidade.csv", dtype=str).fillna("")
    competencia = cap["competencia"].iloc[0]
    cap = cap[cap["nome_fantasia"] != "(pessoa fisica - omitido)"].copy()
    cap["ativo_competencia"] = True
    try:
        from dbfread import DBF
        from cnes_capacidade import AUX, ler_cnv
        cad = pd.DataFrame(iter(DBF(AUX / "DBF" / "CADGERCE.dbf", encoding="latin-1")))
        cad["CNES"] = cad["CNES"].astype(str).str.zfill(7)
        cad = cad[~cad["CNES"].isin(cap["cnes"]) & (cad["CPF_CNPJ"].astype(str).str.strip().str.len() == 14)]
        mun = ler_cnv(AUX / "CNV" / "ce_municip.cnv")
        extra = pd.DataFrame({
            "cnes": cad["CNES"], "nome_fantasia": cad["FANTASIA"].str.strip(),
            "razao_social": cad["RAZ_SOCI"].str.strip(),
            "municipio": cad["CODUFMUN"].astype(str).map(lambda c: re.sub(r"^\d+\s+", "", mun.get(c, ""))),
            "relevante_cirurgia": "False", "ativo_competencia": False})
        cap = pd.concat([cap, extra], ignore_index=True).fillna("")
    except Exception as e:  # noqa: BLE001
        log.warning("CADGERCE indisponível (%s); usando só o ST", e)
    cap["n_fant"] = cap["nome_fantasia"].map(normalizar)
    cap["n_raz"] = cap["razao_social"].map(normalizar)
    cap["mun_t"] = cap["municipio"].map(_texto)
    cap["mun_n"] = cap["municipio"].map(normalizar)
    cap["relev"] = cap["relevante_cirurgia"] == "True"
    return cap, competencia


def _ranquear(cand: pd.DataFrame, nn: str, top_res: list[str]) -> pd.DataFrame:
    dist = {t for t in nn.split() if t not in COMUNS and len(t) >= 3}
    if dist:  # pré-filtro barato: ao menos um token distintivo em comum
        filtro = cand["n_fant"].map(lambda x: bool(dist & set(x.split()))) | \
            cand["n_raz"].map(lambda x: bool(dist & set(x.split())))
        if filtro.any():
            cand = cand[filtro]
    if cand.empty:
        return cand.assign(score=[], total=[])
    if len(cand) > 300:  # pré-ranking por tokens exatos antes da similaridade fina (desempenho)
        tn = set(nn.split())
        rapido = cand["n_fant"].map(lambda x: len(tn & set(x.split()))) + \
            cand["n_raz"].map(lambda x: len(tn & set(x.split())))
        cand = cand.loc[rapido.sort_values(ascending=False).index[:300]]
    sc = cand.apply(lambda r: max(similaridade(nn, r["n_fant"]), similaridade(nn, r["n_raz"])), axis=1)
    bonus = cand["mun_n"].isin(top_res) * 0.05 + cand["relev"] * 0.02 + cand["ativo_competencia"].astype(bool) * 0.02
    return cand.assign(score=sc, total=(sc + bonus).clip(upper=1.09)).sort_values(
        ["total", "relev"], ascending=False)


def gerar(db: Path = DB_PADRAO, relatorio: bool = False) -> Path:
    cap, competencia = candidatos()
    municipios = sorted({m for m in cap.loc[cap["ativo_competencia"] == True, "mun_t"] if m},  # noqa: E712
                        key=len, reverse=True)

    fila = ler_fila(db)
    tot = fila.groupby("nome")["n"].sum()
    residencia = {k: Counter(dict(zip(g["municipio"].map(normalizar), g["n"]))) for k, g in fila.groupby("nome")}

    linhas = []
    for nome, n_reg in tot.sort_values(ascending=False).items():
        nn = normalizar(nome)
        texto = _texto(nome)
        top_res = [m for m, _ in residencia[nome].most_common(3)]
        base = dict(nome_fila=nome, registros_fila=int(n_reg),
                    municipio_residencia_principal=top_res[0] if top_res else "")
        if nn in GENERICOS or not nn:
            linhas.append(base | dict(confianca="SEM_CORRESPONDENCIA", metodo="nome_generico"))
            continue
        # Município explícito no nome: "... DE/DO/DA <MUNICÍPIO>" ou nome terminado no município.
        # Evita falsos positivos como "OSWALDO CRUZ" (Cruz) e "MADALENA NUNES" (Madalena).
        mun_no_nome = next((m for m in municipios if texto != m and (
            re.search(rf"\b(DE|DO|DA) {m}\b", texto) or texto.endswith(" " + m))), None)
        metodo = "nome+residencia"
        tabela = _ranquear(cap, nn, top_res)
        if mun_no_nome:
            restrita = _ranquear(cap[cap["mun_t"] == mun_no_nome], nn, top_res)
            if not restrita.empty and float(restrita.iloc[0]["score"]) >= 0.80:
                tabela, metodo = restrita, "municipio_no_nome"
        if tabela.empty:
            linhas.append(base | dict(confianca="SEM_CORRESPONDENCIA", metodo=metodo))
            continue
        top = tabela.iloc[0]
        outros = tabela[tabela["cnes"] != top["cnes"]]
        # Homônimo inativo (CNES antigo só no CADGERCE) não torna o casamento ambíguo quando o
        # 1º candidato está ativo: a margem é medida contra o melhor outro candidato ATIVO.
        if bool(top["ativo_competencia"]):
            ativos = outros[outros["ativo_competencia"].astype(bool)]
            if len(ativos):
                outros = ativos
        seg = outros.iloc[0] if len(outros) else None
        margem = float(top["total"] - (seg["total"] if seg is not None else 0))
        s = float(top["score"])
        if s >= 0.93 and margem >= 0.05:
            conf = "ALTA"
        elif s >= 0.93:
            conf = "AMBIGUO"  # mesmo nome (ou quase) em mais de um CNES
        elif s >= 0.80 and margem >= 0.03:
            conf = "MEDIA"
        elif s >= 0.55:
            conf = "BAIXA"
        else:
            conf = "SEM_CORRESPONDENCIA"
        if conf == "ALTA" and seg is not None and float(seg["score"]) >= 0.93:
            conf = "MEDIA"  # homônimo ativo em outro município, desempatado só pela residência dos pacientes
        ativo = bool(top["ativo_competencia"])
        if conf == "ALTA" and not ativo:
            conf = "MEDIA"  # nome confere, mas o CNES não aparece ativo na competência
        linhas.append(base | dict(
            confianca=conf, metodo=metodo, cnes=top["cnes"], nome_cnes=top["nome_fantasia"],
            municipio_cnes=top["municipio"], ativo_competencia=ativo, score=round(s, 3), margem=round(margem, 3),
            cnes_2=seg["cnes"] if seg is not None else "", nome_cnes_2=seg["nome_fantasia"] if seg is not None else "",
            municipio_cnes_2=seg["municipio"] if seg is not None else ""))

    colunas = ["nome_fila", "registros_fila", "confianca", "metodo", "cnes", "nome_cnes", "municipio_cnes",
               "ativo_competencia", "score", "margem", "cnes_2", "nome_cnes_2", "municipio_cnes_2",
               "municipio_residencia_principal"]
    out = pd.DataFrame(linhas).reindex(columns=colunas).fillna({"cnes": "", "nome_cnes": "", "municipio_cnes": "",
                                                                  "cnes_2": "", "nome_cnes_2": "",
                                                                  "municipio_cnes_2": "", "score": 0, "margem": 0})
    out.insert(0, "competencia_cnes", competencia)
    PROC.mkdir(parents=True, exist_ok=True)
    destino = PROC / "vinculo_fila_cnes.csv"
    out.to_csv(destino, index=False)
    resumo = out.groupby("confianca").agg(estabelecimentos=("nome_fila", "size"), registros=("registros_fila", "sum"))
    log.info("Casamento nome→CNES:\n%s", resumo.to_string())
    if relatorio:
        escrever_relatorio(out, resumo, competencia)
    return destino


def escrever_relatorio(out: pd.DataFrame, resumo: pd.DataFrame, competencia: str):
    total_e, total_r = len(out), int(out["registros_fila"].sum())
    L = [
        "# Vínculo nome do estabelecimento (fila IntegraSUS) → CNES — revisão manual",
        "",
        f"Gerado por `backend/_SCRIPTS/casar_estabelecimentos_cnes.py` em {date.today():%d/%m/%Y}. "
        f"CNES competência {competencia}. Contém só nomes de estabelecimentos e contagens agregadas.",
        "",
        "Método e limiares: ver `docs/dados/datasus-cnes-sih.md` (seção Vínculo). "
        "ALTA = similaridade ≥ 0,93 e margem ≥ 0,05 sobre o 2º candidato; MEDIA = ≥ 0,80 e margem ≥ 0,03; "
        "AMBIGUO = nome igual (≥ 0,93) em mais de um CNES; BAIXA = ≥ 0,55; abaixo disso ou nome genérico = "
        "SEM_CORRESPONDENCIA. Nunca recebem ALTA: CNES ausente do ST da competência (inativo/sem envio) e homônimo ativo "
        "desempatado só pela residência dos pacientes (ficam MEDIA).",
        "",
        "## Resumo",
        "",
        "| Confiança | Estabelecimentos | % | Registros da fila | % |",
        "|---|---:|---:|---:|---:|",
    ]
    for conf in ["ALTA", "MEDIA", "AMBIGUO", "BAIXA", "SEM_CORRESPONDENCIA"]:
        if conf in resumo.index:
            e, r = int(resumo.loc[conf, "estabelecimentos"]), int(resumo.loc[conf, "registros"])
            L.append(f"| {conf} | {e} | {100*e/total_e:.0f}% | {r:,} | {100*r/total_r:.1f}% |".replace(",", "."))
    L.append(f"| Total | {total_e} | | {total_r:,} | |".replace(",", "."))
    L += ["", "## Para revisar (MEDIA, AMBIGUO, BAIXA e SEM_CORRESPONDENCIA)", "",
          "Ordenado por registros na fila. Preencher a coluna **CNES correto** e devolver para carga no alias.", "",
          "| Nome na fila | Registros | Confiança | Sugestão (CNES — nome — município) | Score | Margem | 2º candidato | CNES correto |",
          "|---|---:|---|---|---:|---:|---|---|"]
    rev = out[out["confianca"] != "ALTA"].sort_values("registros_fila", ascending=False)
    for _, r in rev.iterrows():
        sug = f"{r.cnes} — {r.nome_cnes} — {r.municipio_cnes}" if r.cnes else "—"
        seg = f"{r.cnes_2} — {r.nome_cnes_2} — {r.municipio_cnes_2}" if r.cnes_2 else "—"
        L.append(f"| {r.nome_fila} | {r.registros_fila} | {r.confianca} | {sug} | {r.score} | {r.margem} | {seg} | |")
    L += ["", "## Casados com confiança ALTA (conferência rápida)", "",
          "| Nome na fila | Registros | CNES | Nome no CNES | Município |", "|---|---:|---|---|---|"]
    for _, r in out[out["confianca"] == "ALTA"].sort_values("registros_fila", ascending=False).iterrows():
        L.append(f"| {r.nome_fila} | {r.registros_fila} | {r.cnes} | {r.nome_cnes} | {r.municipio_cnes} |")
    RELATORIO.write_text("\n".join(L) + "\n", encoding="utf-8")
    log.info("Relatório: %s", RELATORIO)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DB_PADRAO)
    ap.add_argument("--relatorio", action="store_true", help=f"escreve {RELATORIO.relative_to(REPO)}")
    a = ap.parse_args()
    print(gerar(a.db, a.relatorio))
