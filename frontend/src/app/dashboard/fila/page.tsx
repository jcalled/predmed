'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { Scale, X, ChevronLeft, ChevronRight, SearchX } from 'lucide-react'
import { filaApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import Badge, { BadgeSwalis, SWALIS_CATEGORIAS } from '@/components/ui/Badge'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

type PacienteFila = {
  id: number
  iniciais: string | null
  hospital_nome: string
  especialidade: string
  classif_swalis: string
  municipio: string
  judicializado: boolean
  procedimento: string
  data_insercao: string | null
  dias_espera: number | null
  data_confiavel: boolean | null
}

export default function FilaPage() {
  const { isGestor } = useAuth()
  const [page, setPage] = useState(1)
  const [esp, setEsp] = useState('')
  const [swalis, setSwalis] = useState('')
  const [judicial, setJudicial] = useState('')

  const { data, error, isValidating, mutate } = useSWR(
    ['fila', page, esp, swalis, judicial],
    () => filaApi.get({
      page,
      limit: 50,
      especialidade: esp || undefined,
      swalis: swalis || undefined,
      judicializado: judicial === 'sim' ? true : judicial === 'nao' ? false : undefined,
    }),
    // Mantém a tabela anterior enquanto a próxima página/filtro carrega (sem "piscar").
    { keepPreviousData: true },
  )

  const semDados = data === undefined
  const stats = data?.stats
  const pacientes: PacienteFila[] = data?.pacientes || []
  const temFiltro = Boolean(esp || swalis || judicial)
  const limparFiltros = () => { setEsp(''); setSwalis(''); setJudicial(''); setPage(1) }

  return (
    <div className="animate-fadein">
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold">Fila Cirúrgica</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Fonte: IntegraSUS SESA/CE (painel público, coleta automática). Espera contada desde a data da solicitação.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 min-[420px]:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        <KPICard label="Total na Fila" value={stats?.total ?? '—'} detail="Pacientes aguardando" color="red"
          status="medido" fonte="IntegraSUS" carregando={semDados && !error} />
        <KPICard label="Categoria A1" value={stats?.a1 ?? '—'} detail="Risco imediato" color="yellow"
          status="medido" fonte="IntegraSUS" carregando={semDados && !error} />
        <KPICard label="Judicializados" value={stats?.judicializados ?? '—'} detail="Ordens judiciais" color="red"
          status="medido" fonte="IntegraSUS" carregando={semDados && !error} />
        <KPICard
          label="Espera mediana"
          value={stats?.espera_mediana_dias != null ? `${stats.espera_mediana_dias} dias` : '—'}
          detail={stats?.datas_a_confirmar
            ? `Sem ${stats.datas_a_confirmar.toLocaleString('pt-BR')} registros com data a confirmar`
            : 'Metade da fila espera mais que isso'}
          color="blue"
          status="medido"
          fonte="Data da solicitação"
          tooltip="Mediana dos dias desde a data da solicitação. Registros com numeração antiga (data a confirmar com a SESA) ficam fora do cálculo."
          carregando={semDados && !error}
        />
      </div>

      {/* Filtros */}
      <form
        className="flex gap-3 flex-wrap items-end mb-4"
        role="search"
        aria-label="Filtros da fila"
        onSubmit={e => e.preventDefault()}
      >
        <div className="flex flex-col gap-1 w-full sm:w-52">
          <label htmlFor="filtro-esp" className="text-xs" style={{ color: 'var(--text2)' }}>Especialidade</label>
          <input
            id="filtro-esp"
            className="input-dark text-sm"
            placeholder="Ex.: ortopedia"
            value={esp}
            onChange={e => { setEsp(e.target.value); setPage(1) }}
          />
        </div>
        <div className="flex flex-col gap-1 flex-1 min-w-[140px] sm:flex-none sm:w-48">
          <label htmlFor="filtro-swalis" className="text-xs" style={{ color: 'var(--text2)' }}>Categoria SWALIS</label>
          <select
            id="filtro-swalis"
            className="input-dark text-sm"
            value={swalis}
            onChange={e => { setSwalis(e.target.value); setPage(1) }}
          >
            <option value="">Todas as categorias</option>
            {SWALIS_CATEGORIAS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1 flex-1 min-w-[140px] sm:flex-none sm:w-44">
          <label htmlFor="filtro-judicial" className="text-xs" style={{ color: 'var(--text2)' }}>Judicialização</label>
          <select
            id="filtro-judicial"
            className="input-dark text-sm"
            value={judicial}
            onChange={e => { setJudicial(e.target.value); setPage(1) }}
          >
            <option value="">Todos</option>
            <option value="sim">Judicializados</option>
            <option value="nao">Não judicializados</option>
          </select>
        </div>
        {temFiltro && (
          <button type="button" className="btn-primary text-xs inline-flex items-center gap-1.5 h-[42px]" onClick={limparFiltros}>
            <X size={14} aria-hidden="true" /> Limpar filtros
          </button>
        )}
      </form>

      {/* Tabela */}
      <div className="card" aria-busy={isValidating}>
        {error && semDados ? (
          <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />
        ) : semDados ? (
          <Carregando mensagem="Carregando fila..." variante="linhas" />
        ) : pacientes.length === 0 ? (
          temFiltro ? (
            <EstadoVazio
              icone={<SearchX size={32} strokeWidth={1.5} />}
              titulo="Nenhum paciente corresponde aos filtros"
              descricao="Tente outra especialidade ou categoria."
              acao={<button type="button" className="btn-primary text-xs" onClick={limparFiltros}>Limpar filtros</button>}
            />
          ) : isGestor ? (
            <EstadoVazio
              titulo="Nenhum paciente na fila importada"
              descricao="Verifique se a última coleta do IntegraSUS foi concluída."
            />
          ) : (
            <EstadoVazio
              titulo="Nenhum paciente da sua instituição nesta lista"
              descricao="Dados de outras instituições aparecem apenas de forma agregada."
            />
          )
        ) : (
          <>
            {isValidating && (
              <div className="text-xs mb-2" role="status" style={{ color: 'var(--text2)' }}>Atualizando…</div>
            )}
            <TabelaRolavel rotulo="Pacientes na fila cirúrgica">
              <table className="table-predmed" style={{ opacity: isValidating ? 0.6 : 1 }}>
                <caption className="sr-only">
                  Fila cirúrgica, página {page}. Colunas: posição, paciente (iniciais), hospital e procedimento, especialidade, SWALIS, município, judicial, dias de espera.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">Paciente</th>
                    <th scope="col">Hospital</th>
                    <th scope="col">Especialidade</th>
                    <th scope="col">SWALIS</th>
                    <th scope="col">Município</th>
                    <th scope="col">Judicial</th>
                    <th scope="col" className="text-right">Espera</th>
                  </tr>
                </thead>
                <tbody>
                  {pacientes.map((p, i) => (
                    <tr key={p.id}>
                      <td className="font-mono text-xs" style={{ color: 'var(--text2)' }}>{(page - 1) * 50 + i + 1}</td>
                      <td className="font-mono text-xs font-medium">{p.iniciais || '—'}</td>
                      <td className="text-xs" style={{ maxWidth: 220 }}>
                        <div className="truncate" title={p.hospital_nome}>{p.hospital_nome}</div>
                        {p.procedimento && (
                          <div className="text-2xs truncate" style={{ color: 'var(--text2)' }} title={p.procedimento}>{p.procedimento}</div>
                        )}
                      </td>
                      <td className="text-xs">{p.especialidade}</td>
                      <td><BadgeSwalis categoria={p.classif_swalis} /></td>
                      <td className="text-xs" style={{ color: 'var(--text2)' }}>{p.municipio}</td>
                      <td>
                        {p.judicializado
                          ? <Badge tom="vermelho" icone={<Scale size={11} />}>Sim</Badge>
                          : <span className="text-xs" style={{ color: 'var(--text2)' }}><span aria-hidden="true">—</span><span className="sr-only">Não</span></span>
                        }
                      </td>
                      <td
                        className="text-right text-xs font-mono whitespace-nowrap"
                        title={p.data_confiavel === false
                          ? 'Numeração antiga do sistema de regulação: data de solicitação a confirmar com a SESA'
                          : p.data_insercao ? `Solicitação em ${p.data_insercao.split('-').reverse().join('/')}` : 'Sem data'}
                      >
                        {p.dias_espera != null ? `${p.dias_espera.toLocaleString('pt-BR')} d` : '—'}
                        {p.data_confiavel === false && (
                          <div><Badge tom="cinza" className="mt-1">a confirmar</Badge></div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TabelaRolavel>
          </>
        )}
      </div>

      {/* Paginação */}
      {!semDados && pacientes.length > 0 && (
        <nav className="flex flex-col sm:flex-row gap-3 justify-between sm:items-center mt-4" aria-label="Paginação da fila">
          <span className="text-xs" style={{ color: 'var(--text2)' }} aria-live="polite">
            Exibindo {((page - 1) * 50) + 1}–{Math.min(page * 50, data?.total || 0)} de {data?.total?.toLocaleString('pt-BR') || '—'}
          </span>
          <div className="flex gap-2">
            <button type="button" className="btn-primary text-xs inline-flex items-center gap-1" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft size={14} aria-hidden="true" /> Anterior
            </button>
            <button type="button" className="btn-primary text-xs inline-flex items-center gap-1" disabled={page * 50 >= (data?.total || 0)} onClick={() => setPage(p => p + 1)}>
              Próxima <ChevronRight size={14} aria-hidden="true" />
            </button>
          </div>
        </nav>
      )}
    </div>
  )
}
