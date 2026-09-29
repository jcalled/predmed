'use client'
import { useState } from 'react'
import useSWR from 'swr'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, ComposedChart
} from 'recharts'
import { previsoesApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'
import SeloDado from '@/components/ui/SeloDado'

// ── Tipos ─────────────────────────────────────────────────
interface PontoSerie {
  mes: string
  fila_total: number
  entradas_mes: number
  saidas_mes: number
  capacidade_mes: number
  tipo: 'historico' | 'projecao'
}

interface Metricas {
  mape_pct: number | null
  mape_status?: string
  slope_mensal_pct: number
  fila_atual: number
  fila_proj_6m: number
  variacao_pct: number
  espera_media_atual_meses: number
  espera_projetada_meses: number
  capacidade_mensal: number
  entradas_media_mensal: number
  fila_com_redistrib_6m: number
  economia_pacientes_redistrib: number
}

interface Alerta {
  nivel: 'critico' | 'alerta'
  msg: string
}

interface DadosPrevisao {
  especialidade: string
  serie_completa: PontoSerie[]
  historico: PontoSerie[]
  projecao: PontoSerie[]
  metricas: Metricas
  alertas: Alerta[]
}

// ── Especialidades ────────────────────────────────────────
const ESPECIALIDADES = [
  { key: '', label: 'Geral (Total)' },
  { key: 'UROLOGIA', label: 'Urologia' },
  { key: 'GINECOLOGIA', label: 'Ginecologia' },
  { key: 'CIR DIGESTIVA', label: 'Cir. Digestiva' },
  { key: 'ORTOPEDIA', label: 'Ortopedia' },
  { key: 'CARDIOVASCULAR', label: 'Cardiovascular' },
  { key: 'NEUROLOGIA', label: 'Neurologia' },
  { key: 'OFTALMOLOGIA', label: 'Oftalmologia' },
  { key: 'ONCOLOGIA', label: 'Oncologia' },
]

// ── Tooltip customizado ───────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const isProj = payload[0]?.payload?.tipo === 'projecao'
  return (
    <div className="card" style={{ minWidth: 180, padding: '10px 14px', fontSize: 13 }}>
      <div className="font-semibold mb-2" style={{ color: isProj ? 'var(--accent3)' : 'var(--accent)' }}>
        {label} {isProj ? '(projeção)' : '(histórico)'}
      </div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-mono font-semibold">{Number(p.value).toLocaleString('pt-BR')}</span>
        </div>
      ))}
    </div>
  )
}

function fmtMes(mes: string) {
  const [ano, m] = mes.split('-')
  const nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
  return `${nomes[parseInt(m) - 1]}/${ano.slice(2)}`
}

function AlertaBadge({ alerta }: { alerta: Alerta }) {
  const isCrit = alerta.nivel === 'critico'
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded-lg text-sm" style={{
      background: isCrit ? 'rgba(255,68,68,0.07)' : 'rgba(255,165,0,0.07)',
      border: `1px solid ${isCrit ? 'rgba(255,68,68,0.25)' : 'rgba(255,165,0,0.25)'}`,
      color: isCrit ? 'var(--red)' : 'var(--yellow)',
    }}>
      <span>{isCrit ? '🚨' : '⚠️'}</span>
      <span>{alerta.msg}</span>
    </div>
  )
}

// ── Página ────────────────────────────────────────────────
export default function PrevisaoLinear() {
  const [espSelecionada, setEspSelecionada] = useState('')
  const [mostrarRedistrib, setMostrarRedistrib] = useState(true)

  const { data, isLoading } = useSWR<DadosPrevisao>(
    ['previsoes', espSelecionada],
    () => previsoesApi.get(espSelecionada || undefined)
  )

  const { data: todas } = useSWR('previsoes-todas', previsoesApi.todas)

  const corte = data?.historico?.length ?? 0

  const serie = data?.serie_completa?.map(p => ({
    ...p,
    mes_fmt: fmtMes(p.mes),
    fila_redistrib: p.tipo === 'projecao' && data?.metricas?.economia_pacientes_redistrib
      ? Math.max(0, p.fila_total - Math.round(data.metricas.economia_pacientes_redistrib / 6 * serie_index(p, data.serie_completa)))
      : undefined,
  })) ?? []

  function serie_index(p: PontoSerie, arr: PontoSerie[]) {
    const projs = arr.filter(x => x.tipo === 'projecao')
    return projs.indexOf(p) + 1
  }

  const m = data?.metricas

  return (
    <div className="animate-fadein">
      <div className="mb-5 flex flex-wrap items-center gap-2 text-sm" style={{ color: 'var(--text2)' }}>
        <span>
          Série histórica <strong>simulada</strong> de 24 meses (estimada a partir da fila atual e do DATASUS) + projeção de 6 meses por regressão linear.
        </span>
        <SeloDado natureza="simulado" />
        <SeloDado natureza="nao_validado" />
      </div>

      {/* Alertas */}
      {data?.alertas && data.alertas.length > 0 && (
        <div className="flex flex-col gap-2 mb-5">
          {data.alertas.map((a, i) => <AlertaBadge key={i} alerta={a} />)}
        </div>
      )}

      {/* Especialidade */}
      <div className="flex flex-wrap gap-2 mb-6" role="group" aria-label="Especialidade">
        {ESPECIALIDADES.map(esp => (
          <button
            key={esp.key}
            type="button"
            aria-pressed={espSelecionada === esp.key}
            onClick={() => setEspSelecionada(esp.key)}
            className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            style={{
              background: espSelecionada === esp.key ? 'var(--accent)' : 'var(--surface)',
              color: espSelecionada === esp.key ? '#0a0f1e' : 'var(--text2)',
              border: `1px solid ${espSelecionada === esp.key ? 'var(--accent)' : 'var(--border)'}`,
            }}
          >
            {esp.label}
          </button>
        ))}
      </div>

      {/* KPIs */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="kpi-card animate-pulse" style={{ height: 90 }} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            label="Fila Atual"
            value={m?.fila_atual?.toLocaleString('pt-BR') ?? '—'}
            detail={ESPECIALIDADES.find(e => e.key === espSelecionada)?.label ?? 'Total'}
            color="red"
            tooltip="Total de pacientes na fila — dados IntegraSUS."
            status="medido"
          />
          <KPICard
            label="Projeção 6 Meses"
            value={m?.fila_proj_6m?.toLocaleString('pt-BR') ?? '—'}
            detail={m ? `${m.variacao_pct > 0 ? '+' : ''}${m.variacao_pct}% vs hoje` : ''}
            color={m && m.variacao_pct > 10 ? 'red' : m && m.variacao_pct > 3 ? 'yellow' : 'green'}
            tooltip="Projeção em 6 meses sem intervenção, por regressão linear sobre série simulada."
            status="nao_validado"
          />
          <KPICard
            label="Espera Projetada (simulado)"
            value={m ? `${m.espera_projetada_meses}m` : '—'}
            detail={m ? `Parâmetro atual: ${m.espera_media_atual_meses}m` : ''}
            color={m && m.espera_projetada_meses > 8 ? 'red' : 'yellow'}
            tooltip="Estimativa sobre série simulada; a espera atual é um parâmetro fixo, não medido."
            status="simulado"
          />
          <KPICard
            label="Acurácia (MAPE)"
            value={m ? (m.mape_pct == null ? 'não validado' : `${m.mape_pct}%`) : '—'}
            detail="Meta do projeto < 15%"
            color="yellow"
            tooltip="Erro em dados reais ainda não medido: a série histórica é simulada. Veja a aba Validação do modelo."
            status="nao_validado"
          />
        </div>
      )}

      {/* Gráfico 1 — Evolução da fila */}
      <div className="card mb-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div>
            <h2 className="text-base font-semibold">Evolução da Fila Cirúrgica</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text2)' }}>
              Linha sólida = histórico simulado · tracejada = projeção
            </p>
          </div>
          {m && m.economia_pacientes_redistrib > 0 && (
            <button
              onClick={() => setMostrarRedistrib(!mostrarRedistrib)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              style={{
                background: mostrarRedistrib ? 'rgba(0,255,136,0.1)' : 'var(--surface)',
                color: mostrarRedistrib ? 'var(--accent2)' : 'var(--text2)',
                border: `1px solid ${mostrarRedistrib ? 'rgba(0,255,136,0.3)' : 'var(--border)'}`,
              }}
            >
              {mostrarRedistrib ? '✓ ' : ''}Cenário simulado c/ redistribuição
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="animate-pulse rounded-lg" style={{ height: 280, background: 'var(--surface)' }} />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={serie} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="mes_fmt"
                tick={{ fill: 'var(--text2)', fontSize: 11 }}
                tickLine={false}
                interval={3}
              />
              <YAxis
                tick={{ fill: 'var(--text2)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => v.toLocaleString('pt-BR')}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text2)', paddingTop: 8 }} />

              {corte > 0 && corte < serie.length && (
                <ReferenceLine
                  x={serie[corte]?.mes_fmt}
                  stroke="rgba(255,255,255,0.2)"
                  strokeDasharray="4 4"
                  label={{ value: 'Hoje', fill: 'var(--text2)', fontSize: 11 }}
                />
              )}

              <Line
                type="monotone"
                dataKey="fila_total"
                name="Fila (sem ação)"
                stroke="var(--accent)"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4 }}
              />

              {mostrarRedistrib && m && m.economia_pacientes_redistrib > 0 && (
                <Line
                  type="monotone"
                  dataKey="fila_redistrib"
                  name="Fila (cenário simulado)"
                  stroke="var(--accent2)"
                  strokeWidth={2}
                  strokeDasharray="5 3"
                  dot={false}
                  connectNulls={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}

        {mostrarRedistrib && m && m.economia_pacientes_redistrib > 0 && (
          <div className="mt-3 px-3 py-2 rounded-lg text-sm flex items-center gap-2" style={{
            background: 'rgba(0,255,136,0.05)',
            border: '1px solid rgba(0,255,136,0.15)',
            color: 'var(--accent2)',
          }}>
            <span>✦</span>
            <span>
              Cenário simulado (aplica a meta de −40% do crescimento, não é resultado): economia de{' '}
              <strong>{m.economia_pacientes_redistrib.toLocaleString('pt-BR')} pacientes</strong>{' '}
              — fila cai de <strong>{m.fila_proj_6m.toLocaleString('pt-BR')}</strong> para{' '}
              <strong>{m.fila_com_redistrib_6m.toLocaleString('pt-BR')}</strong> em 6 meses
            </span>
          </div>
        )}
      </div>

      {/* Gráfico 2 — Entradas vs Saídas */}
      <div className="card mb-5">
        <div className="mb-4">
          <h2 className="text-base font-semibold">Entradas vs Cirurgias Realizadas</h2>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text2)' }}>
            Quando entradas &gt; saídas, a fila cresce · últimos 18 meses + projeção
          </p>
        </div>

        {isLoading ? (
          <div className="animate-pulse rounded-lg" style={{ height: 220, background: 'var(--surface)' }} />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={serie.slice(-18)} margin={{ top: 5, right: 20, left: 0, bottom: 5 }} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="mes_fmt"
                tick={{ fill: 'var(--text2)', fontSize: 11 }}
                tickLine={false}
                interval={2}
              />
              <YAxis
                tick={{ fill: 'var(--text2)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => v.toLocaleString('pt-BR')}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text2)', paddingTop: 8 }} />
              <Bar
                dataKey="entradas_mes"
                name="Entradas"
                fill="var(--yellow)"
                opacity={0.85}
                radius={[3, 3, 0, 0]}
              />
              <Bar
                dataKey="saidas_mes"
                name="Cirurgias realizadas"
                fill="var(--accent2)"
                opacity={0.85}
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Painel todas especialidades */}
      {todas?.por_especialidade?.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Radar por especialidade — projeção de 6 meses</h2>
            <span className="badge badge-blue">{todas.por_especialidade.length} especialidades</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {todas.por_especialidade.map((esp: any) => {
              const urgColor =
                esp.urgencia === 'critica' ? 'var(--red)' :
                esp.urgencia === 'alta' ? 'var(--yellow)' : 'var(--accent2)'
              const tendIcon =
                esp.tendencia === 'crescimento' ? '↗' :
                esp.tendencia === 'reducao' ? '↘' : '→'

              return (
                <button
                  type="button"
                  key={esp.especialidade}
                  className="flex items-center gap-4 p-3 rounded-lg text-left transition-all hover:border-accent"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                  onClick={() => { setEspSelecionada(esp.especialidade); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
                >
                  <div className="text-2xl font-bold w-8 text-center" style={{ color: urgColor }}>
                    {tendIcon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm truncate">{esp.especialidade}</span>
                      <span className="text-xs font-mono ml-2" style={{ color: urgColor, whiteSpace: 'nowrap' }}>
                        {esp.variacao_pct > 0 ? '+' : ''}{esp.variacao_pct}%
                      </span>
                    </div>
                    <div className="flex gap-3 text-xs" style={{ color: 'var(--text2)' }}>
                      <span>Hoje: <strong style={{ color: 'var(--text1)' }}>{esp.fila_atual.toLocaleString('pt-BR')}</strong></span>
                      <span>6m: <strong style={{ color: urgColor }}>{esp.fila_proj_6m.toLocaleString('pt-BR')}</strong></span>
                      <span>Espera: <strong style={{ color: 'var(--text1)' }}>{esp.espera_meses}m</strong></span>
                    </div>
                    <div className="mt-1.5" style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 4, height: 3 }}>
                      <div style={{
                        width: `${Math.min(Math.abs(esp.variacao_pct) * 5, 100)}%`,
                        background: urgColor,
                        borderRadius: 4,
                        height: 3,
                        transition: 'width 0.4s ease',
                      }} />
                    </div>
                  </div>
                  <div className="text-xs text-center shrink-0">
                    <div className="font-mono font-bold" style={{ color: 'var(--yellow)' }}>
                      {esp.mape_pct == null ? 'não validado' : `${esp.mape_pct}%`}
                    </div>
                    <div style={{ color: 'var(--text2)' }}>MAPE</div>
                  </div>
                </button>
              )
            })}
          </div>
          <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
            Selecione uma especialidade para ver o gráfico detalhado acima.
          </p>
        </div>
      )}
    </div>
  )
}