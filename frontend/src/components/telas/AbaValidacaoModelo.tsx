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
 * Holdout temporal: treina o Holt-Winters na série mensal de AIH do SIH sem os
 * últimos N meses, prevê esses meses e compara com o realizado.
 * O alvo é a produção hospitalar (contagem de AIH), NÃO a fila de espera:
 * um MAPE baixo aqui não comprova a meta de previsão da fila.
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
}

const ESPECIALIDADES = [
  'TOTAL', 'ORTOPEDIA', 'CARDIOVASCULAR', 'ONCOLOGIA', 'NEUROLOGIA', 'UROLOGIA', 'GINECOLOGIA', 'OFTALMOLOGIA',
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
  const [meses, setMeses] = useState(6)

  const { data: todas, error: erroTodas, isLoading: carregandoTodas } = useSWR<Record<string, ValidacaoData>>(
    ['validacao-todas', meses],
    async () => {
      const r = await Promise.all(ESPECIALIDADES.map(async e => [e, await analyticsApi.validacaoMape(e, meses)] as const))
      return Object.fromEntries(r)
    },
    { keepPreviousData: true },
  )
  const dados = todas?.[espSel]

  return (
    <div>
      <div className="card mb-5 text-xs flex gap-3 items-start" style={{ color: 'var(--text2)' }} role="note">
        <Info size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
        <div>
          Compara a previsão Holt-Winters com a produção realizada no SIH/DATASUS (contagem de AIH), por holdout temporal.
          <strong style={{ color: 'var(--text)' }}> O alvo é a produção hospitalar, não a fila de espera</strong>: um bom resultado aqui ainda não comprova
          a meta de previsão da fila. Meta do projeto: MAPE {'<'} {META}% <SeloDado natureza="meta" className="ml-1" />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4" role="group" aria-label="Horizonte do holdout">
        <span className="text-xs" style={{ color: 'var(--text2)' }}>Meses retirados para teste:</span>
        {[3, 6, 12].map(m => (
          <button
            key={m}
            type="button"
            aria-pressed={meses === m}
            onClick={() => setMeses(m)}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold"
            style={{
              background: meses === m ? 'rgba(0,194,255,0.15)' : 'var(--surface2)',
              border: `1px solid ${meses === m ? 'rgba(0,194,255,0.45)' : 'var(--border-strong)'}`,
              color: meses === m ? 'var(--accent)' : 'var(--text2)',
            }}
          >
            {m} meses
          </button>
        ))}
      </div>

      {erroTodas && !todas ? (
        <EstadoErro erro={erroTodas} />
      ) : carregandoTodas && !todas ? (
        <Carregando mensagem="Calculando validação por especialidade..." variante="linhas" linhas={3} />
      ) : (
        <>
          <section aria-labelledby="titulo-status-esp" className="mb-6">
            <h3 id="titulo-status-esp" className="text-sm font-semibold mb-2">MAPE por especialidade</h3>
            <ul className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-2">
              {ESPECIALIDADES.map(esp => {
                const d = todas?.[esp]
                const mape = d?.mape_real ?? null
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
                  MAPE — {espSel}
                </h3>
                <div className="text-4xl font-bold font-mono" style={{ color: situacao(dados.mape_real).cor }}>
                  {dados.mape_real !== null ? pct(dados.mape_real) : '—'}
                </div>
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  <Badge tom={situacao(dados.mape_real).tom}>{situacao(dados.mape_real).rotulo}</Badge>
                  <SeloDado natureza={dados.mape_real !== null ? 'medido' : 'nao_validado'} />
                </div>
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
                <h3 id="titulo-comp" className="text-base font-semibold mb-3">Comparação mês a mês</h3>
                {dados.comparacao_mensal.length === 0 ? (
                  <EstadoVazio
                    titulo="Sem dados do SIH para comparar"
                    descricao="A base histórica do SIH não foi carregada neste ambiente (script download_sih.py)."
                  />
                ) : (
                  <TabelaRolavel rotulo="Previsto versus realizado por mês">
                    <table className="table-predmed" style={{ minWidth: 0 }}>
                      <caption className="sr-only">Previsão Holt-Winters versus AIH realizadas no SIH, por mês, com erro percentual</caption>
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
        Metodologia: MAPE (erro percentual absoluto médio) por holdout temporal sobre a série mensal de AIH do SIH/DATASUS Ceará (dados públicos).
        A meta do projeto é referência, não resultado garantido.
      </p>
    </div>
  )
}
