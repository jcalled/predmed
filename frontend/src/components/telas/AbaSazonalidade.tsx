'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { analyticsApi } from '@/lib/api'
import SeloDado from '@/components/ui/SeloDado'
import Badge from '@/components/ui/Badge'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

/*
 * Aba "Sazonalidade" da Previsão de demanda (vinda do antigo Analytics SIH).
 * Mortalidade e valor pago SUS saíram do produto (docs/ux/arquitetura-telas.md):
 * esta aba usa só contagem de internações do SIH/DATASUS.
 */

interface IndiceSazonal {
  mes: number
  nome_mes: string
  indice: number
  media_internacoes: number
  classificacao: 'alta' | 'baixa' | 'normal'
}

interface SazonalidadeData {
  por_especialidade: Record<string, {
    indices_mensais: IndiceSazonal[]
    meses_criticos: string[]
    meses_ociosos: string[]
    recomendacao: string
  }>
  especialidades_disponiveis: string[]
}

interface PontoVolume {
  mes: string
  total_internacoes: number
  evento: 'pico' | 'colapso' | 'normal'
}

const CLASSE = {
  alta:   { cor: 'var(--red)',     rotulo: 'Alta demanda' },
  baixa:  { cor: 'var(--accent2)', rotulo: 'Baixa demanda' },
  normal: { cor: 'var(--accent)',  rotulo: 'Normal' },
} as const

const EVENTO = {
  pico:    { cor: 'var(--red)',    rotulo: 'Pico (> 20% acima da média do período)' },
  colapso: { cor: 'var(--yellow)', rotulo: 'Queda (> 20% abaixo da média do período)' },
  normal:  { cor: 'var(--accent)', rotulo: 'Normal' },
} as const

const fmt = (n: number) => new Intl.NumberFormat('pt-BR').format(Math.round(n))
const dec = (n: number) => n.toFixed(2).replace('.', ',')

export default function AbaSazonalidade() {
  const { data: saz, error, isLoading, mutate } = useSWR<SazonalidadeData>('analytics-sazonalidade', analyticsApi.sazonalidade)
  const { data: pressao } = useSWR('analytics-pressao-historica', analyticsApi.pressaoHistorica)
  const [escolhida, setEscolhida] = useState('')

  if (error && !saz) return <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />
  if (isLoading || !saz) return <Carregando mensagem="Carregando sazonalidade do SIH..." variante="linhas" linhas={4} />

  const lista = saz.especialidades_disponiveis || []
  if (lista.length === 0) {
    return <EstadoVazio titulo="Sem série do SIH" descricao="A base histórica do SIH não foi carregada neste ambiente." />
  }
  const espSel = escolhida && lista.includes(escolhida) ? escolhida : lista[0]
  const espData = saz.por_especialidade?.[espSel]
  const serie: PontoVolume[] = pressao?.serie_temporal || []
  const maxVol = serie.length ? Math.max(...serie.map(p => p.total_internacoes)) : 1

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-2 text-sm" style={{ color: 'var(--text2)' }}>
        <span>
          Índice sazonal = média de internações do mês ÷ média anual, calculado sobre o SIH/DATASUS Ceará.
          Ajuda a planejar mutirões e janelas para eletivas.
        </span>
        <SeloDado natureza="medido" />
      </div>

      <div className="flex flex-col gap-1 w-full sm:w-72 mb-4">
        <label htmlFor="saz-esp" className="text-xs" style={{ color: 'var(--text2)' }}>Especialidade</label>
        <select id="saz-esp" className="input-dark text-sm" value={espSel} onChange={e => setEscolhida(e.target.value)}>
          {lista.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
      </div>

      {espData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <section className="card lg:col-span-2" aria-labelledby="titulo-indice">
            <h3 id="titulo-indice" className="text-base font-semibold mb-4">Índice sazonal mensal — {espSel}</h3>
            <div className="flex items-end gap-1 sm:gap-2 h-44" aria-hidden="true">
              {espData.indices_mensais.map(m => (
                <div key={m.mes} className="flex-1 flex flex-col items-center gap-1 min-w-0">
                  <span className="text-2xs font-mono" style={{ color: 'var(--text2)' }}>{dec(m.indice)}</span>
                  <div className="w-full rounded-t-sm" style={{ height: Math.round(m.indice * 80), background: (CLASSE[m.classificacao] ?? CLASSE.normal).cor, opacity: 0.85 }} />
                  <span className="text-2xs" style={{ color: 'var(--text2)' }}>{m.nome_mes}</span>
                </div>
              ))}
            </div>
            <ul className="flex flex-wrap gap-4 mt-3 text-xs" aria-hidden="true">
              {(Object.keys(CLASSE) as (keyof typeof CLASSE)[]).map(k => (
                <li key={k} className="flex items-center gap-1.5" style={{ color: 'var(--text2)' }}>
                  <span className="w-3 h-3 rounded-sm inline-block" style={{ background: CLASSE[k].cor }} />{CLASSE[k].rotulo}
                </li>
              ))}
            </ul>
            <details className="mt-3">
              <summary className="text-xs cursor-pointer" style={{ color: 'var(--accent)' }}>Ver dados em tabela</summary>
              <TabelaRolavel rotulo="Índice sazonal por mês">
                <table className="table-predmed mt-2" style={{ minWidth: 0 }}>
                  <caption className="sr-only">Índice sazonal e média de internações por mês — {espSel}</caption>
                  <thead>
                    <tr><th scope="col">Mês</th><th scope="col" className="text-right">Índice</th><th scope="col" className="text-right">Média de internações</th><th scope="col">Classificação</th></tr>
                  </thead>
                  <tbody>
                    {espData.indices_mensais.map(m => (
                      <tr key={m.mes}>
                        <td>{m.nome_mes}</td>
                        <td className="text-right font-mono">{dec(m.indice)}</td>
                        <td className="text-right font-mono">{fmt(m.media_internacoes)}</td>
                        <td>{(CLASSE[m.classificacao] ?? CLASSE.normal).rotulo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TabelaRolavel>
            </details>
          </section>

          <div className="space-y-3">
            <section className="card" aria-labelledby="titulo-criticos">
              <h3 id="titulo-criticos" className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--red)', letterSpacing: '0.5px' }}>Meses de maior demanda</h3>
              <div className="flex flex-wrap gap-1">
                {espData.meses_criticos.length ? espData.meses_criticos.map(m => <Badge key={m} tom="vermelho">{m}</Badge>)
                  : <span className="text-xs" style={{ color: 'var(--text2)' }}>Nenhum</span>}
              </div>
            </section>
            <section className="card" aria-labelledby="titulo-janelas">
              <h3 id="titulo-janelas" className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--accent2)', letterSpacing: '0.5px' }}>Janelas para eletivas</h3>
              <div className="flex flex-wrap gap-1">
                {espData.meses_ociosos.length ? espData.meses_ociosos.map(m => <Badge key={m} tom="verde">{m}</Badge>)
                  : <span className="text-xs" style={{ color: 'var(--text2)' }}>Nenhuma</span>}
              </div>
            </section>
            <section className="card" aria-labelledby="titulo-recom">
              <h3 id="titulo-recom" className="text-xs font-semibold uppercase mb-2 flex items-center gap-2" style={{ color: 'var(--text2)', letterSpacing: '0.5px' }}>
                Sugestão <SeloDado natureza="nao_validado" />
              </h3>
              <p className="text-sm">{espData.recomendacao}</p>
            </section>
          </div>
        </div>
      )}

      {serie.length > 0 && (
        <section className="card" aria-labelledby="titulo-volume">
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <h3 id="titulo-volume" className="text-base font-semibold">Volume mensal de internações (todas as especialidades)</h3>
            <SeloDado natureza="medido" />
          </div>
          <div className="tabela-rolavel" aria-hidden="true">
            <div className="flex items-end gap-1 h-44 min-w-[720px]">
              {serie.map((p, i) => (
                <div key={p.mes} className="flex-1 flex flex-col items-center justify-end h-full" title={`${p.mes}: ${fmt(p.total_internacoes)} internações`}>
                  <div className="w-full rounded-t-sm" style={{ height: Math.round((p.total_internacoes / maxVol) * 150), background: (EVENTO[p.evento] ?? EVENTO.normal).cor, opacity: 0.8 }} />
                  <span className="text-2xs mt-1 h-3 whitespace-nowrap" style={{ color: 'var(--text2)' }}>{i % 6 === 0 ? p.mes : ''}</span>
                </div>
              ))}
            </div>
          </div>
          <ul className="flex flex-wrap gap-4 mt-3 text-xs" aria-hidden="true">
            {(Object.keys(EVENTO) as (keyof typeof EVENTO)[]).map(k => (
              <li key={k} className="flex items-center gap-1.5" style={{ color: 'var(--text2)' }}>
                <span className="w-3 h-3 rounded-sm inline-block" style={{ background: EVENTO[k].cor }} />{EVENTO[k].rotulo}
              </li>
            ))}
          </ul>
          <details className="mt-3">
            <summary className="text-xs cursor-pointer" style={{ color: 'var(--accent)' }}>Ver dados em tabela</summary>
            <TabelaRolavel rotulo="Internações por mês">
              <table className="table-predmed mt-2" style={{ minWidth: 0 }}>
                <caption className="sr-only">Total de internações por mês no SIH/DATASUS Ceará</caption>
                <thead><tr><th scope="col">Mês</th><th scope="col" className="text-right">Internações</th><th scope="col">Situação</th></tr></thead>
                <tbody>
                  {serie.map(p => (
                    <tr key={p.mes}><td className="font-mono">{p.mes}</td><td className="text-right font-mono">{fmt(p.total_internacoes)}</td><td>{(EVENTO[p.evento] ?? EVENTO.normal).rotulo}</td></tr>
                  ))}
                </tbody>
              </table>
            </TabelaRolavel>
          </details>
        </section>
      )}
    </div>
  )
}
