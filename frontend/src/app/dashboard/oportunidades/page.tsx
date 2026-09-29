'use client'
import { useEffect, useState } from 'react'
import { Minus, Plus, Trash2, Play, FlaskConical } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { analyticsApi, configApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'
import SeloDado from '@/components/ui/SeloDado'
import Badge from '@/components/ui/Badge'
import { EstadoErro, EstadoVazio } from '@/components/ui/Estados'

/*
 * Oportunidades SUS — docs/ux/arquitetura-telas.md, item 6. SÓ hospital particular.
 * Conteúdo do antigo Simulador de receita. Receita = vagas × ticket médio de AIH
 * do SIH; é projeção (simulado), não faturamento garantido.
 */

interface SimEspecialidade {
  especialidade: string
  vagas_mes: number
  ticket_medio_real: number
  receita_mes: number
  receita_ano: number
  fonte: string
  intervalo_confianca: { baixo: number; alto: number }
  por_complexidade: Record<string, { total_aih: number; ticket_medio: number }>
}

interface SimulacaoResult {
  simulacao_por_especialidade: SimEspecialidade[]
  resumo: {
    total_vagas_mes: number
    receita_total_mes: number
    receita_total_ano: number
    ticket_medio_geral: number
    receita_conservadora_mes: number
    receita_otimista_mes: number
  }
  anos_base: number[]
  nota: string
}

const ESPECIALIDADES_DISPONIVEIS = [
  'ORTOPEDIA', 'CARDIOVASCULAR', 'ONCOLOGIA', 'NEUROLOGIA',
  'UROLOGIA', 'GINECOLOGIA', 'OFTALMOLOGIA', 'CIR DIGESTIVA',
  'BUCOMAXILOFACIAL', 'CIR PLASTICA REPARADORA',
  'OTORRINOLARINGOLOGIA', 'ENDOCRINOLOGIA',
]

const fmtR = (n: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n)

export default function OportunidadesSusPage() {
  const { isParticular } = useAuth()
  const [vagas, setVagas] = useState<Record<string, number>>({ ORTOPEDIA: 10, CARDIOVASCULAR: 5 })
  const [origemVagas, setOrigemVagas] = useState<'exemplo' | 'configuracao'>('exemplo')
  const [resultado, setResultado] = useState<SimulacaoResult | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<unknown>(null)
  const disponiveis = ESPECIALIDADES_DISPONIVEIS.filter(e => vagas[e] == null)
  const [novaEsp, setNovaEsp] = useState('')

  // Parte das vagas SUS já configuradas pelo hospital (Configurações → Vagas SUS)
  useEffect(() => {
    if (!isParticular) return
    configApi.getVagas().then(data => {
      const v: Record<string, number> = {}
      for (const cfg of (data?.vagas || []) as { especialidade: string; vagas_mes: number }[]) {
        if (cfg.vagas_mes > 0) v[cfg.especialidade] = cfg.vagas_mes
      }
      if (Object.keys(v).length) { setVagas(v); setOrigemVagas('configuracao') }
    }).catch(() => { /* mantém o exemplo */ })
  }, [isParticular])

  if (!isParticular) {
    return (
      <div className="animate-fadein">
        <h1 className="text-xl sm:text-2xl font-bold mb-4">Oportunidades SUS</h1>
        <div className="card">
          <EstadoErro
            erro={{ response: { status: 403 } }}
            descricao="Esta tela é do hospital particular conveniado (oferta de vagas SUS). Seu perfil acompanha a rede pelas telas de Redistribuição e Relatórios."
          />
        </div>
      </div>
    )
  }

  const simular = async () => {
    setCarregando(true)
    setErro(null)
    try {
      setResultado(await analyticsApi.simuladorReceita(vagas))
    } catch (e) {
      setErro(e)
    } finally {
      setCarregando(false)
    }
  }

  const alterar = (esp: string, qtd: number) => setVagas(v => ({ ...v, [esp]: Math.max(0, Math.min(500, qtd)) }))
  const remover = (esp: string) => {
    setVagas(v => { const n = { ...v }; delete n[esp]; return n })
    setResultado(null)
  }
  const adicionar = () => {
    const esp = novaEsp || disponiveis[0]
    if (esp && vagas[esp] == null) setVagas(v => ({ ...v, [esp]: 5 }))
    setNovaEsp('')
  }
  const totalVagas = Object.values(vagas).reduce((a, b) => a + b, 0)
  const temBaseSih = (resultado?.anos_base?.length ?? 0) > 0
  const fonteTicket = temBaseSih ? `Ticket: SIH ${resultado!.anos_base.join(', ')}` : 'Ticket: parâmetro fixo'

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">Oportunidades SUS</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Quanto o seu hospital poderia receber ao oferecer vagas cirúrgicas ao SUS, com base no valor médio das AIH pagas no Ceará (SIH/DATASUS).
        </p>
      </div>

      <div className="card mb-6 text-xs flex gap-3 items-start" style={{ borderColor: 'rgba(255,215,0,0.5)', color: 'var(--text2)' }} role="note">
        <FlaskConical size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--yellow)' }} />
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <strong style={{ color: 'var(--yellow)' }}>Valores simulados</strong>
            <SeloDado natureza="simulado" />
          </div>
          Receita = vagas × ticket médio histórico de AIH. Não considera glosas, teto financeiro, contratualização nem a demanda que será de fato encaminhada.
          Não é faturamento garantido.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="card" aria-labelledby="titulo-vagas">
          <h2 id="titulo-vagas" className="text-base font-semibold mb-1">Vagas SUS por mês</h2>
          <p className="text-xs mb-4" style={{ color: 'var(--text2)' }}>
            {origemVagas === 'configuracao'
              ? 'Carregadas das suas Configurações → Vagas SUS. Alterar aqui não salva: é só simulação.'
              : 'Valores de exemplo. Para ofertar vagas de fato, use Configurações → Vagas SUS.'}
          </p>

          {Object.keys(vagas).length === 0 ? (
            <EstadoVazio titulo="Nenhuma especialidade na simulação" descricao="Adicione uma especialidade abaixo." />
          ) : (
            <ul className="space-y-2">
              {Object.entries(vagas).map(([esp, qtd]) => {
                const id = `vagas-${esp.replace(/\s+/g, '-')}`
                return (
                  <li key={esp} className="flex items-center gap-2">
                    <label htmlFor={id} className="flex-1 text-sm truncate">{esp}</label>
                    <button type="button" className="btn-primary !px-2 !py-1.5" onClick={() => alterar(esp, qtd - 1)} aria-label={`Diminuir vagas de ${esp}`}>
                      <Minus size={14} aria-hidden="true" />
                    </button>
                    <input
                      id={id}
                      type="number"
                      inputMode="numeric"
                      min={0}
                      max={500}
                      value={qtd}
                      onChange={e => alterar(esp, parseInt(e.target.value) || 0)}
                      className="input-dark text-center font-mono !w-20 !py-1.5"
                    />
                    <button type="button" className="btn-primary !px-2 !py-1.5" onClick={() => alterar(esp, qtd + 1)} aria-label={`Aumentar vagas de ${esp}`}>
                      <Plus size={14} aria-hidden="true" />
                    </button>
                    <button type="button" className="btn-red !px-2 !py-1.5" onClick={() => remover(esp)} aria-label={`Remover ${esp} da simulação`}>
                      <Trash2 size={14} aria-hidden="true" />
                    </button>
                  </li>
                )
              })}
            </ul>
          )}

          {disponiveis.length > 0 && (
            <div className="mt-4 flex gap-2 items-end">
              <div className="flex-1 flex flex-col gap-1">
                <label htmlFor="nova-esp" className="text-xs" style={{ color: 'var(--text2)' }}>Adicionar especialidade</label>
                <select id="nova-esp" className="input-dark text-sm" value={novaEsp || disponiveis[0]} onChange={e => setNovaEsp(e.target.value)}>
                  {disponiveis.map(e => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
              <button type="button" className="btn-primary text-sm h-[42px]" onClick={adicionar}>Adicionar</button>
            </div>
          )}

          <div className="mt-4 pt-4 border-t flex justify-between items-center" style={{ borderColor: 'var(--border)' }}>
            <span className="text-xs" style={{ color: 'var(--text2)' }}>Total de vagas por mês</span>
            <span className="text-lg font-bold font-mono">{totalVagas.toLocaleString('pt-BR')}</span>
          </div>

          <button
            type="button"
            onClick={simular}
            disabled={carregando || totalVagas === 0}
            className="btn-green w-full mt-4 py-3 inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play size={16} aria-hidden="true" /> {carregando ? 'Calculando...' : 'Simular receita'}
          </button>
        </section>

        <section aria-labelledby="titulo-resultado" aria-live="polite">
          <h2 id="titulo-resultado" className="sr-only">Resultado da simulação</h2>
          {erro ? (
            <div className="card"><EstadoErro erro={erro} aoTentarNovamente={simular} /></div>
          ) : !resultado ? (
            <div className="card">
              <EstadoVazio titulo="Nenhuma simulação ainda" descricao="Ajuste as vagas e clique em “Simular receita”." />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <KPICard label="Receita mensal" value={fmtR(resultado.resumo.receita_total_mes)}
                  detail={`Faixa ±15%: ${fmtR(resultado.resumo.receita_conservadora_mes)} a ${fmtR(resultado.resumo.receita_otimista_mes)}`}
                  color="green" status="simulado" fonte={fonteTicket} />
                <KPICard label="Receita anual" value={fmtR(resultado.resumo.receita_total_ano)}
                  detail={`Ticket médio: ${fmtR(resultado.resumo.ticket_medio_geral)}`}
                  status="simulado" fonte={fonteTicket} />
              </div>

              <div className="card">
                <h3 className="text-base font-semibold mb-3">Por especialidade</h3>
                <ul className="divide-y" style={{ borderColor: 'var(--border)' }}>
                  {resultado.simulacao_por_especialidade.map(s => (
                    <li key={s.especialidade} className="py-3 first:pt-0">
                      <div className="flex items-start justify-between gap-3 mb-1">
                        <div className="min-w-0">
                          <div className="text-sm font-semibold">{s.especialidade}</div>
                          <div className="text-xs" style={{ color: 'var(--text2)' }}>
                            {s.vagas_mes} vagas × {fmtR(s.ticket_medio_real)} (ticket médio)
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-sm font-bold font-mono" style={{ color: 'var(--accent2)' }}>{fmtR(s.receita_mes)}/mês</div>
                          <div className="text-2xs" style={{ color: 'var(--text2)' }}>{fmtR(s.receita_ano)}/ano</div>
                        </div>
                      </div>
                      <div className="text-2xs" style={{ color: 'var(--text2)' }}>
                        Faixa ilustrativa ±15%: {fmtR(s.intervalo_confianca.baixo)} a {fmtR(s.intervalo_confianca.alto)}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {s.fonte === 'SIH real'
                          ? <Badge tom="verde">ticket do SIH</Badge>
                          : <Badge tom="amarelo">ticket estimado (sem dado no SIH)</Badge>}
                        {Object.entries(s.por_complexidade).map(([cx, d]) => (
                          <Badge key={cx} tom="cinza">{cx}: {fmtR(d.ticket_medio)}</Badge>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
                <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
                  {temBaseSih
                    ? `${resultado.nota}.`
                    : 'A base do SIH não está carregada neste ambiente: o ticket usado é um parâmetro fixo, não o valor médio observado.'}
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
