"""
Cenários da meta de −40% no tempo de espera — SIMULADO, reproduzível.

Lê só o predmed.db (fila IntegraSUS, produção SIH por CNES, CNES) em modo leitura e grava
backend/avaliacoes/meta40/cenarios_AAAAMMDD.json (e um CSV do mapa), SÓ com agregados por
estabelecimento/CIR × especialidade. Nenhum dado de paciente é gravado ou impresso.

Uso:
    backend/venv/bin/python backend/_SCRIPTS/cenarios_meta_40.py [--ref AAAA-MM-DD] [--json-only]

Metodologia: docs/dados/meta-40-caminho.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("APP_ENV", "dev")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from services import cenarios_meta40 as cm  # noqa: E402
from services import redistribuicao as rd  # noqa: E402

SAIDA = BACKEND / "avaliacoes" / "meta40"

# Recorte candidato ao piloto (hospital público; ver documento, seção 5)
CANDIDATO = {
    "tipos": ("publico",),
    "fila_min": 100,
    "fila_max": 2500,
    "entradas_mes_min": 15,          # fluxo suficiente para medir quinzenalmente
    "vinculo": ("ALTA", "MANUAL"),
}
# Alavancas que não dependem de mudança de regra regional nem de mercado privado
CENARIO_SEM_POLITICA = "S3_cir_proprio_turno"


def sessao():
    db_path = BACKEND / "predmed.db"
    eng = create_engine(f"sqlite:///file:{db_path}?mode=ro&uri=true", connect_args={"uri": True})
    return sessionmaker(bind=eng)()


def sobrevivencia_semanal(db, ref: date) -> list:
    """Pedidos com data em cada uma das 6 semanas anteriores à coleta que ainda estão na fila,
    relativos à semana mais recente (curva de permanência aproximada; fila estável)."""
    from database import PacienteFila
    from sqlalchemy import func
    out = []
    for w in range(6):
        fim = ref - timedelta(days=7 * w)
        ini = fim - timedelta(days=7)
        n = db.query(func.count(PacienteFila.id)).filter(
            PacienteFila.data_insercao >= ini.isoformat(), PacienteFila.data_insercao < fim.isoformat()).scalar()
        out.append({"semana": w + 1, "de": ini.isoformat(), "ate": (fim - timedelta(days=1)).isoformat(), "na_fila": n})
    base = out[0]["na_fila"] or 1
    for o in out:
        o["relativo_semana_1"] = round(o["na_fila"] / base, 2)
    return out


def grupos_prioridade(db, ref: date, janela: int) -> dict:
    """Espera por grupo (SWALIS, judicializado, oncologia, cardiovascular) — só agregados."""
    import statistics
    from database import PacienteFila
    grupos = {
        "SWALIS A1": PacienteFila.classif_swalis == "Categoria A1",
        "SWALIS B": PacienteFila.classif_swalis == "Categoria B",
        "SWALIS C": PacienteFila.classif_swalis == "Categoria C",
        "SWALIS D": PacienteFila.classif_swalis == "Categoria D",
        "SWALIS nao informada": PacienteFila.classif_swalis == "Não Informada",
        "judicializado": PacienteFila.judicializado == True,  # noqa: E712
        "ONCOLOGIA": PacienteFila.especialidade == "ONCOLOGIA",
        "CARDIOVASCULAR": PacienteFila.especialidade == "CARDIOVASCULAR",
    }
    out = {}
    ini = ref - timedelta(days=janela)
    for nome, filtro in grupos.items():
        idades = sorted(max(0, (ref - date.fromisoformat(str(d)[:10])).days)
                        for (d,) in db.query(PacienteFila.data_insercao).filter(filtro) if d)
        n = len(idades)
        if not n:
            continue
        rec = sum(1 for i in idades if i <= (ref - ini).days and i >= 1)
        lam = rec * cm.DIAS_MES / janela
        out[nome] = {"fila": n, "entradas_mes_est": round(lam, 1),
                     "espera_little_dias": round(n / lam * cm.DIAS_MES) if lam else None,
                     "idade_mediana_estoque_dias": int(statistics.median(idades)),
                     "pct_estoque_mais_180d": round(100 * sum(i > 180 for i in idades) / n, 1)}
    return out


def sistema(hospitais, privados, estadual, p) -> dict:
    """Cenário SIMULTÂNEO (todo o estado ao mesmo tempo): capacidade somada sem dupla contagem.
    É limite superior: ignora descasamento de especialidade e de geografia."""
    ocio = sum(h.get("ociosidade_estimada_mes", 0) for h in hospitais if h.get("cnes") and h.get("apto_receber"))
    prod = sum(sum(h.get("producao_por_especialidade_mes", {}).values()) for h in hospitais if h.get("cnes"))
    e2 = p["fracao_turno_extra"] * prod
    c = sum(cm.capacidade_privada(lst, "", p) for lst in privados.values())
    L, T = estadual["fila"], p["horizonte_meses"]
    out = {"fila": L, "ociosidade_estimada_mes": round(ocio), "turno_extra_mes": round(e2),
           "privados_10pct_nao_sus_mes": round(c), "producao_sus_sem_obstetricia_mes": round(prod)}
    for nome, extra in (("ociosidade", ocio), ("ociosidade+turno", ocio + e2), ("ociosidade+turno+privados", ocio + e2 + c)):
        out[f"reducao_90d_pct_{nome}"] = round(100 * cm.reducao(L, extra, T), 1)
    out["extra_necessario_40_90d_mes"] = round(0.4 * L / T)
    for nome, extra in (("ociosidade", ocio), ("ociosidade+turno", ocio + e2)):
        out[f"meses_para_40pct_{nome}"] = round(0.4 * L / extra, 1) if extra > 0 else None
    out["nota"] = ("Limite superior: supõe que toda a capacidade serve a qualquer especialidade e CIR. "
                   "A redistribuição v1 (regras atuais) aloca bem menos.")
    return out


def contagem(lista, cid, chave="reducao_pct", limiar=40.0):
    return sum(1 for r in lista if r["cenarios"][cid][chave] >= limiar)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", help="data de referência (dia seguinte à última entrada na fila)")
    args = ap.parse_args()
    ref = date.fromisoformat(args.ref) if args.ref else None

    db = sessao()
    ref, estat, hospitais, privados, macro_de_cir, base = cm.carregar(db, ref)
    p = cm._p(None)
    recortes = cm.cenarios_recortes(hospitais, estat, privados, macro_de_cir, p,
                                    estabelecimentos=base.estabelecimentos)
    cirs = cm.cenarios_cir(hospitais, estat, privados, macro_de_cir, p)
    estadual = cm.resumo_estadual(estat, p)
    sem_cnes = sum(base.fila_sem_cnes.values())

    ids = [c for c, _, _ in cm.CENARIOS]
    mapa = {
        "recortes_avaliados": len(recortes),
        "fila_nos_recortes": sum(r["fila"] for r in recortes),
        "atingem_40": {c: contagem(recortes, c) for c in ids},
        "atingem_40_robusto": {c: contagem(recortes, c, "reducao_robusta_pct") for c in ids},
        "fila_em_recortes_que_atingem_40": {c: sum(r["fila"] for r in recortes if r["cenarios"][c]["reducao_pct"] >= 40) for c in ids},
        "por_especialidade": {},
        "cir_atingem_40": {c: sum(1 for r in cirs if r["cenarios"][c]["reducao_pct"] >= 40)
                           for c in ("C1_ociosidade_cir", "C2_mais_turno", "C3_mais_macro", "C4_mais_privado")},
        "cir_recortes_avaliados": len(cirs),
    }
    por_esp = defaultdict(list)
    for r in recortes:
        por_esp[r["especialidade"]].append(r)
    for esp, lst in sorted(por_esp.items(), key=lambda x: -sum(r["fila"] for r in x[1])):
        mapa["por_especialidade"][esp] = {
            "recortes": len(lst), "fila": sum(r["fila"] for r in lst),
            **{c: contagem(lst, c) for c in ids},
        }

    # Distribuição da capacidade necessária (% da produção da especialidade) para 40% em 90 dias
    nec = sorted(r["extra_necessario_40_pct_producao"] for r in recortes if r["extra_necessario_40_pct_producao"] is not None)
    faixas = Counter()
    for v in nec:
        faixas["<=25%" if v <= 25 else "25-50%" if v <= 50 else "50-100%" if v <= 100 else "100-200%" if v <= 200 else ">200%"] += 1
    sem_prod = sum(1 for r in recortes if r["extra_necessario_40_pct_producao"] is None)

    candidatos = [
        r for r in recortes
        if r["tipo"] in CANDIDATO["tipos"] and CANDIDATO["fila_min"] <= r["fila"] <= CANDIDATO["fila_max"]
        and r["entradas_mes_est"] >= CANDIDATO["entradas_mes_min"]
        and (r["vinculo_cnes"] or "ALTA") in CANDIDATO["vinculo"]
        and not r["producao_sih_nao_comparavel"]
        and r["cenarios"][CENARIO_SEM_POLITICA]["reducao_robusta_pct"] >= 40
    ]
    ordem = [c for c, _, _ in cm.CENARIOS]
    candidatos.sort(key=lambda r: (ordem.index(r["cenario_minimo_40_robusto"]), -r["fila"]))

    tot_cap = {k: round(sum(r["alavancas_mes"][k] for r in recortes), 0) for k in recortes[0]["alavancas_mes"]} if recortes else {}

    resultado = {
        "versao": cm.VERSAO,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "data_referencia": ref.isoformat(),
        "natureza": "simulado",
        "metodologia": cm.metodologia(p),
        "fontes": {
            "fila": "pacientes_fila (IntegraSUS, coleta de 28/09/2026, campo data = solicitação)",
            "producao": f"producao_cirurgica_cnes (SIH-RD), {base.competencias[0]}..{base.competencias[-1]}",
            "capacidade": f"cnes_capacidade {base.competencia_cnes}",
            "fila_sem_cnes_fora_do_mapa": sem_cnes,
        },
        "estadual": estadual,
        "grupos_prioridade": grupos_prioridade(db, ref, int(p["janela_entradas_dias"])),
        "sistema_simultaneo": sistema(hospitais, privados, estadual, p),
        "permanencia_semanal_estoque": sobrevivencia_semanal(db, ref),
        "mapa": mapa,
        "capacidade_necessaria_40_90d_pct_producao": {"faixas": dict(faixas), "sem_producao_sih": sem_prod,
                                                      "mediana_pct": nec[len(nec) // 2] if nec else None},
        "capacidade_somada_nos_recortes_mes": tot_cap,
        "candidatos_piloto": [
            {k: r[k] for k in ("cenario_minimo_40", "cenario_minimo_40_robusto", "hospital_nome", "cnes", "cir", "especialidade", "fila", "entradas_mes_est",
                               "espera_little_dias", "idade_mediana_estoque_dias", "producao_esp_mes",
                               "extra_necessario_40_mes", "extra_necessario_40_pct_producao", "alavancas_mes",
                               "ociosidade_propria_mes", "prioritarios", "saneamento_legado",
                               "saneamento_mais_2_anos", "saneamento_possivel_duplicidade")}
            | {"cenarios": r["cenarios"], "priorizacao": r["priorizacao"]}
            for r in candidatos[:25]
        ],
        "recortes": recortes,
        "cir_especialidade": cirs,
    }
    SAIDA.mkdir(parents=True, exist_ok=True)
    arq = SAIDA / f"cenarios_{date.today():%Y%m%d}.json"
    arq.write_text(json.dumps(resultado, ensure_ascii=False, indent=1, default=str))
    with open(SAIDA / f"mapa_recortes_{date.today():%Y%m%d}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cnes", "hospital", "tipo", "cir", "especialidade", "fila", "entradas_mes_est", "espera_little_dias",
                    "idade_mediana_dias", "producao_esp_mes", "extra_40_mes", "extra_40_pct_producao",
                    *[f"red_{c}" for c in ids], *[f"cap_{k}" for k in ("a", "b_macro", "b_estado", "e1", "e2", "c")]])
        for r in recortes:
            w.writerow([r["cnes"], r["hospital_nome"], r["tipo"], r["cir"], r["especialidade"], r["fila"],
                        r["entradas_mes_est"], r["espera_little_dias"], r["idade_mediana_estoque_dias"],
                        r["producao_esp_mes"], r["extra_necessario_40_mes"], r["extra_necessario_40_pct_producao"],
                        *[r["cenarios"][c]["reducao_pct"] for c in ids],
                        *[r["alavancas_mes"][k] for k in ("a", "b_macro", "b_estado", "e1", "e2", "c")]])
    sha = hashlib.sha256(arq.read_bytes()).hexdigest()[:16]

    print(f"Referência {ref}  | arquivo {arq.relative_to(BACKEND.parent)} (sha256 {sha}…)")
    print("Estadual:", json.dumps(estadual, ensure_ascii=False))
    print("Recortes:", mapa["recortes_avaliados"], "fila", mapa["fila_nos_recortes"], "| sem CNES fora:", sem_cnes)
    for c, d, _ in cm.CENARIOS:
        print(f"  {c:24s} ≥40%: {mapa['atingem_40'][c]:3d} (robusto {mapa['atingem_40_robusto'][c]:3d}); "
              f"fila coberta {mapa['fila_em_recortes_que_atingem_40'][c]}")
    print("Capacidade necessária (% produção) p/ 40% em 90d:", dict(faixas), "sem SIH:", sem_prod)
    print("CIR×esp ≥40%:", mapa["cir_atingem_40"], "de", len(cirs))
    print("Sistema simultâneo:", json.dumps(resultado["sistema_simultaneo"], ensure_ascii=False))
    print("Candidatos ao piloto:", len(candidatos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
