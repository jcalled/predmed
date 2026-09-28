"use client";

/*
Por que o Analytics é uma tela crítica
Essa tela é o “cérebro estratégico” do produto. Ela não é operacional — é decisão.
Ela responde 4 perguntas de negócio:

1) Sazonalidade → Quando operar

Mostra quando a demanda sobe/baixa por especialidade
👉 Serve para:

Planejar mutirão
Evitar colapso
Aumentar faturamento com eletivas
Usar ociosidade inteligente
Isso é gestão hospitalar real.

2) Mortalidade → Onde está o risco

Ranking mostra:
Hospitais críticos
Permanência média alta
Taxa fora do padrão

👉 Serve para:

Gestão clínica
Auditoria
Indicador de qualidade
BI médico
Isso é indicador institucional sério.

3) Pressão histórica → Tendência do sistema

Mostra:

Picos
Colapsos
Crescimento estrutural
Estresse do SUS

👉 Serve para:

  Planejamento regional
  Previsão de demanda
  Gestão de leitos
  Gestão macro
  Isso é inteligência de sistema de saúde.

4) Espera real → Gargalo estrutural

Mostra:

  Especialidades com fila crônica
  Onde investir
  Onde fazer eletiva
  Onde faturar mais

👉 Serve para:

  Direcionar produção
  Definir prioridade
  Planejar expansão
  Isso é decisão de investimento.
*/
import { useEffect, useState } from "react";
import { useAuth } from '@/lib/auth'
import { analyticsApi } from '@/lib/api'

// ── Tipos ────────────────────────────────────────────────────────
interface ResumoAnalytics {
  base_dados: {
    total_aih: number;
    total_valor_pago: number;
    total_obitos: number;
    taxa_mortalidade_geral: number;
    anos_disponiveis: number[];
    especialidades: number;
    periodo: string;
  };
  espera_media_real: Record<string, number>;
  espera_media_geral_meses: number;
}

interface IndiceSazonal {
  mes: number;
  nome_mes: string;
  indice: number;
  media_internacoes: number;
  classificacao: "alta" | "baixa" | "normal";
}

interface SazonalidadeData {
  por_especialidade: Record<
    string,
    {
      indices_mensais: IndiceSazonal[];
      meses_criticos: string[];
      meses_ociosos: string[];
      recomendacao: string;
    }
  >;
  especialidades_disponiveis: string[];
}

interface MortalidadeItem {
  cnes: string;
  hospital_nome: string;
  especialidade: string;
  total_internacoes: number;
  total_obitos: number;
  taxa_mortalidade_pct: number;
  media_dias_perm: number;
  ticket_medio_aih: number;
  classificacao: "critico" | "alerta" | "normal";
}

interface PressaoHistoricaItem {
  mes: string;
  total_internacoes: number;
  val_total: number;
  obitos: number;
  media_movel_3m: number;
  evento: "pico" | "colapso" | "normal";
  desvio_media_pct: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Helpers ──────────────────────────────────────────────────────
const fmt = (n: number) => new Intl.NumberFormat("pt-BR").format(n);
const fmtR = (n: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);

function fetchAuth(token: string, path: string) {
  return fetch(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then((r) => r.json());
}

// ── Componente principal ─────────────────────────────────────────
export default function AnalyticsPage() {
  const { token } = useAuth();
  const [resumo, setResumo] = useState<ResumoAnalytics | null>(null);
  const [sazonalidade, setSazonalidade] = useState<SazonalidadeData | null>(null);
  const [mortalidade, setMortalidade] = useState<MortalidadeItem[]>([]);
  const [pressao, setPressao] = useState<PressaoHistoricaItem[]>([]);
  const [espSel, setEspSel] = useState("ORTOPEDIA");
  const [tab, setTab] = useState<"sazonalidade" | "mortalidade" | "pressao" | "espera">("sazonalidade");
  const [loading, setLoading] = useState(true);

useEffect(() => {
  let alive = true
  setLoading(true)

  Promise.all([
    analyticsApi.resumo(),
    analyticsApi.sazonalidade(),
    analyticsApi.mortalidade(2024),
    analyticsApi.pressaoHistorica(),
  ])
    .then(([r, s, m, p]) => {
      if (!alive) return
      setResumo(r)
      setSazonalidade(s)
      setMortalidade(m?.ranking || [])
      setPressao(p?.serie_temporal || [])
      if (s?.especialidades_disponiveis?.[0]) setEspSel(s.especialidades_disponiveis[0])
    })
    .finally(() => alive && setLoading(false))

  return () => { alive = false }
}, [])

  if (loading) return <LoadingState />;

  const espData = sazonalidade?.por_especialidade?.[espSel];

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-white font-mono">
      {/* Header */}
      <div className="border-b border-[#1e3a5f] bg-[#0d1529] px-8 py-5">
        <div className="flex items-center gap-3">
          <div className="w-2 h-8 bg-[#00d4ff] rounded-full" />
          <div>
            <h1 className="text-xl font-bold tracking-widest text-[#00d4ff] uppercase">
              Analytics SIH
            </h1>
            {resumo && (
              <p className="text-xs text-slate-400 mt-0.5">
                {fmt(resumo.base_dados.total_aih)} internações •{" "}
                {resumo.base_dados.periodo} • {resumo.base_dados.especialidades} especialidades
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="px-8 py-6 space-y-6">
        {/* KPIs */}
        {resumo && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Total AIH"
              value={fmt(resumo.base_dados.total_aih)}
              sub={`Período ${resumo.base_dados.periodo}`}
              color="#00d4ff"
            />
            <KpiCard
              label="Valor Pago SUS"
              value={fmtR(resumo.base_dados.total_valor_pago)}
              sub="Total histórico"
              color="#00ff9d"
            />
            <KpiCard
              label="Taxa Mortalidade"
              value={`${resumo.base_dados.taxa_mortalidade_geral}%`}
              sub={`${fmt(resumo.base_dados.total_obitos)} óbitos`}
              color={resumo.base_dados.taxa_mortalidade_geral > 3 ? "#ff4d4d" : "#ffd700"}
            />
            <KpiCard
              label="Espera Média"
              value={`${resumo.espera_media_geral_meses} meses`}
              sub="Média geral todas especialidades"
              color="#a78bfa"
            />
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 bg-[#0d1529] border border-[#1e3a5f] rounded-lg p-1 w-fit">
          {(["sazonalidade", "mortalidade", "pressao", "espera"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-md text-xs font-bold uppercase tracking-wider transition-all ${
                tab === t
                  ? "bg-[#00d4ff] text-[#0a0f1e]"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {t === "sazonalidade" && "📅 Sazonalidade"}
              {t === "mortalidade" && "⚕️ Mortalidade"}
              {t === "pressao" && "📈 Pressão Histórica"}
              {t === "espera" && "⏱ Espera Real"}
            </button>
          ))}
        </div>

        {/* Tab: Sazonalidade */}
        {tab === "sazonalidade" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 uppercase tracking-wider">Especialidade:</span>
              <select
                value={espSel}
                onChange={(e) => setEspSel(e.target.value)}
                className="bg-[#0d1529] border border-[#1e3a5f] text-white text-sm px-3 py-1.5 rounded-lg"
              >
                {sazonalidade?.especialidades_disponiveis.map((e) => (
                  <option key={e} value={e}>{e}</option>
                ))}
              </select>
            </div>

            {espData && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Gráfico de barras sazonal */}
                <div className="lg:col-span-2 bg-[#0d1529] border border-[#1e3a5f] rounded-xl p-5">
                  <h3 className="text-sm font-bold text-[#00d4ff] uppercase tracking-widest mb-4">
                    Índice Sazonal Mensal
                  </h3>
                  <div className="flex items-end gap-2 h-40">
                    {espData.indices_mensais.map((m) => {
                      const h = Math.round(m.indice * 80);
                      const cor =
                        m.classificacao === "alta"
                          ? "#ff4d4d"
                          : m.classificacao === "baixa"
                          ? "#00ff9d"
                          : "#00d4ff";
                      return (
                        <div key={m.mes} className="flex-1 flex flex-col items-center gap-1">
                          <span className="text-[9px] text-slate-400">{m.indice.toFixed(2)}</span>
                          <div
                            className="w-full rounded-t-sm transition-all"
                            style={{ height: h, backgroundColor: cor, opacity: 0.85 }}
                          />
                          <span className="text-[9px] text-slate-500">{m.nome_mes}</span>
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex gap-4 mt-3 text-[10px]">
                    <span className="text-[#ff4d4d]">■ Alta demanda</span>
                    <span className="text-[#00ff9d]">■ Baixa demanda</span>
                    <span className="text-[#00d4ff]">■ Normal</span>
                  </div>
                </div>

                {/* Info lateral */}
                <div className="space-y-3">
                  <div className="bg-[#0d1529] border border-[#ff4d4d]/30 rounded-xl p-4">
                    <p className="text-[10px] text-[#ff4d4d] uppercase tracking-widest mb-2">
                      Meses Críticos
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {espData.meses_criticos.map((m) => (
                        <span key={m} className="bg-[#ff4d4d]/20 text-[#ff4d4d] text-xs px-2 py-0.5 rounded">
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#0d1529] border border-[#00ff9d]/30 rounded-xl p-4">
                    <p className="text-[10px] text-[#00ff9d] uppercase tracking-widest mb-2">
                      Janelas para Eletivas
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {espData.meses_ociosos.map((m) => (
                        <span key={m} className="bg-[#00ff9d]/20 text-[#00ff9d] text-xs px-2 py-0.5 rounded">
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#0d1529] border border-[#a78bfa]/30 rounded-xl p-4">
                    <p className="text-[10px] text-[#a78bfa] uppercase tracking-widest mb-2">
                      Recomendação PREDMED
                    </p>
                    <p className="text-xs text-slate-300">{espData.recomendacao}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Mortalidade */}
        {tab === "mortalidade" && (
          <div className="bg-[#0d1529] border border-[#1e3a5f] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#1e3a5f] flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#00d4ff] uppercase tracking-widest">
                Ranking Mortalidade por Hospital — 2024
              </h3>
              <span className="text-xs text-slate-400">{mortalidade.length} hospitais</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#1e3a5f] text-slate-400 uppercase tracking-wider">
                    <th className="text-left px-5 py-3">Hospital</th>
                    <th className="text-left px-4 py-3">Especialidade</th>
                    <th className="text-right px-4 py-3">Internações</th>
                    <th className="text-right px-4 py-3">Óbitos</th>
                    <th className="text-right px-4 py-3">Taxa</th>
                    <th className="text-right px-4 py-3">Perm. Média</th>
                    <th className="text-right px-4 py-3">Ticket AIH</th>
                    <th className="text-center px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {mortalidade.slice(0, 20).map((h, i) => (
                    <tr
                      key={i}
                      className="border-b border-[#1e3a5f]/50 hover:bg-[#1e3a5f]/20 transition-colors"
                    >
                      <td className="px-5 py-3 text-white font-medium max-w-[200px] truncate">
                        {h.hospital_nome}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{h.especialidade}</td>
                      <td className="px-4 py-3 text-right text-slate-300">{fmt(h.total_internacoes)}</td>
                      <td className="px-4 py-3 text-right text-slate-300">{fmt(h.total_obitos)}</td>
                      <td className="px-4 py-3 text-right font-bold" style={{
                        color: h.taxa_mortalidade_pct > 5 ? "#ff4d4d" : h.taxa_mortalidade_pct > 2 ? "#ffd700" : "#00ff9d"
                      }}>
                        {h.taxa_mortalidade_pct}%
                      </td>
                      <td className="px-4 py-3 text-right text-slate-300">{h.media_dias_perm}d</td>
                      <td className="px-4 py-3 text-right text-slate-300">{fmtR(h.ticket_medio_aih)}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          h.classificacao === "critico"
                            ? "bg-[#ff4d4d]/20 text-[#ff4d4d]"
                            : h.classificacao === "alerta"
                            ? "bg-[#ffd700]/20 text-[#ffd700]"
                            : "bg-[#00ff9d]/20 text-[#00ff9d]"
                        }`}>
                          {h.classificacao.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab: Pressão Histórica */}
        {tab === "pressao" && (
          <div className="bg-[#0d1529] border border-[#1e3a5f] rounded-xl p-5">
            <h3 className="text-sm font-bold text-[#00d4ff] uppercase tracking-widest mb-4">
              Volume de Internações — Série Histórica
            </h3>
            <div className="overflow-x-auto">
              <div className="flex items-end gap-1 h-48 min-w-[800px]">
                {pressao.map((p, i) => {
                  const max = Math.max(...pressao.map((x) => x.total_internacoes));
                  const h = Math.round((p.total_internacoes / max) * 160);
                  const cor =
                    p.evento === "pico"
                      ? "#ff4d4d"
                      : p.evento === "colapso"
                      ? "#ffd700"
                      : "#00d4ff";
                  return (
                    <div
                      key={i}
                      className="flex-1 flex flex-col items-center gap-0.5 group relative"
                      title={`${p.mes}: ${fmt(p.total_internacoes)} internações`}
                    >
                      <div
                        className="w-full rounded-t-sm transition-all group-hover:opacity-100 opacity-75"
                        style={{ height: h, backgroundColor: cor }}
                      />
                      {i % 6 === 0 && (
                        <span className="text-[8px] text-slate-500 -rotate-90 mt-1 whitespace-nowrap">
                          {p.mes}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex gap-4 mt-4 text-[10px]">
              <span className="text-[#ff4d4d]">■ Pico (&gt;20% acima da média)</span>
              <span className="text-[#ffd700]">■ Colapso (&gt;20% abaixo)</span>
              <span className="text-[#00d4ff]">■ Normal</span>
            </div>
          </div>
        )}

        {/* Tab: Espera Real */}
        {tab === "espera" && resumo && (
          <div className="bg-[#0d1529] border border-[#1e3a5f] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#1e3a5f]">
              <h3 className="text-sm font-bold text-[#00d4ff] uppercase tracking-widest">
                Tempo de Espera Real por Especialidade
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Calculado a partir de {fmt(resumo.base_dados.total_aih)} internações reais SIH/DATASUS
              </p>
            </div>
            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(resumo.espera_media_real)
                .sort(([, a], [, b]) => b - a)
                .map(([esp, meses]) => (
                  <div key={esp} className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 w-48 truncate">{esp}</span>
                    <div className="flex-1 bg-[#1e3a5f]/40 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${Math.min((meses / 12) * 100, 100)}%`,
                          backgroundColor: meses > 8 ? "#ff4d4d" : meses > 5 ? "#ffd700" : "#00ff9d",
                        }}
                      />
                    </div>
                    <span className="text-xs font-bold text-white w-16 text-right">
                      {meses} meses
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-componentes ──────────────────────────────────────────────

function KpiCard({
  label, value, sub, color,
}: {
  label: string; value: string; sub: string; color: string;
}) {
  return (
    <div
      className="bg-[#0d1529] border rounded-xl p-4"
      style={{ borderColor: `${color}30` }}
    >
      <p className="text-[10px] uppercase tracking-widest mb-1" style={{ color }}>
        {label}
      </p>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-[10px] text-slate-500 mt-1">{sub}</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-[#0a0f1e] flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="w-8 h-8 border-2 border-[#00d4ff] border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-[#00d4ff] text-sm font-mono">Carregando analytics SIH...</p>
      </div>
    </div>
  );
}