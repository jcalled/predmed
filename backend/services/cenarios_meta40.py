"""
PREDMED — Cenários para a meta de −40% no tempo de espera (SIMULADO).

Metodologia, hipóteses e protocolo do piloto: docs/dados/meta-40-caminho.md.

Métrica (Lei de Little, fila estável): W = L / λ
  L = pedidos ativos no recorte (estabelecimento × especialidade, ou CIR × especialidade);
  λ = entradas por mês no recorte.
Com λ estável, a redução relativa de W é a redução relativa de L obtida com atendimentos
ADICIONAIS (acima da produção habitual):   redução = min(L, extra_mês × T) / L.
Remover pedidos sem atendimento (saneamento) NÃO entra nessa conta: é tratado à parte.

Alavancas (capacidade adicional por mês, tudo ESTIMADO ou HIPÓTESE):
  a  redistribuição na mesma CIR (regras da redistribuição v1);
  b  redistribuição na mesma macrorregião / no estado (decisão da SESA);
  c  vagas SUS compradas de hospitais privados/filantrópicos (fração da capacidade não SUS; hipótese de mercado);
  d  ordenação por priorização (não muda W médio; reduz W do subgrupo prioritário);
  e1 mutirão com a ociosidade estimada do próprio estabelecimento;
  e2 turno extra financiado (fração da produção da especialidade; hipótese);
  f  saneamento da fila (só contagem de candidatos; efeito ZERO na métrica).

Só agregados: nenhum dado individual sai deste módulo.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from services import redistribuicao as rd

VERSAO = "cenarios-meta40-v1"
DIAS_MES = 30.44

PARAMS: Dict[str, float] = {
    "horizonte_meses": 3,                 # piloto de 90 dias
    "meta_reducao": 0.40,
    "janela_entradas_dias": 28,           # λ = pedidos com data nos últimos 28 dias ainda na fila (limite inferior)
    "fracao_turno_extra": 0.20,           # e2: +20% da produção mensal da especialidade (≈ 1 turno de sábado/semana)
    "fracao_privada_contratavel": 0.10,   # c: 10% da capacidade NÃO SUS das salas de privados/filantrópicos
    "cirurgias_sala_mes": 88,             # mesmo nominal da redistribuição v1 (2 turnos × 22 dias × 2)
    "fracao_capacidade_prioridade": 0.50,  # d: até 50% das saídas podem ir ao subgrupo prioritário
    "fila_min_recorte": 50,               # recortes menores não entram no mapa (ruído e pouca relevância)
    "materializacao_robusta": 0.60,       # robustez: só 60% da capacidade estimada se confirma
    "idade_saneamento_dias": 730,         # pedidos com mais de 2 anos: candidatos a revalidação
}

ESP_HABILITACAO = rd.HABILITACAO_EXIGIDA   # onco/cardio/neuro exigem habilitação no destino

# Especialidades em que o SIH (internação) mede mal a produção: a cirurgia é sobretudo ambulatorial (SIA/APAC)
ESP_SIH_SUBESTIMA = {"OFTALMOLOGIA", "PEQUENAS CIRURGIAS"}
# "OUTRAS" mistura torácica e politrauma (majoritariamente urgência): a produção não é comparável à fila
ESP_NAO_COMPARAVEL = ESP_SIH_SUBESTIMA | {"OUTRAS"}

# Naturezas jurídicas CNES de empresa pública / economia mista (ex.: EBSERH, 2011): administração pública,
# embora o campo `natureza` do CNES as agrupe em PRIVADO.
NAT_JUR_PUBLICA_INDIRETA = {"2011", "2038"}
TP_UNID_HOSPITALAR = {"05", "07", "15", "62"}   # hospital geral, especializado, unidade mista, hospital-dia


def tipo_ajustado(est: Dict, tipo_rd: Optional[str]) -> Optional[str]:
    if str(est.get("nat_jur") or "") in NAT_JUR_PUBLICA_INDIRETA:
        return "publico"
    return tipo_rd

CENARIOS = [
    # (id, descrição, alavancas somadas)
    ("S0_v1_compartilhado", "a: redistribuição v1 (mesma CIR, capacidade dividida entre todas as origens)", ("a_comp",)),
    ("S1_cir", "a: mesma CIR, recorte do piloto com precedência na capacidade ociosa", ("a",)),
    ("S2_cir_proprio", "a + e1: + ociosidade estimada do próprio estabelecimento", ("a", "e1")),
    ("S3_cir_proprio_turno", "a + e1 + e2: + turno extra financiado (+20% da produção)", ("a", "e1", "e2")),
    ("S4_macro", "S3 + b: redistribuição em toda a macrorregião", ("a", "b_macro", "e1", "e2")),
    ("S5_macro_privado", "S4 + c: vagas SUS de privados/filantrópicos (10% da capacidade não SUS)", ("a", "b_macro", "e1", "e2", "c")),
    ("S6_estado_privado", "S5 com redistribuição em todo o estado", ("a", "b_macro", "b_estado", "e1", "e2", "c")),
]


def _p(params: Optional[Dict]) -> Dict:
    p = dict(PARAMS)
    p.update(params or {})
    return p


# ──────────────────────────────────────────────
# 1. Estatísticas agregadas da fila (sem dado individual)
# ──────────────────────────────────────────────
@dataclass
class EstatFila:
    L: int = 0
    n_recentes: int = 0            # pedidos com data na janela de entradas
    n_prio: int = 0                # A1 ou judicializado ou oncológico
    n_prio_recentes: int = 0
    n_legado: int = 0              # data a confirmar (numeração antiga)
    n_antigos: int = 0             # > idade_saneamento_dias
    n_dup_extra: int = 0           # cópias além da 1ª de pedidos com mesma chave (candidato a duplicidade)
    idades: List[int] = field(default_factory=list)   # descartadas antes de sair do módulo

    def resumo(self, p: Dict) -> Dict:
        lam = self.n_recentes * DIAS_MES / p["janela_entradas_dias"]
        ids = sorted(self.idades)
        med = statistics.median(ids) if ids else None
        p90 = ids[int(0.9 * (len(ids) - 1))] if ids else None
        return {
            "fila": self.L,
            "entradas_mes_est": round(lam, 1),
            "espera_little_dias": round(self.L / lam * DIAS_MES) if lam > 0 else None,
            "idade_mediana_estoque_dias": int(med) if med is not None else None,
            "idade_p90_estoque_dias": p90,
            "pct_estoque_mais_180d": round(100 * sum(1 for i in ids if i > 180) / len(ids), 1) if ids else None,
            "prioritarios": self.n_prio,
            "prioritarios_entradas_mes_est": round(self.n_prio_recentes * DIAS_MES / p["janela_entradas_dias"], 1),
            "saneamento_legado": self.n_legado,
            "saneamento_mais_2_anos": self.n_antigos,
            "saneamento_possivel_duplicidade": self.n_dup_extra,
        }


def estatisticas_fila(registros: Iterable[Tuple], ref: date, params: Optional[Dict] = None
                      ) -> Dict[Tuple[str, str], EstatFila]:
    """registros: (cnes, especialidade_serie, data_iso, swalis, judicializado, oncologico,
    data_confiavel, chave_duplicidade). A chave de duplicidade é opaca e nunca é devolvida."""
    p = _p(params)
    ini_janela = ref - timedelta(days=int(p["janela_entradas_dias"]))
    out: Dict[Tuple[str, str], EstatFila] = defaultdict(EstatFila)
    chaves: Dict[Tuple[str, str], Dict] = defaultdict(lambda: defaultdict(int))
    for cnes, esp, data_iso, swalis, jud, onco, confiavel, chave in registros:
        k = (cnes, esp)
        e = out[k]
        e.L += 1
        prio = (swalis == "Categoria A1") or bool(jud) or bool(onco)
        e.n_prio += prio
        try:
            d = date.fromisoformat(str(data_iso)[:10])
        except (TypeError, ValueError):
            d = None
        if d is not None:
            idade = max(0, (ref - d).days)
            e.idades.append(idade)
            if ini_janela <= d < ref:
                e.n_recentes += 1
                e.n_prio_recentes += prio
            if idade > p["idade_saneamento_dias"]:
                e.n_antigos += 1
        if confiavel is False or confiavel == 0:
            e.n_legado += 1
        if chave:
            chaves[k][chave] += 1
    for k, cont in chaves.items():
        out[k].n_dup_extra = sum(n - 1 for n in cont.values() if n > 1)
    return dict(out)


# ──────────────────────────────────────────────
# 2. Capacidade adicional por alavanca (por mês)
# ──────────────────────────────────────────────
def _excedente_transferivel(fila: int, prod_esp: float, params: Dict) -> int:
    """Regra da redistribuição v1: a origem retém 1,5 mês da própria produção na especialidade."""
    if prod_esp > 0 and fila / prod_esp < params["pressao_origem_min"]:
        return 0
    return max(0, fila - math.ceil(params["meses_fila_retidos_origem"] * prod_esp))


def capacidade_destinos(origem: Dict, esp: str, destinos: Iterable[Dict], params: Dict = rd.PARAMS) -> float:
    """Capacidade mensal que destinos compatíveis podem oferecer ao recorte (precedência do piloto):
    Σ min(ociosidade estimada, +50% da produção do destino na especialidade)."""
    tot = 0.0
    for d in destinos:
        if not d.get("cnes") or d["cnes"] == origem.get("cnes"):
            continue
        ok, _ = rd.destino_compativel(d, esp, params)
        if not ok:
            continue
        prod_d = d["producao_por_especialidade_mes"].get(esp, 0.0)
        tot += min(float(d.get("ociosidade_estimada_mes", 0)),
                   math.floor(params["fator_expansao_especialidade"] * prod_d))
    return tot


def participacao_especialidades(hospitais: Iterable[Dict]) -> Dict[str, float]:
    """Participação de cada especialidade na produção cirúrgica SUS (sem obstetrícia, média 12 meses)."""
    tot: Dict[str, float] = defaultdict(float)
    for h in hospitais:
        for e, v in (h.get("producao_por_especialidade_mes") or {}).items():
            tot[e] += v
    s = sum(tot.values()) or 1.0
    return {e: v / s for e, v in tot.items()}


def capacidade_privada(estabs_privados: Iterable[Dict], esp: str, p: Dict, participacao: float = 1.0) -> float:
    """c: fração contratável da capacidade NÃO SUS das salas (hipótese de mercado), repartida entre as
    especialidades na mesma proporção da produção SUS do estado (`participacao`)."""
    hab = ESP_HABILITACAO.get(esp)
    tot = 0.0
    for e in estabs_privados:
        if hab and not e.get(hab):
            continue
        salas = int(e.get("salas_cirurgicas") or 0)
        le = int(e.get("leitos_cirurgicos_exist") or 0)
        ls = int(e.get("leitos_cirurgicos_sus") or 0)
        frac_sus = (ls / le) if le > 0 else (1.0 if e.get("vinculo_sus") else 0.0)
        tot += salas * p["cirurgias_sala_mes"] * max(0.0, 1.0 - frac_sus) * p["fracao_privada_contratavel"]
    return tot * participacao


def reducao(L: int, extra_mes: float, meses: float) -> float:
    """Redução relativa de W = L/λ com λ estável: atendimentos adicionais ÷ estoque (0 a 1)."""
    if L <= 0:
        return 0.0
    return max(0.0, min(float(L), extra_mes * meses)) / L


def efeito_priorizacao(L: int, lam: float, L_prio: int, lam_prio: float, p: Dict) -> Dict:
    """d: reordenar sem capacidade nova. W médio NÃO muda (conservação); o subgrupo prioritário
    passa a receber até `fracao_capacidade_prioridade` das saídas (saídas ≈ entradas, fila estável)."""
    T = p["horizonte_meses"]
    extra_prio = max(0.0, p["fracao_capacidade_prioridade"] * lam - lam_prio)
    red_prio = reducao(L_prio, extra_prio, T)
    return {
        "reducao_media_geral_pct": 0.0,
        "reducao_prioritarios_pct": round(100 * red_prio, 1),
        "aumento_estoque_nao_prioritarios": int(round(min(L_prio, extra_prio * T))),
        "nota": "Reordenar não cria capacidade: o ganho dos prioritários é espera transferida aos demais.",
    }


# ──────────────────────────────────────────────
# 3. Cenários por recorte
# ──────────────────────────────────────────────
def _agrupar(hospitais: List[Dict], chave) -> Dict[str, List[Dict]]:
    g: Dict[str, List[Dict]] = defaultdict(list)
    for h in hospitais:
        if h.get("cnes"):
            g[chave(h)].append(h)
    return g


def _alloc_compartilhada(hospitais: List[Dict], params: Dict) -> Dict[Tuple[str, str], int]:
    """a_comp: sugestões da redistribuição v1 (capacidade dividida entre todas as origens da CIR)."""
    out: Dict[Tuple[str, str], int] = defaultdict(int)
    for s in rd.sugerir_redistribuicao(hospitais, params):
        out[(s["cnes_origem"], s["especialidade"])] += int(s["qtd_sugerida"])
    return out


def cenarios_recortes(hospitais: List[Dict], estat: Dict[Tuple[str, str], EstatFila],
                      privados_por_cir: Dict[str, List[Dict]], macro_de_cir: Dict[str, str],
                      params: Optional[Dict] = None, rd_params: Dict = rd.PARAMS,
                      estabelecimentos: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """Um registro por estabelecimento × especialidade com fila ≥ fila_min_recorte."""
    p = _p(params)
    rp = dict(rd_params)
    T = p["horizonte_meses"]
    por_cir = _agrupar(hospitais, lambda h: h["cir"])
    por_macro = _agrupar(hospitais, lambda h: macro_de_cir.get(h["cir"], "?"))
    todos = [h for h in hospitais if h.get("cnes")]
    comp = _alloc_compartilhada(hospitais, rp)
    por_cnes = {h["cnes"]: h for h in todos}
    part = participacao_especialidades(todos)
    estabs = estabelecimentos or {}

    out = []
    for (cnes, esp), e in estat.items():
        h = por_cnes.get(cnes)
        if h is None or e.L < p["fila_min_recorte"] or h["cir"] in ("DESCONHECIDO", "FORA_DO_CEARA"):
            continue
        prod = float(h["producao_por_especialidade_mes"].get(esp, 0.0))
        cir, macro = h["cir"], macro_de_cir.get(h["cir"], "?")
        teto_transf = _excedente_transferivel(e.L, prod, rp)

        cap_cir = capacidade_destinos(h, esp, por_cir.get(cir, []), rp)
        cap_macro = capacidade_destinos(h, esp, por_macro.get(macro, []), rp)
        cap_estado = capacidade_destinos(h, esp, todos, rp)
        a = min(cap_cir, teto_transf / T)
        b_macro = max(0.0, min(cap_macro, teto_transf / T) - a)
        b_estado = max(0.0, min(cap_estado, teto_transf / T) - a - b_macro)
        lev = {
            "a_comp": float(comp.get((cnes, esp), 0)),
            "a": a,
            "b_macro": b_macro,
            "b_estado": b_estado,
            "e1": min(float(h.get("ociosidade_estimada_mes", 0)), math.floor(rp["fator_expansao_especialidade"] * prod)),
            "e2": p["fracao_turno_extra"] * prod,
            "c": capacidade_privada([x for c2, lst in privados_por_cir.items() if macro_de_cir.get(c2) == macro
                                     for x in lst], esp, p, part.get(esp, 0.0)),
        }
        r = e.resumo(p)
        lam = r["entradas_mes_est"]
        necessario = p["meta_reducao"] * e.L / T
        cen = {}
        for cid, _, alav in CENARIOS:
            extra = sum(lev[x] for x in alav)
            cen[cid] = {
                "extra_mes": round(extra, 1),
                "reducao_pct": round(100 * reducao(e.L, extra, T), 1),
                "reducao_robusta_pct": round(100 * reducao(e.L, p["materializacao_robusta"] * extra, T), 1),
            }
        ordem = [c for c, _, _ in CENARIOS if c != "S0_v1_compartilhado"]
        minimo = next((c for c in ordem if cen[c]["reducao_pct"] >= 100 * p["meta_reducao"]), None)
        minimo_rob = next((c for c in ordem if cen[c]["reducao_robusta_pct"] >= 100 * p["meta_reducao"]), None)
        out.append({
            "cenario_minimo_40": minimo,
            "cenario_minimo_40_robusto": minimo_rob,
            "cnes": cnes, "hospital_nome": h["hospital_nome"],
            "tipo": tipo_ajustado(estabs.get(cnes, {}), h.get("tipo")),
            "producao_sih_nao_comparavel": esp in ESP_NAO_COMPARAVEL,
            "cir": cir, "macro": macro, "especialidade": esp,
            "vinculo_cnes": h.get("vinculo_cnes"), "vinculo_provisorio": h.get("vinculo_provisorio"),
            **r,
            "producao_esp_mes": round(prod, 1),
            "fila_em_meses_de_producao": round(e.L / prod, 1) if prod > 0 else None,
            "ociosidade_propria_mes": h.get("ociosidade_estimada_mes", 0),
            "transferivel_regra_v1": teto_transf,
            "alavancas_mes": {k: round(v, 1) for k, v in lev.items()},
            "extra_necessario_40_mes": round(necessario, 1),
            "extra_necessario_40_pct_producao": round(100 * necessario / prod, 0) if prod > 0 else None,
            "cenarios": cen,
            "priorizacao": efeito_priorizacao(e.L, lam, e.n_prio, r["prioritarios_entradas_mes_est"], p),
            "natureza_dado": "simulado",
        })
    out.sort(key=lambda x: -x["fila"])
    return out


def cenarios_cir(hospitais: List[Dict], estat: Dict[Tuple[str, str], EstatFila],
                 privados_por_cir: Dict[str, List[Dict]], macro_de_cir: Dict[str, str],
                 params: Optional[Dict] = None, rd_params: Dict = rd.PARAMS) -> List[Dict]:
    """CIR × especialidade: a fila da CIR inteira contra a ociosidade estimada da própria CIR (a+e1 de
    todos os estabelecimentos), turno extra (e2), macro (b) e privados (c)."""
    p = _p(params)
    rp = dict(rd_params)
    T = p["horizonte_meses"]
    por_cnes = {h["cnes"]: h for h in hospitais if h.get("cnes")}
    agg: Dict[Tuple[str, str], EstatFila] = defaultdict(EstatFila)
    for (cnes, esp), e in estat.items():
        h = por_cnes.get(cnes)
        if not h or h["cir"] in ("DESCONHECIDO", "FORA_DO_CEARA"):
            continue
        a = agg[(h["cir"], esp)]
        a.L += e.L; a.n_recentes += e.n_recentes; a.n_prio += e.n_prio
        a.n_prio_recentes += e.n_prio_recentes; a.n_legado += e.n_legado
        a.n_antigos += e.n_antigos; a.n_dup_extra += e.n_dup_extra; a.idades.extend(e.idades)

    def ocio_esp(hs: Iterable[Dict], esp: str, destino_externo: bool = False) -> float:
        """Dentro da CIR (a+e1) a fila é somada, então todo estabelecimento apto conta; fora da CIR (b)
        vale a regra de destino da redistribuição v1 (fila própria da especialidade ≤ 1 mês)."""
        tot = 0.0
        for d in hs:
            if destino_externo:
                if not rd.destino_compativel(d, esp, rp)[0]:
                    continue
            elif not d.get("apto_receber"):
                continue
            prod_d = d["producao_por_especialidade_mes"].get(esp, 0.0)
            if prod_d < rp["producao_min_especialidade"]:
                continue
            hab = ESP_HABILITACAO.get(esp)
            if hab and not d.get("habilitacoes", {}).get(hab):
                continue
            tot += min(float(d.get("ociosidade_estimada_mes", 0)), math.floor(rp["fator_expansao_especialidade"] * prod_d))
        return tot

    por_cir = _agrupar(hospitais, lambda h: h["cir"])
    part = participacao_especialidades(h for h in hospitais if h.get("cnes"))
    out = []
    for (cir, esp), e in agg.items():
        if e.L < p["fila_min_recorte"]:
            continue
        macro = macro_de_cir.get(cir, "?")
        hs = por_cir.get(cir, [])
        prod = sum(h["producao_por_especialidade_mes"].get(esp, 0.0) for h in hs)
        outras = [h for c2, lst in por_cir.items() if c2 != cir and macro_de_cir.get(c2) == macro for h in lst]
        lev = {
            "a_e1": ocio_esp(hs, esp),
            "e2": p["fracao_turno_extra"] * prod,
            "b_macro": ocio_esp(outras, esp, destino_externo=True),
            "c": capacidade_privada(privados_por_cir.get(cir, []), esp, p, part.get(esp, 0.0)),
        }
        r = e.resumo(p)
        cen = {}
        for cid, alav in (("C1_ociosidade_cir", ("a_e1",)), ("C2_mais_turno", ("a_e1", "e2")),
                          ("C3_mais_macro", ("a_e1", "e2", "b_macro")), ("C4_mais_privado", ("a_e1", "e2", "b_macro", "c"))):
            extra = sum(lev[x] for x in alav)
            cen[cid] = {"extra_mes": round(extra, 1), "reducao_pct": round(100 * reducao(e.L, extra, T), 1),
                        "reducao_robusta_pct": round(100 * reducao(e.L, p["materializacao_robusta"] * extra, T), 1)}
        necessario = p["meta_reducao"] * e.L / T
        out.append({"cir": cir, "macro": macro, "especialidade": esp, **r,
                    "producao_sih_nao_comparavel": esp in ESP_NAO_COMPARAVEL,
                    "producao_esp_mes": round(prod, 1),
                    "extra_necessario_40_mes": round(necessario, 1),
                    "extra_necessario_40_pct_producao": round(100 * necessario / prod, 0) if prod > 0 else None,
                    "alavancas_mes": {k: round(v, 1) for k, v in lev.items()},
                    "cenarios": cen, "natureza_dado": "simulado"})
    out.sort(key=lambda x: -x["fila"])
    return out


# ──────────────────────────────────────────────
# 4. Leitura do banco (só agregados saem)
# ──────────────────────────────────────────────
def carregar(db, ref: Optional[date] = None, params: Optional[Dict] = None):
    from sqlalchemy import func
    from database import CnesCapacidade, PacienteFila
    from services.priorizacao import eh_oncologico

    p = _p(params)
    if ref is None:
        mx = db.query(func.max(PacienteFila.data_insercao)).scalar()
        ref = (date.fromisoformat(str(mx)[:10]) + timedelta(days=1)) if mx else date.today()

    def regs():
        q = db.query(PacienteFila.cnes, PacienteFila.especialidade, PacienteFila.data_insercao,
                     PacienteFila.classif_swalis, PacienteFila.judicializado, PacienteFila.procedimento,
                     PacienteFila.data_confiavel, PacienteFila.iniciais, PacienteFila.municipio)
        for cnes, esp, d, sw, jud, proc, conf, ini, mun in q.yield_per(5000):
            if not cnes:
                continue
            chave = hash((ini or "", mun or "", proc or "")) if ini else None   # opaca, só para contagem
            yield (cnes, rd.especialidade_serie(esp), d, sw, jud, eh_oncologico(esp, proc), conf, chave)

    estat = estatisticas_fila(regs(), ref, p)
    base = rd.carregar_base(db)
    hospitais = rd.estimar_hospitais(base)

    comp = base.competencia_cnes
    macro_de_cir: Dict[str, str] = {}
    privados: Dict[str, List[Dict]] = defaultdict(list)
    cols = [c.name for c in CnesCapacidade.__table__.columns]
    for r in db.query(CnesCapacidade).filter(CnesCapacidade.competencia == comp).all():
        if r.cir_ads_predmed and r.macrorregiao_cnes:
            macro_de_cir.setdefault(r.cir_ads_predmed, r.macrorregiao_cnes)
        if (r.natureza in ("PRIVADO", "SEM FINS LUCRATIVOS") and r.centro_cirurgico
                and str(r.nat_jur or "") not in NAT_JUR_PUBLICA_INDIRETA
                and str(r.tp_unid or "") in TP_UNID_HOSPITALAR
                and (r.salas_cirurgicas or 0) > 0 and r.cir_ads_predmed):
            privados[r.cir_ads_predmed].append({k: getattr(r, k) for k in cols})
    return ref, estat, hospitais, dict(privados), macro_de_cir, base


def resumo_estadual(estat: Dict[Tuple[str, str], EstatFila], p: Dict) -> Dict:
    tot = EstatFila()
    for e in estat.values():
        tot.L += e.L; tot.n_recentes += e.n_recentes; tot.n_prio += e.n_prio
        tot.n_prio_recentes += e.n_prio_recentes; tot.n_legado += e.n_legado
        tot.n_antigos += e.n_antigos; tot.n_dup_extra += e.n_dup_extra; tot.idades.extend(e.idades)
    return tot.resumo(p)


def metodologia(params: Optional[Dict] = None) -> Dict:
    return {
        "versao": VERSAO,
        "natureza": "simulado",
        "documento": "docs/dados/meta-40-caminho.md",
        "metrica": "W = L / λ (Lei de Little). Com λ estável, redução de W = atendimentos adicionais ÷ estoque.",
        "parametros": _p(params),
        "cenarios": [{"id": c, "descricao": d, "alavancas": list(a)} for c, d, a in CENARIOS],
        "avisos": [
            "Tudo é simulado: capacidade ociosa é ESTIMADA (CNES + SIH), não vaga confirmada.",
            "λ vem dos pedidos recentes que ainda estão na fila (limite inferior); W em dias é limite superior. "
            "A redução percentual não depende de λ.",
            "Saneamento (duplicidade, pedidos antigos) não conta como redução de espera.",
            "Priorização não reduz a espera média; só redistribui a espera entre grupos.",
            "A meta de −40% não está comprovada; exige o piloto com protocolo pré-registrado.",
        ],
    }
