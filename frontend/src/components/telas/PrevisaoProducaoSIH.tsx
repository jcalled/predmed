'use client'
import { useState } from 'react'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import { Info } from 'lucide-react'
import { previsaoProducaoApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'
import SeloDado from '@/components/ui/SeloDado'
import Badge from '@/components/ui/Badge'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

/*
 * Aba "Previsão" da Previsão de demanda.
 * Alvo: PRODUÇÃO cirúrgica SUS registrada no SIH (AIH principais do grupo SIGTAP 04), NÃO a fila.
 * Modelo: o escolhido por série na avaliação fora da amostra versionada (avaliacao_id), treinado
 * com toda a série e projetado 30/60/90 dias; intervalo de 80% empírico (erros do teste).
 * Método: docs/dados/previsao-demanda-v1.md; script _SCRIPTS/prever_producao_cirurgica.py.
 */

const GraficoPrevisao = dynamic(() => import('./GraficoPrevisaoProducao'), { ssr: false })

type Carater = 'TODOS' | 'ELETIVO'

interface Ponto {
  horizonte: 'h1' | 'h2' | 'h3'
  horizonte_dias: number
  competencia: string
  previsto: number
  intervalo_80_inferior: number | null
  intervalo_80_superior: number | null
  mape_teste_pct: number | null
}

interface PrevisaoResp {
  status: 'ok' | 'sem_serie' | 'indisponivel'
  mensagem?: string
  previsao_id?: string
  avaliacao_id?: string
  alvo_resumo?: string
  ultima_competencia_observada?: string
  competencias_provisorias?: string[]
  intervalo_metodo?: string
  meta_mape_pct?: number
  especialidades_disponiveis?: string[]
  modelo?: string
  modelo_descricao?: string
  baixo_volume?: boolean
  mape_trimestre_pct?: number | null
  previsao?: Ponto[]
  historico?: { competencia: string; aihs: number }[]
}

const fmt = (n?: number | null) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const pct = (n?: number | null) => (n == null ? '—' : `${n.toFixed(1).replace('.', ',')}%`)
const META = 15

function mesAno(c?: string) {
  if (!c) return '—'
  const [a, m] = c.split('-')
  const nomes = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
  return `${nomes[parseInt(m, 10) - 1]}/${a}`
}

export default function PrevisaoProducaoSIH() {
  const [especialidade, setEspecialidade] = useState('TOTAL')
  const [carater, setCarater] = useState<Carater>('TODOS')

  const { data, error, isLoading, mutate } = useSWR<PrevisaoResp>(
    ['previsao-producao', especialidade, carater],
    () => previsaoProducaoApi.get(especialidade, carater),
    { keepPreviousData: true },
  )
  const esps = data?.especialidades_disponiveis || []
  const pontos = data?.previsao || []

  return (
    <div>
      <div className="card mb-5 text-xs flex gap-3 items-start" style={{ color: 'var(--text2)' }} role="note">
        <Info size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
        <div>
          <strong style={{ color: 'var(--text)' }}>O que é previsto: cirurgias SUS realizadas no Ceará (produção registrada no SIH/DATASUS), não o tamanho da fila.</strong>{' '}
          Cada especialidade usa o modelo escolhido na avaliação fora da amostra; o erro (MAPE) mostrado é o medido no teste
          {data?.avaliacao_id ? <> (<span className="font-mono">{data.avaliacao_id}</span>)</> : null}.
          Os horizontes contam a partir da última competência consolidada ({mesAno(data?.ultima_competencia_observada)}).
          <span className="inline-flex gap-1 ml-1 align-middle"><SeloDado natureza="estimado" /></span>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <label htmlFor="prev-esp" className="text-xs" style={{ color: 'var(--text2)' }}>Especialidade</label>
        <select
          id="prev-esp"
          value={especialidade}
          onChange={e => setEspecialidade(e.target.value)}
          className="px-3 py-2 rounded-lg text-sm"
          style={{ background: 'var(--surface2)', border: '1px solid var(--border-strong)', color: 'var(--text)', minWidth: 220 }}
        >
          <option value="TOTAL">Total (sem obstetrícia)</option>
          {esps.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <div className="inline-flex rounded-lg p-1 gap-1" role="group" aria-label="Caráter da internação"
          style={{ background: 'var(--surface2)', border: '1px solid var(--border-strong)' }}>
          {(['TODOS', 'ELETIVO'] as Carater[]).map(c => (
            <button key={c} type="button" aria-pressed={carater === c} onClick={() => setCarater(c)}
              className="px-3 py-1.5 rounded-md text-xs"
              style={carater === c ? { background: 'rgba(0,194,255,0.15)', color: 'var(--accent)', fontWeight: 600 } : { color: 'var(--text2)' }}>
              {c === 'TODOS' ? 'Todas as internações' : 'Só eletivas'}
            </button>
          ))}
        </div>
      </div>

      {error && !data ? (
        <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />
      ) : isLoading && !data ? (
        <Carregando mensagem="Carregando previsão..." />
      ) : !data || data.status === 'indisponivel' ? (
        <EstadoVazio titulo="Previsão não gerada" descricao={data?.mensagem || 'Rode _SCRIPTS/prever_producao_cirurgica.py.'} />
      ) : data.status !== 'ok' ? (
        <EstadoVazio titulo="Sem série para esta especialidade" descricao="A especialidade não tem série avaliada neste caráter." />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6">
            {pontos.map(p => (
              <KPICard
                key={p.horizonte}
                label={`${p.horizonte_dias} dias · ${mesAno(p.competencia)}`}
                value={fmt(p.previsto)}
                detail={`80%: ${fmt(p.intervalo_80_inferior)}–${fmt(p.intervalo_80_superior)} · MAPE teste ${pct(p.mape_teste_pct)}`}
                color={p.mape_teste_pct != null && p.mape_teste_pct < META ? 'green' : 'yellow'}
                status="estimado"
                tooltip={`Cirurgias SUS previstas na competência ${mesAno(p.competencia)} (SIH). Erro percentual médio medido fora da amostra para este horizonte: ${pct(p.mape_teste_pct)} (meta do projeto < ${META}%).`}
              />
            ))}
          </div>

          <section className="card mb-6" aria-labelledby="titulo-graf-prev">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h3 id="titulo-graf-prev" className="text-base font-semibold">
                Produção cirúrgica SUS — {especialidade === 'TOTAL' ? 'total sem obstetrícia' : especialidade}
                {carater === 'ELETIVO' ? ' (eletivas)' : ''}
              </h3>
              <div className="flex flex-wrap gap-2 items-center">
                <Badge tom="azul">Modelo: {data.modelo}</Badge>
                {data.baixo_volume && <Badge tom="amarelo">baixo volume</Badge>}
              </div>
            </div>
            <GraficoPrevisao historico={data.historico || []} previsao={pontos} />
            <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
              Linha contínua: AIH observadas no SIH (medido
              {data.competencias_provisorias?.length ? `; ${data.competencias_provisorias.map(mesAno).join(' e ')} ainda provisórias` : ''}).
              Linha tracejada e faixa: previsão e intervalo de 80% (estimado). {data.modelo_descricao}
            </p>
          </section>

          <section className="card" aria-labelledby="titulo-tab-prev">
            <h3 id="titulo-tab-prev" className="text-base font-semibold mb-3">Previsão e erro medido por horizonte</h3>
            <TabelaRolavel rotulo="Previsão por horizonte com intervalo e MAPE">
              <table className="table-predmed" style={{ minWidth: 0 }}>
                <caption className="sr-only">Previsão da produção cirúrgica em 30, 60 e 90 dias, intervalo de 80% e MAPE do teste fora da amostra</caption>
                <thead>
                  <tr>
                    <th scope="col">Horizonte</th>
                    <th scope="col">Competência</th>
                    <th scope="col" className="text-right">Previsto</th>
                    <th scope="col" className="text-right">Intervalo 80%</th>
                    <th scope="col" className="text-right">MAPE (teste)</th>
                    <th scope="col" className="text-center">Meta {'<'} {META}%</th>
                  </tr>
                </thead>
                <tbody>
                  {pontos.map(p => {
                    const ok = p.mape_teste_pct != null && p.mape_teste_pct < META
                    return (
                      <tr key={p.horizonte}>
                        <td>{p.horizonte_dias} dias</td>
                        <td className="font-mono">{mesAno(p.competencia)}</td>
                        <td className="text-right font-mono">{fmt(p.previsto)}</td>
                        <td className="text-right font-mono">{fmt(p.intervalo_80_inferior)}–{fmt(p.intervalo_80_superior)}</td>
                        <td className="text-right font-mono font-semibold" style={{ color: ok ? 'var(--accent2)' : 'var(--red)' }}>{pct(p.mape_teste_pct)}</td>
                        <td className="text-center text-xs" style={{ color: ok ? 'var(--accent2)' : 'var(--red)' }}>{ok ? 'atingida' : 'não atingida'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </TabelaRolavel>
            <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
              {data.intervalo_metodo}. Previsão {data.previsao_id}; avaliação {data.avaliacao_id}.
              A previsão não inclui mutirões ou mudanças de política não observadas na série.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
