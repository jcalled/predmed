'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { Upload, Hospital, Database, Info, CheckCircle2, Clock, Lightbulb } from 'lucide-react'
import { configApi, adminApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import Abas, { type Aba } from '@/components/ui/Abas'
import Badge from '@/components/ui/Badge'
import { Carregando, EstadoErro, EstadoVazio, TabelaRolavel } from '@/components/ui/Estados'

/*
 * Configurações — docs/ux/arquitetura-telas.md, item 8. Abas por perfil:
 * - SESA: Importação de dados + Status da coleta
 * - SMS: Status da coleta
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

function AbaStatusColeta() {
  return (
    <div className="max-w-4xl space-y-5">
      <div className="card text-xs flex gap-3 items-start" style={{ color: 'var(--text2)' }} role="note">
        <Info size={16} aria-hidden="true" className="flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
        <div>
          Esta é a <strong style={{ color: 'var(--text)' }}>programação</strong> das coletas. O horário e o resultado da última execução
          ainda não são expostos pela API; quando forem, aparecerão aqui.
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
