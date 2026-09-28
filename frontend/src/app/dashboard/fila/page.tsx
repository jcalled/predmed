'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { filaApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'

const SWALIS_COLORS: Record<string, string> = {
  'Categoria A1': 'var(--red)',
  'Categoria A2': 'var(--accent3)',
  'Categoria B':  'var(--yellow)',
  'Categoria C':  'var(--accent)',
  'Categoria D':  'var(--text2)',
}

const SWALIS_BADGE: Record<string, string> = {
  'Categoria A1': 'badge-red',
  'Categoria A2': 'badge-red',
  'Categoria B':  'badge-yellow',
  'Categoria C':  'badge-blue',
  'Categoria D':  'badge-gray',
}

export default function FilaPage() {
  const [page, setPage] = useState(1)
  const [esp, setEsp] = useState('')
  const [swalis, setSwalis] = useState('')
  const [judicial, setJudicial] = useState('')

  const { data, isLoading } = useSWR(
    ['fila', page, esp, swalis, judicial],
    () => filaApi.get({
      page,
      limit: 50,
      especialidade: esp || undefined,
      swalis: swalis || undefined,
      judicializado: judicial === 'sim' ? true : judicial === 'nao' ? false : undefined,
    })
  )

  const stats = data?.stats
  const pacientes = data?.pacientes || []

  return (
    <div className="animate-fadein">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Fila Cirúrgica</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>Última importação — IntegraSUS SESA/CE</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard label="Total na Fila" value={stats?.total ?? 0} detail="Pacientes aguardando" color="red" />
        <KPICard label="Categoria A1" value={stats?.a1 ?? 0} detail="Risco imediato" color="yellow" />
        <KPICard label="Judicializados" value={stats?.judicializados ?? 0} detail="Ordens judiciais" color="red" />
        <KPICard label="Página" value={`${page} / ${Math.ceil((data?.total || 0) / 50)}`} detail={`${data?.total?.toLocaleString('pt-BR') || '—'} total`} color="blue" />
      </div>

      {/* Filtros */}
      <div className="flex gap-3 flex-wrap mb-4">
        <input
          className="input-dark text-sm"
          style={{ width: 200 }}
          placeholder="Especialidade..."
          value={esp}
          onChange={e => { setEsp(e.target.value); setPage(1) }}
        />
        <select
          className="input-dark text-sm"
          style={{ width: 180 }}
          value={swalis}
          onChange={e => { setSwalis(e.target.value); setPage(1) }}
        >
          <option value="">Todas as categorias</option>
          {['Categoria A1', 'Categoria A2', 'Categoria B', 'Categoria C', 'Categoria D'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="input-dark text-sm"
          style={{ width: 160 }}
          value={judicial}
          onChange={e => { setJudicial(e.target.value); setPage(1) }}
        >
          <option value="">Todos</option>
          <option value="sim">Judicializados</option>
          <option value="nao">Não judicializados</option>
        </select>
        {(esp || swalis || judicial) && (
          <button className="btn-primary text-xs" onClick={() => { setEsp(''); setSwalis(''); setJudicial(''); setPage(1) }}>
            ✕ Limpar filtros
          </button>
        )}
      </div>

      {/* Tabela */}
      <div className="card overflow-x-auto">
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
                <th>Judicial</th>
              </tr>
            </thead>
            <tbody>
              {pacientes.map((p: {
                id: number
                iniciais: string
                hospital_nome: string
                especialidade: string
                classif_swalis: string
                municipio: string
                judicializado: boolean
                procedimento: string
              }, i: number) => (
                <tr key={p.id}>
                  <td className="font-mono text-xs" style={{ color: 'var(--text2)' }}>{(page - 1) * 50 + i + 1}</td>
                  <td className="font-mono text-xs font-medium">{p.iniciais || '—'}</td>
                  <td className="text-xs" style={{ maxWidth: 200 }}>
                    <div className="truncate" title={p.hospital_nome}>{p.hospital_nome}</div>
                    {p.procedimento && (
                      <div className="text-xs truncate" style={{ color: 'var(--text2)', fontSize: 10 }} title={p.procedimento}>{p.procedimento}</div>
                    )}
                  </td>
                  <td className="text-xs">{p.especialidade}</td>
                  <td>
                    <span className={`badge ${SWALIS_BADGE[p.classif_swalis] || 'badge-gray'}`} style={{ fontSize: 10 }}>
                      {p.classif_swalis?.replace('Categoria ', '') || '—'}
                    </span>
                  </td>
                  <td className="text-xs" style={{ color: 'var(--text2)' }}>{p.municipio}</td>
                  <td>
                    {p.judicializado
                      ? <span className="badge badge-red" style={{ fontSize: 10 }}>⚖️ Sim</span>
                      : <span className="text-xs" style={{ color: 'var(--text2)' }}>—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginação */}
      <div className="flex justify-between items-center mt-4">
        <span className="text-xs" style={{ color: 'var(--text2)' }}>
          Exibindo {((page - 1) * 50) + 1}–{Math.min(page * 50, data?.total || 0)} de {data?.total?.toLocaleString('pt-BR') || '—'}
        </span>
        <div className="flex gap-2">
          <button className="btn-primary text-xs" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Anterior</button>
          <button className="btn-primary text-xs" disabled={page * 50 >= (data?.total || 0)} onClick={() => setPage(p => p + 1)}>Próxima →</button>
        </div>
      </div>
    </div>
  )
}
