"""
Capacidade instalada por estabelecimento (CNES) no Ceará — a partir dos arquivos já baixados
por coleta_datasus.py (ST, LT, HB da competência mais recente + TAB_CNES auxiliar).

Saída (dados públicos institucionais, sem pacientes):
    ~/PredmedDados/datasus/processado/cnes_capacidade.csv          (última competência)
    ~/PredmedDados/datasus/processado/cnes_capacidade_AAAAMM.csv   (histórico)

Campos principais (fonte e significado em docs/dados/datasus-cnes-sih.md):
    salas_cirurgicas            ST.QTINST31  sala de cirurgia do centro cirúrgico
    salas_recuperacao           ST.QTINST32
    leitos_recuperacao          ST.QTLEIT32
    salas_cirurgia_ambulatorial ST.QTINST33 (centro cirúrgico) + ST.QTINST30 (ambulatório)
    salas_cirurgia_obstetrica   ST.QTINST37 (centro obstétrico)
    leitos_cirurgicos_exist/sus LT, TP_LEITO = 1 (Cirúrgico), QT_EXIST / QT_SUS
    leitos_total_exist/sus      LT, todos os tipos
    leitos_complementares_exist LT, TP_LEITO = 3 (UTI/UCI etc.)
    habilitacoes                HB vigentes (CMPT_FIM >= competência), descrição via HABILITA.DBF

Estabelecimentos de pessoa física (PF_PJ = 1) têm o nome omitido (nome de profissional).

Uso:
    backend/venv/bin/python backend/_SCRIPTS/cnes_capacidade.py
    backend/venv/bin/python backend/_SCRIPTS/cnes_capacidade.py --competencia 2608
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

DADOS_DIR = Path(os.getenv("PREDMED_DADOS_DIR", Path.home() / "PredmedDados"))
RAIZ = DADOS_DIR / "datasus"
CNES_DIR = RAIZ / "cnes"
AUX = CNES_DIR / "auxiliar"
SAIDA = RAIZ / "processado"

# Tipos de estabelecimento que podem executar cirurgia (TP_ESTAB.CNV)
TIPOS_CIRURGICOS = {"05", "07", "15", "62", "36", "04", "20", "21"}

# Palavras-chave (descrição da habilitação) → marcador usado pela priorização/redistribuição
MARCADORES_HAB = {
    "hab_oncologia": r"ONCOLOG|UNACON|CACON|RADIOTERAPIA",
    "hab_cardiovascular": r"CARDIOVASCULAR|CARDIOLOGIA INTERVENCIONISTA",
    "hab_traumato_ortopedia": r"TRAUMATO",
    "hab_neurocirurgia": r"NEUROCIRURG",
    "hab_oftalmologia": r"OFTALMO",
    "hab_bariatrica": r"BARIATRIC|OBESIDADE",
    "hab_transplante": r"TRANSPLANTE",
    "hab_videocirurgia": r"VIDEOCIRURG",
    "hab_uti_adulto": r"UTI (?:I|II|III) ADULTO",
    "hab_pnrf_eletivas": r"REDUCAO DE FILAS DE CIRURGIAS ELETIVAS",
}

log = logging.getLogger("cnes_capacidade")


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().strip()


def ler_cnv(caminho: Path) -> dict[str, str]:
    """Lê um .cnv do TabWin (código → rótulo). Considera listas 'a,b,c'; ignora faixas 'a-b'."""
    mapa: dict[str, str] = {}
    for ln in caminho.read_text(encoding="latin-1").splitlines()[1:]:
        partes = ln.rstrip().rsplit(None, 1)
        if len(partes) < 2:
            continue
        esquerda, codigos = partes
        m = re.match(r"^\s*\d+\s+(.*)$", esquerda)
        rotulo = (m.group(1) if m else esquerda).strip()
        for c in codigos.split(","):
            c = c.strip()
            if c and "-" not in c:
                mapa[c] = rotulo
    return mapa


def mapa_cir_ads() -> dict[str, str]:
    """Nome do município (sem acento) → 'CIR <sede da ADS>' usado no PREDMED (gerador_CIR_ceara.py)."""
    try:
        from gerador_CIR_ceara import CIR_OFICIAL
        return CIR_OFICIAL
    except Exception:  # noqa: BLE001
        return {}


def ultima_competencia(grupo: str) -> str:
    arqs = sorted((CNES_DIR / grupo).glob(f"{grupo}CE*.dbc"))
    if not arqs:
        raise FileNotFoundError(f"Nenhum {grupo}CE*.dbc em {CNES_DIR / grupo} — rode coleta_datasus.py")
    return arqs[-1].name[4:8]


def natureza_grupo(nat_jur: str) -> str:
    return {"1": "PUBLICO", "2": "PRIVADO", "3": "SEM FINS LUCRATIVOS", "4": "PESSOA FISICA"}.get(
        str(nat_jur)[:1], "NAO INFORMADO")


def gerar(competencia: str | None = None) -> Path:
    from coleta_datasus import ler_dbc
    from dbfread import DBF

    aamm = competencia or ultima_competencia("ST")
    log.info("Capacidade CNES — competência 20%s", aamm)
    st = ler_dbc(CNES_DIR / "ST" / f"STCE{aamm}.dbc")
    lt = ler_dbc(CNES_DIR / "LT" / f"LTCE{aamm}.dbc")
    hb_path = CNES_DIR / "HB" / f"HBCE{aamm}.dbc"
    hb = ler_dbc(hb_path) if hb_path.exists() else pd.DataFrame(columns=["CNES", "SGRUPHAB", "CMPT_FIM"])

    def num(s):
        return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

    base = pd.DataFrame({
        "competencia": f"20{aamm[:2]}-{aamm[2:]}",
        "cnes": st["CNES"].astype(str).str.zfill(7),
        "codufmun": st["CODUFMUN"].astype(str),
        "tp_unid": st["TP_UNID"].astype(str),
        "pf_pj": st["PF_PJ"].astype(str),
        "nat_jur": st["NAT_JUR"].astype(str),
        "esfera_adm": st["ESFERA_A"].astype(str),
        "vinculo_sus": st["VINC_SUS"].astype(str) == "1",
        "centro_cirurgico": st["CENTRCIR"].astype(str) == "1",
        "salas_cirurgicas": num(st["QTINST31"]),
        "salas_recuperacao": num(st["QTINST32"]),
        "leitos_recuperacao": num(st["QTLEIT32"]),
        "salas_cirurgia_ambulatorial": num(st["QTINST33"]) + num(st["QTINST30"]),
        "salas_pequena_cirurgia": num(st["QTINST13"]) + num(st["QTINST24"]),
        "salas_cirurgia_obstetrica": num(st["QTINST37"]),
        "leitos_cirurgicos_st": num(st["QTLEITP1"]),
    })

    lt = lt.assign(cnes=lt["CNES"].astype(str).str.zfill(7), QT_EXIST=num(lt["QT_EXIST"]),
                   QT_SUS=num(lt["QT_SUS"]), TP_LEITO=lt["TP_LEITO"].astype(str))

    def agg(df, pref):
        return df.groupby("cnes")[["QT_EXIST", "QT_SUS"]].sum().rename(
            columns={"QT_EXIST": f"{pref}_exist", "QT_SUS": f"{pref}_sus"})

    leitos = agg(lt[lt.TP_LEITO == "1"], "leitos_cirurgicos").join(agg(lt, "leitos_total"), how="outer")
    leitos = leitos.join(agg(lt[lt.TP_LEITO == "3"], "leitos_complementares"), how="outer").fillna(0).astype(int)
    base = base.merge(leitos, left_on="cnes", right_index=True, how="left")
    for c in leitos.columns:
        base[c] = base[c].fillna(0).astype(int)

    # Habilitações vigentes na competência
    hab_desc = {}
    if (AUX / "DBF" / "HABILITA.DBF").exists():
        hab_desc = {r["CD_HABILIT"]: r["DS_HABIL"].strip()
                    for r in DBF(AUX / "DBF" / "HABILITA.DBF", encoding="latin-1")}
    hb = hb.assign(cnes=hb["CNES"].astype(str).str.zfill(7))
    hb = hb[hb["CMPT_FIM"].astype(str) >= f"20{aamm}"]
    hb = hb.assign(desc=hb["SGRUPHAB"].map(lambda c: hab_desc.get(c, f"COD {c}")))
    habs = hb.groupby("cnes")["desc"].apply(lambda s: " | ".join(sorted(set(s))))
    base["habilitacoes"] = base["cnes"].map(habs).fillna("")
    base["n_habilitacoes"] = base["cnes"].map(hb.groupby("cnes").size()).fillna(0).astype(int)
    for col, rx in MARCADORES_HAB.items():
        base[col] = base["habilitacoes"].str.contains(rx, regex=True)

    # Nomes (CADGERCE) — omite nome de estabelecimento de pessoa física
    cad = pd.DataFrame(iter(DBF(AUX / "DBF" / "CADGERCE.dbf", encoding="latin-1")))[["CNES", "FANTASIA", "RAZ_SOCI"]]
    cad["CNES"] = cad["CNES"].astype(str).str.zfill(7)
    cad = cad.drop_duplicates("CNES", keep="last").set_index("CNES")
    base["nome_fantasia"] = base["cnes"].map(cad["FANTASIA"]).fillna("").str.strip()
    base["razao_social"] = base["cnes"].map(cad["RAZ_SOCI"]).fillna("").str.strip()
    base.loc[base["pf_pj"] == "1", ["nome_fantasia", "razao_social"]] = "(pessoa fisica - omitido)"

    # Território
    municip = ler_cnv(AUX / "CNV" / "ce_municip.cnv")
    regsaud = ler_cnv(AUX / "CNV" / "ce_regsaud.cnv")
    macro = ler_cnv(AUX / "CNV" / "ce_macsaud.cnv")
    cir_ads = mapa_cir_ads()
    base["municipio"] = base["codufmun"].map(lambda c: re.sub(r"^\d+\s+", "", municip.get(c, "")))
    base["regiao_saude_cnes"] = base["codufmun"].map(regsaud).fillna("")
    base["macrorregiao_cnes"] = base["codufmun"].map(macro).fillna("")
    base["cir_ads_predmed"] = base["municipio"].map(lambda m: cir_ads.get(sem_acento(m), "DESCONHECIDO"))

    tipos = ler_cnv(AUX / "CNV" / "TP_ESTAB.CNV")
    base["tipo_unidade"] = base["tp_unid"].map(tipos).fillna("")
    base["natureza"] = base["nat_jur"].map(natureza_grupo)

    base["relevante_cirurgia"] = (base["centro_cirurgico"] | (base["salas_cirurgicas"] > 0)
                                  | (base["leitos_cirurgicos_exist"] > 0) | base["tp_unid"].isin(TIPOS_CIRURGICOS)
                                  | (base["salas_cirurgia_ambulatorial"] > 0))

    ordem = ["competencia", "cnes", "nome_fantasia", "razao_social", "codufmun", "municipio",
             "cir_ads_predmed", "regiao_saude_cnes", "macrorregiao_cnes", "tp_unid", "tipo_unidade",
             "natureza", "nat_jur", "esfera_adm", "vinculo_sus", "relevante_cirurgia", "centro_cirurgico",
             "salas_cirurgicas", "salas_recuperacao", "leitos_recuperacao", "salas_cirurgia_ambulatorial",
             "salas_pequena_cirurgia", "salas_cirurgia_obstetrica", "leitos_cirurgicos_st",
             "leitos_cirurgicos_exist", "leitos_cirurgicos_sus", "leitos_total_exist", "leitos_total_sus",
             "leitos_complementares_exist", "leitos_complementares_sus", "n_habilitacoes",
             *MARCADORES_HAB.keys(), "habilitacoes"]
    base = base[ordem].sort_values("cnes")

    SAIDA.mkdir(parents=True, exist_ok=True)
    hist = SAIDA / f"cnes_capacidade_20{aamm}.csv"
    base.to_csv(hist, index=False)
    base.to_csv(SAIDA / "cnes_capacidade.csv", index=False)
    log.info("  %s estabelecimentos; %s relevantes p/ cirurgia; %s com centro cirúrgico; %s salas cirúrgicas; "
             "%s leitos cirúrgicos (%s SUS)", len(base), int(base.relevante_cirurgia.sum()),
             int(base.centro_cirurgico.sum()), int(base.salas_cirurgicas.sum()),
             int(base.leitos_cirurgicos_exist.sum()), int(base.leitos_cirurgicos_sus.sum()))
    return hist


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", help="AAMM (padrão: a mais recente baixada)")
    print(gerar(ap.parse_args().competencia))
