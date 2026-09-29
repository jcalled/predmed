'use client'
import useSWR from 'swr'
import Link from 'next/link'
import { ArrowRight, TrendingUp, TrendingDown, Minus, FlaskConical } from 'lucide-react'
import { zerarFilasApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import Badge from '@/components/ui/Badge'
import SeloDado from '@/components/ui/SeloDado'
import { Carregando, EstadoErro, EstadoVazio } from '@/components/ui/Estados'

/*
 * Aba "Simulação de mutirão" da Redistribuição (ex-/dashboard/zerarfilas).
 * Só SESA/SMS veem a aba (como antes no menu). Tudo aqui é cenário simulado:
 * série histórica estimada, espera média e valor de AIH são parâmetros fixos.
 */

interface PlanoEsp {
  especialidade: string
  urgencia: string
  tendencia: string
  fila_atual: number
  fila_6m_sem_acao: number
  fila_6m_com_redistrib: number
  espera_media_meses: number
  pacientes_redistribuiveis: number
  aih_estimada_redistrib: number
  meses_para_zeramento: number
}

interface SugestaoMutirao {
  origem: { hospital_nome: string }
  destino: { hospital_nome: string }
  especialidade: string
  cir: string
  distancia_km: number | null
  qtd_sugerida: number
  aih_estimada: number
}

const fmt = (n?: number | null) => (n == null ? '—' : n.toLocaleString('pt-BR'))

function IconeTendencia({ t }: { t: string }) {
  if (t === 'crescimento') return <><TrendingUp size={16} aria-hidden="true" /><span className="sr-only">tendência de crescimento</span></>
  if (t === 'reducao') return <><TrendingDown size={16} aria-hidden="true" /><span className="sr-only">tendência de redução</span></>
  return <><Minus size={16} aria-hidden="true" /><span className="sr-only">tendência estável</span></>
}

export default function AbaMutirao() {
  // Só texto de orientação; o botão aprovar (aba Sugestões) usa `pode_aprovar` da API.
  const { isSesa, isSms } = useAuth()
  const { data, error, isLoading, mutate } = useSWR('zerarfilas', zerarFilasApi.get)
  const r = data?.resumo
  const plano: PlanoEsp[] = data?.plano_por_especialidade || []
  const sugestoes: SugestaoMutirao[] = data?.sugestoes_redistribuicao || []

  if (error && !data) return <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />

  return (
    <div>
      <div className="card mb-5 text-xs flex gap-3 items-start" style={{ borderColor: 'rgba(255,215,0,0.5)', color: 'var(--text2)' }} role="note">
        <FlaskConical size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--yellow)' }} />
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <strong style={{ color: 'var(--yellow)' }}>Cenário simulado</strong>
            <SeloDado natureza="simulado" />
          </div>
          Combina a projeção sobre série histórica estimada com as sugestões de redistribuição por CIR.
          Espera média e valor de AIH (R$ 1.500) são parâmetros fixos, não medidos. Serve para planejar um mutirão, não é resultado.
        </div>
      </div>

      {r && (
        <section aria-label="Impacto projetado em 6 meses" className="mb-6 p-4 rounded-xl flex flex-wrap gap-6 items-center"
          style={{ background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.2)' }}>
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Fila projetada sem ação</div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--red)' }}>{fmt(r.fila_total_6m_sem_acao)}</div>
          </div>
          <ArrowRight size={20} aria-hidden="true" style={{ color: 'var(--text2)' }} />
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Com redistribuição</div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--accent2)' }}>{fmt(r.fila_total_6m_com_redistrib)}</div>
          </div>
          <div className="sm:ml-auto sm:text-right">
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Redução em 6 meses</div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--accent2)' }}>
              {r.reducao_total_pct != null ? `−${r.reducao_total_pct}%` : '—'}
            </div>
          </div>
          <SeloDado natureza="simulado" />
        </section>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        <KPICard label="Fila atual" value={fmt(r?.fila_total_atual)} detail="IntegraSUS" color="red" status="medido" carregando={isLoading}
          tooltip="Total de pacientes aguardando cirurgia eletiva no Ceará." />
        <KPICard label="Redistribuíveis" value={fmt(r?.total_pacientes_redistribuiveis)} detail="Dentro da CIR" color="yellow" status="estimado" carregando={isLoading}
          tooltip="Pacientes que poderiam ser realocados para hospitais com capacidade ociosa na mesma CIR." />
        <KPICard label="AIH para receptores" value={r?.total_aih_estimada ? `R$ ${fmt(Math.round(r.total_aih_estimada / 1e6))} mi` : '—'} detail="R$ 1.500 por AIH" color="green" status="simulado" carregando={isLoading}
          tooltip="Valor fixo por cirurgia multiplicado pelas redistribuições sugeridas; não é faturamento observado." />
        <KPICard label="Redução projetada" value={r?.reducao_total_pct ? `−${r.reducao_total_pct}%` : '—'} detail="Em 6 meses" color="blue" status="simulado" carregando={isLoading}
          tooltip="Cenário simulado sobre série histórica estimada; não é resultado medido." />
      </div>

      <section className="card" aria-labelledby="titulo-plano">
        <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
          <h3 id="titulo-plano" className="text-base font-semibold">Plano por especialidade</h3>
          {plano.length > 0 && <Badge tom="azul">{plano.length} especialidades</Badge>}
        </div>

        {isLoading ? (
          <Carregando mensagem="Montando o plano..." variante="linhas" />
        ) : plano.length === 0 ? (
          <EstadoVazio titulo="Sem plano calculado" descricao="Verifique se a fila e as previsões foram carregadas." />
        ) : (
          <ul className="space-y-3">
            {plano.map(p => {
              const cor = p.urgencia === 'critica' ? 'var(--red)' : p.urgencia === 'alta' ? 'var(--yellow)' : 'var(--accent2)'
              const pctBarra = Math.min((p.fila_atual / (r?.fila_total_atual || 1)) * 100, 100)
              return (
                <li key={p.especialidade} className="p-4 rounded-lg" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                  <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span style={{ color: cor }} className="inline-flex"><IconeTendencia t={p.tendencia} /></span>
                      <span className="font-semibold text-sm">{p.especialidade}</span>
                      {p.urgencia === 'critica' && <Badge tom="vermelho">crítica</Badge>}
                      {p.urgencia === 'alta' && <Badge tom="amarelo">alta</Badge>}
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs font-mono" style={{ color: 'var(--text2)' }}>
                      <span>Hoje <strong style={{ color: 'var(--text)' }}>{fmt(p.fila_atual)}</strong></span>
                      <span>6 meses sem ação <strong style={{ color: 'var(--red)' }}>{fmt(p.fila_6m_sem_acao)}</strong></span>
                      <span>6 meses com redistribuição <strong style={{ color: 'var(--accent2)' }}>{fmt(p.fila_6m_com_redistrib)}</strong></span>
                    </div>
                  </div>
                  <div className="mb-2 h-1 rounded" style={{ background: 'rgba(255,255,255,0.05)' }} aria-hidden="true">
                    <div className="h-1 rounded" style={{ width: `${pctBarra}%`, background: cor }} />
                  </div>
                  <div className="flex flex-wrap gap-4 text-xs" style={{ color: 'var(--text2)' }}>
                    <span>Espera média (parâmetro fixo): <strong style={{ color: 'var(--text)' }}>{p.espera_media_meses} meses</strong></span>
                    {p.pacientes_redistribuiveis > 0 && <span>Redistribuíveis: <strong style={{ color: 'var(--accent2)' }}>{fmt(p.pacientes_redistribuiveis)}</strong></span>}
                    {p.aih_estimada_redistrib > 0 && <span>AIH (simulado): <strong style={{ color: 'var(--accent2)' }}>R$ {fmt(p.aih_estimada_redistrib)}</strong></span>}
                    {p.meses_para_zeramento > 0 && <span>Zeramento (simulado): <strong style={{ color: 'var(--text)' }}>{p.meses_para_zeramento} meses</strong></span>}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {sugestoes.length > 0 && (
        <section className="card mt-5" aria-labelledby="titulo-sug-mutirao">
          <h3 id="titulo-sug-mutirao" className="text-base font-semibold mb-4">Redistribuições consideradas no cenário</h3>
          <ul className="space-y-3">
            {sugestoes.map((s, i) => (
              <li key={i} className="flex items-center gap-3 p-3 rounded-lg flex-wrap text-sm" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-semibold">{s.origem.hospital_nome}</span>
                    <ArrowRight size={14} aria-label="para" style={{ color: 'var(--text2)' }} />
                    <span className="font-semibold">{s.destino.hospital_nome}</span>
                  </div>
                  <div className="flex flex-wrap gap-x-3 text-xs" style={{ color: 'var(--text2)' }}>
                    <span>{s.especialidade}</span>
                    <span>{s.cir}</span>
                    <span>{s.distancia_km != null ? `~${s.distancia_km} km` : 'distância não calculada'}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-bold font-mono" style={{ color: 'var(--accent)' }}>{fmt(s.qtd_sugerida)} pacientes</div>
                  <div className="text-xs" style={{ color: 'var(--text2)' }}>AIH (simulado) R$ {fmt(s.aih_estimada)}</div>
                </div>
              </li>
            ))}
          </ul>
          <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
            {isSesa || isSms
              ? <>Para aprovar{isSms ? ' (só transferências dentro da sua CIR)' : ''}, use a aba <Link href="/dashboard/redistribuicao" className="underline" style={{ color: 'var(--accent)' }}>Sugestões</Link>.</>
              : 'A aprovação de redistribuições é feita na aba Sugestões.'}
          </p>
        </section>
      )}
    </div>
  )
}
