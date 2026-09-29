"""
Análise comparativa dos snapshots da fila IntegraSUS (B17 / base para B35).

SOMENTE LEITURA: lê os CSVs em backend/data/ e imprime apenas estatísticas
agregadas. Não grava arquivos, não altera bancos e não imprime iniciais,
números de solicitação individuais nem linhas de pacientes.

Uso:
    python backend/_SCRIPTS/analise_snapshots_integrasus.py
"""
from __future__ import annotations

import csv
import glob
import os
import statistics
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
COLS = ["POSICAO_FILA", "MUNICIPIO", "UNIDADE", "PROCEDIMENTO", "ESPECIALIDADE",
        "INIC_NOME_PACIENTE", "JUDICIALIZADO", "CLASSIF_SWALIS", "NUN_SOLICITACAO"]
MIN_GRUPO = 30  # não reportar recortes com menos registros


def ler(path: str) -> list[dict]:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    # O snapshot de 22/02 veio com acentos já substituídos por U+FFFD (perda na
    # exportação); o de 24/02 veio em ISO-8859-1. Para comparar, todo caractere
    # não ASCII vira "?" nos dois arquivos.
    txt = "".join(ch if ord(ch) < 128 else "?" for ch in txt)
    linhas = list(csv.DictReader(txt.splitlines(), delimiter=";"))
    return linhas


def serie(n: int) -> str:
    """Série de numeração inferida pelo nº de dígitos do nº de solicitação."""
    d = len(str(n))
    if d >= 11:
        return "11 digitos"
    if d == 7:
        return "7 digitos"
    return "<=6 digitos"


def as_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def spearman(xs, ys):
    def ranks(v):
        ordem = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(ordem):
            j = i
            while j + 1 < len(ordem) and v[ordem[j + 1]] == v[ordem[i]]:
                j += 1
            for k in range(i, j + 1):
                r[ordem[k]] = (i + j) / 2
            i = j + 1
        return r
    if len(xs) < 3:
        return None
    rx, ry = ranks(xs), ranks(ys)
    return statistics.correlation(rx, ry)


def quantis(v, qs=(0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1)):
    s = sorted(v)
    return {q: s[min(len(s) - 1, int(q * (len(s) - 1)))] for q in qs}


def resumo_snapshot(nome, linhas):
    print(f"\n=== Snapshot {nome} ===")
    print("registros:", len(linhas))
    print("colunas:", list(linhas[0].keys()) if linhas else [])
    for c in COLS:
        vazios = sum(1 for r in linhas if not (r.get(c) or "").strip())
        print(f"  {c}: vazios={vazios} distintos={len(set(r.get(c) for r in linhas))}")
    nun = [as_int(r["NUN_SOLICITACAO"]) for r in linhas]
    nun_ok = [n for n in nun if n is not None]
    print("NUN_SOLICITACAO numérico:", len(nun_ok), "| duplicados:", len(nun_ok) - len(set(nun_ok)))
    print("NUN_SOLICITACAO nº de dígitos:", dict(Counter(len(str(n)) for n in nun_ok)))
    # Quantis arredondados para milhar (evita expor números individuais)
    print("NUN_SOLICITACAO quantis (arred. 1000):",
          {q: round(v, -3) for q, v in quantis(nun_ok).items()})
    pos = [as_int(r["POSICAO_FILA"]) for r in linhas]
    pos_ok = [p for p in pos if p is not None]
    print("POSICAO_FILA min/max:", min(pos_ok), max(pos_ok), "| distintos:", len(set(pos_ok)),
          "| =9999:", sum(p == 9999 for p in pos_ok), "| >1000:", sum(p > 1000 for p in pos_ok))
    print("nº solicitação = 0:", sum(n == 0 for n in nun_ok))
    por_serie = Counter(serie(n) for n in nun_ok)
    unid_serie = {}
    for r in linhas:
        n = as_int(r["NUN_SOLICITACAO"])
        if n is not None:
            unid_serie.setdefault(serie(n), set()).add(r["UNIDADE"])
    print("por série:", dict(por_serie), "| unidades por série:",
          {k: len(v) for k, v in unid_serie.items()})
    mult = sum(1 for u in set(r["UNIDADE"] for r in linhas)
               if sum(u in v for v in unid_serie.values()) > 1)
    print("unidades com mais de uma série:", mult)
    return nun_ok


def _rho_por_grupo(linhas, chave, y="NUN_SOLICITACAO"):
    grupos = {}
    for r in linhas:
        p = as_int(r["POSICAO_FILA"])
        v = as_int(r[y]) if y == "NUN_SOLICITACAO" else ORDEM_SWALIS.get(r[y].strip(), 9)
        if p is None or v is None:
            continue
        grupos.setdefault(chave(r), ([], []))
        grupos[chave(r)][0].append(p)
        grupos[chave(r)][1].append(v)
    rhos, pesos = [], []
    for ps, vs in grupos.values():
        if len(ps) >= MIN_GRUPO and len(set(vs)) > 2 - (y != "NUN_SOLICITACAO"):
            rho = spearman(ps, vs)
            if rho is not None and rho == rho:
                rhos.append(rho)
                pesos.append(len(ps))
    return rhos, pesos


ORDEM_SWALIS = {"Categoria A1": 0, "Categoria B": 1, "Categoria C": 2, "Categoria D": 3}


def correlacao_posicao(linhas, nome):
    """Spearman posição × nº de solicitação dentro de cada fila (grupos com n >= 30)."""
    print(f"\n--- Posição × nº solicitação ({nome}) ---")
    par = [(as_int(r["POSICAO_FILA"]), as_int(r["NUN_SOLICITACAO"])) for r in linhas]
    par = [(p, n) for p, n in par if p is not None and n is not None]
    print("Spearman global:", round(spearman([p for p, _ in par], [n for _, n in par]), 3))
    recortes = {
        "unidade x especialidade": lambda r: (r["UNIDADE"], r["ESPECIALIDADE"]),
        "unidade x procedimento": lambda r: (r["UNIDADE"], r["PROCEDIMENTO"]),
        "unidade x procedimento x SWALIS": lambda r: (r["UNIDADE"], r["PROCEDIMENTO"], r["CLASSIF_SWALIS"]),
    }
    for rotulo, chave in recortes.items():
        rhos, pesos = _rho_por_grupo(linhas, chave)
        if not rhos:
            continue
        s = sorted(rhos)
        print(f"  {rotulo}: grupos={len(rhos)} registros={sum(pesos)} "
              f"mediana={statistics.median(rhos):.3f} ponderada={sum(r * w for r, w in zip(rhos, pesos)) / sum(pesos):.3f} "
              f"p10={s[len(s) // 10]:.3f} | grupos rho>0.9: {sum(r > 0.9 for r in rhos)}")
    rhos, _ = _rho_por_grupo(linhas, lambda r: (r["UNIDADE"], r["PROCEDIMENTO"]), y="CLASSIF_SWALIS")
    if rhos:
        print(f"  posição x SWALIS (unidade x procedimento): grupos={len(rhos)} mediana={statistics.median(rhos):.3f}")
    chaves_pos = Counter((r["UNIDADE"], r["ESPECIALIDADE"], r["POSICAO_FILA"]) for r in linhas)
    print("  posições repetidas em (unidade, especialidade):", sum(1 for v in chaves_pos.values() if v > 1))
    chaves_pos2 = Counter((r["UNIDADE"], r["PROCEDIMENTO"], r["POSICAO_FILA"]) for r in linhas)
    print("  posições repetidas em (unidade, procedimento):", sum(1 for v in chaves_pos2.values() if v > 1))


def main():
    arquivos = sorted(glob.glob(os.path.join(DATA_DIR, "consulta-fila-espera_*.csv")))
    if len(arquivos) < 2:
        raise SystemExit("São necessários ao menos dois snapshots.")
    a_path, b_path = arquivos[0], arquivos[-1]
    a, b = ler(a_path), ler(b_path)
    na = resumo_snapshot(os.path.basename(a_path), a)
    nb = resumo_snapshot(os.path.basename(b_path), b)
    correlacao_posicao(a, "snapshot A")
    correlacao_posicao(b, "snapshot B")

    sa, sb = set(na), set(nb)
    comuns, sairam, entraram = sa & sb, sa - sb, sb - sa
    print("\n=== Comparação A → B ===")
    print("comuns:", len(comuns), "| saíram:", len(sairam), "| entraram:", len(entraram))

    # Estabilidade dos atributos para o mesmo nº de solicitação
    ia = {as_int(r["NUN_SOLICITACAO"]): r for r in a}
    ib = {as_int(r["NUN_SOLICITACAO"]): r for r in b}
    for c in ["MUNICIPIO", "UNIDADE", "PROCEDIMENTO", "ESPECIALIDADE", "INIC_NOME_PACIENTE",
              "JUDICIALIZADO", "CLASSIF_SWALIS"]:
        dif = sum(1 for n in comuns if (ia[n][c] or "").strip() != (ib[n][c] or "").strip())
        print(f"  mudou {c}: {dif}")
    # Movimento de posição
    deltas = [as_int(ib[n]["POSICAO_FILA"]) - as_int(ia[n]["POSICAO_FILA"]) for n in comuns
              if as_int(ib[n]["POSICAO_FILA"]) is not None and as_int(ia[n]["POSICAO_FILA"]) is not None]
    print("delta posição (B−A): quantis", quantis(deltas),
          "| subiram:", sum(d < 0 for d in deltas), "| iguais:", sum(d == 0 for d in deltas),
          "| desceram:", sum(d > 0 for d in deltas))

    # Os que entraram têm nº de solicitação mais alto (recentes)?
    if entraram:
        ent = sorted(entraram)
        rank = sorted(sa)
        import bisect
        pct = [bisect.bisect_left(rank, n) / len(rank) for n in ent]
        print("entraram: percentil do nº no estoque A — quantis",
              {q: round(v, 3) for q, v in quantis(pct).items()})
        print("entraram com nº > máximo de A:", sum(n > rank[-1] for n in ent))
    if sairam:
        rank = sorted(sa)
        import bisect
        pct = [bisect.bisect_left(rank, n) / len(rank) for n in sairam]
        print("saíram: percentil do nº no estoque A — quantis",
              {q: round(v, 3) for q, v in quantis(pct).items()})
        pos_sai = [as_int(ia[n]["POSICAO_FILA"]) for n in sairam]
        print("saíram: posição em A — quantis", quantis([p for p in pos_sai if p is not None]))

    # Por série de numeração: entradas acima do máximo anterior = numeração sequencial
    print("\n--- Por série de numeração ---")
    horas = 41 + 51 / 60  # 22/02 13:14 → 24/02 07:06
    for sr in ["11 digitos", "7 digitos", "<=6 digitos"]:
        a_s = [n for n in sa if serie(n) == sr]
        b_s = [n for n in sb if serie(n) == sr]
        e_s = [n for n in entraram if serie(n) == sr]
        s_s = [n for n in sairam if serie(n) == sr]
        if not a_s:
            continue
        mx = max(a_s)
        acima = sum(n > mx for n in e_s)
        inc = max(b_s) - mx
        print(f"  {sr}: estoque A={len(a_s)} B={len(b_s)} entraram={len(e_s)} "
              f"(acima do máx. de A: {acima}) saíram={len(s_s)} | avanço do máx.: {inc} "
              f"(~{inc / horas * 24:.0f} números/dia)")
        # Entradas abaixo do máximo: quão abaixo? (reentrada/alteração x numeração antiga)
        abaixo = sorted(mx - n for n in e_s if n <= mx)
        if abaixo:
            print(f"     entradas abaixo do máx.: {len(abaixo)}; distância ao máx. mediana="
                  f"{statistics.median(abaixo):.0f}, p90={abaixo[int(0.9 * (len(abaixo) - 1))]}")
        # Amplitude da numeração no estoque (proxy de idade, a calibrar)
        q = quantis(a_s)
        print(f"     amplitude estoque (máx − p05) = {q[1] - q[0.05]}; (máx − mediana) = {q[1] - q[0.5]}")

    # Entradas/saídas por especialidade (agregado, só recortes >= MIN_GRUPO no estoque)
    print("\n--- Por especialidade (estoque A, estoque B, entraram, saíram) ---")
    ea = Counter(ia[n]["ESPECIALIDADE"] for n in sa)
    eb = Counter(ib[n]["ESPECIALIDADE"] for n in sb)
    ee = Counter(ib[n]["ESPECIALIDADE"] for n in entraram)
    es = Counter(ia[n]["ESPECIALIDADE"] for n in sairam)
    for esp in sorted(set(ea) | set(eb), key=lambda e: -ea.get(e, 0)):
        if max(ea.get(esp, 0), eb.get(esp, 0)) >= MIN_GRUPO:
            print(f"  {esp[:40]:40s} {ea.get(esp,0):6d} {eb.get(esp,0):6d} {ee.get(esp,0):5d} {es.get(esp,0):5d}")

    print("\nSWALIS (A):", dict(Counter((r["CLASSIF_SWALIS"] or "").strip() or "(vazio)" for r in a)))
    print("JUDICIALIZADO (A):", dict(Counter((r["JUDICIALIZADO"] or "").strip() or "(vazio)" for r in a)))
    print("unidades A/B:", len(set(r["UNIDADE"] for r in a)), len(set(r["UNIDADE"] for r in b)))


if __name__ == "__main__":
    main()
