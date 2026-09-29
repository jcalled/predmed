"""
PREDMED — Importador de Dados Reais
IntegraSUS (fila cirúrgica) + DATASUS (capacidade hospitalar) + CNES (cadastro)
"""
import pandas as pd
import os
import glob
import re
import unicodedata
import json
from collections import Counter
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from database import (
    PacienteFila,
    CapacidadeHospital,
    HospitalCirMap,
    Hospital,
    HospitalAlias,
    HospitalEspecialidade,
)
from datetime import datetime


class ImportacaoInvalida(ValueError):
    """Arquivo de importação rejeitado na validação; a base anterior é mantida."""


# ═══════════════════════════════════════════════════════════════════════
# CIR OFICIAL — Fonte: SESA-CE lista_sr_ads_20220203.pdf
# Todos os 184 municípios do Ceará mapeados para sua CIR/ADS
# ═══════════════════════════════════════════════════════════════════════

CIR_OFICIAL = {
    # CIR Acaraú
    "ACARAU": "CIR Acaraú",
    "ACARAÚ": "CIR Acaraú",
    "BELA CRUZ": "CIR Acaraú",
    "CRUZ": "CIR Acaraú",
    "ITAREMA": "CIR Acaraú",
    "JIJOCA DE JERICOACOARA": "CIR Acaraú",
    "MARCO": "CIR Acaraú",
    "MORRINHOS": "CIR Acaraú",

    # CIR Aracati
    "ARACATI": "CIR Aracati",
    "FORTIM": "CIR Aracati",
    "ICAPUI": "CIR Aracati",
    "ITAICABA": "CIR Aracati",

    # CIR Baturité
    "ARACOIABA": "CIR Baturité",
    "ARATUBA": "CIR Baturité",
    "BATURITE": "CIR Baturité",
    "CAPISTRANO": "CIR Baturité",
    "GUARAMIRANGA": "CIR Baturité",
    "ITAPIUNA": "CIR Baturité",
    "MULUNGU": "CIR Baturité",
    "PACOTI": "CIR Baturité",

    # CIR Brejo Santo
    "ABAIARA": "CIR Brejo Santo",
    "AURORA": "CIR Brejo Santo",
    "BARRO": "CIR Brejo Santo",
    "BREJO SANTO": "CIR Brejo Santo",
    "JATI": "CIR Brejo Santo",
    "MAURITI": "CIR Brejo Santo",
    "MILAGRES": "CIR Brejo Santo",
    "PENAFORTE": "CIR Brejo Santo",
    "PORTEIRAS": "CIR Brejo Santo",

    # CIR Camocim
    "BARROQUINHA": "CIR Camocim",
    "CAMOCIM": "CIR Camocim",
    "CHAVAL": "CIR Camocim",
    "GRANJA": "CIR Camocim",
    "MARTINOPOLE": "CIR Camocim",

    # CIR Canindé
    "BOA VIAGEM": "CIR Canindé",
    "CANINDE": "CIR Canindé",
    "CARIDADE": "CIR Canindé",
    "ITATIRA": "CIR Canindé",
    "MADALENA": "CIR Canindé",
    "PARAMOTI": "CIR Canindé",

    # CIR Cascavel
    "BEBERIBE": "CIR Cascavel",
    "CASCAVEL": "CIR Cascavel",
    "CHOROZINHO": "CIR Cascavel",
    "HORIZONTE": "CIR Cascavel",
    "OCARA": "CIR Cascavel",
    "PACAJUS": "CIR Cascavel",
    "PINDORETAMA": "CIR Cascavel",

    # CIR Caucaia
    "APUIARES": "CIR Caucaia",
    "CAUCAIA": "CIR Caucaia",
    "GENERAL SAMPAIO": "CIR Caucaia",
    "ITAPAJE": "CIR Caucaia",
    "PARACURU": "CIR Caucaia",
    "PARAIPABA": "CIR Caucaia",
    "PENTECOSTE": "CIR Caucaia",
    "SAO GONCALO DO AMARANTE": "CIR Caucaia",
    "SAO LUIS DO CURU": "CIR Caucaia",
    "TEJUCOCA": "CIR Caucaia",

    # CIR Crateús
    "ARARENDA": "CIR Crateús",
    "CRATEUS": "CIR Crateús",
    "INDEPENDENCIA": "CIR Crateús",
    "IPAPORANGA": "CIR Crateús",
    "IPUEIRAS": "CIR Crateús",
    "MONSENHOR TABOSA": "CIR Crateús",
    "NOVA RUSSAS": "CIR Crateús",
    "NOVO ORIENTE": "CIR Crateús",
    "PORANGA": "CIR Crateús",
    "QUITERIANOPOLIS": "CIR Crateús",
    "TAMBORIL": "CIR Crateús",

    # CIR Crato
    "ALTANEIRA": "CIR Crato",
    "ANTONINA DO NORTE": "CIR Crato",
    "ARARIPE": "CIR Crato",
    "ASSARE": "CIR Crato",
    "CAMPOS SALES": "CIR Crato",
    "CRATO": "CIR Crato",
    "FARIAS BRITO": "CIR Crato",
    "NOVA OLINDA": "CIR Crato",
    "POTENGI": "CIR Crato",
    "SALITRE": "CIR Crato",
    "SANTANA DO CARIRI": "CIR Crato",
    "TARRAFAS": "CIR Crato",

    # CIR Fortaleza
    "AQUIRAZ": "CIR Fortaleza",
    "EUSEBIO": "CIR Fortaleza",
    "FORTALEZA": "CIR Fortaleza",
    "ITAITINGA": "CIR Fortaleza",

    # CIR Icó
    "BAIXIO": "CIR Icó",
    "CEDRO": "CIR Icó",
    "ICO": "CIR Icó",
    "IPAUMIRIM": "CIR Icó",
    "LAVRAS DA MANGABEIRA": "CIR Icó",
    "OROS": "CIR Icó",
    "UMARI": "CIR Icó",
    "VARZEA ALEGRE": "CIR Icó",

    # CIR Iguatu
    "ACOPIARA": "CIR Iguatu",
    "CARIUS": "CIR Iguatu",
    "CATARINA": "CIR Iguatu",
    "DEPUTADO IRAPUAN PINHEIRO": "CIR Iguatu",
    "IGUATU": "CIR Iguatu",
    "JUCAS": "CIR Iguatu",
    "MOMBACA": "CIR Iguatu",
    "PIQUET CARNEIRO": "CIR Iguatu",
    "QUIXELO": "CIR Iguatu",
    "SABOEIRO": "CIR Iguatu",

    # CIR Itapipoca
    "AMONTADA": "CIR Itapipoca",
    "ITAPIPOCA": "CIR Itapipoca",
    "MIRAIMA": "CIR Itapipoca",
    "TRAIRI": "CIR Itapipoca",
    "TURURU": "CIR Itapipoca",
    "UMIRIM": "CIR Itapipoca",
    "URUBURETAMA": "CIR Itapipoca",

    # CIR Juazeiro do Norte
    "BARBALHA": "CIR Juazeiro do Norte",
    "CARIRIACU": "CIR Juazeiro do Norte",
    "GRANJEIRO": "CIR Juazeiro do Norte",
    "JARDIM": "CIR Juazeiro do Norte",
    "JUAZEIRO DO NORTE": "CIR Juazeiro do Norte",
    "MISSAO VELHA": "CIR Juazeiro do Norte",

    # CIR Limoeiro do Norte
    "ALTO SANTO": "CIR Limoeiro do Norte",
    "ERERE": "CIR Limoeiro do Norte",
    "IRACEMA": "CIR Limoeiro do Norte",
    "JAGUARIBARA": "CIR Limoeiro do Norte",
    "JAGUARIBE": "CIR Limoeiro do Norte",
    "LIMOEIRO DO NORTE": "CIR Limoeiro do Norte",
    "PEREIRO": "CIR Limoeiro do Norte",
    "POTIRETAMA": "CIR Limoeiro do Norte",
    "QUIXERE": "CIR Limoeiro do Norte",
    "SAO JOAO DO JAGUARIBE": "CIR Limoeiro do Norte",
    "TABULEIRO DO NORTE": "CIR Limoeiro do Norte",

    # CIR Maracanaú
    "ACARAPE": "CIR Maracanaú",
    "BARREIRA": "CIR Maracanaú",
    "GUAIUBA": "CIR Maracanaú",
    "MARACANAU": "CIR Maracanaú",
    "MARANGUAPE": "CIR Maracanaú",
    "PACATUBA": "CIR Maracanaú",
    "PALMACIA": "CIR Maracanaú",
    "REDENCAO": "CIR Maracanaú",

    # CIR Russas
    "JAGUARETAMA": "CIR Russas",
    "JAGUARUANA": "CIR Russas",
    "MORADA NOVA": "CIR Russas",
    "PALHANO": "CIR Russas",
    "RUSSAS": "CIR Russas",

    # CIR Quixadá
    "BANABUIU": "CIR Quixadá",
    "CHORO": "CIR Quixadá",
    "IBARETAMA": "CIR Quixadá",
    "IBICUITINGA": "CIR Quixadá",
    "MILHA": "CIR Quixadá",
    "PEDRA BRANCA": "CIR Quixadá",
    "QUIXADA": "CIR Quixadá",
    "QUIXERAMOBIM": "CIR Quixadá",
    "SENADOR POMPEU": "CIR Quixadá",
    "SOLONOPOLE": "CIR Quixadá",

    # CIR Sobral
    "ALCANTARAS": "CIR Sobral",
    "BOA HORA": "CIR Sobral",
    "CARIRE": "CIR Sobral",
    "CATUNDA": "CIR Sobral",
    "COREAU": "CIR Sobral",
    "FORQUILHA": "CIR Sobral",
    "FRECHEIRINHA": "CIR Sobral",
    "GRACA": "CIR Sobral",
    "GROAIRAS": "CIR Sobral",
    "HIDROLANDIA": "CIR Sobral",
    "IPU": "CIR Sobral",
    "IRAUCUBA": "CIR Sobral",
    "MASSAPE": "CIR Sobral",
    "MERUOCA": "CIR Sobral",
    "MORAUJO": "CIR Sobral",
    "MUCAMBO": "CIR Sobral",
    "PACUJA": "CIR Sobral",
    "PIRES FERREIRA": "CIR Sobral",
    "RERIUTABA": "CIR Sobral",
    "SANTA QUITERIA": "CIR Sobral",
    "SANTANA DO ACARAU": "CIR Sobral",
    "SENADOR SA": "CIR Sobral",
    "SOBRAL": "CIR Sobral",
    "URUOCA": "CIR Sobral",
    "VARJOTA": "CIR Sobral",

    # CIR Tauá
    "AIUABA": "CIR Tauá",
    "ARNEIROZ": "CIR Tauá",
    "PARAMBU": "CIR Tauá",
    "TAUA": "CIR Tauá",

    # CIR Tianguá
    "CARNAUBAL": "CIR Tianguá",
    "CROATA": "CIR Tianguá",
    "GUARACIABA DO NORTE": "CIR Tianguá",
    "IBIAPINA": "CIR Tianguá",
    "SAO BENEDITO": "CIR Tianguá",
    "TIANGUA": "CIR Tianguá",
    "UBAJARA": "CIR Tianguá",
    "VICOSA DO CEARA": "CIR Tianguá",
}
# Tabela de-para manual (pode ser usada como aliases iniciais)
HOSPITAL_ALIAS = {
    "IJF INSTITUTO DR JOSE FROTA CENTRAL":         "IJF INSTITUTO DR JOSE FROTA",
    "HOSPITAL SAO RAIMUNDO":                        "HOSPITAL SAO RAIMUNDO",
    "HIAS HOSPITAL INFANTIL ALBERT SABIN":          "HOSPITAL INFANTIL ALBERT SABIN",
    "HGF HOSPITAL GERAL DE FORTALEZA":              "HOSPITAL GERAL DE FORTALEZA",
    "HGCC HOSPITAL GERAL DR CESAR CALS":            "HOSPITAL GERAL DR CESAR CALS",
    "HOSPITAL UNIVERSITARIO WALTER CANTIDIO":       "HOSPITAL UNIVERSITARIO WALTER CANTIDIO",
    "HOSPITAL UNIVERSITARIO DO CEARA HUC":          "HOSPITAL UNIVERSITARIO DO CEARA",
    "SANTA CASA DE MISERICORDIA DE SOBRAL":         "SANTA CASA DE MISERICORDIA SOBRAL",
    "HOSPITAL REGIONAL NORTE SOBRAL":               "HOSPITAL REGIONAL NORTE",
    "HOSPITAL REGIONAL DO CARIRI":                  "HOSPITAL REGIONAL DO CARIRI",
    "HOSPITAL DISTRITAL GONZAGA MOTA JOSE WALTER":  "HOSPITAL DISTRITAL GONZAGA MOTA",
    "HOSP MATERN SANTA IZABEL ARACOIABA":           "HOSPITAL MATERNIDADE SANTA IZABEL",
    "SANTE CARIRI":                                 "SANTE CARIRI",
    "HOSPITAL GERAL DR JOSE ARCANJO NETO":          "HOSPITAL GERAL DR JOSE ARCANJO NETO",
}


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def norm(s: str) -> str:
    """Remove acentos e normaliza para uppercase"""
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().strip()


def get_cir_from_municipio(municipio: str) -> str:
    """Retorna CIR pelo município usando CIR_OFICIAL"""
    return CIR_OFICIAL.get(norm(municipio), "DESCONHECIDO")


def detect_encoding(filepath: str) -> str:
    """Detecta encoding do CSV automaticamente"""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            with open(filepath, encoding=enc) as f:
                content = f.read(2000)
            if "ï¿" not in content and "â€" not in content:
                return enc
        except Exception:
            pass
    return "latin-1"


def encontrar_hospital_por_nome(nome: str, municipio: str, db: Session, limiar: float = 0.7):
    """
    Tenta encontrar um hospital na tabela Hospital por nome e município.
    Usa a tabela de aliases e fuzzy matching.
    """
    nome_norm = norm(nome)
    mun_norm = norm(municipio)

    # 1. Busca direta na tabela de aliases
    alias = db.query(HospitalAlias).filter(HospitalAlias.alias_nome == nome).first()
    if alias and alias.cnes:
        hospital = db.query(Hospital).filter(Hospital.cnes == alias.cnes).first()
        if hospital:
            return hospital

    # 2. Busca por nome similar no mesmo município
    hospitais = db.query(Hospital).filter(Hospital.municipio.ilike(f"%{municipio}%")).all()
    melhor = None
    melhor_ratio = limiar

    for h in hospitais:
        candidatos = [h.nome_fantasia, h.razao_social] if h.razao_social else [h.nome_fantasia]
        for cand in candidatos:
            if not cand:
                continue
            cand_norm = norm(cand)
            if nome_norm in cand_norm or cand_norm in nome_norm:
                return h
            ratio = SequenceMatcher(None, nome_norm, cand_norm).ratio()
            if ratio > melhor_ratio:
                melhor_ratio = ratio
                melhor = h

    return melhor if melhor_ratio >= limiar else None


def _inferir_mun_por_nome(nome: str) -> str:
    """
    Infere município pelo nome do hospital no DATASUS.
    Usa palavras-chave do próprio nome.
    Fallback: FORTALEZA (hospitais regionais sem pista geográfica).
    """
    n = norm(nome)
    keywords = [
        ("MADALENA NUNES",      "TIANGUÁ"),
        ("TIANGUA",             "TIANGUÁ"),
        ("SOBRAL",              "SOBRAL"),
        ("CARIRI",              "JUAZEIRO DO NORTE"),
        ("JUAZEIRO",            "JUAZEIRO DO NORTE"),
        ("CRATO",               "CRATO"),
        ("BARBALHA",            "BARBALHA"),
        ("ARACOIABA",           "ARACOIABA"),
        ("ITAPIPOCA",           "ITAPIPOCA"),
        ("CAUCAIA",             "CAUCAIA"),
        ("MARACANAU",           "MARACANAÚ"),
        ("MARANGUAPE",          "MARANGUAPE"),
        ("BATURITE",            "BATURITE"),
        ("QUIXADA",             "QUIXADÁ"),
        ("SERTAO CENTRAL",      "QUIXERAMOBIM"), 
        ("QUIXERAMOBIM",        "QUIXERAMOBIM"),
        ("LIMOEIRO DO NORTE",   "LIMOEIRO DO NORTE"),
        ("RUSSAS",              "RUSSAS"),
        ("ARACATI",             "ARACATI"),
        ("CAMOCIM",             "CAMOCIM"),
        ("CRATEUS",             "CRATEÚS"),
        ("IGUATU",              "IGUATU"),
        ("BREJO SANTO",         "BREJO SANTO"),
        ("CANINDE",             "CANINDE"),
        ("TAUA",                "TAUA"),
    ]
    for keyword, municipio in keywords:
        if keyword in n:
            return municipio
    return "FORTALEZA"


# ═══════════════════════════════════════════════════════════════════════
# CNES (fonte confiável de todos os estabelecimentos)
# ═══════════════════════════════════════════════════════════════════════

def import_cnes_json(json_path: str, db: Session) -> int:
    """
    Importa JSON do CNES para tabela Hospital (substitui tudo).
    Fonte confiável: todos os estabelecimentos de saúde do Ceará.
    """
    if not os.path.exists(json_path):
        print(f"[CNES] Arquivo não encontrado: {json_path}")
        return 0

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Limpa hospitais existentes (fazemos replace completo)
    db.query(Hospital).delete()
    db.commit()

    count = 0
    batch = []
    for item in data:
        cnes = item.get("cnes", "").strip()
        if not cnes:
            continue
        nome_fantasia = item.get("noFantasia", "").strip()
        razao_social = item.get("noEmpresarial", "").strip()
        municipio = item.get("noMunicipio", "").strip()
        uf = item.get("uf", "CE")
        gestao = item.get("gestao", "")
        natureza = item.get("natJuridica", "")
        atende_sus = item.get("atendeSus", "S") == "S"
        esfera = item.get("coEsferaAdministrativa", "").strip()

        tipo = "publico" if natureza == "1" else "particular" if natureza == "2" else "outro"
        cir = get_cir_from_municipio(municipio)

        hospital = Hospital(
            cnes=cnes,
            nome_fantasia=nome_fantasia,
            razao_social=razao_social,
            municipio=municipio,
            uf=uf,
            gestao=gestao,
            natureza_juridica=natureza,
            atende_sus=atende_sus,
            esfera_administrativa=esfera,
            tipo=tipo,
            cir=cir,
            fonte="cnes",
            confiavel=True,
            is_cirurgico=False,  # ainda não sabemos
        )
        batch.append(hospital)
        count += 1
        if len(batch) >= 500:
            db.bulk_save_objects(batch)
            db.commit()
            batch = []

    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    print(f"[CNES] {count} hospitais importados.")
    return count


# ═══════════════════════════════════════════════════════════════════════
# DATASUS (capacidade cirúrgica)
# ═══════════════════════════════════════════════════════════════════════

def import_datasus(csv_path: str, db: Session) -> int:
    """
    Importa CSV do DATASUS (TabNet — internações cirúrgicas por hospital)
    e atualiza as tabelas Hospital, CapacidadeHospital e HospitalAlias.
    """
    if not os.path.exists(csv_path):
        print(f"[DATASUS] Arquivo não encontrado: {csv_path}")
        return 0

    enc = detect_encoding(csv_path)
    try:
        df = pd.read_csv(csv_path, encoding=enc, sep=";", skiprows=4, quotechar='"')
    except Exception:
        df = pd.read_csv(csv_path, encoding=enc, sep=";", skiprows=3, quotechar='"')

    df.columns = [
        c.strip().strip('"').upper()
         .replace(" ", "_").replace("Ç", "C").replace("Õ", "O")
         .replace("Ã", "A").replace("Ê", "E")
        for c in df.columns
    ]
    df = df[df.iloc[:, 0].notna()]
    df = df[~df.iloc[:, 0].astype(str).str.upper().str.startswith("TOTAL")]
    df = df[df.iloc[:, 0].astype(str).str.len() > 3]

    print(f"[DATASUS] Colunas: {list(df.columns)}")
    print(f"[DATASUS] Linhas úteis: {len(df)}")

    col_hosp = df.columns[0]
    col_total = df.columns[1] if len(df.columns) > 1 else None
    n_meses = 66  # Jan/2020–Jun/2025

    # Substituição transacional: só faz commit no fim; erro ou arquivo vazio → rollback
    imported = 0
    try:
        db.query(CapacidadeHospital).delete(synchronize_session=False)
        for _, row in df.iterrows():
            nome_raw = str(row[col_hosp]).strip().strip('"')
            if len(nome_raw) < 3:
                continue

            # Extrai CNES (7 dígitos no início)
            match = re.match(r'^(\d{7})\s+(.*)', nome_raw)
            if match:
                cnes = match.group(1)
                nome = match.group(2).strip()
            else:
                cnes = None
                nome = nome_raw

            # Total de internações
            try:
                total_str = str(row[col_total] if col_total else 0).replace(".", "").replace(",", "").strip()
                total = int(total_str) if total_str.isdigit() else 0
            except Exception:
                total = 0

            if total <= 0:
                continue

            # Inferir município (fallback)
            mun_inferido = _inferir_mun_por_nome(nome)
            cir_inferido = CIR_OFICIAL.get(norm(mun_inferido), "DESCONHECIDO")

            # --- Tenta encontrar hospital na base (pelo CNES ou nome) ---
            hospital = None
            if cnes:
                hospital = db.query(Hospital).filter(Hospital.cnes == cnes).first()
            if not hospital:
                hospital = encontrar_hospital_por_nome(nome, mun_inferido, db)

            if hospital:
                hospital_id = hospital.id
                # Atualiza campos se necessário
                if cnes and not hospital.cnes:
                    hospital.cnes = cnes
                    hospital.fonte = "combinado"
                # Marca como cirúrgico e atualiza capacidade
                hospital.is_cirurgico = True
            else:
                # Cria novo hospital (fonte = datasus)
                hospital = Hospital(
                    cnes=cnes,
                    nome_fantasia=nome,
                    razao_social=None,
                    municipio=mun_inferido,
                    uf="CE",
                    cir=cir_inferido,
                    tipo="publico",
                    fonte="datasus",
                    confiavel=False,
                    atende_sus=True,
                    is_cirurgico=True,
                )
                db.add(hospital)
                db.flush()
                hospital_id = hospital.id

            # --- Cria registro de capacidade ---
            media = round(total / n_meses, 1)
            capacidade = CapacidadeHospital(
                hospital_id=hospital_id,
                cnes=cnes or hospital.cnes,
                hospital_nome=nome,
                municipio=hospital.municipio,
                cir=hospital.cir,
                tipo=hospital.tipo,
                total_cirurgias=total,
                meses=n_meses,
                media_mensal=media,
            )
            db.add(capacidade)

            # --- Registra alias (nome original) para matching futuro ---
            alias = db.query(HospitalAlias).filter(HospitalAlias.alias_nome == nome_raw).first()
            if not alias:
                alias = HospitalAlias(
                    alias_nome=nome_raw,
                    cnes=cnes,
                    hospital_nome=nome,
                    fonte="datasus",
                )
                db.add(alias)
                db.flush()

            imported += 1
            if imported % 100 == 0:
                db.flush()

        if imported == 0:
            raise ImportacaoInvalida("Nenhum hospital válido no arquivo DATASUS; base anterior mantida")
        db.commit()
    except Exception:
        db.rollback()
        print("[DATASUS] ❌ Falha na importação — rollback; capacidade anterior preservada.")
        raise
    print(f"[DATASUS] ✅ {imported} hospitais processados / {db.query(CapacidadeHospital).count()} capacidades inseridas.")
    return imported


# ═══════════════════════════════════════════════════════════════════════
# INTEGRASUS (fila de espera)
# ═══════════════════════════════════════════════════════════════════════

def _valor_texto(row, col) -> str:
    if not col:
        return ""
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _ler_e_validar_integrasus(csv_path: str) -> list:
    """
    Lê e valida o CSV sem tocar no banco. Retorna lista de dicts prontos para inserir.
    Levanta ImportacaoInvalida se o arquivo não puder substituir a fila atual.
    """
    if not os.path.exists(csv_path):
        raise ImportacaoInvalida(f"Arquivo não encontrado: {os.path.basename(csv_path)}")

    enc = detect_encoding(csv_path)
    try:
        df = pd.read_csv(csv_path, encoding=enc, sep=";", low_memory=False, on_bad_lines='skip')
    except Exception as e:
        raise ImportacaoInvalida(f"CSV ilegível: {type(e).__name__}") from e
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]

    print(f"[INTEGRASUS] Encoding: {enc} | Colunas: {list(df.columns)} | Linhas: {len(df)}")

    col_map = {
        "hospital":      ["UNIDADE", "HOSPITAL", "NM_UNIDADE", "ESTABELECIMENTO"],
        "municipio":     ["MUNICIPIO", "NM_MUNICIPIO", "MUNICÍPIO"],
        "especialidade": ["ESPECIALIDADE", "NM_ESPECIALIDADE", "PROCEDIMENTO_GRUPO"],
        "swalis":        ["CLASSIF_SWALIS", "SWALIS", "CLASSIFICACAO", "PRIORIDADE"],
        "iniciais":      ["INIC_NOME_PACIENTE", "INICIAIS", "PACIENTE"],
        "judicial":      ["JUDICIALIZADO", "JUDICIAL", "ORDEM_JUDICIAL"],
        "procedimento":  ["PROCEDIMENTO", "NM_PROCEDIMENTO", "DS_PROCEDIMENTO"],
        "data":          ["DT_INCLUSAO", "DATA_INCLUSAO", "DATA_ENTRADA"],
    }

    def get_col(options):
        for o in options:
            if o in df.columns:
                return o
        return None

    cols = {k: get_col(v) for k, v in col_map.items()}
    if not cols["hospital"]:
        raise ImportacaoInvalida("Coluna de hospital/unidade não encontrada")
    if not cols["especialidade"]:
        raise ImportacaoInvalida("Coluna de especialidade não encontrada")

    registros = []
    ignoradas = 0
    for _, row in df.iterrows():
        hospital_nome = _valor_texto(row, cols["hospital"])
        especialidade = _valor_texto(row, cols["especialidade"]).upper()
        if not hospital_nome or hospital_nome.lower() == "nan" or not especialidade:
            ignoradas += 1
            continue
        judicial = _valor_texto(row, cols["judicial"]).upper() in ["SIM", "S", "1", "TRUE", "X"]
        registros.append({
            "iniciais": _valor_texto(row, cols["iniciais"])[:10] or None,
            "municipio": _valor_texto(row, cols["municipio"]).upper() or "DESCONHECIDO",
            "hospital_nome": hospital_nome,
            "especialidade": especialidade,
            "classif_swalis": _valor_texto(row, cols["swalis"]) or "Categoria D",
            "judicializado": judicial,
            "procedimento": _valor_texto(row, cols["procedimento"])[:200] or None,
            "data_insercao": _valor_texto(row, cols["data"]) or None,
        })

    if not registros:
        raise ImportacaoInvalida("Nenhuma linha válida no arquivo; fila atual mantida")
    if ignoradas:
        print(f"[INTEGRASUS] {ignoradas} linhas ignoradas (sem hospital ou especialidade)")
    return registros


def import_integrasus(csv_path: str, db: Session) -> int:
    """
    Importa CSV do IntegraSUS (fila de espera cirúrgica) de forma não destrutiva:
    1) lê e valida o arquivo inteiro sem tocar no banco;
    2) numa única transação, substitui a fila, vincula hospitais e recalcula mapas;
    3) commit só no fim — qualquer erro faz rollback e a fila anterior é preservada.
    Levanta ImportacaoInvalida se o arquivo for rejeitado.
    """
    registros = _ler_e_validar_integrasus(csv_path)
    data_import_str = datetime.now().strftime("%Y-%m-%d")
    hospital_cache = {}

    try:
        db.query(PacienteFila).delete(synchronize_session=False)

        batch = []
        for reg in registros:
            hospital_nome = reg["hospital_nome"]
            municipio = reg["municipio"]

            hospital_id = hospital_cache.get(hospital_nome)
            if hospital_id is None:
                hospital = encontrar_hospital_por_nome(hospital_nome, municipio, db)
                if hospital:
                    hospital_id = hospital.id
                    existe_alias = db.query(HospitalAlias).filter(
                        HospitalAlias.alias_nome == hospital_nome).first()
                    if not existe_alias:
                        db.add(HospitalAlias(
                            alias_nome=hospital_nome,
                            cnes=hospital.cnes,
                            hospital_nome=hospital.nome_fantasia,
                            fonte="integrasus_auto",
                        ))
                        db.flush()
                else:
                    hospital = Hospital(
                        nome_fantasia=hospital_nome,
                        municipio=municipio,
                        uf="CE",
                        cir=get_cir_from_municipio(municipio),
                        fonte="integrasus",
                        confiavel=False,
                        atende_sus=True,
                        is_cirurgico=False,
                    )
                    db.add(hospital)
                    db.flush()
                    hospital_id = hospital.id
                hospital_cache[hospital_nome] = hospital_id

            batch.append(PacienteFila(
                **reg, hospital_id=hospital_id, data_atualizacao=data_import_str,
            ))
            if len(batch) >= 1000:
                db.bulk_save_objects(batch)
                batch = []

        if batch:
            db.bulk_save_objects(batch)
        db.flush()

        hospital_cir_map = build_hospital_cir_map(db)
        _salvar_hospital_cir_map(hospital_cir_map, db, commit=False)
        build_hospital_especialidades(db, commit=False)

        db.commit()
    except Exception:
        db.rollback()
        print("[INTEGRASUS] ❌ Falha na importação — rollback; fila anterior preservada.")
        raise

    total = len(registros)
    print(f"[INTEGRASUS] ✅ {total:,} pacientes importados; {len(hospital_cache)} hospitais envolvidos")
    return total


def build_hospital_cir_map(db: Session) -> dict:
    """Infere município e CIR de cada hospital pelo município mais frequente dos pacientes."""
    rows = db.query(PacienteFila.hospital_nome, PacienteFila.municipio).all()
    contagem = {}
    for hosp, mun in rows:
        if not hosp or not mun:
            continue
        contagem.setdefault(hosp, Counter())[norm(mun)] += 1

    hospital_cir = {}
    for hosp, counter in contagem.items():
        mun_dominante = counter.most_common(1)[0][0]
        cir = CIR_OFICIAL.get(mun_dominante, "DESCONHECIDO")
        confianca = counter[mun_dominante] / sum(counter.values())
        hospital_cir[hosp] = {
            "municipio": mun_dominante,
            "cir": cir,
            "confianca": round(confianca, 3),
        }
    return hospital_cir


def _salvar_hospital_cir_map(hospital_cir_map: dict, db: Session, commit: bool = True):
    db.query(HospitalCirMap).delete(synchronize_session=False)
    batch = []
    for hosp, info in hospital_cir_map.items():
        batch.append(HospitalCirMap(
            hospital_nome=hosp,
            municipio=info["municipio"],
            cir=info["cir"],
            confianca=info["confianca"],
            atualizado_em=datetime.utcnow(),
        ))
    db.bulk_save_objects(batch)
    if commit:
        db.commit()
    print(f"[INTEGRASUS] HospitalCirMap: {len(batch)} hospitais salvos")


def build_hospital_especialidades(db: Session, commit: bool = True):
    """Constrói tabela HospitalEspecialidade a partir dos pacientes (IntegraSUS)."""
    from database import HospitalEspecialidade
    from sqlalchemy import func

    rows = db.query(
        PacienteFila.hospital_id,
        PacienteFila.especialidade,
        func.count(PacienteFila.id).label("total")
    ).filter(
        PacienteFila.hospital_id.isnot(None),
        PacienteFila.especialidade.isnot(None),
    ).group_by(
        PacienteFila.hospital_id,
        PacienteFila.especialidade
    ).all()

    if not rows:
        print("[ESPECIALIDADES] ⚠️  Nenhum dado encontrado em PacienteFila")
        return

    db.query(HospitalEspecialidade).filter(
        HospitalEspecialidade.fonte == "integrasus"
    ).delete(synchronize_session=False)

    batch = []
    for hospital_id, esp, total in rows:
        batch.append(HospitalEspecialidade(
            hospital_id=hospital_id,
            especialidade=esp.upper().strip(),
            total_procedimentos=int(total),
            pacientes_na_fila=int(total),
            fonte="integrasus",
            ultima_atualizacao=datetime.utcnow(),
        ))
        if len(batch) >= 500:
            db.bulk_save_objects(batch)
            batch = []

    if batch:
        db.bulk_save_objects(batch)
    if commit:
        db.commit()
    print(f"[ESPECIALIDADES] ✅ {len(rows)} combinações inseridas")


# ═══════════════════════════════════════════════════════════════════════
# AUTO IMPORT E SEEDS (opcional, para testes)
# ═══════════════════════════════════════════════════════════════════════

def auto_import(db: Session, importar_datasus: bool = True, importar_fila: bool = True):
    """Importa os CSVs mais recentes de backend/data/ (sem apagar nada se o CSV faltar)."""
    base = os.path.join(os.path.dirname(__file__), "..", "data")
    if importar_datasus:
        datasus_files = sorted(glob.glob(os.path.join(base, "*datasus*.csv")))
        if datasus_files:
            try:
                import_datasus(datasus_files[-1], db)
            except ImportacaoInvalida as e:
                print(f"[DATASUS] Arquivo rejeitado: {e}")
        else:
            print("[DATASUS] Nenhum CSV encontrado em data/")
            _seed_demo_datasus(db)

    if importar_fila:
        integra_files = sorted(
            glob.glob(os.path.join(base, "*fila*.csv")) +
            glob.glob(os.path.join(base, "*consulta*.csv")) +
            glob.glob(os.path.join(base, "*integrasus*.csv"))
        )
        if integra_files:
            try:
                import_integrasus(integra_files[-1], db)
            except ImportacaoInvalida as e:
                print(f"[INTEGRASUS] Arquivo rejeitado: {e}")
        else:
            print("[INTEGRASUS] Nenhum CSV encontrado em data/")
            _seed_demo_fila(db)


def _seed_demo_fila(db: Session):
    # ... (código de demo, opcional)
    pass


def _seed_demo_datasus(db: Session):
    # ... (código de demo, opcional)
    pass