'use client'
import useSWR from 'swr'
import { hospitaisApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import { useState } from 'react'

const STATUS_MAP: Record<string, { label: string; color: string; badge: string }> = {
  critico: { label: '🔴 Crítico',  color: 'var(--red)',    badge: 'badge-red' },
  alerta:  { label: '🟠 Alerta',   color: 'var(--accent3)', badge: 'badge-red' },
  normal:  { label: '🟡 Normal',   color: 'var(--yellow)',  badge: 'badge-yellow' },
  ocioso:  { label: '🟢 Ocioso',   color: 'var(--accent2)', badge: 'badge-green' },
}

interface Hospital {
  hospital_nome: string
  municipio: string
  cir: string
  tipo: string
  fila_atual: number
  media_mensal: number
  pressao: number
  pressao_status: string
}

export default function HospitaisPage() {
  const { isParticular, isPublico } = useAuth()
  const { data, isLoading } = useSWR('hospitais', hospitaisApi.get)
  const [filtroStatus, setFiltroStatus] = useState('')

  const hospitais: Hospital[] = (data?.hospitais || []).filter((h: Hospital) =>
    !filtroStatus || h.pressao_status === filtroStatus
  )

  const criticos = (data?.hospitais || []).filter((h: Hospital) => h.pressao_status === 'critico').length
  const ociosos  = (data?.hospitais || []).filter((h: Hospital) => h.pressao_status === 'ocioso').length

  return (
    <div className="animate-fadein">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Hospitais</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          {isParticular ? 'Hospitais públicos da sua CIR com demanda reprimida' :
           isPublico ? 'Hospitais da sua região de saúde (CIR)' :
           'Todos os hospitais monitorados — dados DATASUS × IntegraSUS'}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard label="Total" value={data?.total ?? 0} detail="Monitorados" color="blue" />
        <KPICard label="Alta Pressão" value={criticos} detail="Índice > 2×" color="red" />
        <KPICard label="Capacidade Ociosa" value={ociosos} detail="Índice < 0.8×" color="green" />
        <KPICard label="Filtrados" value={hospitais.length} detail="Exibindo" color="default" />
      </div>

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap mb-4">
        {['', 'critico', 'alerta', 'normal', 'ocioso'].map(s => (
          <button
            key={s}
            onClick={() => setFiltroStatus(s)}
            className="text-xs px-3 py-1.5 rounded-full transition-all"
            style={{
              background: filtroStatus === s ? 'rgba(0,194,255,0.15)' : 'var(--surface2)',
              border: filtroStatus === s ? '1px solid rgba(0,194,255,0.35)' : '1px solid var(--border)',
              color: filtroStatus === s ? 'var(--accent)' : 'var(--text2)',
            }}
          >
            {s === '' ? 'Todos' : STATUS_MAP[s]?.label || s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="kpi-card animate-pulse" style={{ height: 140 }} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {hospitais.map((h: Hospital) => {
            const st = STATUS_MAP[h.pressao_status] || STATUS_MAP.normal
            const pct = Math.min((h.pressao / 5) * 100, 100)
            return (
              <div key={h.hospital_nome} className="card transition-all hover:border-accent/25" style={{ borderColor: h.pressao >= 2 ? 'rgba(255,68,68,0.2)' : h.pressao < 0.8 ? 'rgba(0,255,157,0.15)' : 'var(--border)' }}>
                <div className="flex justify-between items-start mb-2">
                  <div className="font-semibold text-sm leading-tight pr-2" style={{ maxWidth: '75%' }}>{h.hospital_nome}</div>
                  <span className={`badge ${st.badge} flex-shrink-0 text-xs`} style={{ fontSize: 10 }}>{st.label}</span>
                </div>
                <div className="text-xs mb-3" style={{ color: 'var(--text2)' }}>
                  📍 {h.municipio} · {h.cir}
                  {h.tipo === 'particular' && <span className="ml-2" style={{ color: 'var(--yellow)' }}>· particular</span>}
                </div>

                <div className="grid grid-cols-3 gap-2 text-center mb-3">
                  <div className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                    <div className="font-mono font-bold text-sm" style={{ color: h.pressao >= 2 ? 'var(--red)' : 'var(--text1)' }}>{h.fila_atual.toLocaleString('pt-BR')}</div>
                    <div className="text-xs" style={{ color: 'var(--text2)', fontSize: 10 }}>fila</div>
                  </div>
                  <div className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                    <div className="font-mono font-bold text-sm" style={{ color: 'var(--text1)' }}>{Math.round(h.media_mensal).toLocaleString('pt-BR')}</div>
                    <div className="text-xs" style={{ color: 'var(--text2)', fontSize: 10 }}>cap/mês</div>
                  </div>
                  <div className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                    <div className="font-mono font-bold text-sm" style={{ color: st.color }}>{h.pressao === 99 ? '—' : `${h.pressao}×`}</div>
                    <div className="text-xs" style={{ color: 'var(--text2)', fontSize: 10 }}>pressão</div>
                  </div>
                </div>

                <div className="pressure-bar-bg">
                  <div className="pressure-bar" style={{ width: `${pct}%`, background: h.pressao >= 3 ? 'var(--red)' : h.pressao >= 1.5 ? 'var(--accent3)' : h.pressao >= 0.5 ? 'var(--accent)' : 'var(--accent2)' }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
