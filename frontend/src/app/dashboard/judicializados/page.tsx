'use client'
import useSWR from 'swr'
import { judicializadosApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'

export default function JudicializadosPage() {
  const { data, isLoading } = useSWR('judicializados', judicializadosApi.get)

  return (
    <div className="animate-fadein">
      <div className="mb-4 px-4 py-3 rounded-lg flex gap-3 items-center" style={{ background: 'rgba(255,68,68,0.06)', border: '1px solid rgba(255,68,68,0.2)' }}>
        <span className="text-xl">⚖️</span>
        <div>
          <div className="text-sm font-semibold" style={{ color: 'var(--red)' }}>Atenção: Casos Judicializados</div>
          <div className="text-xs" style={{ color: 'var(--text2)' }}>Pacientes com determinação judicial têm prioridade automática máxima no algoritmo. Atrasos podem resultar em sanções ao Estado.</div>
        </div>
      </div>

      <div className="mb-6">
        <h1 className="text-2xl font-bold">Casos Judicializados</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>Pacientes com ordem judicial — prioridade máxima automática no PREDMED</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <KPICard label="Total Judicializados" value={data?.total ?? 0} detail="Ordens judiciais ativas" color="red" />
        <KPICard label="Prazo Médio" value="48h" detail="Para cumprimento da ordem" color="yellow" />
        <KPICard label="Risco de Sanção" value={data?.total ?? 0} detail="Casos sem data de cirurgia" color="red" />
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">📋 Listagem de Casos Judicializados</h2>
          <span className="badge badge-red">{data?.total ?? 0} casos</span>
        </div>
        {isLoading ? (
          <div className="text-center py-8" style={{ color: 'var(--text2)' }}>Carregando...</div>
        ) : (
          <table className="table-predmed">
            <thead>
              <tr>
                <th>#</th>
                <th>Paciente</th>
                <th>Hospital</th>
                <th>Especialidade</th>
                <th>SWALIS</th>
                <th>Município</th>
                <th>Procedimento</th>
              </tr>
            </thead>
            <tbody>
              {(data?.pacientes || []).map((p: {
                id: number
                iniciais: string
                hospital_nome: string
                especialidade: string
                classif_swalis: string
                municipio: string
                procedimento: string
              }, i: number) => (
                <tr key={p.id}>
                  <td className="font-mono text-xs" style={{ color: 'var(--red)', fontWeight: 700 }}>#{i + 1}</td>
                  <td className="font-mono text-sm">{p.iniciais || '—'}</td>
                  <td className="text-xs" style={{ maxWidth: 180 }}>
                    <div className="truncate" title={p.hospital_nome}>{p.hospital_nome}</div>
                  </td>
                  <td className="text-xs">{p.especialidade}</td>
                  <td><span className="badge badge-red" style={{ fontSize: 10 }}>{p.classif_swalis?.replace('Categoria ', '') || '—'}</span></td>
                  <td className="text-xs" style={{ color: 'var(--text2)' }}>{p.municipio}</td>
                  <td className="text-xs" style={{ color: 'var(--text2)', maxWidth: 150 }}>
                    <div className="truncate" title={p.procedimento || ''}>{p.procedimento || '—'}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
