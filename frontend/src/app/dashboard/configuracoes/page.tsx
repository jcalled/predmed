'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { Upload, Hospital, Database, Info, CheckCircle2, Clock, Lightbulb, AlertTriangle } from 'lucide-react'
import { configApi, adminApi, coletaApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import Abas, { type Aba } from '@/components/ui/Abas'
import Badge from '@/components/ui/Badge'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

/*
 * Configurações — docs/ux/arquitetura-telas.md, item 8. Abas por perfil:
 * - SESA: Importação de dados + Status da coleta
 * - SMS: Status da coleta (GET /coleta/status, require_gestor)
 * - Hospital particular: Vagas SUS
 * - Hospital público: não tem a tela (fora do menu; acesso direto mostra "sem permissão").
 * Os endpoints continuam protegidos no backend (import: require_sesa; PUT vagas: particular).
 */

interface Vaga {
  id: number
  especialidade: string
  vagas_mes: number
  aceito_mes: number
  disponivel: number
  ativo: boolean
  lotado: boolean
}

/* ---------------- Vagas SUS (hospital particular) ---------------- */

function AbaVagasSus() {
  const { user } = useAuth()
  const { data, error, isLoading, mutate } = useSWR('config-vagas', configApi.getVagas)
  const [salvando, setSalvando] = useState<string | null>(null)
  const [salvo, setSalvo] = useState<string | null>(null)
  const [erroSalvar, setErroSalvar] = useState<string | null>(null)

  const atualizar = async (vaga: Vaga, vagasMes: number, ativo: boolean) => {
    if (vagasMes === vaga.vagas_mes && ativo === vaga.ativo) return
    setSalvando(vaga.especialidade)
    setErroSalvar(null)
    try {
      await configApi.updateVaga({ especialidade: vaga.especialidade, vagas_mes: vagasMes, ativo })
      setSalvo(vaga.especialidade)
      mutate()
      setTimeout(() => setSalvo(null), 2500)
    } catch {
      setErroSalvar(vaga.especialidade)
    }
    setSalvando(null)
  }

  const vagas: Vaga[] = data?.vagas || []

  return (
    <div className="max-w-4xl">
      <p className="text-sm mb-4" style={{ color: 'var(--text2)' }}>
        Quantas vagas cirúrgicas por mês o hospital oferece ao SUS em cada especialidade. A SESA vê essas vagas nas sugestões de
        redistribuição; o hospital nunca recebe mais do que o limite configurado. Ao atingir o limite, a especialidade sai das sugestões
        até o contador zerar no primeiro dia do mês.
      </p>

      <div className="flex items-center gap-3 mb-4 px-4 py-3 rounded-lg" style={{ background: 'rgba(0,255,157,0.05)', border: '1px solid rgba(0,255,157,0.25)' }}>
        <CheckCircle2 size={18} aria-hidden="true" style={{ color: 'var(--accent2)' }} />
        <div>
          <div className="text-sm font-semibold" style={{ color: 'var(--accent2)' }}>{user?.tenant_nome}</div>
          <div className="text-xs" style={{ color: 'var(--text2)' }}>{user?.tenant_cir} · situação de credenciamento informada no cadastro da instituição</div>
        </div>
      </div>

      <div className="card">
        {error && !data ? (
          <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />
        ) : isLoading ? (
          <Carregando mensagem="Carregando vagas..." variante="linhas" linhas={4} />
        ) : vagas.length === 0 ? (
          <EstadoVazio titulo="Nenhuma especialidade cadastrada" descricao="Peça à equipe PREDMED para habilitar as especialidades do contrato." />
        ) : (
          <TabelaRolavel rotulo="Vagas SUS por especialidade">
            <table className="table-predmed">
              <caption className="sr-only">Vagas SUS por especialidade: limite mensal, aceitas no mês, disponíveis e se a oferta está ativa</caption>
              <thead>
                <tr>
                  <th scope="col">Especialidade</th>
                  <th scope="col" className="text-center">Vagas/mês</th>
                  <th scope="col" className="text-center">Aceitas no mês</th>
                  <th scope="col" className="text-center">Disponíveis</th>
                  <th scope="col">Ocupação</th>
                  <th scope="col" className="text-center">Oferta ativa</th>
                  <th scope="col"><span className="sr-only">Situação do salvamento</span></th>
                </tr>
              </thead>
              <tbody>
                {vagas.map(v => {
                  const pct = v.vagas_mes > 0 ? Math.round((v.aceito_mes / v.vagas_mes) * 100) : 0
                  const idInput = `vagas-${v.especialidade.replace(/\s+/g, '-')}`
                  return (
                    <tr key={v.especialidade}>
                      <td className="font-medium"><label htmlFor={idInput}>{v.especialidade}</label></td>
                      <td className="text-center">
                        <input
                          id={idInput}
                          type="number"
                          inputMode="numeric"
                          defaultValue={v.vagas_mes}
                          min={0}
                          max={500}
                          className="input-dark text-center font-mono"
                          style={{ width: 80, padding: '4px 8px' }}
                          onBlur={e => atualizar(v, parseInt(e.target.value) || 0, v.ativo)}
                        />
                      </td>
                      <td className="text-center font-mono">{v.aceito_mes}</td>
                      <td className="text-center font-mono font-bold">
                        {v.lotado ? <Badge tom="vermelho">lotado</Badge> : <span style={{ color: 'var(--accent2)' }}>{v.disponivel}</span>}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 pressure-bar-bg !mt-0" style={{ minWidth: 60 }} aria-hidden="true">
                            <div className="pressure-bar" style={{ width: `${Math.min(pct, 100)}%`, background: pct >= 100 ? 'var(--red)' : pct >= 70 ? 'var(--yellow)' : 'var(--accent2)' }} />
                          </div>
                          <span className="text-xs font-mono" style={{ color: 'var(--text2)', minWidth: 32 }}>{pct}%</span>
                        </div>
                      </td>
                      <td className="text-center">
                        <button
                          type="button"
                          role="switch"
                          aria-checked={v.ativo}
                          aria-label={`Oferta de ${v.especialidade} ativa`}
                          className={`toggle ${v.ativo ? 'on' : ''}`}
                          onClick={() => atualizar(v, v.vagas_mes, !v.ativo)}
                        />
                      </td>
                      <td className="text-xs text-right whitespace-nowrap" aria-live="polite">
                        {salvando === v.especialidade ? <span style={{ color: 'var(--text2)' }}>Salvando...</span>
                          : salvo === v.especialidade ? <span style={{ color: 'var(--accent2)' }}>Salvo</span>
                          : erroSalvar === v.especialidade ? <span style={{ color: 'var(--red)' }}>Não salvou</span> : null}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </TabelaRolavel>
        )}
      </div>

      <p className="mt-4 text-xs flex gap-2 items-start" style={{ color: 'var(--text2)' }}>
        <Lightbulb size={14} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--yellow)' }} />
        Para estimar a receita dessas vagas, veja a tela Oportunidades SUS.
      </p>
    </div>
  )
}

/* ---------------- Importação de dados (SESA) ---------------- */

function AbaImportacao() {
  const [enviando, setEnviando] = useState<string | null>(null)
  const [mensagem, setMensagem] = useState<{ tipo: 'ok' | 'erro'; texto: string } | null>(null)

  const importar = async (tipo: 'integrasus' | 'datasus', arquivo: File) => {
    setEnviando(tipo)
    setMensagem(null)
    try {
      if (tipo === 'integrasus') {
        const r = await adminApi.importIntegrasus(arquivo)
        setMensagem({ tipo: 'ok', texto: `IntegraSUS importado: ${r.pacientes_importados.toLocaleString('pt-BR')} registros da fila. As previsões serão recalculadas em segundo plano.` })
      } else {
        const r = await adminApi.importDataSus(arquivo)
        setMensagem({ tipo: 'ok', texto: `DATASUS importado: ${r.hospitais_importados.toLocaleString('pt-BR')} hospitais.` })
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setMensagem({ tipo: 'erro', texto: `Falha na importação: ${err.response?.data?.detail || 'erro desconhecido'}` })
    }
    setEnviando(null)
  }

  const fontes = [
    { id: 'integrasus' as const, titulo: 'IntegraSUS — fila cirúrgica (SESA-CE)', desc: 'CSV da fila de espera cirúrgica. Substitui a fila atual.' },
    { id: 'datasus' as const, titulo: 'DATASUS — TabNet SIH/SUS', desc: 'CSV de internações por hospital. Atualização semestral ou anual.' },
  ]

  return (
    <div className="max-w-4xl">
      <p className="text-sm mb-4" style={{ color: 'var(--text2)' }}>
        Importação manual, para quando a coleta automática falhar ou para carregar bases históricas. Só o perfil SESA pode importar.
      </p>
      {mensagem && (
        <div role={mensagem.tipo === 'erro' ? 'alert' : 'status'} className="mb-4 px-4 py-3 rounded-lg text-sm"
          style={{
            background: mensagem.tipo === 'ok' ? 'rgba(0,255,157,0.06)' : 'rgba(255,107,107,0.08)',
            border: `1px solid ${mensagem.tipo === 'ok' ? 'rgba(0,255,157,0.3)' : 'rgba(255,107,107,0.35)'}`,
            color: mensagem.tipo === 'ok' ? 'var(--accent2)' : 'var(--red)',
          }}>
          {mensagem.texto}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {fontes.map(f => (
          <div key={f.id} className="card">
            <div className="text-sm font-semibold mb-1">{f.titulo}</div>
            <div className="text-xs mb-3" style={{ color: 'var(--text2)' }}>{f.desc}</div>
            <label className="btn-primary text-sm cursor-pointer inline-flex items-center gap-2 has-[:focus-visible]:outline has-[:focus-visible]:outline-2">
              <Upload size={14} aria-hidden="true" />
              {enviando === f.id ? 'Importando...' : 'Enviar arquivo CSV'}
              <input type="file" accept=".csv" className="sr-only" disabled={enviando !== null}
                onChange={e => { const arq = e.target.files?.[0]; if (arq) importar(f.id, arq); e.target.value = '' }} />
            </label>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ---------------- Status da coleta (SESA e SMS) ---------------- */

const COLETAS = [
  { fonte: 'IntegraSUS — fila cirúrgica', como: 'Coleta automática da API pública', quando: 'Duas vezes ao dia (7h e 19h)', ativa: true },
  { fonte: 'DATASUS — SIH/SUS e CNES', como: 'Coleta automática de arquivos .dbc', quando: 'Dias 10 e 25 de cada mês', ativa: true },
  { fonte: 'SISREG', como: 'Integração', quando: 'Prevista para depois do MVP', ativa: false },
  { fonte: 'Prontuários hospitalares (FHIR R4)', como: 'Integração', quando: 'Prevista para depois do MVP', ativa: false },
]

const PARAMETROS = [
  { rotulo: 'Meta de acurácia (MAPE)', valor: '< 15%' },
  { rotulo: 'Horizonte de previsão', valor: '30 a 90 dias' },
  { rotulo: 'Índice de pressão crítico', valor: '3,0×' },
  { rotulo: 'Raio de redistribuição', valor: 'mesma CIR (distância ainda não calculada)' },
]

interface ColetaFila {
  coletado_em: string
  total: number | null
  entradas: number | null
  saidas: number | null
  data_max: string | null
  judicializados: number | null
  estabelecimentos: number | null
}

interface RegistroDatasus {
  registrado_em: string
  fonte: string | null
  competencia: string | null
  acao: string | null
  registros: number | null
}

interface StatusColeta {
  verificado_em: string
  fila: {
    limite_atraso_horas: number
    atrasada: boolean
    horas_desde_ultima: number | null
    total_coletas: number
    ultima: ColetaFila | null
    ultimas: ColetaFila[]
  }
  datasus: {
    total_registros: number
    ultimo_registro_em: string | null
    por_fonte: RegistroDatasus[]
  }
}

const fmtDataHora = (iso: string) =>
  new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
const fmtData = (iso: string | null) => (iso ? new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString('pt-BR') : '—')
const fmtNum = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('pt-BR'))
const fmtHoras = (h: number) => (h < 1 ? 'menos de 1 hora' : `${h.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h`)

function SituacaoColeta() {
  const { data, error, isLoading, mutate } = useSWR<StatusColeta>('coleta-status', () => coletaApi.status(10), { refreshInterval: 5 * 60_000 })

  if (error && !data) return <div className="card"><EstadoErro erro={error} aoTentarNovamente={() => mutate()} /></div>
  if (isLoading || !data) return <div className="card"><Carregando mensagem="Lendo o registro das coletas..." variante="linhas" linhas={3} /></div>

  const { fila, datasus } = data
  const ultima = fila.ultima
  const corAtraso = fila.atrasada ? 'var(--red)' : 'var(--accent2)'

  return (
    <>
      <section className="card" aria-labelledby="titulo-ultima" style={{ borderColor: fila.atrasada ? 'rgba(255,107,107,0.55)' : undefined }}>
        <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
          <h2 id="titulo-ultima" className="text-base font-semibold flex items-center gap-2">
            <Database size={16} aria-hidden="true" /> Fila cirúrgica (IntegraSUS) — última coleta
          </h2>
          {fila.atrasada ? <Badge tom="vermelho" icone={<AlertTriangle size={11} />}>atrasada</Badge> : <Badge tom="verde">em dia</Badge>}
        </div>

        <div role={fila.atrasada ? 'alert' : 'status'} className="text-sm mb-4 flex gap-2 items-start" style={{ color: corAtraso }}>
          {fila.atrasada ? <AlertTriangle size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" /> : <CheckCircle2 size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" />}
          <span>
            {!ultima
              ? 'Nenhuma coleta registrada. Verifique se a coleta automática está instalada.'
              : fila.atrasada
                ? `Sem coleta da fila há ${fmtHoras(fila.horas_desde_ultima ?? 0)} (limite: ${fila.limite_atraso_horas} h). Os dados exibidos podem estar desatualizados.`
                : `Última coleta há ${fmtHoras(fila.horas_desde_ultima ?? 0)}.`}
          </span>
        </div>

        {ultima && (
          <dl className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {[
              { rotulo: 'Data e hora', valor: fmtDataHora(ultima.coletado_em) },
              { rotulo: 'Pacientes na fila', valor: fmtNum(ultima.total) },
              { rotulo: 'Entradas', valor: fmtNum(ultima.entradas) },
              { rotulo: 'Saídas', valor: fmtNum(ultima.saidas) },
              { rotulo: 'Inserção mais recente', valor: fmtData(ultima.data_max) },
            ].map(i => (
              <div key={i.rotulo} className="kpi-card">
                <dt className="text-xs" style={{ color: 'var(--text2)' }}>{i.rotulo}</dt>
                <dd className="font-mono text-sm font-bold mt-1">{i.valor}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
          Entradas e saídas comparam com a coleta anterior (— quando não há anterior). Verificado em {fmtDataHora(data.verificado_em)}.
        </p>
      </section>

      {fila.ultimas.length > 0 && (
        <section className="card" aria-labelledby="titulo-historico">
          <h2 id="titulo-historico" className="text-base font-semibold mb-3">
            Últimas coletas da fila <span className="text-xs font-normal" style={{ color: 'var(--text2)' }}>({fila.ultimas.length} de {fmtNum(fila.total_coletas)})</span>
          </h2>
          <TabelaRolavel rotulo="Últimas coletas da fila cirúrgica">
            <table className="table-predmed">
              <caption className="sr-only">Últimas coletas da fila cirúrgica, da mais recente para a mais antiga</caption>
              <thead>
                <tr>
                  <th scope="col">Data e hora</th>
                  <th scope="col" className="text-right">Total</th>
                  <th scope="col" className="text-right">Entradas</th>
                  <th scope="col" className="text-right">Saídas</th>
                  <th scope="col" className="text-right">Judicializados</th>
                  <th scope="col">Inserção mais recente</th>
                </tr>
              </thead>
              <tbody>
                {fila.ultimas.map(c => (
                  <tr key={c.coletado_em}>
                    <td className="text-xs whitespace-nowrap">{fmtDataHora(c.coletado_em)}</td>
                    <td className="text-right font-mono text-xs">{fmtNum(c.total)}</td>
                    <td className="text-right font-mono text-xs">{fmtNum(c.entradas)}</td>
                    <td className="text-right font-mono text-xs">{fmtNum(c.saidas)}</td>
                    <td className="text-right font-mono text-xs">{fmtNum(c.judicializados)}</td>
                    <td className="text-xs">{fmtData(c.data_max)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaRolavel>
        </section>
      )}

      <section className="card" aria-labelledby="titulo-datasus">
        <h2 id="titulo-datasus" className="text-base font-semibold mb-3">DATASUS (SIH/SUS e CNES) — último arquivo por fonte</h2>
        {datasus.por_fonte.length === 0 ? (
          <EstadoVazio titulo="Nenhum arquivo do DATASUS registrado" descricao="A coleta roda nos dias 10 e 25 de cada mês." />
        ) : (
          <TabelaRolavel rotulo="Último arquivo do DATASUS por fonte">
            <table className="table-predmed">
              <caption className="sr-only">Último registro de coleta do DATASUS por fonte</caption>
              <thead>
                <tr>
                  <th scope="col">Fonte</th>
                  <th scope="col">Competência</th>
                  <th scope="col">Registrado em</th>
                  <th scope="col" className="text-right">Registros</th>
                  <th scope="col">Ação</th>
                </tr>
              </thead>
              <tbody>
                {datasus.por_fonte.map(r => (
                  <tr key={r.fonte ?? r.registrado_em}>
                    <td className="text-xs font-medium">{r.fonte ?? '—'}</td>
                    <td className="text-xs font-mono">{r.competencia ?? '—'}</td>
                    <td className="text-xs whitespace-nowrap">{fmtDataHora(r.registrado_em)}</td>
                    <td className="text-right font-mono text-xs">{fmtNum(r.registros)}</td>
                    <td className="text-xs">{r.acao === 'baixado' ? 'baixado' : r.acao === 'validado_existente' ? 'já existente (validado)' : (r.acao ?? '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaRolavel>
        )}
      </section>
    </>
  )
}

function AbaStatusColeta() {
  return (
    <div className="max-w-4xl space-y-5">
      <SituacaoColeta />

      <div className="card text-xs flex gap-3 items-start" style={{ color: 'var(--text2)' }} role="note">
        <Info size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
        <div>
          Situação lida do registro (manifesto) de cada coleta: só números agregados, sem dados de pacientes.
          A coleta da fila é considerada <strong style={{ color: 'var(--text)' }}>atrasada</strong> após 14 horas sem execução.
        </div>
      </div>

      <section className="card" aria-labelledby="titulo-fontes">
        <h2 id="titulo-fontes" className="text-base font-semibold mb-3 flex items-center gap-2">
          <Database size={16} aria-hidden="true" /> Fontes de dados
        </h2>
        <ul>
          {COLETAS.map(c => (
            <li key={c.fonte} className="flex items-center justify-between gap-3 py-3 border-b last:border-b-0" style={{ borderColor: 'var(--border)' }}>
              <div className="min-w-0">
                <div className="text-sm font-medium">{c.fonte}</div>
                <div className="text-xs flex items-center gap-1" style={{ color: 'var(--text2)' }}>
                  <Clock size={12} aria-hidden="true" /> {c.como} · {c.quando}
                </div>
              </div>
              {c.ativa ? <Badge tom="verde">programada</Badge> : <Badge tom="cinza">planejada</Badge>}
            </li>
          ))}
        </ul>
      </section>

      <section className="card" aria-labelledby="titulo-parametros">
        <h2 id="titulo-parametros" className="text-base font-semibold mb-3">Parâmetros do modelo (referência)</h2>
        <dl>
          {PARAMETROS.map(p => (
            <div key={p.rotulo} className="flex items-center justify-between gap-3 py-2.5 border-b last:border-b-0" style={{ borderColor: 'var(--border)' }}>
              <dt className="text-sm">{p.rotulo}</dt>
              <dd className="font-mono text-sm text-right" style={{ color: 'var(--accent)' }}>{p.valor}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  )
}

/* ---------------- Página ---------------- */

export default function ConfiguracoesPage() {
  const { isSesa, isSms, isParticular } = useAuth()

  const abas: Aba[] = []
  if (isSesa) abas.push({ id: 'importacao', rotulo: 'Importação de dados', icone: <Upload size={16} />, conteudo: <AbaImportacao /> })
  if (isSesa || isSms) abas.push({ id: 'coleta', rotulo: 'Status da coleta', icone: <Database size={16} />, conteudo: <AbaStatusColeta /> })
  if (isParticular) abas.push({ id: 'vagas', rotulo: 'Vagas SUS', icone: <Hospital size={16} />, conteudo: <AbaVagasSus /> })

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">Configurações</h1>
        {abas.length > 0 && (
          <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
            {isParticular ? 'Oferta de vagas SUS do seu hospital.' : 'Dados que alimentam o PREDMED.'}
          </p>
        )}
      </div>

      {abas.length === 0 ? (
        <div className="card">
          <EstadoErro erro={{ response: { status: 403 } }} descricao="Seu perfil não tem configurações próprias. Dúvidas sobre os dados: fale com a SESA." />
        </div>
      ) : abas.length === 1 ? (
        <section aria-label={abas[0].rotulo}>{abas[0].conteudo}</section>
      ) : (
        <Abas abas={abas} rotulo="Seções das configurações" />
      )}
    </div>
  )
}
