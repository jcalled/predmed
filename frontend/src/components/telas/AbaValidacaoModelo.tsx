'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { Check, X, Info } from 'lucide-react'
import { analyticsApi } from '@/lib/api'
import SeloDado from '@/components/ui/SeloDado'
import Badge from '@/components/ui/Badge'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

/*
 * Aba "Validação do modelo" da Previsão de demanda (ex-/dashboard/validacao).
 * Mostra a avaliação fora da amostra VERSIONADA (avaliacao_id): origem móvel, modelo escolhido
 * na janela de validação e erro reportado na janela de teste, por horizonte (30/60/90 dias).
 * O alvo é a produção cirúrgica SIH (contagem de AIH), NÃO a fila de espera:
 * um MAPE baixo aqui não comprova a meta de previsão da fila (docs/dados/previsao-demanda-v1.md).
 */

interface ComparacaoMensal {
  mes: string
  previsto: number
  realizado: number
  erro_absoluto: number
  erro_pct: number
  dentro_meta: boolean
}

interface ValidacaoData {
  especialidade: string
  mape_real: number | null
  meta_projeto_mape_pct: number
  dentro_da_meta: boolean | null
  status?: 'calculado' | 'nao_validado'
  alvo_validado?: string
  comparacao_mensal: ComparacaoMensal[]
  meses_comparados: number
  meses_sem_dados_reais: number
  resumo: { meses_dentro_meta: number }
  interpretacao: string
  avaliacao_id?: string
  modelo?: string | null
  modelo_descricao?: string
  mape_por_horizonte?: Partial<Record<'h1' | 'h2' | 'h3' | 'trimestre', number | null>>
  janela_teste?: string[]
  baixo_volume?: boolean
}

const HORIZONTES = [
  { id: 'h1', dias: 30 },
  { id: 'h2', dias: 60 },
  { id: 'h3', dias: 90 },
] as const
type Horizonte = (typeof HORIZONTES)[number]['id']

/** MAPE do horizonte escolhido; sem avaliação versionada, cai no MAPE de 30 dias. */
function mapeDo(d: ValidacaoData | undefined, h: Horizonte): number | null {
  if (!d) return null
  const v = d.mape_por_horizonte?.[h]
  if (v !== undefined) return v ?? null
  return h === 'h1' ? d.mape_real : null
}

const ESPECIALIDADES = [
  'TOTAL', 'CIR DIGESTIVA', 'ORTOPEDIA', 'GINECOLOGIA', 'CARDIOVASCULAR', 'UROLOGIA',
  'ONCOLOGIA', 'OTORRINO', 'NEUROLOGIA', 'PEQUENAS CIRURGIAS', 'OFTALMOLOGIA', 'OUTRAS',
] as const

const META = 15
const fmt = (n: number) => new Intl.NumberFormat('pt-BR').format(Math.round(n))
const pct = (n: number) => `${n.toFixed(1).replace('.', ',')}%`

function situacao(mape: number | null) {
  if (mape === null) return { rotulo: 'Sem dados', cor: 'var(--text2)', tom: 'cinza' as const }
  if (mape < META) return { rotulo: 'Dentro da meta', cor: 'var(--accent2)', tom: 'verde' as const }
  return { rotulo: 'Acima da meta', cor: 'var(--red)', tom: 'vermelho' as const }
}

export default function AbaValidacaoModelo() {
  const [espSel, setEspSel] = useState<string>('TOTAL')
  const [horizonte, setHorizonte] = useState<Horizonte>('h1')
  const [carater, setCarater] = useState<'TODOS' | 'ELETIVO'>('TODOS')

  const { data: todas, error: erroTodas, isLoading: carregandoTodas } = useSWR<Record<string, ValidacaoData>>(
    ['validacao-todas', carater],
    async () => {
      const r = await Promise.all(ESPECIALIDADES.map(async e => [e, await analyticsApi.validacaoMape(e, 6, carater)] as const))
      return Object.fromEntries(r)
    },
    { keepPreviousData: true },
  )
  const dados = todas?.[espSel]
  const diasSel = HORIZONTES.find(h => h.id === horizonte)!.dias
  const mapeSel = mapeDo(dados, horizonte)
  const avaliacaoId = dados?.avaliacao_id ?? Object.values(todas || {})[0]?.avaliacao_id

  return (
    <div>
      <div className="card mb-5 text-xs flex gap-3 items-start" style={{ color: 'var(--text2)' }} role="note">
        <Info size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
        <div>
          Avaliação fora da amostra da previsão da produção cirúrgica SUS (SIH/DATASUS, contagem de AIH): cada modelo é treinado só com
          meses anteriores e testado{dados?.janela_teste ? ` de ${dados.janela_teste.join(' a ')}` : ''}; o modelo de cada especialidade foi escolhido antes, numa janela de validação separada.
          <strong style={{ color: 'var(--text)' }}> O alvo é a produção cirúrgica, não a fila de espera</strong>: um bom resultado aqui ainda não comprova
          a previsão da fila. Meta do projeto: MAPE {'<'} {META}% <SeloDado natureza="meta" className="ml-1" />
          {avaliacaoId && (
            <div className="mt-1">Avaliação versionada: <span className="font-mono" style={{ color: 'var(--text)' }}>{avaliacaoId}</span></div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Horizonte da previsão avaliada">
          <span className="text-xs" style={{ color: 'var(--text2)' }}>Horizonte:</span>
          {HORIZONTES.map(h => (
            <button
              key={h.id}
              type="button"
              aria-pressed={horizonte === h.id}
              onClick={() => setHorizonte(h.id)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold"
              style={{
                background: horizonte === h.id ? 'rgba(0,194,255,0.15)' : 'var(--surface2)',
                border: `1px solid ${horizonte === h.id ? 'rgba(0,194,255,0.45)' : 'var(--border-strong)'}`,
                color: horizonte === h.id ? 'var(--accent)' : 'var(--text2)',
              }}
            >
              {h.dias} dias
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:ml-4" role="group" aria-label="Caráter da internação">
          {(['TODOS', 'ELETIVO'] as const).map(c => (
            <button
              key={c}
              type="button"
              aria-pressed={carater === c}
              onClick={() => setCarater(c)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold"
              style={{
                background: carater === c ? 'rgba(0,194,255,0.15)' : 'var(--surface2)',
                border: `1px solid ${carater === c ? 'rgba(0,194,255,0.45)' : 'var(--border-strong)'}`,
                color: carater === c ? 'var(--accent)' : 'var(--text2)',
              }}
            >
              {c === 'TODOS' ? 'Todas as internações' : 'Só eletivas'}
            </button>
          ))}
        </div>
      </div>

      {erroTodas && !todas ? (
        <EstadoErro erro={erroTodas} />
      ) : carregandoTodas && !todas ? (
        <Carregando mensagem="Calculando validação por especialidade..." variante="linhas" linhas={3} />
      ) : (
        <>
          <section aria-labelledby="titulo-status-esp" className="mb-6">
            <h3 id="titulo-status-esp" className="text-sm font-semibold mb-2">MAPE por especialidade — {diasSel} dias</h3>
            <ul className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-6 gap-2">
              {ESPECIALIDADES.map(esp => {
                const d = todas?.[esp]
                const mape = mapeDo(d, horizonte)
                const st = situacao(mape)
                const sel = espSel === esp
                return (
                  <li key={esp}>
                    <button
                      type="button"
                      aria-pressed={sel}
                      onClick={() => setEspSel(esp)}
                      className="w-full p-3 rounded-xl text-center transition-colors"
                      style={{
                        background: sel ? 'rgba(0,194,255,0.1)' : 'var(--surface)',
                        border: `1px solid ${sel ? 'rgba(0,194,255,0.5)' : 'var(--border)'}`,
                      }}
                    >
                      <span className="block text-2xs truncate mb-1" style={{ color: 'var(--text2)' }}>{esp}</span>
                      <span className="block text-sm font-bold font-mono" style={{ color: st.cor }}>{mape !== null ? pct(mape) : '—'}</span>
                      <span className="block text-2xs font-semibold mt-0.5" style={{ color: st.cor }}>{st.rotulo}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>

          {dados && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <section className="card flex flex-col items-center text-center" aria-labelledby="titulo-mape">
                <h3 id="titulo-mape" className="text-xs font-semibold uppercase mb-3" style={{ color: 'var(--text2)', letterSpacing: '0.5px' }}>
                  MAPE {diasSel} dias — {espSel}
                </h3>
                <div className="text-4xl font-bold font-mono" style={{ color: situacao(mapeSel).cor }}>
                  {mapeSel !== null ? pct(mapeSel) : '—'}
                </div>
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  <Badge tom={situacao(mapeSel).tom}>{situacao(mapeSel).rotulo}</Badge>
                  <SeloDado natureza={mapeSel !== null ? 'medido' : 'nao_validado'} />
                </div>
                {dados.modelo && (
                  <p className="text-xs mt-2" style={{ color: 'var(--text2)' }}>
                    Modelo: <span className="font-mono" style={{ color: 'var(--text)' }}>{dados.modelo}</span>
                    {dados.baixo_volume ? ' · série de baixo volume' : ''}
                  </p>
                )}
                {dados.mape_por_horizonte && (
                  <dl className="mt-3 grid grid-cols-3 gap-2 w-full text-center">
                    {HORIZONTES.map(h => {
                      const v = dados.mape_por_horizonte?.[h.id] ?? null
                      return (
                        <div key={h.id} className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                          <dt className="text-2xs uppercase" style={{ color: 'var(--text2)' }}>{h.dias} dias</dt>
                          <dd className="font-mono font-bold text-sm" style={{ color: situacao(v).cor }}>{v !== null ? pct(v) : '—'}</dd>
                        </div>
                      )
                    })}
                  </dl>
                )}
                <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>{dados.interpretacao}</p>
                <dl className="mt-4 w-full pt-4 border-t grid grid-cols-2 gap-3" style={{ borderColor: 'var(--border)' }}>
                  <div>
                    <dt className="text-2xs uppercase" style={{ color: 'var(--text2)' }}>Meses comparados</dt>
                    <dd className="text-lg font-bold font-mono">{dados.meses_comparados}</dd>
                  </div>
                  <div>
                    <dt className="text-2xs uppercase" style={{ color: 'var(--text2)' }}>Dentro da meta</dt>
                    <dd className="text-lg font-bold font-mono">{dados.resumo.meses_dentro_meta}/{dados.meses_comparados}</dd>
                  </div>
                </dl>
                {dados.meses_sem_dados_reais > 0 && (
                  <p className="mt-3 text-xs" style={{ color: 'var(--yellow)' }}>
                    {dados.meses_sem_dados_reais} meses ainda sem dados do SIH
                  </p>
                )}
              </section>

              <section className="card lg:col-span-2" aria-labelledby="titulo-comp">
                <h3 id="titulo-comp" className="text-base font-semibold mb-1">Comparação mês a mês (previsão de 30 dias)</h3>
                <p className="text-xs mb-3" style={{ color: 'var(--text2)' }}>
                  Cada linha é a previsão feita um mês antes, na janela de teste. Para 60 e 90 dias, veja o MAPE ao lado.
                </p>
                {dados.comparacao_mensal.length === 0 ? (
                  <EstadoVazio
                    titulo="Sem dados do SIH para comparar"
                    descricao="A base histórica do SIH não foi carregada neste ambiente (script download_sih.py)."
                  />
                ) : (
                  <TabelaRolavel rotulo="Previsto versus realizado por mês">
                    <table className="table-predmed" style={{ minWidth: 0 }}>
                      <caption className="sr-only">Previsão de 30 dias do modelo escolhido versus AIH realizadas no SIH, por mês, com erro percentual</caption>
                      <thead>
                        <tr>
                          <th scope="col">Mês</th>
                          <th scope="col" className="text-right">Previsto</th>
                          <th scope="col" className="text-right">Realizado (SIH)</th>
                          <th scope="col" className="text-right">Erro</th>
                          <th scope="col" className="text-center">Meta</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dados.comparacao_mensal.map(c => (
                          <tr key={c.mes}>
                            <td className="font-mono">{c.mes}</td>
                            <td className="text-right font-mono">{fmt(c.previsto)}</td>
                            <td className="text-right font-mono">{fmt(c.realizado)}</td>
                            <td className="text-right font-mono font-semibold" style={{ color: c.dentro_meta ? 'var(--accent2)' : 'var(--red)' }}>{pct(c.erro_pct)}</td>
                            <td className="text-center">
                              {c.dentro_meta
                                ? <span className="inline-flex items-center gap-1 text-xs" style={{ color: 'var(--accent2)' }}><Check size={14} aria-hidden="true" />dentro</span>
                                : <span className="inline-flex items-center gap-1 text-xs" style={{ color: 'var(--red)' }}><X size={14} aria-hidden="true" />fora</span>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </TabelaRolavel>
                )}
              </section>
            </div>
          )}
        </>
      )}

      <p className="text-xs mt-5" style={{ color: 'var(--text2)' }}>
        Metodologia: MAPE (erro percentual absoluto médio) fora da amostra, com origem móvel, sobre a série mensal de AIH cirúrgicas do SIH/DATASUS Ceará
        (dados públicos). Relatório: docs/dados/previsao-demanda-v1.md. A meta do projeto é referência, não resultado garantido.
      </p>
    </div>
  )
}
