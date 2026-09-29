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
from services import redistribuicao as rd

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


# Valor fixo por AIH usado nas simulações de redistribuição (não é valor pago pelo SUS).
VALOR_AIH_SIMULADO = 1500


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
        "especialidades_top": [{"nome": e, "total": n} for e, n in esp_counts],
        # B05: sem avaliação calculada → null + status. Metas do projeto vêm separadas.
        "reducao_estimada_pct": None,
        "reducao_estimada_status": "nao_validado",
        "meta_reducao_espera_pct": 40,
        "acuracia_mape": None,
        "acuracia_mape_status": "nao_validado",
        "meta_mape_pct": 15,
        "horizonte_dias": 90,
        # A fila IntegraSUS importada não traz data de entrada confiável: espera não é calculada.
        "espera_media_oncologia_dias": None,
        "espera_media_oncologia_status": "nao_disponivel",
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

def _cir_fallback_fila(db: Session) -> Dict[str, str]:
    """CIR dos nomes da fila SEM CNES: HospitalCirMap (município de residência dos pacientes)."""
    from database import HospitalCirMap
    return {r.hospital_nome: r.cir for r in db.query(HospitalCirMap).all()
            if r.cir and (r.confianca or 0) >= 0.3}


def get_hospitais_pressao(db: Session, cir: Optional[str] = None) -> List[Dict]:
    """Pressão (fila ÷ produção SIH) e ociosidade ESTIMADA por estabelecimento (CNES).
    Metodologia: services/redistribuicao.py e docs/dados/redistribuicao-v1.md."""
    base = rd.carregar_base(db)
    hospitais = rd.estimar_hospitais(base)
    fallback = _cir_fallback_fila(db) if base.fila_sem_cnes else {}
    for h in hospitais:
        if not h.get("cnes") and h["hospital_nome"] in fallback:
            h["cir"] = fallback[h["hospital_nome"]]
            h["cir_fonte"] = "residencia_pacientes"
    hospitais = [h for h in hospitais if h["cir"] != "FORA_DO_CEARA"]
    if cir:
        hospitais = [h for h in hospitais if h["cir"] == cir]
    return hospitais


def _vagas_declaradas(db: Session) -> List[Dict]:
    """Vagas SUS informadas por hospitais particulares (capacidade confirmada pelo hospital)."""
    from database import Tenant
    mes_atual = date.today().strftime("%Y-%m")
    out = []
    for t in db.query(Tenant).filter(Tenant.tipo == "hospital_particular", Tenant.ativo == True).all():  # noqa: E712
        for cfg in db.query(ConfigVagas).filter(ConfigVagas.tenant_id == t.id, ConfigVagas.ativo == True,  # noqa: E712
                                                ConfigVagas.vagas_mes > 0).all():
            aceito = db.query(func.sum(Transferencia.qtd_pacientes)).filter(
                Transferencia.tenant_destino_id == t.id,
                Transferencia.especialidade == cfg.especialidade,
                Transferencia.status == "aprovado",
                Transferencia.data_aprovacao >= f"{mes_atual}-01",
            ).scalar() or 0
            disp = max(0, cfg.vagas_mes - aceito)
            if disp > 0:
                out.append({"tenant_id": t.id, "hospital_nome": t.nome, "cir": t.cir,
                            "municipio": t.municipio_gestor, "especialidade": rd.especialidade_serie(cfg.especialidade),
                            "disponivel": disp})
    return out


def get_redistribuicao_sugestoes(db: Session, cir_filter: Optional[str] = None) -> Dict:
    """Sugestões de redistribuição dentro da MESMA CIR, com capacidade estimada (CNES + SIH)
    ou declarada (vagas SUS do hospital particular). Tudo é ESTIMADO e apoio à decisão."""
    base = rd.carregar_base(db)
    hospitais = rd.estimar_hospitais(base)

    mes_atual = date.today().strftime("%Y-%m")
    ja_transferido: Dict[str, int] = {}
    for t in db.query(Transferencia).filter(Transferencia.data_aprovacao >= f"{mes_atual}-01",
                                            Transferencia.status == "aprovado").all():
        ja_transferido[t.hospital_destino] = ja_transferido.get(t.hospital_destino, 0) + t.qtd_pacientes

    sugestoes = rd.sugerir_redistribuicao(hospitais, vagas_declaradas=_vagas_declaradas(db),
                                          ja_transferido=ja_transferido, valor_aih=VALOR_AIH_SIMULADO)
    for s in sugestoes:
        s["macro_origem"] = get_macro_regiao(s["origem"]["cir"])
        s["macro_destino"] = get_macro_regiao(s["destino"]["cir"])

    validos = [h for h in hospitais if h["cir"] not in ("DESCONHECIDO", "FORA_DO_CEARA")]
    if cir_filter:
        sugestoes = [s for s in sugestoes if s["cir"] == cir_filter]
        validos = [h for h in validos if h["cir"] == cir_filter]
    sobrecarregados = [h for h in validos if h["pressao_status"] in ("critico", "alerta") and h["fila_atual"] > 0]
    com_ociosidade = [h for h in validos if h.get("ociosidade_estimada_mes", 0) >= 1]

    return {
        "sugestoes": sugestoes,
        "total_sobrecarregados": len(sobrecarregados),
        "total_ociosos": len(com_ociosidade),
        "hospitais_com_ociosidade": len(com_ociosidade),
        "ociosidade_total_mes": int(sum(h["ociosidade_estimada_mes"] for h in com_ociosidade)),
        "total_redistribuiveis": int(sum(s["qtd_sugerida"] for s in sugestoes)),
        "total_redistribuiveis_periodo": "por mês",
        "sugestoes_com_vinculo_provisorio": sum(1 for s in sugestoes if s["vinculo_provisorio"]),
        "reducao_media_espera": None,
        "reducao_media_espera_status": "nao_validado",
        "cirs_disponiveis": sorted({h["cir"] for h in hospitais if h["cir"] not in ("DESCONHECIDO", "FORA_DO_CEARA")}),
        "cir_selecionada": cir_filter,
        "natureza": "estimado",
        "regra_regional": "mesma_cir",
        "metodologia": rd.metodologia(base),
        "macros": {
            macro: {
                "sobrecarregados": len([h for h in sobrecarregados if get_macro_regiao(h["cir"]) == macro]),
                "ociosos": len([h for h in com_ociosidade if get_macro_regiao(h["cir"]) == macro]),
            }
            for macro in set(MACRO_POR_REGIAO.values())
        },
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