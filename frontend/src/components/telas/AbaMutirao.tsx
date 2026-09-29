'use client'
import useSWR from 'swr'
import Link from 'next/link'
import { ArrowRight, FlaskConical } from 'lucide-react'
import { zerarFilasApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import Badge from '@/components/ui/Badge'
import SeloDado from '@/components/ui/SeloDado'
import { Carregando, EstadoErro, EstadoVazio } from '@/components/ui/Estados'

/*
 * Aba "Simulação de mutirão" da Redistribuição (ex-/dashboard/zerarfilas). Só SESA/SMS.
 * Cenário SIMULADO: repete por 3 meses as sugestões mensais da redistribuição v1 (mesma CIR,
 * ociosidade estimada CNES + SIH), limitado ao excedente de cada origem. A fila sem ação é
 * suposta estável (não há série de entradas). Garantias do backend: redistribuíveis ≤ fila,
 * redução entre 0 e 100%.
 */

interface PlanoEsp {
  especialidade: string
  fila_atual: number
  fila_sem_acao: number
  fila_com_redistribuicao: number
  pacientes_redistribuiveis: number
  reducao_pct: number
  aih_estimada_redistrib: number
}

interface SugestaoMutirao {
  origem: { hospital_nome: string }
  destino: { hospital_nome: string }
  especialidade: string
  cir: string
  distancia_km: number | null
  qtd_sugerida: number
  aih_estimada: number
  capacidade_natureza?: 'estimada' | 'declarada'
  vinculo_provisorio?: boolean
}

const fmt = (n?: number | null) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const pct = (n?: number | null) => (n == null ? '—' : `${n.toFixed(1).replace('.', ',')}%`)

export default function AbaMutirao() {
  // Só texto de orientação; o botão aprovar (aba Sugestões) usa `pode_aprovar` da API.
  const { isSesa, isSms } = useAuth()
  const { data, error, isLoading, mutate } = useSWR('zerarfilas', zerarFilasApi.get)
  const r = data?.resumo
  const plano: PlanoEsp[] = data?.plano_por_especialidade || []
  const sugestoes: SugestaoMutirao[] = data?.sugestoes_redistribuicao || []
  const hipoteses: string[] = data?.hipoteses || []
  const dias = r?.horizonte_dias ?? 90

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
          Quanto da fila atual poderia ser operado em outro hospital da mesma CIR em {dias} dias, se as sugestões mensais de
          redistribuição (capacidade ociosa <em>estimada</em> a partir do CNES e do SIH) se repetissem. Não é resultado medido nem vaga confirmada.
          {hipoteses.length > 0 && (
            <ul className="list-disc ml-4 mt-1 space-y-0.5">
              {hipoteses.map(h => <li key={h}>{h}</li>)}
            </ul>
          )}
        </div>
      </div>

      {r && (
        <section aria-label={`Impacto simulado em ${dias} dias`} className="mb-6 p-4 rounded-xl flex flex-wrap gap-6 items-center"
          style={{ background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.2)' }}>
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Fila hoje (sem ação, suposta estável)</div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--red)' }}>{fmt(r.fila_total_sem_acao)}</div>
          </div>
          <ArrowRight size={20} aria-hidden="true" style={{ color: 'var(--text2)' }} />
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Com redistribuição em {dias} dias</div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--accent2)' }}>{fmt(r.fila_total_com_redistribuicao)}</div>
          </div>
          <div className="sm:ml-auto sm:text-right">
            <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>Parcela da fila redistribuída</div>
            <div className="text-2xl font-bold font-mono" style={{ color: 'var(--accent2)' }}>{pct(r.reducao_total_pct)}</div>
          </div>
          <SeloDado natureza="simulado" />
        </section>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        <KPICard label="Fila atual" value={fmt(r?.fila_total_atual)} detail="IntegraSUS" color="red" status="medido" carregando={isLoading}
          tooltip="Total de pacientes aguardando cirurgia eletiva no Ceará." />
        <KPICard label={`Redistribuíveis em ${dias} dias`} value={fmt(r?.total_pacientes_redistribuiveis)} detail={`${fmt(r?.redistribuiveis_por_mes)} por mês · mesma CIR`} color="yellow" status="simulado" carregando={isLoading}
          tooltip="Soma das sugestões mensais repetidas no período, limitada ao excedente de cada hospital de origem. Nunca passa da fila." />
        <KPICard label="Hospitais com ociosidade" value={fmt(r?.hospitais_com_ociosidade)} detail="Estimativa CNES + SIH" color="green" status="estimado" carregando={isLoading}
          tooltip="Estabelecimentos com folga mensal estimada; precisa de confirmação do hospital." />
        <KPICard label="AIH para receptores" value={r?.total_aih_estimada ? `R$ ${(r.total_aih_estimada / 1e6).toFixed(1).replace('.', ',')} mi` : '—'} detail="R$ 1.500 por AIH" color="blue" status="simulado" carregando={isLoading}
          tooltip="Valor fixo por cirurgia multiplicado pelos redistribuíveis; não é faturamento observado." />
      </div>

      <section className="card" aria-labelledby="titulo-plano">
        <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
          <h3 id="titulo-plano" className="text-base font-semibold">Cenário por especialidade ({dias} dias)</h3>
          <div className="flex gap-2 items-center">
            {plano.length > 0 && <Badge tom="azul">{plano.length} especialidades</Badge>}
            <SeloDado natureza="simulado" />
          </div>
        </div>

        {isLoading ? (
          <Carregando mensagem="Montando o cenário..." variante="linhas" />
        ) : plano.length === 0 ? (
          <EstadoVazio titulo="Sem cenário calculado" descricao="Verifique se a fila, o CNES e a produção SIH por estabelecimento foram carregados." />
        ) : (
          <ul className="space-y-3">
            {plano.map(p => {
              const pctBarra = Math.min(Math.max(p.reducao_pct, 0), 100)
              return (
                <li key={p.especialidade} className="p-4 rounded-lg" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                  <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                    <span className="font-semibold text-sm">{p.especialidade}</span>
                    <div className="flex flex-wrap gap-3 text-xs font-mono" style={{ color: 'var(--text2)' }}>
                      <span>Fila <strong style={{ color: 'var(--text)' }}>{fmt(p.fila_atual)}</strong></span>
                      <span>Redistribuíveis <strong style={{ color: 'var(--accent2)' }}>{fmt(p.pacientes_redistribuiveis)}</strong></span>
                      <span>Restante <strong style={{ color: 'var(--text)' }}>{fmt(p.fila_com_redistribuicao)}</strong></span>
                      <span><strong style={{ color: 'var(--accent2)' }}>{pct(p.reducao_pct)}</strong> da fila</span>
                    </div>
                  </div>
                  <div className="h-1 rounded" style={{ background: 'rgba(255,255,255,0.05)' }} aria-hidden="true">
                    <div className="h-1 rounded" style={{ width: `${pctBarra}%`, background: 'var(--accent2)' }} />
                  </div>
                  {p.pacientes_redistribuiveis === 0 && (
                    <p className="text-xs mt-2" style={{ color: 'var(--text2)' }}>
                      Sem destino compatível com ociosidade estimada na mesma CIR (produção na especialidade, habilitação ou capacidade).
                    </p>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {sugestoes.length > 0 && (
        <section className="card mt-5" aria-labelledby="titulo-sug-mutirao">
          <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
            <h3 id="titulo-sug-mutirao" className="text-base font-semibold">Redistribuições mensais consideradas no cenário</h3>
            <SeloDado natureza="estimado" />
          </div>
          <ul className="space-y-3">
            {sugestoes.map((s, i) => (
              <li key={i} className="flex items-center gap-3 p-3 rounded-lg flex-wrap text-sm" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-semibold">{s.origem.hospital_nome}</span>
                    <ArrowRight size={14} aria-label="para" style={{ color: 'var(--text2)' }} />
                    <span className="font-semibold">{s.destino.hospital_nome}</span>
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs items-center" style={{ color: 'var(--text2)' }}>
                    <span>{s.especialidade}</span>
                    <span>{s.cir}</span>
                    <span>{s.capacidade_natureza === 'declarada' ? 'vagas declaradas pelo hospital' : 'capacidade estimada'}</span>
                    {s.vinculo_provisorio && <Badge tom="amarelo">vínculo CNES provisório</Badge>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-bold font-mono" style={{ color: 'var(--accent)' }}>{fmt(s.qtd_sugerida)} pacientes/mês</div>
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
