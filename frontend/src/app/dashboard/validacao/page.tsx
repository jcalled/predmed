"use client";

/*
Tela Validação (MAPE): mede o erro da previsão Holt-Winters contra dados observados.
Método: holdout temporal — treina na série mensal de AIH do SIH sem os últimos N meses,
prevê esses N meses e compara com o realizado.
Atenção: o alvo validado aqui é a produção hospitalar (contagem de AIH), não a fila.
"SEM DADOS" significa que o backend não encontrou base SIH suficiente (não é bug do frontend).
Meta do projeto (proposta Centelha): MAPE < 15%. A meta é referência, não resultado.
*/

import { useEffect, useMemo, useState } from "react";
import { analyticsApi } from "@/lib/api";

interface ComparacaoMensal {
  mes: string;
  previsto: number;
  realizado: number;
  erro_absoluto: number;
  erro_pct: number;
  dentro_meta: boolean;
}

interface ValidacaoData {
  especialidade: string;
  mape_real: number | null;
  meta_projeto_mape_pct: number;
  dentro_da_meta: boolean | null;
  status?: "calculado" | "nao_validado";
  alvo_validado?: string;
  comparacao_mensal: ComparacaoMensal[];
  meses_comparados: number;
  meses_sem_dados_reais: number;
  resumo: {
    melhor_mes: ComparacaoMensal | null;
    pior_mes: ComparacaoMensal | null;
    meses_dentro_meta: number;
  };
  interpretacao: string;
}

const ESPECIALIDADES = [
  "TOTAL",
  "ORTOPEDIA",
  "CARDIOVASCULAR",
  "ONCOLOGIA",
  "NEUROLOGIA",
  "UROLOGIA",
  "GINECOLOGIA",
  "OFTALMOLOGIA",
] as const;

const fmt = (n: number) => new Intl.NumberFormat("pt-BR").format(Math.round(n));

export default function ValidacaoPage() {
  const [espSel, setEspSel] = useState<(typeof ESPECIALIDADES)[number]>("TOTAL");
  const [meses, setMeses] = useState(6);

  const [dados, setDados] = useState<ValidacaoData | null>(null);
  const [loading, setLoading] = useState(false);

  const [todas, setTodas] = useState<Record<string, ValidacaoData>>({});
  const [loadingTodas, setLoadingTodas] = useState(false);

  const mapeColor = (mape: number | null) => {
    if (mape === null) return "#64748b";
    if (mape < 10) return "#00ff9d";
    if (mape < 15) return "#ffd700";
    return "#ff4d4d";
  };

  const mapeLabel = (mape: number | null) => {
    if (mape === null) return "NÃO VALIDADO";
    if (mape < 15) return "DENTRO DA META";
    return "ACIMA DA META";
  };

  const carregar = async (esp: string, horizonte: number) => {
    setLoading(true);
    try {
      const data = await analyticsApi.validacaoMape(esp, horizonte);
      setDados(data);
      setTodas((prev) => ({ ...prev, [esp]: data }));
    } finally {
      setLoading(false);
    }
  };

  // Carrega a especialidade selecionada (sempre que mudar esp/horizonte)
  useEffect(() => {
    let alive = true;

    (async () => {
      setLoading(true);
      try {
        const data = await analyticsApi.validacaoMape(espSel, meses);
        if (!alive) return;
        setDados(data);
        setTodas((prev) => ({ ...prev, [espSel]: data }));
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [espSel, meses]);

  // Carrega o “status por especialidade” (todas) — respeitando o horizonte atual
  useEffect(() => {
    let alive = true;

    (async () => {
      setLoadingTodas(true);
      try {
        const results = await Promise.all(
          ESPECIALIDADES.map(async (esp) => {
            const data = await analyticsApi.validacaoMape(esp, meses);
            return [esp, data] as const;
          })
        );

        if (!alive) return;

        const map: Record<string, ValidacaoData> = {};
        for (const [esp, data] of results) map[esp] = data;
        setTodas(map);

        // Se ainda não tem detalhe carregado (primeira vez), usa TOTAL
        if (!dados && map[espSel]) setDados(map[espSel]);
      } finally {
        if (alive) setLoadingTodas(false);
      }
    })();

    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meses]);

  const comparacaoMax = useMemo(() => {
    if (!dados?.comparacao_mensal?.length) return 0;
    return Math.max(...dados.comparacao_mensal.map((x) => Math.max(x.previsto, x.realizado)));
  }, [dados]);

  return (
    <div
      className="min-h-screen bg-[#08080f] text-white"
      style={{ fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}
    >
      {/* Header */}
      <div className="border-b border-violet-900/30 bg-[#0c0c1a] px-8 py-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-widest text-violet-400 uppercase">
              Validação MAPE (holdout SIH)
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Compara previsão Holt-Winters vs produção SIH realizada (contagem de AIH, não a fila). Meta do projeto: MAPE &lt; 15%
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500">Horizonte:</span>
            {[3, 6, 12].map((m) => (
              <button
                key={m}
                onClick={() => setMeses(m)}
                className={`px-3 py-1.5 rounded text-xs font-bold transition-all ${
                  meses === m
                    ? "bg-violet-600 text-white"
                    : "bg-violet-900/20 text-violet-400 hover:bg-violet-900/40"
                }`}
              >
                {m}m
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="px-8 py-6 space-y-6">
        {/* Grid de status — todas especialidades */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[10px] text-slate-500 uppercase tracking-widest">
              Status por Especialidade
            </p>
            {loadingTodas && (
              <div className="flex items-center gap-2 text-[10px] text-slate-500">
                <div className="w-3 h-3 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                atualizando…
              </div>
            )}
          </div>

          <div className="grid grid-cols-4 lg:grid-cols-8 gap-2">
            {ESPECIALIDADES.map((esp) => {
              const d = todas[esp];
              const mape = d?.mape_real ?? null;
              const cor = mapeColor(mape);

              return (
                <button
                  key={esp}
                  onClick={() => setEspSel(esp)}
                  className={`p-3 rounded-xl border transition-all text-center ${
                    espSel === esp
                      ? "border-violet-500 bg-violet-900/30"
                      : "border-slate-800 bg-[#0c0c1a] hover:border-slate-600"
                  }`}
                >
                  <p className="text-[9px] text-slate-400 truncate mb-1">{esp}</p>
                  <p className="text-sm font-bold" style={{ color: cor }}>
                    {d ? (mape !== null ? `${mape.toFixed(1)}%` : "—") : "…"}
                  </p>
                  <p className="text-[8px] font-bold mt-0.5" style={{ color: cor }}>
                    {d ? mapeLabel(mape) : "CARREGANDO"}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Detalhe da especialidade selecionada */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : dados ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Resultado principal */}
            <div className="bg-[#0c0c1a] border border-violet-900/30 rounded-xl p-6 flex flex-col items-center justify-center text-center">
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-3">
                MAPE calculado — {espSel}
              </p>

              <div className="relative w-32 h-32 mb-4">
                <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#1e1e3a" strokeWidth="10" />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke={mapeColor(dados.mape_real)}
                    strokeWidth="10"
                    strokeDasharray={`${Math.min(((dados.mape_real ?? 0) / 30) * 251, 251)} 251`}
                    strokeLinecap="round"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#ffd700"
                    strokeWidth="2"
                    strokeDasharray={`2 ${251 - 2}`}
                    strokeDashoffset={`-${(15 / 30) * 251}`}
                    opacity={0.6}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold" style={{ color: mapeColor(dados.mape_real) }}>
                    {dados.mape_real !== null ? `${dados.mape_real.toFixed(1)}%` : "—"}
                  </span>
                  <span className="text-[10px] font-bold mt-0.5" style={{ color: mapeColor(dados.mape_real) }}>
                    {mapeLabel(dados.mape_real)}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-400">{dados.interpretacao}</p>

              <div className="mt-4 w-full pt-4 border-t border-violet-900/20 grid grid-cols-2 gap-3 text-center">
                <div>
                  <p className="text-[9px] text-slate-500 uppercase">Meses comparados</p>
                  <p className="text-lg font-bold text-white">{dados.meses_comparados}</p>
                </div>
                <div>
                  <p className="text-[9px] text-slate-500 uppercase">Dentro da meta</p>
                  <p className="text-lg font-bold text-white">
                    {dados.resumo.meses_dentro_meta}/{dados.meses_comparados}
                  </p>
                </div>
              </div>

              {dados.meses_sem_dados_reais > 0 && (
                <p className="mt-3 text-[9px] text-yellow-600">
                  ⚠ {dados.meses_sem_dados_reais} meses sem dados SIH ainda
                </p>
              )}
            </div>

            {/* Tabela comparação mensal */}
            <div className="lg:col-span-2 bg-[#0c0c1a] border border-violet-900/30 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-violet-900/20">
                <h3 className="text-xs font-bold text-violet-400 uppercase tracking-widest">
                  Comparação Mês a Mês
                </h3>
              </div>

              {dados.comparacao_mensal.length > 0 ? (
                <>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-violet-900/20 text-slate-500 uppercase tracking-wider">
                        <th className="text-left px-5 py-3">Mês</th>
                        <th className="text-right px-4 py-3">Previsto</th>
                        <th className="text-right px-4 py-3">Realizado</th>
                        <th className="text-right px-4 py-3">Erro</th>
                        <th className="text-center px-4 py-3">Meta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dados.comparacao_mensal.map((c, i) => (
                        <tr
                          key={i}
                          className="border-b border-violet-900/10 hover:bg-violet-900/10 transition-colors"
                        >
                          <td className="px-5 py-3 text-white font-bold">{c.mes}</td>
                          <td className="px-4 py-3 text-right text-slate-300">{fmt(c.previsto)}</td>
                          <td className="px-4 py-3 text-right text-slate-300">{fmt(c.realizado)}</td>
                          <td
                            className="px-4 py-3 text-right font-bold"
                            style={{ color: c.dentro_meta ? "#00ff9d" : "#ff4d4d" }}
                          >
                            {c.erro_pct.toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-center">
                            {c.dentro_meta ? (
                              <span className="text-[#00ff9d] text-sm">✓</span>
                            ) : (
                              <span className="text-[#ff4d4d] text-sm">✗</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="px-5 py-4 border-t border-violet-900/20">
                    <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-3">
                      Previsto vs Realizado
                    </p>
                    <div className="space-y-2">
                      {dados.comparacao_mensal.map((c, i) => {
                        const max = comparacaoMax || 1;
                        return (
                          <div key={i} className="flex items-center gap-2 text-[9px]">
                            <span className="text-slate-500 w-16">{c.mes}</span>
                            <div className="flex-1 space-y-0.5">
                              <div
                                className="h-1.5 rounded-full bg-violet-500 opacity-70"
                                style={{ width: `${(c.previsto / max) * 100}%` }}
                              />
                              <div
                                className="h-1.5 rounded-full bg-[#00ff9d] opacity-70"
                                style={{ width: `${(c.realizado / max) * 100}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex gap-4 mt-2 text-[9px]">
                      <span className="text-violet-400">■ Previsto</span>
                      <span className="text-[#00ff9d]">■ Realizado</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="px-5 py-12 text-center">
                  <p className="text-slate-500 text-sm">Sem dados SIH disponíveis para comparação.</p>
                  <p className="text-slate-600 text-xs mt-2">
                    Execute o download_sih.py para importar dados históricos.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : null}

        {/* Nota metodológica */}
        <div className="bg-[#0c0c1a] border border-violet-900/20 rounded-xl p-5">
          <p className="text-[10px] text-violet-400 uppercase tracking-widest mb-2 font-bold">
            Metodologia
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">
            O MAPE (Mean Absolute Percentage Error) é calculado por holdout temporal: o modelo Holt-Winters é
            treinado sem os últimos meses da série mensal de AIH do SIH/DATASUS Ceará e comparado com o realizado
            nesses meses. O alvo é a produção hospitalar, não a fila de espera. A meta do projeto (proposta ao
            Programa Centelha 3) é MAPE &lt; 15%; é uma meta, não um resultado garantido. Os dados de validação
            são públicos (TabNet/DATASUS).
          </p>
        </div>
      </div>
    </div>
  );
}