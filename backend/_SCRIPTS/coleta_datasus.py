"""
Coleta mensal de dados públicos do DATASUS para o Ceará (CNES e SIH-RD).

Fontes (FTP público do DATASUS, verificadas em 28/09/2026):
    SIH-RD  ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RDCEaamm.dbc
    CNES    ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/{ST,LT,HB,SR,EQ}/{GRP}CEaamm.dbc
    CNES aux ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Auxiliar/TAB_CNES.zip
             (nomes dos estabelecimentos — CADGERCE.dbf — e tabelas de conversão .cnv)

O que o script faz:
1. Lista o FTP e descobre as competências disponíveis.
2. Baixa só o que falta ou mudou (compara tamanho e data de modificação do FTP com o estado local).
   Grava em .part e renomeia — um arquivo interrompido nunca é tomado como válido.
3. Valida cada .dbc (lê o arquivo, confere colunas esperadas e a competência, conta registros).
   Arquivo inválido é removido e a execução termina com erro.
4. Acrescenta ao manifesto (JSONL) apenas números agregados: registros por competência,
   tamanho, sha256. Nenhuma linha de AIH/paciente é impressa ou registrada.
5. Após o CNES, gera a tabela de capacidade instalada (cnes_capacidade.py) e o casamento
   nome da fila → CNES (casar_estabelecimentos_cnes.py), ambos em CSV fora do repositório.

Os dados brutos ficam em ~/PredmedDados/datasus/ (PREDMED_DADOS_DIR), fora do git.
O script NÃO carrega nada em banco. Ver docs/dados/datasus-cnes-sih.md.

Uso:
    backend/venv/bin/python backend/_SCRIPTS/coleta_datasus.py                # CNES (última competência) + SIH novo
    backend/venv/bin/python backend/_SCRIPTS/coleta_datasus.py --so-sih
    backend/venv/bin/python backend/_SCRIPTS/coleta_datasus.py --so-cnes --cnes-competencias 3
    backend/venv/bin/python backend/_SCRIPTS/coleta_datasus.py --verificar    # só lista o FTP, não baixa
"""
from __future__ import annotations

import argparse
import ftplib
import hashlib
import json
import logging
import os
import sys
import tempfile
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "SIH"))

FTP_HOST = "ftp.datasus.gov.br"
DIR_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
DIR_CNES = "/dissemin/publicos/CNES/200508_/Dados"
DIR_CNES_AUX = "/dissemin/publicos/CNES/200508_/Auxiliar"
UF = "CE"

GRUPOS_CNES = {
    # grupo: colunas mínimas esperadas
    "ST": {"CNES", "CODUFMUN", "VINC_SUS", "TP_UNID", "CENTRCIR", "QTINST31", "QTLEITP1", "COMPETEN"},
    "LT": {"CNES", "CODUFMUN", "TP_LEITO", "CODLEITO", "QT_EXIST", "QT_SUS", "COMPETEN"},
    "HB": {"CNES", "SGRUPHAB", "CMPT_INI", "CMPT_FIM", "COMPETEN"},
    "SR": {"CNES", "SERV_ESP", "CLASS_SR", "AMB_SUS", "HOSP_SUS", "COMPETEN"},
    "EQ": {"CNES", "TIPEQUIP", "CODEQUIP", "QT_EXIST", "QT_USO", "IND_SUS", "COMPETEN"},
}
COLUNAS_SIH = {"CNES", "ANO_CMPT", "MES_CMPT", "PROC_REA", "DT_INTER", "DT_SAIDA", "ESPEC"}

# Arquivos extraídos do TAB_CNES.zip (só tabelas de apoio; nenhuma é de pessoa física)
AUX_EXTRAIR = {
    "DBF/CADGERCE.dbf", "DBF/HABILITA.DBF", "DBF/S_CLASSEA.dbf",
    "CNV/ce_regsaud.cnv", "CNV/ce_macsaud.cnv", "CNV/ce_municip.cnv", "CNV/TP_ESTAB.CNV",
    "CNV/NATJUR.CNV", "CNV/EsferAdm.CNV", "CNV/Esp_leit.CNV", "CNV/tip1leit.cnv",
    "Docs/IT_CNES_201706.pdf", "Estabelecimento.def",
}

DADOS_DIR = Path(os.getenv("PREDMED_DADOS_DIR", Path.home() / "PredmedDados"))
RAIZ = DADOS_DIR / "datasus"
MANIFESTO = RAIZ / "manifesto.jsonl"
ESTADO = RAIZ / "estado.json"

log = logging.getLogger("coleta_datasus")


class ArquivoInvalido(Exception):
    pass


# ── FTP ─────────────────────────────────────────────────────────
class FTPDatasus:
    def __init__(self, tentativas: int = 3):
        self.tentativas = tentativas
        self.ftp: ftplib.FTP | None = None

    def conectar(self):
        for i in range(self.tentativas):
            try:
                self.ftp = ftplib.FTP(FTP_HOST, timeout=120)
                self.ftp.login()
                return
            except Exception as e:  # noqa: BLE001
                log.warning("Falha ao conectar no FTP (%s/%s): %s", i + 1, self.tentativas, e)
                time.sleep(10 * (i + 1))
        raise ConnectionError("FTP do DATASUS indisponível")

    def _op(self, fn, *a):
        for i in range(self.tentativas):
            try:
                if self.ftp is None:
                    self.conectar()
                return fn(*a)
            except (ftplib.error_temp, OSError, EOFError) as e:
                log.warning("Erro FTP (%s/%s): %s", i + 1, self.tentativas, e)
                self.ftp = None
                time.sleep(10 * (i + 1))
        raise ConnectionError("Operação FTP falhou após retentativas")

    def listar(self, pasta: str) -> list[str]:
        return self._op(lambda: self.ftp.nlst(pasta))

    def info(self, caminho: str) -> dict:
        def _i():
            tam = self.ftp.size(caminho)
            try:
                mdtm = self.ftp.voidcmd(f"MDTM {caminho}").split()[-1]
            except ftplib.all_errors:
                mdtm = None
            return {"bytes": tam, "mdtm": mdtm}
        return self._op(_i)

    def baixar(self, caminho: str, destino: Path):
        destino.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_suffix(destino.suffix + ".part")

        def _b():
            with open(parcial, "wb") as fh:
                self.ftp.retrbinary(f"RETR {caminho}", fh.write, blocksize=1 << 16)
        self._op(_b)
        parcial.replace(destino)

    def fechar(self):
        try:
            if self.ftp:
                self.ftp.quit()
        except Exception:  # noqa: BLE001
            pass


# ── Utilidades ──────────────────────────────────────────────────
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_estado() -> dict:
    return json.loads(ESTADO.read_text()) if ESTADO.exists() else {}


def salvar_estado(estado: dict):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, indent=1, sort_keys=True))
    tmp.replace(ESTADO)


def registrar(linha: dict):
    MANIFESTO.parent.mkdir(parents=True, exist_ok=True)
    linha = {"registrado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), **linha}
    with open(MANIFESTO, "a") as fh:
        fh.write(json.dumps(linha, ensure_ascii=False) + "\n")


def ler_dbc(caminho: Path, colunas: list[str] | None = None):
    """Lê .dbc (pyreaddbc + dbfread, já no venv). Retorna DataFrame (só colunas pedidas)."""
    import pandas as pd
    from dbfread import DBF
    from pyreaddbc import dbc2dbf

    fd, dbf = tempfile.mkstemp(suffix=".dbf")
    os.close(fd)
    try:
        dbc2dbf(str(caminho), dbf)
        tabela = DBF(dbf, encoding="latin-1", load=False)
        campos = tabela.field_names
        if colunas:
            usar = [c for c in colunas if c in campos]
            df = pd.DataFrame(({c: r[c] for c in usar} for r in tabela), columns=usar)
        else:
            df = pd.DataFrame(iter(tabela))
        df.attrs["campos"] = campos
        return df
    finally:
        os.remove(dbf)


def aamm_para_competencia(aamm: str) -> str:
    if aamm == "0000":  # tabelas auxiliares (TAB_CNES.zip) não têm competência
        return "auxiliar"
    return f"20{aamm[:2]}-{aamm[2:]}"


# ── Validação ───────────────────────────────────────────────────
def validar_sih(caminho: Path, aamm: str) -> dict:
    df = ler_dbc(caminho, ["ANO_CMPT", "MES_CMPT", "DT_INTER", "PROC_REA", "CNES"])
    faltando = COLUNAS_SIH - set(df.attrs["campos"])
    if faltando:
        raise ArquivoInvalido(f"colunas ausentes: {sorted(faltando)}")
    if len(df) == 0:
        raise ArquivoInvalido("arquivo sem registros")
    cmpt = Counter(f"{a}-{m}" for a, m in zip(df["ANO_CMPT"], df["MES_CMPT"]))
    esperado = f"20{aamm[:2]}-{aamm[2:]}"
    principal, n = cmpt.most_common(1)[0]
    if principal != esperado:
        raise ArquivoInvalido(f"competência predominante {principal} ≠ {esperado}")
    dt = df["DT_INTER"].astype(str).str[:6]
    return {
        "registros": int(len(df)),
        "registros_competencia_esperada": int(n),
        "estabelecimentos": int(df["CNES"].nunique()),
        "internacao_min": f"{dt.min()[:4]}-{dt.min()[4:]}",
        "internacao_max": f"{dt.max()[:4]}-{dt.max()[4:]}",
        "cirurgicos_grupo04": int(df["PROC_REA"].astype(str).str.startswith("04").sum()),
    }


def validar_cnes(caminho: Path, grupo: str, aamm: str) -> dict:
    cols = sorted(GRUPOS_CNES[grupo] | ({"QTLEITP1"} if grupo == "ST" else set()))
    df = ler_dbc(caminho, cols)
    faltando = GRUPOS_CNES[grupo] - set(df.attrs["campos"])
    if faltando:
        raise ArquivoInvalido(f"colunas ausentes: {sorted(faltando)}")
    if len(df) == 0:
        raise ArquivoInvalido("arquivo sem registros")
    compet = df["COMPETEN"].astype(str).str.strip()
    esperado = f"20{aamm}"
    if not (compet == esperado).all():
        raise ArquivoInvalido(f"COMPETEN diferente de {esperado} em {int((compet != esperado).sum())} linhas")
    extra = {"registros": int(len(df)), "estabelecimentos": int(df["CNES"].nunique())}
    if grupo == "ST":
        num = lambda c: df[c].apply(lambda v: int(v or 0))  # noqa: E731
        extra["com_centro_cirurgico"] = int((df["CENTRCIR"].astype(str) == "1").sum())
        extra["salas_cirurgicas_total"] = int(num("QTINST31").sum())
        extra["leitos_cirurgicos_total"] = int(num("QTLEITP1").sum())
        extra["vinculo_sus"] = int((df["VINC_SUS"].astype(str) == "1").sum())
    return extra


# ── Rotinas por fonte ───────────────────────────────────────────
def precisa_baixar(chave: str, remoto: dict, local: Path, estado: dict) -> bool:
    if not local.exists():
        return True
    anterior = estado.get(chave)
    if not anterior:
        return local.stat().st_size != remoto["bytes"]
    return anterior.get("bytes") != remoto["bytes"] or (
        remoto.get("mdtm") and anterior.get("mdtm") and anterior["mdtm"] != remoto["mdtm"])


def processar_arquivo(ftp: FTPDatasus, estado: dict, fonte: str, remoto_path: str, local: Path,
                      aamm: str, validar, verificar: bool) -> dict | None:
    chave = f"{fonte}/{local.name}"
    info = ftp.info(remoto_path)
    if not precisa_baixar(chave, info, local, estado):
        if chave in estado:
            return None
        acao = "validado_existente"  # arquivo já presente (mesmo tamanho), ainda sem registro
    else:
        acao = "atualizado" if local.exists() else "baixado"
    if verificar:
        log.info("[verificar] %s: %s (%s bytes)", local.name, acao, info["bytes"])
        return {"arquivo": local.name, "acao": f"{acao} (simulado)"}
    if acao != "validado_existente":
        log.info("Baixando %s (%.1f MB)", local.name, info["bytes"] / 1e6)
        ftp.baixar(remoto_path, local)
    if local.stat().st_size != info["bytes"]:
        local.unlink()
        raise ArquivoInvalido(f"{local.name}: tamanho diferente do FTP")
    try:
        resumo = validar(local)
    except Exception as e:
        local.unlink(missing_ok=True)
        raise ArquivoInvalido(f"{local.name}: {e}") from e
    linha = {"fonte": fonte, "arquivo": local.name, "competencia": aamm_para_competencia(aamm),
             "acao": acao, "bytes": info["bytes"], "mdtm_ftp": info.get("mdtm"),
             "sha256": sha256(local), **resumo}
    estado[chave] = {k: linha[k] for k in ("bytes", "sha256", "competencia", "registros")} | {
        "mdtm": info.get("mdtm")}
    salvar_estado(estado)
    registrar(linha)
    log.info("  ok: %s registros", f"{resumo['registros']:,}")
    return linha


def coletar_sih(ftp: FTPDatasus, estado: dict, inicio: str, verificar: bool) -> list[dict]:
    nomes = sorted(Path(n).name for n in ftp.listar(DIR_SIH))
    alvo = [n for n in nomes if n.upper().startswith(f"RD{UF}") and n.lower().endswith(".dbc")
            and aamm_para_competencia(n[4:8]) >= inicio]
    log.info("SIH-RD %s: %s competências no FTP a partir de %s (última: %s)",
             UF, len(alvo), inicio, alvo[-1] if alvo else "-")
    feitos = []
    for n in alvo:
        aamm = n[4:8]
        r = processar_arquivo(ftp, estado, "SIH-RD", f"{DIR_SIH}/{n}", RAIZ / "sih" / "RD" / n,
                              aamm, lambda p, a=aamm: validar_sih(p, a), verificar)
        if r:
            feitos.append(r)
    return feitos


def coletar_cnes(ftp: FTPDatasus, estado: dict, n_competencias: int, verificar: bool) -> list[dict]:
    feitos = []
    for grupo in GRUPOS_CNES:
        nomes = sorted(Path(n).name for n in ftp.listar(f"{DIR_CNES}/{grupo}")
                       if Path(n).name.upper().startswith(f"{grupo}{UF}"))
        for n in nomes[-n_competencias:]:
            aamm = n[4:8]
            r = processar_arquivo(ftp, estado, f"CNES-{grupo}", f"{DIR_CNES}/{grupo}/{n}",
                                  RAIZ / "cnes" / grupo / n, aamm,
                                  lambda p, g=grupo, a=aamm: validar_cnes(p, g, a), verificar)
            if r:
                feitos.append(r)
    # Tabelas auxiliares (nomes dos estabelecimentos, regiões de saúde, códigos)
    zip_local = RAIZ / "cnes" / "auxiliar" / "TAB_CNES.zip"

    def _validar_zip(p: Path) -> dict:
        with zipfile.ZipFile(p) as z:
            presentes = set(z.namelist())
            faltam = AUX_EXTRAIR - presentes
            if "DBF/CADGERCE.dbf" in faltam:
                raise ArquivoInvalido("CADGERCE.dbf ausente no TAB_CNES.zip")
            for membro in AUX_EXTRAIR & presentes:
                z.extract(membro, zip_local.parent)
        from dbfread import DBF
        cad = DBF(zip_local.parent / "DBF" / "CADGERCE.dbf", encoding="latin-1", load=False)
        n = sum(1 for _ in cad)
        return {"registros": n, "auxiliares_ausentes": sorted(faltam)}

    r = processar_arquivo(ftp, estado, "CNES-AUX", f"{DIR_CNES_AUX}/TAB_CNES.zip", zip_local,
                          "0000", _validar_zip, verificar)
    if r:
        feitos.append(r)
    return feitos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so-sih", action="store_true")
    ap.add_argument("--so-cnes", action="store_true")
    ap.add_argument("--sih-inicio", default="2025-01", help="primeira competência SIH (AAAA-MM)")
    ap.add_argument("--cnes-competencias", type=int, default=1, help="quantas competências CNES recentes")
    ap.add_argument("--sem-processar", action="store_true", help="não gera capacidade/casamento")
    ap.add_argument("--verificar", action="store_true", help="só lista o que seria baixado")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    RAIZ.mkdir(parents=True, exist_ok=True)
    estado = carregar_estado()
    ftp = FTPDatasus()
    ftp.conectar()
    erros = 0
    feitos: list[dict] = []
    try:
        if not args.so_cnes:
            try:
                feitos += coletar_sih(ftp, estado, args.sih_inicio, args.verificar)
            except (ArquivoInvalido, ConnectionError) as e:
                log.error("SIH: %s", e)
                erros += 1
        if not args.so_sih:
            try:
                feitos += coletar_cnes(ftp, estado, args.cnes_competencias, args.verificar)
            except (ArquivoInvalido, ConnectionError) as e:
                log.error("CNES: %s", e)
                erros += 1
    finally:
        ftp.fechar()

    cnes_novo = any(f.get("arquivo", "").startswith(("ST", "LT", "HB", "SR", "TAB_CNES")) for f in feitos)
    if not args.verificar and not args.sem_processar and not args.so_sih and (
            cnes_novo or not (RAIZ / "processado" / "cnes_capacidade.csv").exists()):
        try:
            import cnes_capacidade
            import casar_estabelecimentos_cnes
            cnes_capacidade.gerar()
            casar_estabelecimentos_cnes.gerar()
        except Exception as e:  # noqa: BLE001
            log.error("Processamento pós-coleta falhou: %s", e)
            erros += 1

    log.info("Fim: %s arquivo(s) novos/atualizados, %s erro(s).", len(feitos), erros)
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
