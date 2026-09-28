'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { previsoesMlApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import dynamic from 'next/dynamic'

// Carrega o gráfico dinamicamente (evita erro de SSR)
const LineChart = dynamic(() => import('@/components/ui/LineChart'), { ssr: false })

export default function PrevisoesMLPage() {
  const { isSesa } = useAuth()
  const [especialidade, setEspecialidade] = useState<string>('')
  const [horizonte, setHorizonte] = useState<number>(6)

  // Previsão Holt-Winters (série histórica simulada — não validada)
  const { data, isLoading } = useSWR(
    ['previsoes-ml', especialidade, horizonte],
    () => previsoesMlApi.previsao(especialidade || undefined, horizonte)
  )

  // Busca resumo de todas especialidades
  const { data: resumo } = useSWR(
    'previsoes-ml-todas',
    () => previsoesMlApi.todas()
  )

  // Lista de especialidades para o select
  const especialidades = resumo?.por_especialidade?.map((e: any) => e.especialidade) || []

  return (
    <div className="animate-fadein">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text1">Previsões ML — Holt-Winters</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Suavização exponencial com sazonalidade anual sobre série histórica <strong>simulada</strong>.
          Previsão não validada — meta do projeto: MAPE {'<'} 15% em dados reais.
        </p>
      </div>

      {/* KPIs do modelo */}
      {data?.metricas && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            label="MAPE (erro)"
            value={data.metricas.mape_pct == null ? 'não validado' : `${data.metricas.mape_pct}%`}
            detail="Meta do projeto: < 15%"
            color="yellow"
            tooltip="Erro percentual médio em dados reais ainda não medido: a série histórica usada é simulada."
          />
          <KPICard
            label="Tendência"
            value={data.metricas.tendencia}
            detail={`${data.metricas.variacao_tendencia_pct}%`}
            color="blue"
            tooltip="Direção da fila nos próximos meses"
          />
          <KPICard
            label="Fila Atual"
            value={data.metricas.fila_atual?.toLocaleString('pt-BR')}
            detail="hoje"
            color="yellow"
          />
          <KPICard
            label="Fila em 6 meses"
            value={data.metricas.fila_projetada?.toLocaleString('pt-BR')}
            detail="projeção"
            color={data.metricas.fila_projetada > data.metricas.fila_atual ? 'red' : 'green'}
          />
        </div>
      )}

      {/* Alertas do modelo */}
      {data?.alertas?.length > 0 && (
        <div className="mb-6 space-y-2">
          {data.alertas.map((alerta: any, i: number) => (
            <div
              key={i}
              className="p-3 rounded-lg text-sm"
              style={{
                background: alerta.nivel === 'critico' ? 'rgba(255,68,68,0.1)' :
                           alerta.nivel === 'alerta' ? 'rgba(255,215,0,0.1)' :
                           'rgba(0,255,157,0.1)',
                border: `1px solid ${
                  alerta.nivel === 'critico' ? 'var(--red)' :
                  alerta.nivel === 'alerta' ? 'var(--yellow)' :
                  'var(--accent2)'
                }`,
                color: alerta.nivel === 'critico' ? 'var(--red)' :
                       alerta.nivel === 'alerta' ? 'var(--yellow)' :
                       'var(--accent2)'
              }}
            >
              {alerta.msg}
            </div>
          ))}
        </div>
      )}

      {/* Controles */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select
          value={especialidade}
          onChange={(e) => setEspecialidade(e.target.value)}
          className="px-3 py-2 rounded-lg text-sm"
          style={{
            background: 'var(--surface2)',
            border: '1px solid var(--border)',
            color: 'var(--text1)',
            minWidth: '200px'
          }}
        >
          <option value="">Todas especialidades (TOTAL)</option>
          {especialidades.map((esp: string) => (
            <option key={esp} value={esp}>{esp}</option>
          ))}
        </select>

        <select
          value={horizonte}
          onChange={(e) => setHorizonte(Number(e.target.value))}
          className="px-3 py-2 rounded-lg text-sm"
          style={{
            background: 'var(--surface2)',
            border: '1px solid var(--border)',
            color: 'var(--text1)'
          }}
        >
          <option value={3}>3 meses</option>
          <option value={6}>6 meses</option>
          <option value={12}>12 meses</option>
        </select>

        <span className="text-xs" style={{ color: 'var(--text2)' }}>
          Holt-Winters com sazonalidade anual · faixa ±10% ilustrativa
        </span>
      </div>

      {/* Gráfico */}
      {isLoading ? (
        <div className="card h-96 animate-pulse" />
      ) : (
        data?.serie_completa && (
          <div className="card">
            <LineChart
              data={data.serie_completa}
              xKey="mes"
              yKey="fila_total"
              color="var(--accent)"
              title={`Previsão - ${data.especialidade}`}
              tooltip="Fila de pacientes"
            />
            
            {/* Legenda do gráfico */}
            <div className="flex gap-4 mt-3 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: 'var(--accent)' }} />
                <span style={{ color: 'var(--text2)' }}>Histórico (simulado)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: 'var(--accent2)' }} />
                <span style={{ color: 'var(--text2)' }}>Projeção Holt-Winters</span>
              </div>
            </div>
          </div>
        )
      )}

      {/* Resumo por especialidade */}
      {resumo?.por_especialidade && (
        <div className="card mt-6">
          <h2 className="text-base font-semibold mb-4">Resumo por Especialidade</h2>
          <div className="space-y-3">
            {resumo.por_especialidade.map((esp: any) => (
              <div
                key={esp.especialidade}
                className="p-3 rounded-lg flex items-center justify-between"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <div>
                  <span className="font-semibold text-sm">{esp.especialidade}</span>
                  <div className="flex gap-3 mt-1 text-xs" style={{ color: 'var(--text2)' }}>
                    <span>MAPE: {esp.mape_pct == null ? 'não validado' : `${esp.mape_pct}%`}</span>
                    <span>•</span>
                    <span>Fila atual: {esp.fila_atual.toLocaleString('pt-BR')}</span>
                    <span>•</span>
                    <span>Proj. 6m: {esp.fila_proj_6m.toLocaleString('pt-BR')}</span>
                  </div>
                </div>
                <div>
                  <span
                    className="text-xs px-2 py-1 rounded-full"
                    style={{
                      background: esp.urgencia === 'critica' ? 'rgba(255,68,68,0.1)' :
                                  esp.urgencia === 'alta' ? 'rgba(255,215,0,0.1)' :
                                  'rgba(0,255,157,0.1)',
                      color: esp.urgencia === 'critica' ? 'var(--red)' :
                             esp.urgencia === 'alta' ? 'var(--yellow)' :
                             'var(--accent2)'
                    }}
                  >
                    {esp.urgencia}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}