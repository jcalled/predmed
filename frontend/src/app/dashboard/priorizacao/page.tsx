'use client'
import { Fragment, useState } from 'react'
import useSWR from 'swr'
import { priorizacaoApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'

const SWALIS_CONFIG: Record<string, { badge: string; icon: string; color: string }> = {
  'Categoria A1':  { badge: 'badge-red',    icon: '🔴', color: 'var(--red)'    },
  'Categoria A2':  { badge: 'badge-red',    icon: '🟠', color: 'var(--accent3)'},
  'Categoria B':   { badge: 'badge-yellow', icon: '🟡', color: 'var(--yellow)' },
  'Categoria C':   { badge: 'badge-blue',   icon: '🔵', color: 'var(--accent)' },
  'Categoria D':   { badge: 'badge-gray',   icon: '⚪', color: 'var(--text2)'  },
  'Não Informada': { badge: 'badge-gray',   icon: '❔', color: 'var(--text2)'  },
}

type Componente = { criterio: string; pontos: number; detalhe: string }
type Paciente = {
  id: number
  iniciais: string | null
  hospital_nome: string
  municipio: string
  especialidade: string
  classif_swalis: string
  judicializado: boolean
  procedimento: string | null
  dias_espera: number | null
  data_confiavel: boolean | null
  score: number
  componentes: Componente[]
  alertas: string[]
}

export default function PriorizacaoPage() {
  const [esp, setEsp] = useState('')
  const [onco, setOnco] = useState(false)
  const [aberto, setAberto] = useState<number | null>(null)
  const { data, isLoading } = useSWR(
    ['priorizacao', esp, onco],
    () => priorizacaoApi.get({ limit: 50, especialidade: esp || undefined, apenas_oncologia: onco || undefined }),
  )

  const dist: Record<string, number> = data?.distribuicao_swalis || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  const lista: Paciente[] = data?.top_prioritarios || []

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-2xl font-bold">Priorização Clínica</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Score explicável: SWALIS + tempo de espera + mandado judicial + oncologia + cardiovascular grave.
          Clique em um paciente para ver de onde vem cada ponto.
        </p>
      </div>

      <div className="card mb-6 text-xs" style={{ borderColor: 'var(--yellow)', color: 'var(--text2)' }}>
        <strong style={{ color: 'var(--yellow)' }}>Regras {data?.versao_regras || 'v0.1'}.</strong>{' '}
        Ferramenta de apoio à decisão: não substitui a regulação nem o julgamento clínico.
        Os pesos serão revisados com equipe clínica antes do uso no piloto.
      </div>

      {/* Resumo */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard label="Avaliados" value={data?.total_avaliados ?? 0} detail="Pacientes com score calculado" color="blue" />
        <KPICard label="Score ≥ 70" value={data?.resumo?.score_70_ou_mais ?? 0} detail="Maior prioridade combinada" color="red" />
        <KPICard label="Oncologia > 60 dias" value={data?.resumo?.oncologia_acima_60_dias ?? 0} detail="Referência Lei 12.732/2012" color="yellow" />
        <KPICard label="Datas a confirmar" value={data?.resumo?.datas_a_confirmar ?? 0} detail="Numeração antiga da regulação" color="blue" />
      </div>

      {/* Distribuição SWALIS */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {Object.keys(SWALIS_CONFIG).map(cat => {
          const n = dist[cat] || 0
          const pct = total > 0 ? ((n / total) * 100).toFixed(1) : '0'
          const cfg = SWALIS_CONFIG[cat]
          return (
            <div key={cat} className="kpi-card text-center">
              <div className="text-xl mb-1">{cfg.icon}</div>
              <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text2)' }}>{cat}</div>
              <div className="text-xl font-bold font-mono" style={{ color: cfg.color }}>{n.toLocaleString('pt-BR')}</div>
              <div className="text-xs mt-1" style={{ color: 'var(--text2)' }}>{pct}%</div>
            </div>
          )
        })}
      </div>

      {/* Filtros */}
      <div className="flex gap-3 flex-wrap mb-4 items-center">
        <input
          className="input-dark text-sm"
          style={{ width: 220 }}
          placeholder="Filtrar especialidade..."
          value={esp}
          onChange={e => setEsp(e.target.value)}
          aria-label="Filtrar por especialidade"
        />
        <label className="text-sm flex items-center gap-2" style={{ color: 'var(--text2)' }}>
          <input type="checkbox" checked={onco} onChange={e => setOnco(e.target.checked)} />
          Somente oncologia
        </label>
      </div>

      {/* Lista priorizada */}
      <div className="card overflow-x-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">Top 50 por score</h2>
          <span className="text-xs" style={{ color: 'var(--text2)' }}>Empate: quem espera há mais tempo vem primeiro</span>
        </div>
        {isLoading ? (
          <div className="text-center py-8" style={{ color: 'var(--text2)' }}>Calculando prioridades...</div>
        ) : (
          <table className="table-predmed">
            <thead>
              <tr>
                <th>#</th>
                <th>Paciente</th>
                <th>Hospital</th>
                <th>Especialidade</th>
                <th>SWALIS</th>
                <th className="text-right">Espera</th>
                <th>Alertas</th>
                <th className="text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {lista.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center text-sm text-slate-500 py-6">
                    Nenhum paciente da sua instituição nesta lista. Dados de outras instituições aparecem apenas de forma agregada.
                  </td>
                </tr>
              )}
              {lista.map((p, i) => {
                const cfg = SWALIS_CONFIG[p.classif_swalis] || SWALIS_CONFIG['Não Informada']
                const expandido = aberto === p.id
                return (
                  <Fragment key={p.id}>
                    <tr
                      onClick={() => setAberto(expandido ? null : p.id)}
                      style={{ cursor: 'pointer' }}
                      aria-expanded={expandido}
                    >
                      <td className="font-mono text-xs" style={{ color: 'var(--text2)' }}>{i + 1}</td>
                      <td className="font-mono text-sm">{p.iniciais || '—'}</td>
                      <td className="text-xs" style={{ maxWidth: 200 }}>
                        <div className="truncate" title={p.hospital_nome}>{p.hospital_nome}</div>
                        {p.procedimento && (
                          <div className="truncate" style={{ color: 'var(--text2)', fontSize: 10 }} title={p.procedimento}>{p.procedimento}</div>
                        )}
                      </td>
                      <td className="text-xs">{p.especialidade}</td>
                      <td>
                        <span className={`badge ${cfg.badge}`} style={{ fontSize: 10 }}>
                          {cfg.icon} {p.classif_swalis?.replace('Categoria ', '') || '—'}
                        </span>
                      </td>
                      <td className="text-right text-xs font-mono">
                        {p.dias_espera != null ? `${p.dias_espera.toLocaleString('pt-BR')} d` : '—'}
                      </td>
                      <td className="text-xs">
                        {p.judicializado && <span className="badge badge-red mr-1" style={{ fontSize: 9 }}>⚖️ judicial</span>}
                        {p.alertas.length > 0 && (
                          <span className="badge badge-yellow" style={{ fontSize: 9 }} title={p.alertas.join('\n')}>
                            ⚠️ {p.alertas.length}
                          </span>
                        )}
                      </td>
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="h-1.5 w-16 rounded-full" style={{ background: 'var(--border)' }}>
                            <div className="h-full rounded-full" style={{ width: `${p.score}%`, background: p.score >= 70 ? 'var(--red)' : p.score >= 50 ? 'var(--yellow)' : 'var(--accent)' }} />
                          </div>
                          <span className="font-mono text-sm font-bold">{p.score}</span>
                        </div>
                      </td>
                    </tr>
                    {expandido && (
                      <tr>
                        <td colSpan={8} style={{ background: 'var(--bg2, rgba(255,255,255,0.03))' }}>
                          <div className="grid md:grid-cols-2 gap-4 py-2 text-xs">
                            <div>
                              <div className="font-semibold mb-2">Por que este score?</div>
                              <table className="w-full">
                                <tbody>
                                  {p.componentes.map(c => (
                                    <tr key={c.criterio}>
                                      <td className="py-0.5">{c.criterio}</td>
                                      <td className="py-0.5" style={{ color: 'var(--text2)' }}>{c.detalhe}</td>
                                      <td className="py-0.5 text-right font-mono">+{c.pontos}</td>
                                    </tr>
                                  ))}
                                  <tr>
                                    <td className="pt-1 font-semibold" colSpan={2}>Total</td>
                                    <td className="pt-1 text-right font-mono font-semibold">{p.score}</td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                            <div>
                              <div className="font-semibold mb-2">Alertas para revisão</div>
                              {p.alertas.length === 0
                                ? <div style={{ color: 'var(--text2)' }}>Nenhum.</div>
                                : <ul className="list-disc pl-4">{p.alertas.map(a => <li key={a}>{a}</li>)}</ul>}
                              <div className="mt-2" style={{ color: 'var(--text2)' }}>Município: {p.municipio}</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
