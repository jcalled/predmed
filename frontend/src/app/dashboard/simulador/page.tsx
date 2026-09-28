"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { analyticsApi, configApi } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SimEspecialidade {
  especialidade: string;
  vagas_mes: number;
  ticket_medio_real: number;
  receita_mes: number;
  receita_ano: number;
  fonte: string;
  intervalo_confianca: { baixo: number; alto: number };
  por_complexidade: Record<string, {
    total_aih: number;
    ticket_medio: number;
    minimo: number;
    maximo: number;
  }>;
}

interface SimResumo {
  total_vagas_mes: number;
  receita_total_mes: number;
  receita_total_ano: number;
  ticket_medio_geral: number;
  receita_conservadora_mes: number;
  receita_otimista_mes: number;
}

interface SimulacaoResult {
  simulacao_por_especialidade: SimEspecialidade[];
  resumo: SimResumo;
  anos_base: number[];
  nota: string;
}

const ESPECIALIDADES_DISPONIVEIS = [
  "ORTOPEDIA", "CARDIOVASCULAR", "ONCOLOGIA", "NEUROLOGIA",
  "UROLOGIA", "GINECOLOGIA", "OFTALMOLOGIA", "CIR DIGESTIVA",
  "BUCOMAXILOFACIAL", "CIR PLASTICA REPARADORA",
  "OTORRINOLARINGOLOGIA", "ENDOCRINOLOGIA",
];

const fmtR = (n: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
const fmt = (n: number) => new Intl.NumberFormat("pt-BR").format(n);

export default function SimuladorPage() {
  const { token, user } = useAuth();
  const [vagas, setVagas] = useState<Record<string, number>>({
    ORTOPEDIA: 10,
    CARDIOVASCULAR: 5,
  });
  const [resultado, setResultado] = useState<SimulacaoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [novaEsp, setNovaEsp] = useState(ESPECIALIDADES_DISPONIVEIS[0]);

  // Carrega vagas configuradas do hospital particular
  useEffect(() => {
    if (user?.role !== "hospital_particular") return;

    configApi.getVagas().then((data) => {
      if (data?.vagas?.length) {
        const v: Record<string, number> = {};
        data.vagas.forEach((cfg: { especialidade: string; vagas_mes: number }) => {
          if (cfg.vagas_mes > 0) v[cfg.especialidade] = cfg.vagas_mes;
        });
        if (Object.keys(v).length) setVagas(v);
      }
    });
  }, [user?.role]);

  const simular = async () => {
    setLoading(true);
    try {
      const data = await analyticsApi.simuladorReceita(vagas);
      setResultado(data);
    } finally {
      setLoading(false);
    }
  };

  const addEspecialidade = () => {
    if (!vagas[novaEsp]) setVagas({ ...vagas, [novaEsp]: 5 });
  };

  const removeEsp = (esp: string) => {
    const v = { ...vagas };
    delete v[esp];
    setVagas(v);
    if (resultado) {
      setResultado({
        ...resultado,
        simulacao_por_especialidade: resultado.simulacao_por_especialidade.filter(
          (s) => s.especialidade !== esp
        ),
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#050d1a] text-white" style={{ fontFamily: "'DM Mono', 'Courier New', monospace" }}>
      {/* Header */}
      <div className="border-b border-emerald-900/40 bg-[#071220] px-8 py-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-lg">
              💰
            </div>
            <div>
              <h1 className="text-lg font-bold text-emerald-400 tracking-widest uppercase">
                Simulador de Receita
              </h1>
              <p className="text-xs text-slate-500">
                Baseado em valores reais SIH/DATASUS Ceará
              </p>
            </div>
          </div>
          {resultado && (
            <div className="text-right">
              <p className="text-xs text-slate-500 uppercase tracking-wider">Receita Projetada / Mês</p>
              <p className="text-3xl font-bold text-emerald-400">
                {fmtR(resultado.resumo.receita_total_mes)}
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="px-8 py-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Painel de configuração */}
        <div className="space-y-4">
          <div className="bg-[#071220] border border-emerald-900/30 rounded-xl p-5">
            <h2 className="text-sm font-bold text-emerald-400 uppercase tracking-widest mb-4">
              Configure as Vagas
            </h2>

            <div className="space-y-3">
              {Object.entries(vagas).map(([esp, qtd]) => (
                <div key={esp} className="flex items-center gap-3">
                  <div className="flex-1 bg-[#0a1628] border border-emerald-900/20 rounded-lg px-3 py-2">
                    <p className="text-xs text-slate-400 uppercase tracking-wider">{esp}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setVagas({ ...vagas, [esp]: Math.max(0, qtd - 1) })}
                      className="w-7 h-7 rounded bg-emerald-900/30 text-emerald-400 hover:bg-emerald-900/50 text-sm font-bold"
                    >
                      −
                    </button>
                    <input
                      type="number"
                      value={qtd}
                      onChange={(e) => setVagas({ ...vagas, [esp]: parseInt(e.target.value) || 0 })}
                      className="w-14 text-center bg-[#0a1628] border border-emerald-900/30 rounded text-white text-sm py-1"
                    />
                    <button
                      onClick={() => setVagas({ ...vagas, [esp]: qtd + 1 })}
                      className="w-7 h-7 rounded bg-emerald-900/30 text-emerald-400 hover:bg-emerald-900/50 text-sm font-bold"
                    >
                      +
                    </button>
                  </div>
                  <button
                    onClick={() => removeEsp(esp)}
                    className="text-slate-600 hover:text-red-400 text-xs px-1"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            {/* Adicionar especialidade */}
            <div className="mt-4 flex gap-2">
              <select
                value={novaEsp}
                onChange={(e) => setNovaEsp(e.target.value)}
                className="flex-1 bg-[#0a1628] border border-emerald-900/20 text-slate-300 text-xs px-3 py-2 rounded-lg"
              >
                {ESPECIALIDADES_DISPONIVEIS.filter((e) => !vagas[e]).map((e) => (
                  <option key={e} value={e}>{e}</option>
                ))}
              </select>
              <button
                onClick={addEspecialidade}
                className="px-3 py-2 bg-emerald-900/30 border border-emerald-500/30 text-emerald-400 text-xs rounded-lg hover:bg-emerald-900/50"
              >
                + Adicionar
              </button>
            </div>

            {/* Total vagas */}
            <div className="mt-4 pt-4 border-t border-emerald-900/20 flex justify-between items-center">
              <span className="text-xs text-slate-500">Total vagas/mês</span>
              <span className="text-lg font-bold text-white">
                {Object.values(vagas).reduce((a, b) => a + b, 0)} pacientes
              </span>
            </div>
          </div>

          {/* Botão simular */}
          <button
            onClick={simular}
            disabled={loading || Object.keys(vagas).length === 0}
            className="w-full py-4 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-[#050d1a] font-bold text-sm uppercase tracking-widest rounded-xl transition-all"
          >
            {loading ? "Calculando..." : "▶ Simular Receita"}
          </button>

          {resultado && (
            <div className="bg-[#071220] border border-emerald-900/30 rounded-xl p-5 text-xs text-slate-400">
              <p className="text-emerald-400 font-bold mb-1">Fonte dos dados</p>
              <p>{resultado.nota}</p>
              <p className="mt-1">Anos base: {resultado.anos_base.join(", ")}</p>
            </div>
          )}
        </div>

        {/* Painel de resultado */}
        <div className="space-y-4">
          {resultado ? (
            <>
              {/* Cards resumo */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#071220] border border-emerald-500/20 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Receita Mensal</p>
                  <p className="text-xl font-bold text-emerald-400">
                    {fmtR(resultado.resumo.receita_total_mes)}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    {fmtR(resultado.resumo.receita_conservadora_mes)} — {fmtR(resultado.resumo.receita_otimista_mes)}
                  </p>
                </div>
                <div className="bg-[#071220] border border-emerald-500/20 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Receita Anual</p>
                  <p className="text-xl font-bold text-white">
                    {fmtR(resultado.resumo.receita_total_ano)}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    Ticket médio: {fmtR(resultado.resumo.ticket_medio_geral)}
                  </p>
                </div>
              </div>

              {/* Por especialidade */}
              <div className="bg-[#071220] border border-emerald-900/30 rounded-xl overflow-hidden">
                <div className="px-5 py-3 border-b border-emerald-900/20">
                  <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-widest">
                    Por Especialidade
                  </h3>
                </div>
                <div className="divide-y divide-emerald-900/20">
                  {resultado.simulacao_por_especialidade.map((s) => (
                    <div key={s.especialidade} className="px-5 py-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="text-sm font-bold text-white">{s.especialidade}</p>
                          <p className="text-xs text-slate-500">
                            {s.vagas_mes} vagas × {fmtR(s.ticket_medio_real)} ticket médio real
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold text-emerald-400">{fmtR(s.receita_mes)}/mês</p>
                          <p className="text-[10px] text-slate-500">{fmtR(s.receita_ano)}/ano</p>
                        </div>
                      </div>

                      {/* Barra de confiança */}
                      <div className="flex items-center gap-2 text-[9px] text-slate-600">
                        <span>{fmtR(s.intervalo_confianca.baixo)}</span>
                        <div className="flex-1 bg-emerald-900/20 rounded-full h-1.5">
                          <div className="h-1.5 bg-emerald-500 rounded-full" style={{ width: "70%" }} />
                        </div>
                        <span>{fmtR(s.intervalo_confianca.alto)}</span>
                      </div>

                      {/* Complexidade */}
                      {Object.keys(s.por_complexidade).length > 0 && (
                        <div className="mt-2 flex gap-2 flex-wrap">
                          {Object.entries(s.por_complexidade).map(([complex, dados]) => (
                            <span
                              key={complex}
                              className="text-[9px] bg-emerald-900/20 text-emerald-400 px-2 py-0.5 rounded"
                            >
                              {complex}: {fmtR(dados.ticket_medio)}
                            </span>
                          ))}
                        </div>
                      )}

                      {s.fonte === "SIH real" ? (
                        <span className="text-[9px] text-emerald-600 mt-1 block">✓ Baseado em dados reais SIH</span>
                      ) : (
                        <span className="text-[9px] text-yellow-600 mt-1 block">⚠ Estimativa (sem dados SIH)</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-[#071220] border border-emerald-900/20 rounded-xl p-12 text-center">
              <div className="text-4xl mb-4">📊</div>
              <p className="text-slate-400 text-sm">
                Configure as vagas e clique em Simular para ver a projeção de receita baseada em valores reais do SIH.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}