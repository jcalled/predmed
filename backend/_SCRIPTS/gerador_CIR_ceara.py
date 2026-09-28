"""
PREDMED — Gerador do mapa completo Município → CIR
Fonte oficial: SESA-CE / lista_sr_ads_20220203.pdf

Uso:
    python build_cir_map.py --csv caminho/do/integrasus.csv

Saída:
    cir_map_resultado.txt  — para você revisar e copiar para o código
    cir_desconhecidos.txt  — municípios não encontrados (para revisão manual)
"""

import pandas as pd
import unicodedata
import sys
import argparse
import os

# ═══════════════════════════════════════════════════════════════════════
# MAPA OFICIAL — SESA-CE lista_sr_ads_20220203.pdf
# Formato: "MUNICIPIO": "CIR Sede (Superintendência)"
# ═══════════════════════════════════════════════════════════════════════

CIR_OFICIAL = {
    # ── SUPERINTENDÊNCIA FORTALEZA ─────────────────────────────────────
    # ADS Fortaleza
    "FORTALEZA":              "CIR Fortaleza",
    "EUSEBIO":                "CIR Fortaleza",
    "EUSÉBIO":                "CIR Fortaleza",
    "AQUIRAZ":                "CIR Fortaleza",
    "ITAITINGA":              "CIR Fortaleza",
    # ADS Caucaia
    "CAUCAIA":                "CIR Caucaia",
    "SAO GONCALO DO AMARANTE":"CIR Caucaia",
    "PARACURU":               "CIR Caucaia",
    "PARAIPABA":              "CIR Caucaia",
    "SAO LUIS DO CURU":       "CIR Caucaia",
    "PENTECOSTE":             "CIR Caucaia",
    "APUIARES":               "CIR Caucaia",
    "GENERAL SAMPAIO":        "CIR Caucaia",
    "TEJUCOCA":               "CIR Caucaia",
    "ITAPAJE":                "CIR Caucaia",
    "TEJUCUOCA":              "CIR Caucaia",
    # ADS Maracanaú
    "MARACANAU":              "CIR Maracanaú",
    "MARACANAÚ":              "CIR Maracanaú",
    "PACATUBA":               "CIR Maracanaú",
    "MARANGUAPE":             "CIR Maracanaú",
    "PALMACIA":               "CIR Maracanaú",
    "GUAIUBA":                "CIR Maracanaú",
    "ACARAPE":                "CIR Maracanaú",
    "REDENCAO":               "CIR Maracanaú",
    "BARREIRA":               "CIR Maracanaú",
    # ADS Baturité
    "BATURITE":               "CIR Baturité",
    "PACOTI":                 "CIR Baturité",
    "GUARAMIRANGA":           "CIR Baturité",
    "MULUNGU":                "CIR Baturité",
    "ARACOIABA":              "CIR Baturité",
    "ARATUBA":                "CIR Baturité",
    "CAPISTRANO":             "CIR Baturité",
    "ITAPIUNA":               "CIR Baturité",
    # ADS Itapipoca
    "ITAPIPOCA":              "CIR Itapipoca",
    "TRAIRI":                 "CIR Itapipoca",
    "TURURU":                 "CIR Itapipoca",
    "UMIRIM":                 "CIR Itapipoca",
    "URUBURETAMA":            "CIR Itapipoca",
    "AMONTADA":               "CIR Itapipoca",
    "MIRAIIMA":               "CIR Itapipoca",
    "MIRAIMA":                "CIR Itapipoca",
    # ADS Beberibe
    "BEBERIBE":               "CIR Beberibe",
    "CASCAVEL":               "CIR Beberibe",
    "PINDORETAMA":            "CIR Beberibe",
    "HORIZONTE":              "CIR Beberibe",
    "PACAJUS":                "CIR Beberibe",
    "CHOROZINHO":             "CIR Beberibe",
    "OCARA":                  "CIR Beberibe",

    # ── SUPERINTENDÊNCIA NORTE ─────────────────────────────────────────
    # ADS Sobral
    "SOBRAL":                 "CIR Sobral",
    "SENADOR SA":             "CIR Sobral",
    "URUOCA":                 "CIR Sobral",
    "SANTANA DO ACARAU":      "CIR Sobral",
    "MASSAPE":                "CIR Sobral",
    "MERUOCA":                "CIR Sobral",
    "MORAUJO":                "CIR Sobral",
    "MUCAMBO":                "CIR Sobral",
    "COREAUS":                "CIR Sobral",
    "FRECHEIRINHA":           "CIR Sobral",
    "ALCANTARAS":             "CIR Sobral",
    "FORQUILHA":              "CIR Sobral",
    "IRAUCUBA":               "CIR Sobral",
    "SANTA QUITERIA":         "CIR Sobral",
    "CATUNDA":                "CIR Sobral",
    "HIDROLANDIA":            "CIR Sobral",
    "IPU":                    "CIR Sobral",
    "PIRES FERREIRA":         "CIR Sobral",
    "RERIUTABA":              "CIR Sobral",
    "GRACA":                  "CIR Sobral",
    "VARJOTA":                "CIR Sobral",
    "PACUJA":                 "CIR Sobral",
    "CARIRE":                 "CIR Sobral",
    "GROAIRAS":               "CIR Sobral",
    "COREAU":                 "CIR Sobral",
    "BOA HORA":               "CIR Sobral",
    # ADS Acaraú
    "ACARAU":                 "CIR Acaraú",
    "ACARAÚ":                 "CIR Acaraú",
    "BELA CRUZ":              "CIR Acaraú",
    "CRUZ":                   "CIR Acaraú",
    "ITAREMA":                "CIR Acaraú",
    "JIJOCA DE JERICOACOARA": "CIR Acaraú",
    "MARCO":                  "CIR Acaraú",
    "MORRINHOS":              "CIR Acaraú",
    # ADS Tianguá
    "TIANGUA":                "CIR Tianguá",
    "TIANGUÁ":                "CIR Tianguá",
    "UBAJARA":                "CIR Tianguá",
    "VICOSA DO CEARA":        "CIR Tianguá",
    "SAO BENEDITO":           "CIR Tianguá",
    "IBIAPINA":               "CIR Tianguá",
    "CARNAUBAL":              "CIR Tianguá",
    "CROATA":                 "CIR Tianguá",
    "GUARACIABA DO NORTE":    "CIR Tianguá",
    # ADS Crateús
    "CRATEUS":                "CIR Crateús",
    "IPUEIRAS":               "CIR Crateús",
    "PORANGA":                "CIR Crateús",
    "QUITERIANOPOLIS":        "CIR Crateús",
    "NOVA RUSSAS":            "CIR Crateús",
    "NOVO ORIENTE":           "CIR Crateús",
    "INDEPENDENCIA":          "CIR Crateús",
    "IPAPORANGA":             "CIR Crateús",
    "TAMBORIL":               "CIR Crateús",
    "MONSENHOR TABOSA":       "CIR Crateús",
    "ARERENDA":               "CIR Crateús",
    "ARARENDA":               "CIR Crateús",

    # ADS Camocim
    "CAMOCIM":                "CIR Camocim",
    "BARROQUINHA":            "CIR Camocim",
    "CHAVAL":                 "CIR Camocim",
    "MARTINOPOLE":            "CIR Camocim",
    "GRANJA":                 "CIR Camocim",

    # ── SUPERINTENDÊNCIA CARIRI ────────────────────────────────────────
    # ADS Juazeiro do Norte
    "JUAZEIRO DO NORTE":      "CIR Juazeiro do Norte",
    "JUAZEIRO":               "CIR Juazeiro do Norte",
    "GRANJEIRO":              "CIR Juazeiro do Norte",
    "CARIRIACU":              "CIR Juazeiro do Norte",
    "BARBALHA":               "CIR Juazeiro do Norte",
    "MISSAO VELHA":           "CIR Juazeiro do Norte",
    "JARDIM":                 "CIR Juazeiro do Norte",
    # ADS Icó
    "ICO":                    "CIR Icó",
    "OROS":                   "CIR Icó",
    "CEDRO":                  "CIR Icó",
    "VARZEA ALEGRE":          "CIR Icó",
    "LAVRAS DA MANGABEIRA":   "CIR Icó",
    "UMARI":                  "CIR Icó",
    "BAIXIO":                 "CIR Icó",
    "IPAUMIRIM":              "CIR Icó",
    # ADS Iguatu
    "IGUATU":                 "CIR Iguatu",
    "MOMBACA":                "CIR Iguatu",
    "DEPUTADO IRAPUAN PINHEIRO":"CIR Iguatu",
    "PIQUET CARNEIRO":        "CIR Iguatu",
    "ACOPIARA":               "CIR Iguatu",
    "CATARINA":               "CIR Iguatu",
    "QUIXELO":                "CIR Iguatu",
    "SABOEIRO":               "CIR Iguatu",
    "JUCAS":                  "CIR Iguatu",
    "CARIUS":                 "CIR Iguatu",
    # ADS Brejo Santo
    "BREJO SANTO":            "CIR Brejo Santo",
    "AURORA":                 "CIR Brejo Santo",
    "BARRO":                  "CIR Brejo Santo",
    "MILAGRES":               "CIR Brejo Santo",
    "ABAIARA":                "CIR Brejo Santo",
    "MAURITI":                "CIR Brejo Santo",
    "JATI":                   "CIR Brejo Santo",
    "PENAFORTE":              "CIR Brejo Santo",
    "PORTEIRAS":              "CIR Brejo Santo",
    # ADS Crato
    "CRATO":                  "CIR Crato",
    "CAMPOS SALES":           "CIR Crato",
    "ALTANEIRA":              "CIR Crato",
    "ANTONINA DO NORTE":      "CIR Crato",
    "ARARIPE":                "CIR Crato",
    "ASSARE":                 "CIR Crato",
    "FARIAS BRITO":           "CIR Crato",
    "NOVA OLINDA":            "CIR Crato",
    "POTENGI":                "CIR Crato",
    "SALITRE":                "CIR Crato",
    "SANTANA DO CARIRI":      "CIR Crato",
    "TARRAFAS":               "CIR Crato",

    # ── SUPERINTENDÊNCIA SERTÃO CENTRAL ───────────────────────────────
    # ADS Quixadá
    "QUIXADA":                "CIR Quixadá",
    "QUIXADÁ":                "CIR Quixadá",
    "CHORO":                  "CIR Quixadá",
    "IBARETAMA":              "CIR Quixadá",
    "IBICUITINGA":            "CIR Quixadá",
    "QUIXERAMOBIM":           "CIR Quixadá",
    "BANABUIU":               "CIR Quixadá",
    "PEDRA BRANCA":           "CIR Quixadá",
    "SENADOR POMPEU":         "CIR Quixadá",
    "MILHA":                  "CIR Quixadá",
    "SOLONOPOLE":             "CIR Quixadá",
    # ADS Canindé
    "CANINDE":                "CIR Canindé",
    "CARIDADE":               "CIR Canindé",
    "PARAMOTI":               "CIR Canindé",
    "ITATIRA":                "CIR Canindé",
    "MADALENA":               "CIR Canindé",
    "BOA VIAGEM":             "CIR Canindé",
    # ADS Tauá
    "TAUA":                   "CIR Tauá",
    "PARAMBU":                "CIR Tauá",
    "AIUABA":                 "CIR Tauá",
    "ARNEIROZ":               "CIR Tauá",

    # ── SUPERINTENDÊNCIA LITORAL LESTE/JAGUARIBE ──────────────────────
    # ADS Limoeiro do Norte
    "LIMOEIRO DO NORTE":      "CIR Limoeiro do Norte",
    "QUIXERE":                "CIR Limoeiro do Norte",
    "TABULEIRO DO NORTE":     "CIR Limoeiro do Norte",
    "SAO JOAO DO JAGUARIBE":  "CIR Limoeiro do Norte",
    "ALTO SANTO":             "CIR Limoeiro do Norte",
    "JAGUARIBARA":            "CIR Limoeiro do Norte",
    "IRACEMA":                "CIR Limoeiro do Norte",
    "POTIRETAMA":             "CIR Limoeiro do Norte",
    "JAGUARIBE":              "CIR Limoeiro do Norte",
    "PEREIRO":                "CIR Limoeiro do Norte",
    "ERERE":                  "CIR Limoeiro do Norte",
    # ADS Aracati
    "ARACATI":                "CIR Aracati",
    "FORTIM":                 "CIR Aracati",
    "ICAPUI":                 "CIR Aracati",
    "ITAICABA":               "CIR Aracati",
    # ADS Russas
    "RUSSAS":                 "CIR Russas",
    "MORADA NOVA":            "CIR Russas",
    "PALHANO":                "CIR Russas",
    "JAGUARETAMA":            "CIR Russas",
    "JAGUARUANA":             "CIR Russas",


    # ── OUTROS ESTADOS ────────────────────────────────────────────────
    "ACRELANDIA": "FORA_DO_CEARA", "AGUA DOCE DO MARANHAO": "FORA_DO_CEARA",
    "ALTAMIRA": "FORA_DO_CEARA", "ALTAMIRA DO MARANHAO": "FORA_DO_CEARA",
    "ALTO DO RODRIGUES": "FORA_DO_CEARA", "ANANINDEUA": "FORA_DO_CEARA",
    "APODI": "FORA_DO_CEARA", "ARACATUBA": "FORA_DO_CEARA",
    "ARARIPINA": "FORA_DO_CEARA", "BARAUNA": "FORA_DO_CEARA",
    "BELEM": "FORA_DO_CEARA", "BELO HORIZONTE": "FORA_DO_CEARA",
    "BODOCO": "FORA_DO_CEARA", "BRASILIA": "FORA_DO_CEARA",
    "CENTRO NOVO DO MARANHAO": "FORA_DO_CEARA", "GOVERNADOR DIX-SEPT ROSADO": "FORA_DO_CEARA",
    "IMPERATRIZ": "FORA_DO_CEARA", "ITABORAI": "FORA_DO_CEARA",
    "JAICOS": "FORA_DO_CEARA", "JUIZ DE FORA": "FORA_DO_CEARA",
    "LASTRO": "FORA_DO_CEARA", "LUZILANDIA": "FORA_DO_CEARA",
    "MACAPA": "FORA_DO_CEARA", "MACAU": "FORA_DO_CEARA",
    "MANAUS": "FORA_DO_CEARA", "MARCELINO VIEIRA": "FORA_DO_CEARA",
    "MOSSORO": "FORA_DO_CEARA", "NATAL": "FORA_DO_CEARA",
    "OURICURI": "FORA_DO_CEARA", "PALMEIRAIS": "FORA_DO_CEARA",
    "PAQUETA": "FORA_DO_CEARA", "PARNAIBA": "FORA_DO_CEARA",
    "PATU": "FORA_DO_CEARA", "PETROLINA": "FORA_DO_CEARA",
    "SANTA INES": "FORA_DO_CEARA", "SERRITA": "FORA_DO_CEARA",
    "SOUSA": "FORA_DO_CEARA", "TERESINA": "FORA_DO_CEARA",
    "TIMON": "FORA_DO_CEARA",
}


def norm(s: str) -> str:
    """Remove acentos e normaliza para uppercase"""
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().strip()


def detect_encoding(filepath):
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            with open(filepath, encoding=enc) as f:
                f.read(2000)
            return enc
        except Exception:
            pass
    return "latin-1"


def get_cir(municipio: str) -> str:
    """Retorna CIR para um município — versão normalizada"""
    return CIR_OFICIAL.get(norm(municipio), "DESCONHECIDO")


def processar_csv(csv_path: str):
    print(f"\n{'='*60}")
    print(f"  Processando: {csv_path}")
    print(f"{'='*60}\n")

    enc = detect_encoding(csv_path)
    print(f"  Encoding detectado: {enc}")

    df = pd.read_csv(csv_path, encoding=enc, sep=";", low_memory=False, on_bad_lines='skip')
    df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]

    # Encontra coluna de município
    col_mun = None
    for c in df.columns:
        if "MUNICIPIO" in c or "MUNICÍPIO" in c:
            col_mun = c
            break

    if not col_mun:
        print(f"  ❌ Coluna MUNICIPIO não encontrada. Colunas: {list(df.columns)}")
        return

    print(f"  Coluna município: {col_mun}")
    print(f"  Total de linhas: {len(df):,}\n")

    # Extrai municípios únicos
    municipios = df[col_mun].dropna().unique()
    municipios_norm = sorted(set(norm(m) for m in municipios))

    print(f"  Municípios únicos encontrados: {len(municipios_norm)}")
    print()

    # Mapeia CIR
    mapeados   = {}
    desconhecidos = []

    for m in municipios_norm:
        cir = CIR_OFICIAL.get(m, None)
        if cir:
            mapeados[m] = cir
        else:
            desconhecidos.append(m)

    # ── RESULTADO ──────────────────────────────────────────────────────
    print(f"  ✅ Mapeados: {len(mapeados)}")
    print(f"  ❓ Desconhecidos: {len(desconhecidos)}")
    print()

    # Agrupa por CIR para visualização
    cir_grupos = {}
    for m, cir in sorted(mapeados.items()):
        cir_grupos.setdefault(cir, []).append(m)

    print("─" * 60)
    print("  MUNICÍPIOS POR CIR")
    print("─" * 60)
    for cir in sorted(cir_grupos):
        muns = cir_grupos[cir]
        print(f"\n  {cir} ({len(muns)} municípios):")
        for m in muns:
            print(f"    • {m}")

    if desconhecidos:
        print()
        print("─" * 60)
        print(f"  ❓ NÃO MAPEADOS ({len(desconhecidos)}) — revisão manual:")
        print("─" * 60)
        for m in desconhecidos:
            print(f"    • {m}")

    # ── SALVA ARQUIVOS ─────────────────────────────────────────────────
    # Resultado completo
    with open("cir_map_resultado.txt", "w", encoding="utf-8") as f:
        f.write("# PREDMED — Mapa Município → CIR\n")
        f.write("# Gerado automaticamente. Cole no data_import.py\n\n")
        f.write("CIR_OFICIAL = {\n")
        for cir in sorted(cir_grupos):
            f.write(f"\n    # {cir}\n")
            for m in cir_grupos[cir]:
                f.write(f'    "{m}": "{cir}",\n')
        f.write("}\n")

    # Desconhecidos para revisão manual
    if desconhecidos:
        with open("cir_desconhecidos.txt", "w", encoding="utf-8") as f:
            f.write("# Municípios do IntegraSUS SEM CIR mapeada\n")
            f.write("# Adicione manualmente no CIR_OFICIAL em data_import.py\n\n")
            for m in desconhecidos:
                f.write(f'    "{m}": "",  # TODO: qual CIR?\n')

    # Código Python pronto para copiar
    with open("cir_map_code.py", "w", encoding="utf-8") as f:
        f.write('"""\nPREDMED — Cole este dicionário em data_import.py\n"""\n\n')
        f.write("CIR_OFICIAL = {\n")
        for cir in sorted(cir_grupos):
            f.write(f"\n    # {cir}\n")
            for m in cir_grupos[cir]:
                f.write(f'    "{m}": "{cir}",\n')
        if desconhecidos:
            f.write("\n    # ── PENDENTES — revisar manualmente ──────────\n")
            for m in desconhecidos:
                f.write(f'    "{m}": "CIR ???",  # TODO\n')
        f.write("}\n")

    print()
    print("─" * 60)
    print("  ARQUIVOS GERADOS:")
    print("    📄 cir_map_resultado.txt  — visualização por CIR")
    print("    📄 cir_desconhecidos.txt  — municípios para revisão manual")
    print("    📄 cir_map_code.py        — código pronto para colar no sistema")
    print("─" * 60)

    # ── ESTATÍSTICAS DO CSV ────────────────────────────────────────────
    print()
    print("  ESTATÍSTICAS DO INTEGRASUS:")
    print(f"  Total pacientes: {len(df):,}")

    # Conta por município com CIR
    df['_MUN_NORM'] = df[col_mun].apply(lambda x: norm(str(x)))
    df['_CIR'] = df['_MUN_NORM'].map(CIR_OFICIAL).fillna('DESCONHECIDO')

    por_cir = df.groupby('_CIR').size().sort_values(ascending=False)
    print()
    print("  Pacientes por CIR/Região:")
    for cir, n in por_cir.items():
        pct = n / len(df) * 100
        bar = '█' * int(pct / 2)
        print(f"    {cir:<35} {n:>6,}  ({pct:4.1f}%) {bar}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mapeia municípios do IntegraSUS para CIR")
    parser.add_argument("--csv", required=True, help="Caminho do CSV do IntegraSUS")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"❌ Arquivo não encontrado: {args.csv}")
        sys.exit(1)

    processar_csv(args.csv)


  # python build_cir_map.py --csv ../data/consulta-fila-espera_2026-02-22.csv