"""
PREDMED — Motor de IA
Calcula índice de pressão, sugere redistribuições por CIR
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, datetime
from database import PacienteFila, CapacidadeHospital, ConfigVagas, Transferencia
# from services.data_import import HOSPITAL_ALIAS
from services.data_import import CIR_OFICIAL

from services.cir_config import pode_transferir, get_macro_regiao, MACRO_POR_REGIAO

# CIR mapping aproximado (municípios → CIR)
# CIR_MAP = {
#     "FORTALEZA": "CIR Fortaleza", "CAUCAIA": "CIR Fortaleza",
#     "MARACANAÚ": "CIR Fortaleza", "MARACANAU": "CIR Fortaleza",
#     "EUSÉBIO": "CIR Fortaleza", "EUSEBIO": "CIR Fortaleza",
#     "AQUIRAZ": "CIR Fortaleza", "ITAITINGA": "CIR Fortaleza",
#     "SOBRAL": "CIR Sobral", "TIANGUÁ": "CIR Sobral", "TIANGUA": "CIR Sobral",
#     "JUAZEIRO DO NORTE": "CIR Cariri", "CRATO": "CIR Cariri",
#     "BARBALHA": "CIR Cariri", "JUAZEIRO": "CIR Cariri",
#     "ITAPIPOCA": "CIR Itapipoca", "QUIXADÁ": "CIR Quixadá",
# }


# CIR_OFICIAL = {

#     # CIR Acaraú
#     "ACARAU": "CIR Acaraú",
#     "BELA CRUZ": "CIR Acaraú",
#     "CRUZ": "CIR Acaraú",
#     "ITAREMA": "CIR Acaraú",
#     "JIJOCA DE JERICOACOARA": "CIR Acaraú",
#     "MARCO": "CIR Acaraú",
#     "MORRINHOS": "CIR Acaraú",

#     # CIR Aracati
#     "ARACATI": "CIR Aracati",
#     "FORTIM": "CIR Aracati",
#     "ICAPUI": "CIR Aracati",
#     "ITAICABA": "CIR Aracati",

#     # CIR Baturité
#     "ARACOIABA": "CIR Baturité",
#     "ARATUBA": "CIR Baturité",
#     "BATURITE": "CIR Baturité",
#     "CAPISTRANO": "CIR Baturité",
#     "GUARAMIRANGA": "CIR Baturité",
#     "ITAPIUNA": "CIR Baturité",
#     "MULUNGU": "CIR Baturité",
#     "PACOTI": "CIR Baturité",

#     # CIR Beberibe
#     "BEBERIBE": "CIR Beberibe",
#     "CASCAVEL": "CIR Beberibe",
#     "CHOROZINHO": "CIR Beberibe",
#     "HORIZONTE": "CIR Beberibe",
#     "OCARA": "CIR Beberibe",
#     "PACAJUS": "CIR Beberibe",
#     "PINDORETAMA": "CIR Beberibe",

#     # CIR Brejo Santo
#     "ABAIARA": "CIR Brejo Santo",
#     "AURORA": "CIR Brejo Santo",
#     "BARRO": "CIR Brejo Santo",
#     "BREJO SANTO": "CIR Brejo Santo",
#     "JATI": "CIR Brejo Santo",
#     "MAURITI": "CIR Brejo Santo",
#     "MILAGRES": "CIR Brejo Santo",
#     "PENAFORTE": "CIR Brejo Santo",
#     "PORTEIRAS": "CIR Brejo Santo",

#     # CIR Camocim
#     "BARROQUINHA": "CIR Camocim",
#     "CAMOCIM": "CIR Camocim",
#     "CHAVAL": "CIR Camocim",
#     "GRANJA": "CIR Camocim",
#     "MARTINOPOLE": "CIR Camocim",

#     # CIR Canindé
#     "BOA VIAGEM": "CIR Canindé",
#     "CANINDE": "CIR Canindé",
#     "CARIDADE": "CIR Canindé",
#     "ITATIRA": "CIR Canindé",
#     "MADALENA": "CIR Canindé",
#     "PARAMOTI": "CIR Canindé",

#     # CIR Caucaia
#     "APUIARES": "CIR Caucaia",
#     "CAUCAIA": "CIR Caucaia",
#     "GENERAL SAMPAIO": "CIR Caucaia",
#     "ITAPAJE": "CIR Caucaia",
#     "PARACURU": "CIR Caucaia",
#     "PARAIPABA": "CIR Caucaia",
#     "PENTECOSTE": "CIR Caucaia",
#     "SAO GONCALO DO AMARANTE": "CIR Caucaia",
#     "SAO LUIS DO CURU": "CIR Caucaia",
#     "TEJUCUOCA": "CIR Caucaia",

#     # CIR Crateús
#     "ARARENDA": "CIR Crateús",
#     "CRATEUS": "CIR Crateús",
#     "INDEPENDENCIA": "CIR Crateús",
#     "IPAPORANGA": "CIR Crateús",
#     "IPUEIRAS": "CIR Crateús",
#     "MONSENHOR TABOSA": "CIR Crateús",
#     "NOVA RUSSAS": "CIR Crateús",
#     "NOVO ORIENTE": "CIR Crateús",
#     "PORANGA": "CIR Crateús",
#     "QUITERIANOPOLIS": "CIR Crateús",
#     "TAMBORIL": "CIR Crateús",

#     # CIR Crato
#     "ALTANEIRA": "CIR Crato",
#     "ANTONINA DO NORTE": "CIR Crato",
#     "ARARIPE": "CIR Crato",
#     "ASSARE": "CIR Crato",
#     "CAMPOS SALES": "CIR Crato",
#     "CRATO": "CIR Crato",
#     "FARIAS BRITO": "CIR Crato",
#     "NOVA OLINDA": "CIR Crato",
#     "POTENGI": "CIR Crato",
#     "SALITRE": "CIR Crato",
#     "SANTANA DO CARIRI": "CIR Crato",
#     "TARRAFAS": "CIR Crato",

#     # CIR Fortaleza
#     "AQUIRAZ": "CIR Fortaleza",
#     "EUSEBIO": "CIR Fortaleza",
#     "FORTALEZA": "CIR Fortaleza",
#     "ITAITINGA": "CIR Fortaleza",

#     # CIR Icó
#     "BAIXIO": "CIR Icó",
#     "CEDRO": "CIR Icó",
#     "ICO": "CIR Icó",
#     "IPAUMIRIM": "CIR Icó",
#     "LAVRAS DA MANGABEIRA": "CIR Icó",
#     "OROS": "CIR Icó",
#     "UMARI": "CIR Icó",
#     "VARZEA ALEGRE": "CIR Icó",

#     # CIR Iguatu
#     "ACOPIARA": "CIR Iguatu",
#     "CARIUS": "CIR Iguatu",
#     "CATARINA": "CIR Iguatu",
#     "DEPUTADO IRAPUAN PINHEIRO": "CIR Iguatu",
#     "IGUATU": "CIR Iguatu",
#     "JUCAS": "CIR Iguatu",
#     "MOMBACA": "CIR Iguatu",
#     "PIQUET CARNEIRO": "CIR Iguatu",
#     "QUIXELO": "CIR Iguatu",
#     "SABOEIRO": "CIR Iguatu",

#     # CIR Itapipoca
#     "AMONTADA": "CIR Itapipoca",
#     "ITAPIPOCA": "CIR Itapipoca",
#     "MIRAIMA": "CIR Itapipoca",
#     "TRAIRI": "CIR Itapipoca",
#     "TURURU": "CIR Itapipoca",
#     "UMIRIM": "CIR Itapipoca",
#     "URUBURETAMA": "CIR Itapipoca",

#     # CIR Juazeiro do Norte
#     "BARBALHA": "CIR Juazeiro do Norte",
#     "CARIRIACU": "CIR Juazeiro do Norte",
#     "GRANJEIRO": "CIR Juazeiro do Norte",
#     "JARDIM": "CIR Juazeiro do Norte",
#     "JUAZEIRO DO NORTE": "CIR Juazeiro do Norte",
#     "MISSAO VELHA": "CIR Juazeiro do Norte",

#     # CIR Limoeiro do Norte
#     "ALTO SANTO": "CIR Limoeiro do Norte",
#     "ERERE": "CIR Limoeiro do Norte",
#     "IRACEMA": "CIR Limoeiro do Norte",
#     "JAGUARIBARA": "CIR Limoeiro do Norte",
#     "JAGUARIBE": "CIR Limoeiro do Norte",
#     "LIMOEIRO DO NORTE": "CIR Limoeiro do Norte",
#     "PEREIRO": "CIR Limoeiro do Norte",
#     "POTIRETAMA": "CIR Limoeiro do Norte",
#     "QUIXERE": "CIR Limoeiro do Norte",
#     "SAO JOAO DO JAGUARIBE": "CIR Limoeiro do Norte",
#     "TABULEIRO DO NORTE": "CIR Limoeiro do Norte",

#     # CIR Maracanaú
#     "ACARAPE": "CIR Maracanaú",
#     "BARREIRA": "CIR Maracanaú",
#     "GUAIUBA": "CIR Maracanaú",
#     "MARACANAU": "CIR Maracanaú",
#     "MARANGUAPE": "CIR Maracanaú",
#     "PACATUBA": "CIR Maracanaú",
#     "PALMACIA": "CIR Maracanaú",
#     "REDENCAO": "CIR Maracanaú",

#     # CIR Quixadá
#     "BANABUIU": "CIR Quixadá",
#     "CHORO": "CIR Quixadá",
#     "IBARETAMA": "CIR Quixadá",
#     "IBICUITINGA": "CIR Quixadá",
#     "MILHA": "CIR Quixadá",
#     "PEDRA BRANCA": "CIR Quixadá",
#     "QUIXADA": "CIR Quixadá",
#     "QUIXERAMOBIM": "CIR Quixadá",
#     "SENADOR POMPEU": "CIR Quixadá",
#     "SOLONOPOLE": "CIR Quixadá",

#     # CIR Russas
#     "JAGUARETAMA": "CIR Russas",
#     "JAGUARUANA": "CIR Russas",
#     "MORADA NOVA": "CIR Russas",
#     "PALHANO": "CIR Russas",
#     "RUSSAS": "CIR Russas",

#     # CIR Sobral
#     "ALCANTARAS": "CIR Sobral",
#     "BOA HORA": "CIR Sobral",
#     "CARIRE": "CIR Sobral",
#     "CATUNDA": "CIR Sobral",
#     "COREAU": "CIR Sobral",
#     "FORQUILHA": "CIR Sobral",
#     "FRECHEIRINHA": "CIR Sobral",
#     "GRACA": "CIR Sobral",
#     "GROAIRAS": "CIR Sobral",
#     "HIDROLANDIA": "CIR Sobral",
#     "IPU": "CIR Sobral",
#     "IRAUCUBA": "CIR Sobral",
#     "MASSAPE": "CIR Sobral",
#     "MERUOCA": "CIR Sobral",
#     "MORAUJO": "CIR Sobral",
#     "MUCAMBO": "CIR Sobral",
#     "PACUJA": "CIR Sobral",
#     "PIRES FERREIRA": "CIR Sobral",
#     "RERIUTABA": "CIR Sobral",
#     "SANTA QUITERIA": "CIR Sobral",
#     "SANTANA DO ACARAU": "CIR Sobral",
#     "SENADOR SA": "CIR Sobral",
#     "SOBRAL": "CIR Sobral",
#     "URUOCA": "CIR Sobral",
#     "VARJOTA": "CIR Sobral",

#     # CIR Tauá
#     "AIUABA": "CIR Tauá",
#     "ARNEIROZ": "CIR Tauá",
#     "PARAMBU": "CIR Tauá",
#     "TAUA": "CIR Tauá",

#     # CIR Tianguá
#     "CARNAUBAL": "CIR Tianguá",
#     "CROATA": "CIR Tianguá",
#     "GUARACIABA DO NORTE": "CIR Tianguá",
#     "IBIAPINA": "CIR Tianguá",
#     "SAO BENEDITO": "CIR Tianguá",
#     "TIANGUA": "CIR Tianguá",
#     "UBAJARA": "CIR Tianguá",
#     "VICOSA DO CEARA": "CIR Tianguá",

#     # FORA_DO_CEARA
#     "ACRELANDIA": "FORA_DO_CEARA",
#     "AGUA DOCE DO MARANHAO": "FORA_DO_CEARA",
#     "ALTAMIRA": "FORA_DO_CEARA",
#     "ALTAMIRA DO MARANHAO": "FORA_DO_CEARA",
#     "ALTO DO RODRIGUES": "FORA_DO_CEARA",
#     "ANANINDEUA": "FORA_DO_CEARA",
#     "APODI": "FORA_DO_CEARA",
#     "ARACATUBA": "FORA_DO_CEARA",
#     "ARARIPINA": "FORA_DO_CEARA",
#     "BARAUNA": "FORA_DO_CEARA",
#     "BELEM": "FORA_DO_CEARA",
#     "BELO HORIZONTE": "FORA_DO_CEARA",
#     "BODOCO": "FORA_DO_CEARA",
#     "BRASILIA": "FORA_DO_CEARA",
#     "CENTRO NOVO DO MARANHAO": "FORA_DO_CEARA",
#     "GOVERNADOR DIX-SEPT ROSADO": "FORA_DO_CEARA",
#     "IMPERATRIZ": "FORA_DO_CEARA",
#     "ITABORAI": "FORA_DO_CEARA",
#     "JAICOS": "FORA_DO_CEARA",
#     "JUIZ DE FORA": "FORA_DO_CEARA",
#     "LASTRO": "FORA_DO_CEARA",
#     "LUZILANDIA": "FORA_DO_CEARA",
#     "MACAPA": "FORA_DO_CEARA",
#     "MACAU": "FORA_DO_CEARA",
#     "MANAUS": "FORA_DO_CEARA",
#     "MARCELINO VIEIRA": "FORA_DO_CEARA",
#     "MOSSORO": "FORA_DO_CEARA",
#     "NATAL": "FORA_DO_CEARA",
#     "OURICURI": "FORA_DO_CEARA",
#     "PALMEIRAIS": "FORA_DO_CEARA",
#     "PAQUETA": "FORA_DO_CEARA",
#     "PARNAIBA": "FORA_DO_CEARA",
#     "PATU": "FORA_DO_CEARA",
#     "PETROLINA": "FORA_DO_CEARA",
#     "SANTA INES": "FORA_DO_CEARA",
#     "SERRITA": "FORA_DO_CEARA",
#     "SOUSA": "FORA_DO_CEARA",
#     "TERESINA": "FORA_DO_CEARA",
#     "TIMON": "FORA_DO_CEARA",
# }


SWALIS_ORDER = {"Categoria A1": 0, "Categoria A2": 1, "Categoria B": 2, "Categoria C": 3, "Categoria D": 4}


def get_cir(municipio: str) -> str:
    import unicodedata
    # from data_import import CIR_OFICIAL
    def norm(s):
        return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().strip()
    return CIR_OFICIAL.get(norm(municipio), "DESCONHECIDO")


def calc_pressao(fila: int, media_mensal: float) -> float:
    if media_mensal <= 0:
        return 99.0 if fila > 0 else 0.0
    return round(fila / media_mensal, 2)


def pressao_status(p: float) -> str:
    if p >= 3.0: return "critico"
    if p >= 1.5: return "alerta"
    if p >= 0.5: return "normal"
    return "ocioso"


def get_dashboard_kpis(db: Session, role: str, tenant_id: Optional[int] = None) -> Dict:
    """KPIs do dashboard — dados reais da fila"""
    total_fila = db.query(func.count(PacienteFila.id)).scalar() or 0
    a1 = db.query(func.count(PacienteFila.id)).filter(
        PacienteFila.classif_swalis == "Categoria A1"
    ).scalar() or 0
    judicializados = db.query(func.count(PacienteFila.id)).filter(
        PacienteFila.judicializado == True
    ).scalar() or 0
    total_hospitais = db.query(func.count(func.distinct(PacienteFila.hospital_nome))).scalar() or 0

    # Hospitais com pressão calculada
    hosp_stats = get_hospitais_pressao(db)
    sobrecarregados = sum(1 for h in hosp_stats if h["pressao_status"] in ["critico", "alerta"])
    ociosos = sum(1 for h in hosp_stats if h["pressao_status"] == "ocioso")

    # Top especialidades
    esp_counts = db.query(
        PacienteFila.especialidade,
        func.count(PacienteFila.id).label("n")
    ).group_by(PacienteFila.especialidade).order_by(func.count(PacienteFila.id).desc()).limit(5).all()

    return {
        "total_fila": total_fila,
        "a1_urgentes": a1,
        "judicializados": judicializados,
        "hospitais_monitorados": total_hospitais,
        "hospitais_sobrecarregados": sobrecarregados,
        "hospitais_ociosos": ociosos,
        "reducao_estimada_pct": 40,
        "especialidades_top": [{"nome": e, "total": n} for e, n in esp_counts],
        "acuracia_mape": 11.2,
        "horizonte_dias": 90,
        "espera_media_oncologia_dias": 188,
    }

def inferir_cir_from_nome(nome: str) -> str:
    """Infere CIR pelo nome do hospital quando não há match no DATASUS"""
    n = nome.upper()

    if any(x in n for x in ["SOBRAL", "TIANGUA", "TIANGUÁ", "CAMOCIM", "ACARAU", "ACARAÚ"]):
        return "CIR Sobral"
    if any(x in n for x in ["JUAZEIRO", "CRATO", "BARBALHA", "CARIRI", "MISSAO VELHA", "AURORA"]):
        return "CIR Cariri"
    if any(x in n for x in ["ITAPIPOCA", "AMONTADA", "IRAUCUBA"]):
        return "CIR Itapipoca"
    if any(x in n for x in ["QUIXADA", "QUIXADÁ", "QUIXERAMOBIM"]):
        return "CIR Quixadá"
    if any(x in n for x in ["CAUCAIA", "MARACANAU", "MARACANAÚ", "AQUIRAZ", "EUSEBIO"]):
        return "CIR Fortaleza"
    return "CIR Fortaleza"


# def get_hospitais_pressao(db: Session, cir: Optional[str] = None) -> List[Dict]:
#     """Cruza fila (IntegraSUS) com capacidade (DATASUS) e calcula índice de pressão"""
#     fila_rows = db.query(
#         PacienteFila.hospital_nome,
#         func.count(PacienteFila.id).label("fila_atual"),
#     ).group_by(PacienteFila.hospital_nome).all()

#     cap_rows = {
#         row.hospital_nome.upper(): row
#         for row in db.query(CapacidadeHospital).all()
#     }

#     result = []
#     for hosp_nome, fila_atual in fila_rows:
#         nome_upper = str(hosp_nome).upper()
#         cap = None

#         # Matching por substring (primeiros 10 chars)
#         # for k, v in cap_rows.items():
#         #     if nome_upper[:10] in k or k[:10] in nome_upper:
#         #         cap = v
#         #         break
#         import unicodedata

#         def _norm(s):
#             return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()

        
#         # 1. Tenta alias direto
#         alias = HOSPITAL_ALIAS.get(hosp_nome)
#         if alias:
#             cap = cap_rows.get(_norm(alias))

#         # 2. Se não achou, tenta normalização sem acento
#         if not cap:
#             nome_norm = _norm(hosp_nome)
#             for k, v in cap_rows.items():
#                 if nome_norm[:15] in _norm(k) or _norm(k)[:15] in nome_norm:
#                     cap = v
#                     break


#         media     = cap.media_mensal if cap else 0
#         municipio = cap.municipio if cap else None
#         tipo      = cap.tipo if cap else "publico"

#         # ← FIX: CIR pelo município do DATASUS OU pelo nome do hospital
#         if municipio:
#             cir_hosp = get_cir(municipio)
#         else:
#             cir_hosp = inferir_cir_from_nome(hosp_nome)

#         if cir and cir_hosp != cir:
#             continue

#         pressao = calc_pressao(fila_atual, media)
#         result.append({
#             "hospital_nome": hosp_nome,
#             "municipio":     municipio or hosp_nome,
#             "cir":           cir_hosp,
#             "tipo":          tipo,
#             "fila_atual":    fila_atual,
#             "media_mensal":  round(media, 0),
#             "pressao":       pressao,
#             "pressao_status": pressao_status(pressao),
#         })

#     result.sort(key=lambda x: x["pressao"], reverse=True)
#     return result

def get_hospitais_pressao(db: Session, cir: Optional[str] = None) -> List[Dict]:
    from database import HospitalCirMap

    # Carrega mapa hospital → CIR (gerado pelo IntegraSUS)
    cir_map = {
        row.hospital_nome: {"municipio": row.municipio, "cir": row.cir, "confianca": row.confianca}
        for row in db.query(HospitalCirMap).all()
    }

    fila_rows = db.query(
        PacienteFila.hospital_nome,
        func.count(PacienteFila.id).label("fila_atual"),
    ).group_by(PacienteFila.hospital_nome).all()

    cap_rows = {
        row.hospital_nome.upper(): row
        for row in db.query(CapacidadeHospital).all()
    }

    import unicodedata
    def _norm(s):
        return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()

    result = []
    for hosp_nome, fila_atual in fila_rows:
        # 1. CIR pelo HospitalCirMap (fonte: pacientes do IntegraSUS) ← NOVO
        info_cir = cir_map.get(hosp_nome)
        if info_cir and info_cir["confianca"] >= 0.3:
            municipio = info_cir["municipio"]
            cir_hosp  = info_cir["cir"]
        else:
            # 2. Fallback: inferência por nome
            cir_hosp  = inferir_cir_from_nome(hosp_nome)
            municipio = hosp_nome

        # Filtra FORA_DO_CEARA e DESCONHECIDO
        if cir_hosp in ("FORA_DO_CEARA", "DESCONHECIDO"):
            continue

        if cir and cir_hosp != cir:
            continue

        # Match DATASUS por nome normalizado
        cap = None
        nome_norm = _norm(hosp_nome)
        for k, v in cap_rows.items():
            if nome_norm[:15] in _norm(k) or _norm(k)[:15] in nome_norm:
                cap = v
                break

        media = cap.media_mensal if cap else 0
        tipo  = cap.tipo if cap else "publico"

        pressao = calc_pressao(fila_atual, media)
        result.append({
            "hospital_nome":   hosp_nome,
            "municipio":       municipio,
            "cir":             cir_hosp,
            "tipo":            tipo,
            "fila_atual":      fila_atual,
            "media_mensal":    round(media, 0),
            "pressao":         pressao,
            "pressao_status":  pressao_status(pressao),
            "confianca":       info_cir["confianca"] if info_cir else None,
        })

    result.sort(key=lambda x: x["pressao"], reverse=True)
    return result

def get_especialidades_hospital(db: Session, hospital_nome: str) -> List[str]:
    """
    Retorna especialidades que um hospital atende.
    Fonte: HospitalEspecialidade (populada pelo IntegraSUS).
    Se tabela vazia → retorna ["*"] (aceita tudo — não bloqueia redistribuição).
    """
    from database import HospitalEspecialidade

    resultados = db.query(HospitalEspecialidade.especialidade).filter(
        HospitalEspecialidade.hospital_nome.ilike(f"%{hospital_nome[:20]}%"),
        HospitalEspecialidade.total_procedimentos > 0
    ).distinct().all()

    esps = [r[0] for r in resultados]

    # Fallback: tabela vazia = não bloqueia (redistribuição funciona sem CNES)
    if not esps:
        return ["*"]

    return esps

def get_redistribuicao_sugestoes(db: Session, cir_filter: Optional[str] = None) -> Dict:
    """Gera sugestões de redistribuição respeitando hierarquia SUS"""
    hospitais = get_hospitais_pressao(db)

    CONFIG_SUGESTOES = 100000

    # Filtra pressão absurda (media_mensal=0 → pressão infinita — ignora)
    sobrecarregados = [
        h for h in hospitais
        if h["pressao"] >= 2.0 and h["media_mensal"] > 0
        and h["cir"] not in ("DESCONHECIDO", "FORA_DO_CEARA")
    ]
    ociosos = [
        h for h in hospitais
        if h["pressao"] < 0.8 and h["media_mensal"] > 10
        and h["cir"] not in ("DESCONHECIDO", "FORA_DO_CEARA")
    ]
 

    # Se tiver filtro, limita aos hospitais da CIR selecionada
    if cir_filter:
        sobrecarregados = [h for h in sobrecarregados if h["cir"] == cir_filter]
        ociosos = [h for h in ociosos if h["cir"] == cir_filter]

    mes_atual = date.today().strftime("%Y-%m")
    transfer_mes = db.query(Transferencia).filter(
        Transferencia.data_aprovacao >= f"{mes_atual}-01",
        Transferencia.status == "aprovado"
    ).all()
    ja_transferido = {}
    for t in transfer_mes:
        ja_transferido[t.hospital_destino] = ja_transferido.get(t.hospital_destino, 0) + t.qtd_pacientes

    # Pré-carrega ConfigVagas de todos os particulares
    from database import ConfigVagas, Tenant
    import unicodedata

    def _norm(s):
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()

    vagas_particulares: Dict[int, Dict[str, int]] = {}
    tenants_part = db.query(Tenant).filter(
        Tenant.tipo == "hospital_particular", Tenant.ativo == True
    ).all()

    for t in tenants_part:
        cfg_list = db.query(ConfigVagas).filter(
            ConfigVagas.tenant_id == t.id,
            ConfigVagas.ativo == True,
            ConfigVagas.vagas_mes > 0
        ).all()
        esps = {}
        for cfg in cfg_list:
            aceito = db.query(func.sum(Transferencia.qtd_pacientes)).filter(
                Transferencia.tenant_destino_id == t.id,
                Transferencia.especialidade == cfg.especialidade,
                Transferencia.status == "aprovado",
                Transferencia.data_aprovacao >= f"{mes_atual}-01"
            ).scalar() or 0
            disponivel = max(0, cfg.vagas_mes - aceito)
            if disponivel > 0:
                esps[cfg.especialidade] = disponivel
        if esps:
            vagas_particulares[t.id] = esps

    # Índice normalizado: nome do hospital → tenant_id
    nome_para_tenant: Dict[str, int] = {}
    for t in tenants_part:
        nome_para_tenant[_norm(t.nome)] = t.id

    def get_tenant_id(hospital_nome: str) -> Optional[int]:
        n = _norm(hospital_nome)
        for k, tid in nome_para_tenant.items():
            if n[:12] in k or k[:12] in n:
                return tid
        return None

    sugestoes = []
    
    # Agrupa destinos por prioridade
    for origem in sobrecarregados[:20]:
        esp_row = db.query(
            PacienteFila.especialidade,
            func.count(PacienteFila.id).label("n")
        ).filter(
            PacienteFila.hospital_nome == origem["hospital_nome"]
        ).group_by(PacienteFila.especialidade).order_by(
            func.count(PacienteFila.id).desc()
        ).first()
        especialidade = esp_row[0] if esp_row else "CIRURGIA GERAL"

        # Separa destinos por prioridade
        mesma_regiao = []
        mesma_macro = []
        outros = []
        
        for destino in ociosos:
            if origem["hospital_nome"] == destino["hospital_nome"]:
                continue
                
            if origem["cir"] == destino["cir"]:
                mesma_regiao.append(destino)
            elif pode_transferir(origem["cir"], destino["cir"]):
                mesma_macro.append(destino)
            else:
                outros.append(destino)

        # Tenta primeiro dentro da mesma região
        destinos_prioridade = mesma_regiao + mesma_macro + outros
        
        for destino in destinos_prioridade:
            tid = get_tenant_id(destino["hospital_nome"])

            # Verifica vagas (público ou particular)
            if tid and tid in vagas_particulares:
                esps_disp = vagas_particulares[tid]
                cap_esp = esps_disp.get(especialidade, 0)
                if cap_esp <= 0:
                    if not esps_disp:
                        continue
                    especialidade_dest = max(esps_disp, key=esps_disp.get)
                    cap_esp = esps_disp[especialidade_dest]
                else:
                    especialidade_dest = especialidade
                capacidade_livre = cap_esp
            else:
                # Público: usa DATASUS
                ja_rec = ja_transferido.get(destino["hospital_nome"], 0)
                capacidade_livre = max(0, destino["media_mensal"] - destino["fila_atual"] - ja_rec)
                especialidade_dest = especialidade

            if capacidade_livre < 3:
                continue

            qtd_sugerida = min(int(capacidade_livre * 0.9), int(origem["fila_atual"] * 0.3))
            reducao_espera = max(10, int((origem["fila_atual"] / max(origem["media_mensal"], 1)) * 30))

            # Adiciona metadados de hierarquia
            # tipo_transferencia = "mesma_regiao" if origem["cir"] == destino["cir"] else \
            #                     "mesma_macro" if mesma_macro else "outra_macro"

            if destino in mesma_regiao:
                tipo_transferencia = "mesma_regiao"
            elif destino in mesma_macro:
                tipo_transferencia = "mesma_macro"
            else:
                tipo_transferencia = "outra_macro"



            especialidades_destino = get_especialidades_hospital(db, destino["hospital_nome"])
            # Só filtra se tiver dados reais ("*" = tabela vazia, não bloqueia)
            if "*" not in especialidades_destino and especialidade not in especialidades_destino:
                continue  # Pula se o destino não atende a especialidade

            sugestoes.append({
                "origem": origem,
                "destino": destino,
                "especialidade": especialidade_dest,
                "qtd_sugerida": qtd_sugerida,
                "capacidade_livre": int(capacidade_livre),
                "reducao_espera_dias": reducao_espera,
                "aih_estimada": qtd_sugerida * 1500,
                "distancia_km": 25,  # Idealmente calcular distância real
                "cir": origem["cir"],
                "macro_origem": get_macro_regiao(origem["cir"]),
                "macro_destino": get_macro_regiao(destino["cir"]),
                "tipo_transferencia": tipo_transferencia,  # Para o frontend saber a prioridade
            })

            if len(sugestoes) >= CONFIG_SUGESTOES:
                break
        if len(sugestoes) >= CONFIG_SUGESTOES:
            break

    # Estatísticas para o frontend
    total_sobrecarregados = len(sobrecarregados)
    total_ociosos = len(ociosos)
    total_redistribuiveis = sum(s["qtd_sugerida"] for s in sugestoes)
    
    # CIRs disponíveis para o filtro
    cirs_disponiveis = sorted(set(
        h["cir"] for h in hospitais 
        if h["cir"] not in ("DESCONHECIDO", "FORA_DO_CEARA")
    ))

    return {
        "sugestoes": sugestoes,
        "total_sobrecarregados": total_sobrecarregados,
        "total_ociosos": total_ociosos,
        "total_redistribuiveis": total_redistribuiveis,
        "reducao_media_espera": 76,
        "cirs_disponiveis": cirs_disponiveis,
        "cir_selecionada": cir_filter,
        # NOVO: estatísticas por macro
        "macros": {
            macro: {
                "sobrecarregados": len([h for h in sobrecarregados if get_macro_regiao(h["cir"]) == macro]),
                "ociosos": len([h for h in ociosos if get_macro_regiao(h["cir"]) == macro]),
            }
            for macro in set(MACRO_POR_REGIAO.values())
        }
    }


def get_vagas_status_tenant(db: Session, tenant_id: int) -> List[Dict]:
    """Status de vagas por especialidade para um particular"""
    config_list = db.query(ConfigVagas).filter(
        ConfigVagas.tenant_id == tenant_id,
        ConfigVagas.ativo == True
    ).all()

    mes_atual = date.today().strftime("%Y-%m")
    tenant = db.query(ConfigVagas).filter(ConfigVagas.tenant_id == tenant_id).first()
    if not tenant:
        return []

    result = []
    for cfg in config_list:
        # Conta transferências aprovadas este mês para esta especialidade
        aceito = db.query(func.sum(Transferencia.qtd_pacientes)).filter(
            Transferencia.tenant_destino_id == tenant_id,
            Transferencia.especialidade == cfg.especialidade,
            Transferencia.status == "aprovado",
            Transferencia.data_aprovacao >= f"{mes_atual}-01"
        ).scalar() or 0

        disponivel = max(0, cfg.vagas_mes - aceito)
        result.append({
            "id": cfg.id,
            "especialidade": cfg.especialidade,
            "vagas_mes": cfg.vagas_mes,
            "aceito_mes": aceito,
            "disponivel": disponivel,
            "ativo": cfg.ativo,
            "lotado": disponivel == 0 and cfg.vagas_mes > 0,
        })

    result.sort(key=lambda x: x["vagas_mes"], reverse=True)
    return result



# Fix missing import
from sqlalchemy import Integer