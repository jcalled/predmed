"""
PREDMED — Redistribuição v1: pressão e ociosidade ESTIMADAS por estabelecimento (CNES).

Metodologia e hipóteses: docs/dados/redistribuicao-v1.md. Resumo:
  - fila por hospital × especialidade: IntegraSUS (pacientes_fila.cnes, vínculo nome→CNES;
    vínculos não-ALTA são provisórios e sinalizados);
  - produção: SIH-RD por CNES (tabela producao_cirurgica_cnes, AIH principais do grupo 04,
    sem obstetrícia), 24 competências;
  - capacidade: CNES (cnes_capacidade: salas cirúrgicas, leitos cirúrgicos SUS, habilitações);
  - ociosidade estimada = menor de três folgas (demonstrada no SIH, salas, leitos) — conservador;
  - sugestões só dentro da MESMA CIR (ADS do município do estabelecimento no CNES), só para destino
    que já realiza a especialidade (produção SIH) e tem a habilitação exigida (onco/cardio/neuro).

Tudo aqui é apoio à decisão e ESTIMADO: não mede disponibilidade real (agenda, equipe, turnos),
que depende de confirmação do hospital. Nenhum dado de paciente sai deste módulo (só contagens).

As funções `estimar_hospitais` e `sugerir_redistribuicao` são puras (testáveis com dados
sintéticos); `carregar_base` lê o banco.
"""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

VERSAO = "redistribuicao-v1"

# Parâmetros (hipóteses explícitas; ver docs/dados/redistribuicao-v1.md)
PARAMS: Dict[str, float] = {
    "janela_media_meses": 12,           # média mensal de produção (pressão e compatibilidade)
    "janela_recente_meses": 6,          # produção recente (base da ociosidade)
    "janela_demonstrada_meses": 24,     # maior média móvel de 3 meses = capacidade demonstrada
    "turnos_por_dia": 2,                # salas: 2 turnos de 6 h
    "dias_uteis_mes": 22,
    "cirurgias_por_sala_turno": 2,      # → 88 cirurgias/sala/mês nominais
    "permanencia_media_dias": 3.0,      # leitos cirúrgicos: permanência média pós-operatória
    "ocupacao_alvo_leitos": 0.85,
    "pressao_origem_min": 1.5,          # origem: fila da especialidade > 1,5 mês da própria produção
    "meses_fila_retidos_origem": 1.5,   # a origem mantém 1,5 mês de fila; só o excedente é redistribuível
    "pressao_destino_max": 1.0,         # destino: fila própria da especialidade ≤ 1 mês de produção
    "producao_min_especialidade": 2.0,  # destino realiza ≥ 2 AIH/mês da especialidade (média 12 m)
    "fator_expansao_especialidade": 0.5,  # destino absorve até +50% da sua produção mensal na especialidade
    "queda_estrutural_fracao": 0.5,     # produção recente < 50% da demonstrada → não conta ociosidade
    "qtd_minima_sugestao": 3,           # sugestões menores que 3 pacientes/mês não são exibidas
}

HABILITACAO_EXIGIDA = {
    "ONCOLOGIA": "hab_oncologia",
    "CARDIOVASCULAR": "hab_cardiovascular",
    "NEUROLOGIA": "hab_neurocirurgia",
}

CONFIANCA_NUMERICA = {"ALTA": 1.0, "MANUAL": 1.0, "PROVISORIO_MEDIA": 0.6,
                      "PROVISORIO_AMBIGUO": 0.4, "PROVISORIO_BAIXA": 0.3}

HIPOTESES = [
    "Alvo: capacidade cirúrgica SUS em regime de internação (SIH-RD, AIH principais do grupo SIGTAP 04, sem obstetrícia). "
    "Cirurgias ambulatoriais (SIA/APAC) e atendimentos não SUS não entram: a ocupação real das salas é maior que a medida.",
    "Ociosidade estimada = menor valor entre (a) capacidade demonstrada no SIH (maior média móvel de 3 meses em 24 meses) "
    "menos a produção dos últimos 6 meses; (b) salas cirúrgicas CNES × 2 turnos × 22 dias × 2 cirurgias × fração SUS dos "
    "leitos cirúrgicos, menos a produção recente; (c) leitos cirúrgicos SUS × 30 dias ÷ 3 dias de permanência × 85% de "
    "ocupação, menos a produção recente. É uma estimativa conservadora; não é vaga confirmada.",
    "Pressão = fila atual (IntegraSUS) ÷ produção cirúrgica mensal média do mesmo estabelecimento (12 meses SIH). "
    "Não é tempo de espera.",
    "Sugestões só entre estabelecimentos da mesma CIR (ADS do município do estabelecimento no CNES).",
    "Compatibilidade: o destino já realizou a especialidade no SIH (≥ 2 AIH/mês em média) e, para oncologia, "
    "cardiovascular e neurologia, tem a habilitação CNES correspondente vigente.",
    "Origem: especialidade com fila maior que 1,5 mês da própria produção; só o excedente acima de 1,5 mês é redistribuível. "
    "Destino: fila própria da especialidade ≤ 1 mês de produção; recebe no máximo +50% da sua produção mensal na "
    "especialidade e nunca mais que a ociosidade total estimada (compartilhada entre especialidades).",
    "Produção recente abaixo de 50% da capacidade demonstrada indica provável fechamento, reforma, troca de CNES ou "
    "atraso de faturamento: o estabelecimento é sinalizado e não conta ociosidade até confirmação.",
    "Vagas declaradas por hospital particular (Configurações → Vagas SUS) contam como capacidade CONFIRMADA pelo hospital, "
    "não verificada no SIH, e têm precedência sobre a capacidade estimada.",
    "Vínculo nome da fila → CNES: vínculos não-ALTA são provisórios (sinalizados em cada hospital e sugestão).",
    "Quantidades são por mês; sugestões com menos de 3 pacientes/mês não são exibidas. Transferências aprovadas no mês corrente reduzem a capacidade do destino.",
]


def norm(s: Optional[str]) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper().strip()


def especialidade_serie(esp_fila: Optional[str]) -> str:
    """Especialidade da fila → nome da série SIH (mesmo mapa da previsão)."""
    e = norm(esp_fila)
    return {"OTORRINO MEDIA COMPLEXIDADE": "OTORRINO", "OTORRINO E PNEUMOLOGIA": "OTORRINO"}.get(e, e)


def pressao_status(p: float) -> str:
    if p >= 3.0:
        return "critico"
    if p >= 1.5:
        return "alerta"
    if p >= 0.5:
        return "normal"
    return "ocioso"


def _media(vals: List[float]) -> float:
    return float(sum(vals) / len(vals)) if vals else 0.0


def _tipo(natureza: Optional[str]) -> str:
    n = norm(natureza)
    if n.startswith("PUBLIC"):
        return "publico"
    if n.startswith("SEM FINS"):
        return "filantropico"
    if n:
        return "particular"
    return "publico"


@dataclass
class Base:
    """Entradas agregadas (sem dado individual)."""
    estabelecimentos: Dict[str, Dict]                     # cnes → linha cnes_capacidade (dict)
    producao: Dict[str, Dict[str, Dict[str, int]]]        # cnes → competência → especialidade → AIHs (todas)
    competencias: List[str]                               # competências SIH em ordem
    fila: Dict[str, Dict[str, int]]                       # cnes → especialidade(série) → pacientes
    nome_fila: Dict[str, str] = field(default_factory=dict)       # cnes → nome mais frequente na fila
    vinculo: Dict[str, str] = field(default_factory=dict)         # cnes → pior confiança do vínculo
    fila_sem_cnes: Dict[str, int] = field(default_factory=dict)   # nome da fila → pacientes sem CNES
    competencia_cnes: Optional[str] = None


# ──────────────────────────────────────────────
# 1. Estimativa por estabelecimento
# ──────────────────────────────────────────────
def estimar_estabelecimento(cnes: str, est: Dict, prod_mensal: Dict[str, Dict[str, int]],
                            competencias: List[str], fila_esp: Dict[str, int],
                            params: Dict = PARAMS) -> Dict:
    p = params
    comps = competencias
    tot = [float(sum(v for e, v in prod_mensal.get(c, {}).items() if e != "OBSTETRICIA")) for c in comps]
    n_media = int(p["janela_media_meses"])
    media12 = _media(tot[-n_media:])
    recente = _media(tot[-int(p["janela_recente_meses"]):])
    dem = tot[-int(p["janela_demonstrada_meses"]):]
    moveis = [_media(dem[i:i + 3]) for i in range(0, max(0, len(dem) - 2))]
    cap_demonstrada = max(moveis) if moveis else recente

    esp_media: Dict[str, float] = {}
    for c in comps[-n_media:]:
        for e, v in prod_mensal.get(c, {}).items():
            if e != "OBSTETRICIA":
                esp_media[e] = esp_media.get(e, 0.0) + v
    esp_media = {e: round(v / max(1, len(comps[-n_media:])), 1) for e, v in esp_media.items()}

    salas = int(est.get("salas_cirurgicas") or 0)
    le = int(est.get("leitos_cirurgicos_exist") or 0)
    ls = int(est.get("leitos_cirurgicos_sus") or 0)
    tipo = _tipo(est.get("natureza"))
    if tipo == "publico":
        fracao_sus = 1.0 if est.get("vinculo_sus", True) else 0.0
    else:
        fracao_sus = (ls / le) if le > 0 else (1.0 if est.get("vinculo_sus") else 0.0)
    cap_salas = salas * p["turnos_por_dia"] * p["dias_uteis_mes"] * p["cirurgias_por_sala_turno"] * fracao_sus
    cap_leitos = ls * 30.0 / p["permanencia_media_dias"] * p["ocupacao_alvo_leitos"]

    apto = bool(est.get("vinculo_sus")) and bool(est.get("centro_cirurgico")) and salas > 0
    folgas = {
        "demonstrada": max(0.0, cap_demonstrada - recente),
        "salas": max(0.0, cap_salas - recente),
        "leitos": max(0.0, cap_leitos - recente),
    }
    # Queda forte da produção recente costuma ser fechamento, reforma, troca de CNES ou atraso de
    # faturamento — não ociosidade. Conservador: não conta como capacidade livre (confirmar).
    queda = bool(cap_demonstrada > 0 and recente < p["queda_estrutural_fracao"] * cap_demonstrada)
    ociosidade = int(math.floor(min(folgas.values()))) if apto and not queda else 0
    limitante = ("queda_de_producao" if queda else min(folgas, key=folgas.get)) if apto else None

    fila_total = int(sum(fila_esp.values()))
    if media12 <= 0:
        pressao = 99.0 if fila_total > 0 else 0.0
    else:
        pressao = round(fila_total / media12, 2)
    status = pressao_status(pressao)
    if status == "ocioso" and ociosidade < 1:
        status = "normal"   # fila baixa, mas sem ociosidade estimada

    return {
        "cnes": cnes,
        "tipo": tipo,
        "natureza": est.get("natureza"),
        "fila_atual": fila_total,
        "fila_por_especialidade": dict(sorted(fila_esp.items(), key=lambda x: -x[1])),
        "media_mensal": round(media12, 0),
        "producao_media_12m": round(media12, 1),
        "producao_recente_mes": round(recente, 1),
        "producao_por_especialidade_mes": esp_media,
        "pressao": pressao,
        "pressao_status": status,
        "salas_cirurgicas": salas,
        "leitos_cirurgicos_sus": ls,
        "fracao_sus": round(fracao_sus, 2),
        "capacidade_demonstrada_mes": round(cap_demonstrada, 1),
        "capacidade_salas_mes": round(cap_salas, 1),
        "capacidade_leitos_mes": round(cap_leitos, 1),
        "utilizacao_salas_pct": round(recente / cap_salas * 100, 1) if cap_salas > 0 else None,
        "cadastro_salas_inconsistente": bool(cap_salas > 0 and recente > cap_salas),
        "apto_receber": apto and not queda,
        "queda_producao_recente": queda,
        "ociosidade_estimada_mes": ociosidade,
        "ociosidade_limitada_por": limitante,
        "habilitacoes": {k: bool(est.get(k)) for k in
                         ("hab_oncologia", "hab_cardiovascular", "hab_neurocirurgia",
                          "hab_traumato_ortopedia", "hab_oftalmologia", "hab_pnrf_eletivas")},
        "natureza_dado": "estimado",
    }


def estimar_hospitais(base: Base, params: Dict = PARAMS) -> List[Dict]:
    """Um registro por CNES (da fila ou com produção SIH e centro cirúrgico) + nomes da fila sem CNES."""
    cnes_set = set(base.fila) | {c for c in base.producao if c in base.estabelecimentos}
    out = []
    for cnes in cnes_set:
        est = base.estabelecimentos.get(cnes, {})
        h = estimar_estabelecimento(cnes, est, base.producao.get(cnes, {}), base.competencias,
                                    base.fila.get(cnes, {}), params)
        vinc = base.vinculo.get(cnes) if cnes in base.fila else None
        h.update({
            "hospital_nome": base.nome_fila.get(cnes) or est.get("nome_fantasia") or f"CNES {cnes}",
            "nome_cnes": est.get("nome_fantasia"),
            "municipio": est.get("municipio") or "—",
            "cir": est.get("cir_ads_predmed") or "DESCONHECIDO",
            "cir_fonte": "cnes" if est.get("cir_ads_predmed") else "sem_cnes",
            "vinculo_cnes": vinc,
            "vinculo_provisorio": bool(vinc and vinc.startswith("PROVISORIO")),
            "confianca": CONFIANCA_NUMERICA.get(vinc or "ALTA", 0.5) if est else None,
            "na_fila_integrasus": cnes in base.fila,
        })
        out.append(h)
    for nome, n in base.fila_sem_cnes.items():
        out.append({
            "cnes": None, "hospital_nome": nome, "nome_cnes": None, "municipio": "—", "cir": "DESCONHECIDO",
            "cir_fonte": "sem_cnes", "tipo": "publico", "natureza": None, "fila_atual": n,
            "fila_por_especialidade": {}, "media_mensal": 0, "producao_media_12m": 0.0,
            "producao_recente_mes": 0.0, "producao_por_especialidade_mes": {}, "pressao": 99.0,
            "pressao_status": "critico", "salas_cirurgicas": 0, "leitos_cirurgicos_sus": 0,
            "apto_receber": False, "ociosidade_estimada_mes": 0, "vinculo_cnes": "SEM_CNES",
            "vinculo_provisorio": True, "confianca": None, "na_fila_integrasus": True,
            "natureza_dado": "estimado",
        })
    out.sort(key=lambda x: (-x["pressao"], -x["fila_atual"]))
    return out


# ──────────────────────────────────────────────
# 2. Sugestões (mesma CIR, compatibilidade, capacidade)
# ──────────────────────────────────────────────
def destino_compativel(dest: Dict, esp: str, params: Dict = PARAMS) -> Tuple[bool, str]:
    if not dest.get("apto_receber"):
        return False, "sem centro cirúrgico/salas ou sem vínculo SUS no CNES"
    prod = dest.get("producao_por_especialidade_mes", {}).get(esp, 0.0)
    if prod < params["producao_min_especialidade"]:
        return False, f"não realiza {esp} no SIH (média {prod:.1f}/mês)"
    hab = HABILITACAO_EXIGIDA.get(esp)
    if hab and not dest.get("habilitacoes", {}).get(hab):
        return False, f"sem habilitação CNES ({hab})"
    fila_d = dest.get("fila_por_especialidade", {}).get(esp, 0)
    if fila_d > params["pressao_destino_max"] * prod:
        return False, "fila própria da especialidade acima do limite"
    return True, "ok"


def demandas_origem(hospitais: Iterable[Dict], params: Dict = PARAMS) -> List[Dict]:
    """(hospital, especialidade) com pressão acima do limite e excedente redistribuível."""
    out = []
    for h in hospitais:
        if not h.get("cnes") or h.get("cir") in (None, "DESCONHECIDO", "FORA_DO_CEARA"):
            continue
        for esp, fila in h.get("fila_por_especialidade", {}).items():
            prod = h.get("producao_por_especialidade_mes", {}).get(esp, 0.0)
            pressao = (fila / prod) if prod > 0 else float("inf")
            if pressao < params["pressao_origem_min"]:
                continue
            retido = math.ceil(params["meses_fila_retidos_origem"] * prod)
            excedente = max(0, fila - retido)
            if excedente > 0:
                out.append({"hospital": h, "especialidade": esp, "fila": fila, "producao_mes": prod,
                            "pressao": pressao, "excedente": excedente})
    out.sort(key=lambda d: (-d["pressao"] if math.isfinite(d["pressao"]) else -1e9, -d["fila"]))
    return out


def sugerir_redistribuicao(hospitais: List[Dict], params: Dict = PARAMS,
                           vagas_declaradas: Optional[List[Dict]] = None,
                           ja_transferido: Optional[Dict[str, int]] = None,
                           valor_aih: float = 0.0) -> List[Dict]:
    """Aloca o excedente das origens na ociosidade dos destinos da MESMA CIR.

    vagas_declaradas: [{"tenant_id", "hospital_nome", "cir", "especialidade", "disponivel"}]
      (capacidade confirmada pelo hospital; precede a estimada).
    ja_transferido: hospital_nome do destino → pacientes já aprovados no mês.
    Garantias: qtd por origem×especialidade ≤ excedente ≤ fila; soma por destino ≤ ociosidade.
    """
    ja_transferido = ja_transferido or {}
    folga = {h["cnes"]: max(0, int(h.get("ociosidade_estimada_mes", 0))
                            - int(ja_transferido.get(h["hospital_nome"], 0)))
             for h in hospitais if h.get("cnes")}
    folga_esp: Dict[Tuple[str, str], int] = {}
    declaradas = {}
    for v in vagas_declaradas or []:
        declaradas[(v["tenant_id"], v["especialidade"])] = int(v["disponivel"])
    por_cir: Dict[str, List[Dict]] = {}
    for h in hospitais:
        if h.get("cnes"):
            por_cir.setdefault(h["cir"], []).append(h)

    sugestoes = []
    for d in demandas_origem(hospitais, params):
        origem, esp = d["hospital"], d["especialidade"]
        restante = d["excedente"]
        # 1) capacidade declarada (confirmada pelo hospital) na mesma CIR
        for v in vagas_declaradas or []:
            if restante <= 0:
                break
            if v["cir"] != origem["cir"] or v["especialidade"] != esp:
                continue
            chave = (v["tenant_id"], esp)
            disp = declaradas.get(chave, 0)
            if disp <= 0:
                continue
            q = min(restante, disp)
            if q < params["qtd_minima_sugestao"]:
                continue
            declaradas[chave] = disp - q
            restante -= q
            destino = {"hospital_nome": v["hospital_nome"], "cnes": None, "cir": v["cir"],
                       "municipio": v.get("municipio") or "—", "tipo": "particular", "fila_atual": 0,
                       "media_mensal": 0, "pressao": 0.0, "pressao_status": "ocioso", "confianca": None}
            sugestoes.append(_sugestao(origem, destino, esp, q, disp, d, "declarada", None,
                                       v["tenant_id"], valor_aih))
        # 2) capacidade estimada (CNES + SIH) na mesma CIR
        candidatos = []
        for dest in por_cir.get(origem["cir"], []):
            if dest["cnes"] == origem["cnes"] or folga.get(dest["cnes"], 0) <= 0:
                continue
            ok, _ = destino_compativel(dest, esp, params)
            if not ok:
                continue
            prod_d = dest["producao_por_especialidade_mes"].get(esp, 0.0)
            chave = (dest["cnes"], esp)
            if chave not in folga_esp:
                folga_esp[chave] = int(math.floor(params["fator_expansao_especialidade"] * prod_d))
            vagas = min(folga[dest["cnes"]], folga_esp[chave])
            if vagas > 0:
                candidatos.append((vagas, dest))
        candidatos.sort(key=lambda x: (-x[0], x[1]["hospital_nome"]))
        for vagas, dest in candidatos:
            if restante <= 0:
                break
            vagas = min(folga[dest["cnes"]], folga_esp[(dest["cnes"], esp)])
            if vagas <= 0:
                continue
            q = min(restante, vagas)
            if q < params["qtd_minima_sugestao"]:
                continue
            folga[dest["cnes"]] -= q
            folga_esp[(dest["cnes"], esp)] -= q
            restante -= q
            sugestoes.append(_sugestao(origem, dest, esp, q, vagas, d, "estimada",
                                       dest.get("ociosidade_estimada_mes"), None, valor_aih))
    return sugestoes


def _sugestao(origem, destino, esp, q, capacidade, dem, natureza_cap, ociosidade, tenant_id, valor_aih):
    prod_o = dem["producao_mes"]
    # Heurística: meses de produção da origem que deixam de ficar na fila (simulado)
    reducao_dias = int(round(q / prod_o * 30)) if prod_o > 0 else None
    return {
        "origem": _resumo_hospital(origem),
        "destino": _resumo_hospital(destino),
        "especialidade": esp,
        "qtd_sugerida": int(q),
        "capacidade_livre": int(capacidade),
        "capacidade_natureza": natureza_cap,          # "estimada" (CNES+SIH) | "declarada" (hospital)
        "tenant_destino_id": tenant_id,
        "cnes_origem": origem.get("cnes"),
        "cnes_destino": destino.get("cnes"),
        "fila_especialidade_origem": int(dem["fila"]),
        "producao_especialidade_origem_mes": round(prod_o, 1),
        "excedente_origem": int(dem["excedente"]),
        "pressao_especialidade_origem": None if not math.isfinite(dem["pressao"]) else round(dem["pressao"], 2),
        "producao_especialidade_destino_mes": (destino.get("producao_por_especialidade_mes") or {}).get(esp),
        "ociosidade_destino_mes": ociosidade,
        "vinculo_provisorio": bool(origem.get("vinculo_provisorio") or destino.get("vinculo_provisorio")),
        "reducao_espera_dias": reducao_dias,
        "reducao_espera_origem": "simulado",
        "aih_estimada": int(q * valor_aih),
        "aih_estimada_origem": "simulado",
        "distancia_km": None,
        "cir": origem["cir"],
        "tipo_transferencia": "mesma_regiao",
        "natureza_dado": "estimado",
    }


_CAMPOS_RESUMO = ("hospital_nome", "cnes", "municipio", "cir", "tipo", "fila_atual", "media_mensal",
                  "pressao", "pressao_status", "confianca", "vinculo_cnes", "vinculo_provisorio",
                  "ociosidade_estimada_mes", "salas_cirurgicas", "leitos_cirurgicos_sus",
                  "producao_por_especialidade_mes")


def _resumo_hospital(h: Dict) -> Dict:
    return {k: h.get(k) for k in _CAMPOS_RESUMO}


# ──────────────────────────────────────────────
# 3. Mutirão (cenário simulado com limites garantidos)
# ──────────────────────────────────────────────
def plano_mutirao(fila_por_especialidade: Dict[str, int], sugestoes: List[Dict],
                  horizonte_meses: int = 3) -> Dict:
    """Cenário: repetir as sugestões mensais por `horizonte_meses`, limitado ao excedente/fila.

    Hipótese explícita: sem série de entradas na fila, a fila sem ação é considerada estável
    (entradas = saídas). Garantias: 0 ≤ redistribuíveis ≤ fila; 0 ≤ redução ≤ 100%.
    """
    teto_origem: Dict[Tuple[Optional[str], str], int] = {}
    mensal_origem: Dict[Tuple[Optional[str], str], int] = {}
    for s in sugestoes:
        k = (s["origem"]["hospital_nome"], s["especialidade"])
        teto_origem[k] = max(teto_origem.get(k, 0), int(s.get("excedente_origem", s["qtd_sugerida"])))
        mensal_origem[k] = mensal_origem.get(k, 0) + int(s["qtd_sugerida"])
    por_esp: Dict[str, int] = {}
    for k, mensal in mensal_origem.items():
        por_esp[k[1]] = por_esp.get(k[1], 0) + min(teto_origem[k], mensal * horizonte_meses)

    plano = []
    for esp, fila in fila_por_especialidade.items():
        fila = max(0, int(fila))
        red = max(0, min(fila, int(por_esp.get(esp, 0))))
        plano.append({
            "especialidade": esp,
            "fila_atual": fila,
            "pacientes_redistribuiveis": red,
            "fila_sem_acao": fila,
            "fila_com_redistribuicao": fila - red,
            "reducao_pct": round(red / fila * 100, 1) if fila > 0 else 0.0,
        })
    plano.sort(key=lambda x: x["fila_atual"], reverse=True)
    fila_total = sum(p["fila_atual"] for p in plano)
    red_total = sum(p["pacientes_redistribuiveis"] for p in plano)
    return {
        "horizonte_meses": horizonte_meses,
        "fila_total_atual": fila_total,
        "total_pacientes_redistribuiveis": red_total,
        "fila_total_com_redistribuicao": fila_total - red_total,
        "reducao_total_pct": round(red_total / fila_total * 100, 1) if fila_total > 0 else 0.0,
        "plano": plano,
    }


# ──────────────────────────────────────────────
# 4. Leitura do banco
# ──────────────────────────────────────────────
def carregar_base(db) -> Base:
    from sqlalchemy import func
    from database import CnesCapacidade, PacienteFila, ProducaoCirurgicaCnes

    comp_cnes = db.query(func.max(CnesCapacidade.competencia)).scalar()
    fila_rows = db.query(PacienteFila.cnes, PacienteFila.hospital_nome, PacienteFila.especialidade,
                         PacienteFila.cnes_confianca, func.count(PacienteFila.id)) \
        .group_by(PacienteFila.cnes, PacienteFila.hospital_nome, PacienteFila.especialidade,
                  PacienteFila.cnes_confianca).all()
    fila: Dict[str, Dict[str, int]] = {}
    nomes: Dict[str, Dict[str, int]] = {}
    vinculo: Dict[str, str] = {}
    sem_cnes: Dict[str, int] = {}
    ordem = ["ALTA", "MANUAL", "PROVISORIO_MEDIA", "PROVISORIO_AMBIGUO", "PROVISORIO_BAIXA"]
    for cnes, nome, esp, conf, n in fila_rows:
        if not cnes:
            sem_cnes[nome] = sem_cnes.get(nome, 0) + n
            continue
        e = especialidade_serie(esp)
        fila.setdefault(cnes, {})[e] = fila.setdefault(cnes, {}).get(e, 0) + n
        nomes.setdefault(cnes, {})[nome] = nomes.setdefault(cnes, {}).get(nome, 0) + n
        c = conf or "ALTA"
        atual = vinculo.get(cnes)
        if atual is None or (ordem.index(c) if c in ordem else 9) > (ordem.index(atual) if atual in ordem else 9):
            vinculo[cnes] = c
    nome_fila = {c: max(d, key=d.get) for c, d in nomes.items()}

    prod: Dict[str, Dict[str, Dict[str, int]]] = {}
    comps = set()
    for comp, cnes, esp, n in db.query(ProducaoCirurgicaCnes.competencia, ProducaoCirurgicaCnes.cnes,
                                       ProducaoCirurgicaCnes.especialidade,
                                       func.sum(ProducaoCirurgicaCnes.aihs)) \
            .group_by(ProducaoCirurgicaCnes.competencia, ProducaoCirurgicaCnes.cnes,
                      ProducaoCirurgicaCnes.especialidade).all():
        prod.setdefault(cnes, {}).setdefault(comp, {})[esp] = int(n or 0)
        comps.add(comp)

    interesse = set(fila) | set(prod)
    est: Dict[str, Dict] = {}
    if comp_cnes and interesse:
        cols = [c.name for c in CnesCapacidade.__table__.columns]
        lista = sorted(interesse)
        for i in range(0, len(lista), 500):
            for r in db.query(CnesCapacidade).filter(CnesCapacidade.competencia == comp_cnes,
                                                     CnesCapacidade.cnes.in_(lista[i:i + 500])).all():
                est[r.cnes] = {k: getattr(r, k) for k in cols}
    return Base(estabelecimentos=est, producao=prod, competencias=sorted(comps), fila=fila,
                nome_fila=nome_fila, vinculo=vinculo, fila_sem_cnes=sem_cnes, competencia_cnes=comp_cnes)


def metodologia(base: Optional[Base] = None, params: Dict = PARAMS) -> Dict:
    comps = base.competencias if base else []
    return {
        "versao": VERSAO,
        "natureza": "estimado",
        "documento": "docs/dados/redistribuicao-v1.md",
        "hipoteses": HIPOTESES,
        "parametros": dict(params),
        "habilitacao_exigida": HABILITACAO_EXIGIDA,
        "fontes": {
            "fila": "IntegraSUS (pacientes_fila) com vínculo nome→CNES (hospital_alias)",
            "producao": f"SIH-RD por CNES, competências {comps[0]}..{comps[-1]}" if comps else "SIH-RD por CNES: não carregado",
            "capacidade": f"CNES competência {base.competencia_cnes}" if base and base.competencia_cnes else "CNES: não carregado",
            "competencias_provisorias": comps[-2:] if comps else [],
        },
        "limitacoes": [
            "Capacidade cadastrada no CNES não é disponibilidade: faltam agenda, equipe e turnos reais.",
            "Sem produção ambulatorial (SIA): oftalmologia e pequenas cirurgias ficam subestimadas.",
            "A redução de espera é heurística (simulado); a meta de −40% não está comprovada.",
            "Priorização clínica (SWALIS, judicialização) ainda não entra na escolha de quem é transferido.",
        ],
    }
