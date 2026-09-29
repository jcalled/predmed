'use client'
import { Fragment, useEffect, useState } from 'react'
import useSWR from 'swr'
import { Scale, AlertTriangle, ChevronDown, ChevronRight, Info, SearchX } from 'lucide-react'
import { priorizacaoApi, judicializadosApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import Badge, { BadgeSwalis, SWALIS_CATEGORIAS, swalisTom } from '@/components/ui/Badge'
import SeloDado from '@/components/ui/SeloDado'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

const TOM_COR: Record<string, string> = {
  vermelho: 'var(--red)',
  laranja:  'var(--accent3)',
  amarelo:  'var(--yellow)',
  azul:     'var(--accent)',
  verde:    'var(--accent2)',
  cinza:    'var(--text2)',
}

type Componente = { criterio: string; pontos: number; detalhe: string }
type Paciente = {
  id: number
  iniciais: string | null
  hospital_nome: string
  municipio: string
  especialidade: string
  classif_swalis: string
  judicializado: boolean
  procedimento: string | null
  dias_espera: number | null
  data_confiavel: boolean | null
  score: number
  componentes: Componente[]
  alertas: string[]
}

const LIMITE_PADRAO = 50
const LIMITE_MAXIMO = 200 // teto aceito por GET /priorizacao

function faixaScore(score: number) {
  if (score >= 70) return { cor: 'var(--red)', rotulo: 'alta' }
  if (score >= 50) return { cor: 'var(--yellow)', rotulo: 'média' }
  return { cor: 'var(--accent)', rotulo: 'baixa' }
}

export default function PriorizacaoPage() {
  const { isGestor, isParticular } = useAuth()
  const [esp, setEsp] = useState('')
  const [onco, setOnco] = useState(false)
  const [judicial, setJudicial] = useState(false)
  const [aberto, setAberto] = useState<number | null>(null)
  // Link antigo /dashboard/judicializados redireciona para cá com ?judicializados=1
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('judicializados') === '1') setJudicial(true)
  }, [])
  // "Somente judicializados" é filtrado no cliente sobre o campo `judicializado`
  // já retornado por /priorizacao (o backend não muda). Com o filtro ligado,
  // pedimos o máximo que a API aceita (200) para cobrir mais casos.
  const limite = judicial ? LIMITE_MAXIMO : LIMITE_PADRAO
  const { data, error, isValidating, mutate } = useSWR(
    ['priorizacao', esp, onco, limite],
    () => priorizacaoApi.get({ limit: limite, especialidade: esp || undefined, apenas_oncologia: onco || undefined }),
    { keepPreviousData: true },
  )
  // Total de judicializados (agregado do estado) e linhas no escopo do perfil,
  // para avisar quando algum caso ficou fora dos 200 de maior score.
  const { data: jud } = useSWR('judicializados', judicializadosApi.get)

  const semDados = data === undefined
  const carregandoKpi = semDados && !error
  const dist: Record<string, number> = data?.distribuicao_swalis || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  const avaliados: Paciente[] = data?.top_prioritarios || []
  const lista = judicial ? avaliados.filter(p => p.judicializado) : avaliados
  const temFiltro = Boolean(esp || onco || judicial)
  const limparFiltros = () => { setEsp(''); setOnco(false); setJudicial(false) }
  // Linhas de judicializados que o perfil pode ver: o estado inteiro, exceto o
  // hospital particular (só as próprias linhas; /judicializados limita a 100).
  const judNoEscopo: number | undefined = isParticular ? jud?.pacientes?.length : jud?.total
  const possivelmenteIncompleto = judicial && !esp && !onco && judNoEscopo != null && lista.length < judNoEscopo

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">Priorização Clínica</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Score explicável: SWALIS + tempo de espera + mandado judicial + oncologia + cardiovascular grave.
          Use &ldquo;Ver justificativa&rdquo; em cada paciente para ver de onde vem cada ponto.
        </p>
      </div>

      <div className="card mb-6 text-xs flex gap-3 items-start" style={{ borderColor: 'rgba(255,215,0,0.5)', color: 'var(--text2)' }} role="note">
        <Info size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--yellow)' }} />
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <strong style={{ color: 'var(--yellow)' }}>Regras {data?.versao_regras || 'v0.1'}</strong>
            <SeloDado natureza="nao_validado" />
          </div>
          Ferramenta de apoio à decisão: não substitui a regulação nem o julgamento clínico.
          Os pesos serão revisados com equipe clínica antes do uso no piloto.
        </div>
      </div>

      {/* Resumo */}
      <div className="grid grid-cols-1 min-[420px]:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 sm:gap-4 mb-6">
        <KPICard label="Avaliados" value={data?.total_avaliados ?? '—'} detail="Pacientes com score calculado" color="blue"
          status="medido" carregando={carregandoKpi} />
        <KPICard label="Score ≥ 70" value={data?.resumo?.score_70_ou_mais ?? '—'} detail="Maior prioridade combinada" color="red"
          status="nao_validado" carregando={carregandoKpi}
          tooltip="Depende dos pesos da regra v0.1, ainda não revisados pela equipe clínica." />
        <KPICard label="Oncologia > 60 dias" value={data?.resumo?.oncologia_acima_60_dias ?? '—'} detail="Referência Lei 12.732/2012" color="yellow"
          status="medido" carregando={carregandoKpi} />
        <KPICard label="Datas a confirmar" value={data?.resumo?.datas_a_confirmar ?? '—'} detail="Numeração antiga da regulação" color="blue"
          status="medido" carregando={carregandoKpi} />
        <KPICard label="Judicializados" value={jud?.total ?? '—'} detail="Ordens judiciais na fila do estado" color="red"
          status="medido" carregando={jud === undefined}
          tooltip="Total agregado do estado. Use o filtro “Somente judicializados” para ver os casos na lista." />
      </div>

      {/* Distribuição SWALIS */}
      <section aria-labelledby="titulo-dist" className="mb-6">
        <h2 id="titulo-dist" className="sr-only">Distribuição por categoria SWALIS</h2>
        <ul className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {SWALIS_CATEGORIAS.map(cat => {
            const n = dist[cat] || 0
            const pct = total > 0 ? ((n / total) * 100).toFixed(1).replace('.', ',') : '0'
            const cor = TOM_COR[swalisTom(cat)]
            return (
              <li key={cat} className="kpi-card text-center">
                <div className="mb-1"><BadgeSwalis categoria={cat === 'Não Informada' ? null : cat} /></div>
                <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text2)' }}>{cat}</div>
                {carregandoKpi ? (
                  <div className="h-7 w-16 mx-auto rounded-md animate-pulse" style={{ background: 'var(--surface2)' }} aria-hidden="true" />
                ) : (
                  <div className="text-xl font-bold font-mono" style={{ color: cor }}>{n.toLocaleString('pt-BR')}</div>
                )}
                <div className="text-xs mt-1" style={{ color: 'var(--text2)' }}>{carregandoKpi ? '' : `${pct}%`}</div>
              </li>
            )
          })}
        </ul>
      </section>

      {/* Filtros */}
      <form className="flex gap-3 flex-wrap mb-4 items-end" role="search" aria-label="Filtros da priorização" onSubmit={e => e.preventDefault()}>
        <div className="flex flex-col gap-1 w-full sm:w-56">
          <label htmlFor="prio-esp" className="text-xs" style={{ color: 'var(--text2)' }}>Especialidade</label>
          <input
            id="prio-esp"
            className="input-dark text-sm"
            placeholder="Ex.: oncologia"
            value={esp}
            onChange={e => setEsp(e.target.value)}
          />
        </div>
        <label className="text-sm flex items-center gap-2 h-[42px]" style={{ color: 'var(--text2)' }}>
          <input type="checkbox" className="w-4 h-4" style={{ accentColor: 'var(--accent)' }} checked={onco} onChange={e => setOnco(e.target.checked)} />
          Somente oncologia
        </label>
        <label className="text-sm flex items-center gap-2 h-[42px]" style={{ color: 'var(--text2)' }}>
          <input type="checkbox" className="w-4 h-4" style={{ accentColor: 'var(--accent)' }} checked={judicial} onChange={e => setJudicial(e.target.checked)} />
          <Scale size={14} aria-hidden="true" />
          Somente judicializados
        </label>
      </form>

      {judicial && (
        <div className="card mb-4 text-xs flex gap-3 items-start" style={{ borderColor: 'rgba(255,107,107,0.45)', color: 'var(--text2)' }} role="note">
          <Scale size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--red)' }} />
          <div>
            Casos com ordem judicial recebem pontos extras no score, mas <strong style={{ color: 'var(--text)' }}>não furam a fila automaticamente</strong>:
            o prazo de cada ordem deve ser conferido no processo. O filtro busca entre os {LIMITE_MAXIMO} pacientes de maior score.
            {possivelmenteIncompleto && (
              <div className="mt-1" style={{ color: 'var(--yellow)' }}>
                Há {judNoEscopo!.toLocaleString('pt-BR')} casos judicializados visíveis para o seu perfil e {lista.length.toLocaleString('pt-BR')} estão entre os {LIMITE_MAXIMO} primeiros.
                Os demais têm score menor; refine por especialidade para encontrá-los.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Lista priorizada */}
      <div className="card" aria-busy={isValidating}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-4">
          <h2 className="text-base font-semibold">
            {judicial ? `Judicializados entre os ${LIMITE_MAXIMO} de maior score` : `Top ${LIMITE_PADRAO} por score`}
          </h2>
          <span className="text-xs" style={{ color: 'var(--text2)' }}>Empate: quem espera há mais tempo vem primeiro</span>
        </div>
        {error && semDados ? (
          <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />
        ) : semDados ? (
          <Carregando mensagem="Calculando prioridades..." variante="linhas" />
        ) : lista.length === 0 ? (
          temFiltro ? (
            <EstadoVazio
              icone={<SearchX size={32} strokeWidth={1.5} />}
              titulo="Nenhum paciente corresponde aos filtros"
              descricao="Tente outra especialidade ou desmarque os filtros “Somente oncologia” e “Somente judicializados”."
              acao={<button type="button" className="btn-primary text-xs" onClick={limparFiltros}>Limpar filtros</button>}
            />
          ) : isGestor ? (
            <EstadoVazio titulo="Nenhum paciente com score calculado" descricao="Verifique se a última coleta do IntegraSUS foi concluída." />
          ) : (
            <EstadoVazio
              titulo="Nenhum paciente da sua instituição nesta lista"
              descricao="Dados de outras instituições aparecem apenas de forma agregada."
            />
          )
        ) : (
          <>
            {isValidating && <div className="text-xs mb-2" role="status" style={{ color: 'var(--text2)' }}>Atualizando…</div>}
            <TabelaRolavel rotulo="Pacientes ordenados por score de prioridade">
              <table className="table-predmed" style={{ opacity: isValidating ? 0.6 : 1 }}>
                <caption className="sr-only">
                  {judicial ? 'Pacientes judicializados' : `Top ${LIMITE_PADRAO} pacientes`} por score de prioridade (regra v0.1, não validada). Cada linha tem um botão para ver a justificativa do score.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">Paciente</th>
                    <th scope="col">Hospital</th>
                    <th scope="col">Especialidade</th>
                    <th scope="col">SWALIS</th>
                    <th scope="col" className="text-right">Espera</th>
                    <th scope="col">Alertas</th>
                    <th scope="col" className="text-right">Score</th>
                    <th scope="col"><span className="sr-only">Justificativa</span></th>
                  </tr>
                </thead>
                <tbody>
                  {lista.map((p, i) => {
                    const expandido = aberto === p.id
                    const faixa = faixaScore(p.score)
                    const idDetalhe = `justificativa-${p.id}`
                    const alternar = () => setAberto(expandido ? null : p.id)
                    return (
                      <Fragment key={p.id}>
                        <tr onClick={alternar} style={{ cursor: 'pointer' }}>
                          <td className="font-mono text-xs" style={{ color: 'var(--text2)' }}>{i + 1}</td>
                          <td className="font-mono text-sm">{p.iniciais || '—'}</td>
                          <td className="text-xs" style={{ maxWidth: 220 }}>
                            <div className="truncate" title={p.hospital_nome}>{p.hospital_nome}</div>
                            {p.procedimento && (
                              <div className="truncate text-2xs" style={{ color: 'var(--text2)' }} title={p.procedimento}>{p.procedimento}</div>
                            )}
                          </td>
                          <td className="text-xs">{p.especialidade}</td>
                          <td><BadgeSwalis categoria={p.classif_swalis} /></td>
                          <td className="text-right text-xs font-mono whitespace-nowrap">
                            {p.dias_espera != null ? `${p.dias_espera.toLocaleString('pt-BR')} d` : '—'}
                            {p.data_confiavel === false && <div><Badge tom="cinza" className="mt-1">a confirmar</Badge></div>}
                          </td>
                          <td className="text-xs">
                            <div className="flex flex-wrap gap-1">
                              {p.judicializado && <Badge tom="vermelho" icone={<Scale size={11} />}>judicial</Badge>}
                              {p.alertas.length > 0 && (
                                <Badge tom="amarelo" icone={<AlertTriangle size={11} />} title={p.alertas.join('\n')}
                                  rotuloAcessivel={`${p.alertas.length} ${p.alertas.length === 1 ? 'alerta' : 'alertas'} para revisão`}>
                                  {p.alertas.length}
                                </Badge>
                              )}
                            </div>
                          </td>
                          <td className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="h-1.5 w-16 rounded-full" style={{ background: 'var(--border)' }} aria-hidden="true">
                                <div className="h-full rounded-full" style={{ width: `${Math.min(p.score, 100)}%`, background: faixa.cor }} />
                              </div>
                              <span className="font-mono text-sm font-bold">{p.score}</span>
                              <span className="sr-only">(prioridade {faixa.rotulo})</span>
                            </div>
                          </td>
                          <td className="text-right">
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 text-xs rounded-md px-2 py-1 whitespace-nowrap hover:bg-white/5"
                              style={{ color: 'var(--accent)' }}
                              aria-expanded={expandido}
                              aria-controls={idDetalhe}
                              onClick={e => { e.stopPropagation(); alternar() }}
                            >
                              {expandido ? <ChevronDown size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
                              {expandido ? 'Ocultar' : 'Ver justificativa'}
                              <span className="sr-only"> do paciente {i + 1}</span>
                            </button>
                          </td>
                        </tr>
                        {expandido && (
                          <tr id={idDetalhe}>
                            <td colSpan={9} style={{ background: 'rgba(255,255,255,0.03)' }}>
                              <div className="grid md:grid-cols-2 gap-4 py-2 text-xs">
                                <div>
                                  <div className="font-semibold mb-2">Por que este score?</div>
                                  <table className="w-full">
                                    <caption className="sr-only">Composição do score</caption>
                                    <thead className="sr-only">
                                      <tr><th scope="col">Critério</th><th scope="col">Detalhe</th><th scope="col">Pontos</th></tr>
                                    </thead>
                                    <tbody>
                                      {p.componentes.map(c => (
                                        <tr key={c.criterio}>
                                          <td className="py-0.5 pr-2">{c.criterio}</td>
                                          <td className="py-0.5 pr-2" style={{ color: 'var(--text2)' }}>{c.detalhe}</td>
                                          <td className="py-0.5 text-right font-mono">+{c.pontos}</td>
                                        </tr>
                                      ))}
                                      <tr>
                                        <td className="pt-1 font-semibold" colSpan={2}>Total</td>
                                        <td className="pt-1 text-right font-mono font-semibold">{p.score}</td>
                                      </tr>
                                    </tbody>
                                  </table>
                                </div>
                                <div>
                                  <div className="font-semibold mb-2">Alertas para revisão</div>
                                  {p.alertas.length === 0
                                    ? <div style={{ color: 'var(--text2)' }}>Nenhum.</div>
                                    : <ul className="list-disc pl-4">{p.alertas.map(a => <li key={a}>{a}</li>)}</ul>}
                                  <div className="mt-2" style={{ color: 'var(--text2)' }}>Município: {p.municipio}</div>
                                  <div className="mt-2" style={{ color: 'var(--text2)' }}>
                                    A decisão final é da regulação e da equipe clínica.
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </TabelaRolavel>
          </>
        )}
      </div>
    </div>
  )
}
