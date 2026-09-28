'use client'
import useSWR from 'swr'
import { priorizacaoApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'

const SWALIS_CONFIG: Record<string, { badge: string; icon: string; color: string }> = {
  'Categoria A1': { badge: 'badge-red',    icon: '🔴', color: 'var(--red)'    },
  'Categoria A2': { badge: 'badge-red',    icon: '🟠', color: 'var(--accent3)'},
  'Categoria B':  { badge: 'badge-yellow', icon: '🟡', color: 'var(--yellow)' },
  'Categoria C':  { badge: 'badge-blue',   icon: '🔵', color: 'var(--accent)' },
  'Categoria D':  { badge: 'badge-gray',   icon: '⚪', color: 'var(--text2)'  },
}

export default function PriorizacaoPage() {
  const { data, isLoading } = useSWR('priorizacao', priorizacaoApi.get)

  const dist: Record<string, number> = data?.distribuicao_swalis || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0)

  return (
    <div className="animate-fadein">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Priorização Clínica</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Classificação SWALIS — ordenação automática por IA para máxima equidade e urgência clínica
        </p>
      </div>

      {/* Distribuição SWALIS */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {['Categoria A1', 'Categoria A2', 'Categoria B', 'Categoria C', 'Categoria D'].map(cat => {
          const n = dist[cat] || 0
          const pct = total > 0 ? ((n / total) * 100).toFixed(1) : '0'
          const cfg = SWALIS_CONFIG[cat]
          return (
            <div key={cat} className="kpi-card text-center">
              <div className="text-2xl mb-1">{cfg.icon}</div>
              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text2)' }}>{cat}</div>
              <div className="text-2xl font-bold font-mono" style={{ color: cfg.color }}>{n.toLocaleString('pt-BR')}</div>
              <div className="text-xs mt-1" style={{ color: 'var(--text2)' }}>{pct}%</div>
            </div>
          )
        })}
      </div>

      {/* Top Prioritários */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">🎯 Top 20 Mais Prioritários — Score IA</h2>
          <span className="badge badge-red">Ordenados por urgência</span>
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
                <th>Judicial</th>
                <th className="text-right">Score IA</th>
              </tr>
            </thead>
            <tbody>
              {(data?.top_prioritarios || []).length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center text-sm text-slate-500 py-6">
                    Nenhum paciente da sua instituição nesta lista. Dados de outras instituições aparecem apenas de forma agregada.
                  </td>
                </tr>
              )}
              {(data?.top_prioritarios || []).map((p: {
                id: number
                iniciais: string | null
                hospital_nome: string
                especialidade: string
                classif_swalis: string
                judicializado: boolean
                score_ia: number
              }, i: number) => {
                const cfg = SWALIS_CONFIG[p.classif_swalis] || SWALIS_CONFIG['Categoria D']
                return (
                  <tr key={p.id}>
                    <td className="font-mono font-bold text-sm" style={{ color: i < 3 ? 'var(--yellow)' : 'var(--text2)' }}>
                      {i < 3 ? ['🥇', '🥈', '🥉'][i] : `#${i + 1}`}
                    </td>
                    <td className="font-mono text-sm">{p.iniciais || '—'}</td>
                    <td className="text-xs" style={{ maxWidth: 180 }}>
                      <div className="truncate" title={p.hospital_nome}>{p.hospital_nome}</div>
                    </td>
                    <td className="text-xs">{p.especialidade}</td>
                    <td>
                      <span className={`badge ${cfg.badge}`} style={{ fontSize: 10 }}>
                        {cfg.icon} {p.classif_swalis?.replace('Categoria ', '') || '—'}
                      </span>
                    </td>
                    <td>
                      {p.judicializado ? <span className="badge badge-red" style={{ fontSize: 10 }}>⚖️</span> : <span style={{ color: 'var(--text2)' }}>—</span>}
                    </td>
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="h-1.5 w-20 rounded-full" style={{ background: 'var(--border)' }}>
                          <div className="h-full rounded-full" style={{ width: `${p.score_ia}%`, background: p.score_ia >= 80 ? 'var(--red)' : p.score_ia >= 60 ? 'var(--yellow)' : 'var(--accent)' }} />
                        </div>
                        <span className="font-mono text-sm font-bold" style={{ color: cfg.color }}>{p.score_ia}</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
