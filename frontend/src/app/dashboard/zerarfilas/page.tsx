'use client'
import useSWR from 'swr'
import { zerarFilasApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'

export default function ZerarFilasPage() {
  const { isSesa } = useAuth()
  const { data, isLoading } = useSWR('zerarfilas', zerarFilasApi.get)

  const r = data?.resumo

  return (
    <div className="animate-fadein">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text1">Programa Zerar Filas</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Plano <strong>simulado</strong> por especialidade — combina previsão sobre série histórica simulada + redistribuição por CIR.
          Espera média e valor de AIH são parâmetros fixos, não medidos.
        </p>
      </div>

      {/* Banner impacto */}
      {r && (
        <div className="mb-6 p-4 rounded-xl flex flex-wrap gap-6 items-center" style={{
          background: 'linear-gradient(135deg, rgba(0,194,255,0.08) 0%, rgba(0,255,136,0.05) 100%)',
          border: '1px solid rgba(0,194,255,0.2)',
        }}>
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Fila projetada sem ação</div>
            <div className="text-2xl font-bold" style={{ color: 'var(--red)' }}>
              {r.fila_total_6m_sem_acao?.toLocaleString('pt-BR')}
            </div>
          </div>
          <div className="text-2xl" style={{ color: 'var(--text2)' }}>→</div>
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Com redistribuição</div>
            <div className="text-2xl font-bold" style={{ color: 'var(--accent2)' }}>
              {r.fila_total_6m_com_redistrib?.toLocaleString('pt-BR')}
            </div>
          </div>
          <div className="ml-auto text-right">
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Redução em 6 meses</div>
            <div className="text-2xl font-bold" style={{ color: 'var(--accent2)' }}>
              -{r.reducao_total_pct}%
            </div>
          </div>
        </div>
      )}

      {/* KPIs */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => <div key={i} className="kpi-card animate-pulse" style={{ height: 90 }} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            label="Fila Atual Total"
            value={r?.fila_total_atual?.toLocaleString('pt-BR') ?? '—'}
            detail="IntegraSUS"
            color="red"
            tooltip="Total de pacientes aguardando cirurgia eletiva no Ceará."
          />
          <KPICard
            label="Redistribuíveis"
            value={r?.total_pacientes_redistribuiveis?.toLocaleString('pt-BR') ?? '—'}
            detail="Dentro do CIR"
            color="yellow"
            tooltip="Pacientes que podem ser realocados para hospitais com capacidade ociosa na mesma CIR."
          />
          <KPICard
            label="AIH Estimada (simulado)"
            value={r?.total_aih_estimada ? `R$ ${(r.total_aih_estimada / 1000).toFixed(0)}k` : '—'}
            detail="Receita redistribuição"
            color="green"
            tooltip="Valor estimado de AIH (R$1.500/cirurgia) que os hospitais receptores podem faturar com as redistribuições aprovadas."
          />
          <KPICard
            label="Redução Projetada (simulado)"
            value={r?.reducao_total_pct ? `-${r.reducao_total_pct}%` : '—'}
            detail="Em 6 meses"
            color="blue"
            tooltip="Cenário simulado sobre série histórica estimada; não é resultado medido."
          />
        </div>
      )}

      {/* Plano por especialidade */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">Plano por Especialidade</h2>
          {!isLoading && data?.plano_por_especialidade && (
            <span className="badge badge-blue">{data.plano_por_especialidade.length} especialidades</span>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="animate-pulse rounded-lg" style={{ height: 72, background: 'var(--surface)' }} />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {data?.plano_por_especialidade?.map((p: any) => {
              const urgColor =
                p.urgencia === 'critica' ? 'var(--red)' :
                p.urgencia === 'alta' ? 'var(--yellow)' : 'var(--accent2)'

              const tendIcon =
                p.tendencia === 'crescimento' ? '↗' :
                p.tendencia === 'reducao' ? '↘' : '→'

              const pctBarra = Math.min(
                ((p.fila_atual / (data?.resumo?.fila_total_atual || 1)) * 100), 100
              )

              return (
                <div key={p.especialidade} className="p-4 rounded-lg" style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                }}>
                  {/* Linha 1: nome + badges */}
                  <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold" style={{ color: urgColor }}>{tendIcon}</span>
                      <span className="font-semibold text-sm">{p.especialidade}</span>
                      {p.urgencia === 'critica' && (
                        <span className="badge badge-red text-xs">CRÍTICA</span>
                      )}
                    </div>
                    <div className="flex gap-3 text-xs font-mono">
                      <span style={{ color: 'var(--text2)' }}>
                        Hoje <strong style={{ color: 'var(--text1)' }}>{p.fila_atual.toLocaleString('pt-BR')}</strong>
                      </span>
                      <span style={{ color: 'var(--text2)' }}>
                        6m s/ ação <strong style={{ color: 'var(--red)' }}>{p.fila_6m_sem_acao.toLocaleString('pt-BR')}</strong>
                      </span>
                      <span style={{ color: 'var(--text2)' }}>
                        6m c/ redistrib <strong style={{ color: 'var(--accent2)' }}>{p.fila_6m_com_redistrib.toLocaleString('pt-BR')}</strong>
                      </span>
                    </div>
                  </div>

                  {/* Barra de proporção */}
                  <div className="mb-2" style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 4, height: 4 }}>
                    <div style={{ width: `${pctBarra}%`, background: urgColor, borderRadius: 4, height: 4, transition: 'width 0.4s ease' }} />
                  </div>

                  {/* Linha 2: métricas detalhadas */}
                  <div className="flex flex-wrap gap-4 text-xs" style={{ color: 'var(--text2)' }}>
                    <span>
                      Espera média (parâmetro fixo): <strong style={{ color: 'var(--text1)' }}>{p.espera_media_meses}m</strong>
                    </span>
                    {p.pacientes_redistribuiveis > 0 && (
                      <span>
                        Redistribuíveis: <strong style={{ color: 'var(--accent2)' }}>{p.pacientes_redistribuiveis}</strong>
                      </span>
                    )}
                    {p.aih_estimada_redistrib > 0 && (
                      <span>
                        AIH (simulado): <strong style={{ color: 'var(--accent2)' }}>R$ {p.aih_estimada_redistrib.toLocaleString('pt-BR')}</strong>
                      </span>
                    )}
                    {p.meses_para_zeramento > 0 && (
                      <span>
                        Zeramento estimado: <strong style={{ color: 'var(--text1)' }}>{p.meses_para_zeramento}m</strong>
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Sugestões de redistribuição */}
      {data?.sugestoes_redistribuicao?.length > 0 && (
        <div className="card mt-5">
          <h2 className="text-base font-semibold mb-4">Redistribuições Sugeridas pelo Modelo</h2>
          <div className="space-y-3">
            {data.sugestoes_redistribuicao.map((s: any, i: number) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg flex-wrap" style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                fontSize: 13,
              }}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-semibold truncate">{s.origem.hospital_nome}</span>
                    <span style={{ color: 'var(--text2)' }}>→</span>
                    <span className="font-semibold truncate">{s.destino.hospital_nome}</span>
                  </div>
                  <div className="flex gap-3 text-xs" style={{ color: 'var(--text2)' }}>
                    <span>{s.especialidade}</span>
                    <span>•</span>
                    <span>{s.cir}</span>
                    <span>•</span>
                    <span>{s.distancia_km != null ? `~${s.distancia_km}km` : 'distância n/d'}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-bold" style={{ color: 'var(--accent)' }}>{s.qtd_sugerida} pac.</div>
                  <div className="text-xs" style={{ color: 'var(--accent2)' }}>
                    AIH (simulado) R$ {s.aih_estimada.toLocaleString('pt-BR')}
                  </div>
                </div>
                {isSesa && (
                  <div className="shrink-0">
                    <span className="badge badge-blue">Ver redistribuição →</span>
                  </div>
                )}
              </div>
            ))}
          </div>
          {isSesa && (
            <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
              Para aprovar as redistribuições, acesse o módulo <strong>Redistribuição</strong>.
            </p>
          )}
        </div>
      )}
    </div>
  )
}