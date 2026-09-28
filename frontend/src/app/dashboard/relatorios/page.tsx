'use client'
import useSWR from 'swr'
import { relatoriosApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function RelatoriosPage() {
  const { isSesa } = useAuth()
  const { data, isLoading } = useSWR('relatorios-resumo', relatoriosApi.resumo)

  return (
    <div className="animate-fadein max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Relatórios</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          {isSesa ? 'Resumo operacional do Ceará' : 'Relatório do seu hospital'}
        </p>
      </div>

      {isLoading ? (
        <div className="text-text2">Gerando relatório...</div>
      ) : (
        <>
          <div className="card mb-4">
            <h2 className="text-base font-semibold mb-4">📊 Resumo Operacional</h2>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Total na fila', data?.kpis?.total_fila?.toLocaleString('pt-BR')],
                ['Categoria A1', data?.kpis?.a1_urgentes?.toLocaleString('pt-BR')],
                ['Judicializados', data?.kpis?.judicializados?.toLocaleString('pt-BR')],
                ['Hospitais monitorados', data?.kpis?.hospitais_monitorados],
                ['Sobrecarregados', data?.kpis?.hospitais_sobrecarregados],
                ['Acurácia IA (MAPE)', `${data?.kpis?.acuracia_mape}%`],
              ].map(([label, val]) => (
                <div key={String(label)} className="flex justify-between py-2 border-b" style={{ borderColor: 'var(--border)' }}>
                  <span style={{ color: 'var(--text2)' }}>{label}</span>
                  <span className="font-mono font-medium" style={{ color: 'var(--accent)' }}>{val ?? '—'}</span>
                </div>
              ))}
            </div>
          </div>

          {data?.hospitais_criticos?.length > 0 && (
            <div className="card mb-4">
              <h2 className="text-base font-semibold mb-4">🔴 Hospitais Críticos</h2>
              <table className="table-predmed">
                <thead>
                  <tr>
                    <th>Hospital</th>
                    <th className="text-center">Fila</th>
                    <th className="text-center">Pressão</th>
                    <th>CIR</th>
                  </tr>
                </thead>
                <tbody>
                  {data.hospitais_criticos.map((h: {
                    hospital_nome: string
                    fila_atual: number
                    pressao: number
                    cir: string
                  }) => (
                    <tr key={h.hospital_nome}>
                      <td className="text-xs">{h.hospital_nome}</td>
                      <td className="text-center font-mono" style={{ color: 'var(--red)' }}>{h.fila_atual.toLocaleString('pt-BR')}</td>
                      <td className="text-center font-mono font-bold" style={{ color: 'var(--red)' }}>{h.pressao}×</td>
                      <td className="text-xs" style={{ color: 'var(--text2)' }}>{h.cir}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="card">
            <h2 className="text-base font-semibold mb-3">📥 Exportar</h2>
            <div className="flex gap-3">
              <button className="btn-primary text-sm" onClick={() => alert('Em produção: exporta PDF executivo')}>📄 Exportar PDF</button>
              <button className="btn-primary text-sm" onClick={() => alert('Em produção: exporta CSV para SISREG')}>📊 Exportar CSV</button>
            </div>
            <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
              Gerado em: {data?.gerado_em ? new Date(data.gerado_em).toLocaleString('pt-BR') : '—'}
            </p>
          </div>
        </>
      )}
    </div>
  )
}
