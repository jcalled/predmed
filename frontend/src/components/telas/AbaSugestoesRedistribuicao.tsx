'use client'
import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { redistApi } from '@/lib/api'
import KPICard from '@/components/ui/KPICard'

// Componente de Tooltip customizado
const Tooltip = ({ children, text, position = 'top' }: { children: React.ReactNode, text: string, position?: 'top' | 'bottom' | 'left' | 'right' }) => {
  const [show, setShow] = useState(false)
  
  const positions = {
    top: '-top-12 left-1/2 transform -translate-x-1/2',
    bottom: '-bottom-12 left-1/2 transform -translate-x-1/2',
    left: 'top-1/2 -left-48 transform -translate-y-1/2',
    right: 'top-1/2 -right-48 transform -translate-y-1/2'
  }

  return (
    <div className="relative inline-block" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && (
        <div className={`absolute ${positions[position]} z-50 w-44 p-2 rounded-lg text-xs`}
          style={{ 
            background: '#1A2B40', 
            border: '1px solid rgba(0,194,255,0.3)',
            color: 'var(--text1)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
          }}
        >
          <div className="relative">
            {text}
            <div className="absolute w-2 h-2" style={{ 
              background: '#1A2B40',
              borderLeft: '1px solid rgba(0,194,255,0.3)',
              borderTop: '1px solid rgba(0,194,255,0.3)',
              transform: 'rotate(45deg)',
              ...(position === 'top' && { bottom: '-5px', left: '50%', marginLeft: '-4px' }),
              ...(position === 'bottom' && { top: '-5px', left: '50%', marginLeft: '-4px' }),
              ...(position === 'left' && { right: '-5px', top: '50%', marginTop: '-4px' }),
              ...(position === 'right' && { left: '-5px', top: '50%', marginTop: '-4px' })
            }} />
          </div>
        </div>
      )}
    </div>
  )
}

// Componente de Ícone de Informação
const InfoIcon = ({ text, position = 'top' }: { text: string, position?: 'top' | 'bottom' | 'left' | 'right' }) => (
  <Tooltip text={text} position={position}>
    <span className="inline-flex items-center justify-center w-4 h-4 rounded-full text-xs cursor-help ml-1"
      style={{ 
        background: 'rgba(0,194,255,0.1)', 
        color: 'var(--accent)',
        border: '1px solid rgba(0,194,255,0.3)'
      }}
    >
      ?
    </span>
  </Tooltip>
)

// Configuração das Macrorregiões do Ceará
const MACRO_REGIOES = {
  'MACRO_FORTALEZA': {
    nome: 'Macro Fortaleza',
    cirs: ['CIR Fortaleza', 'CIR Caucaia', 'CIR Maracanaú', 'CIR Baturité', 'CIR Beberibe']
  },
  'MACRO_SOBRAL': {
    nome: 'Macro Sobral',
    cirs: ['CIR Sobral', 'CIR Acaraú', 'CIR Tianguá', 'CIR Camocim', 'CIR Canindé', 'CIR Tauá']
  },
  'MACRO_SERTAO_CENTRAL': {
    nome: 'Macro Sertão Central',
    cirs: ['CIR Quixadá', 'CIR Quixeramobim']
  },
  'MACRO_LITORAL_LESTE': {
    nome: 'Macro Litoral Leste',
    cirs: ['CIR Aracati', 'CIR Limoeiro do Norte', 'CIR Russas']
  },
  'MACRO_CARIRI': {
    nome: 'Macro Cariri',
    cirs: ['CIR Icó', 'CIR Iguatu', 'CIR Brejo Santo', 'CIR Crato', 'CIR Juazeiro do Norte']
  }
}

// Mapeamento CIR -> Macrorregião
const CIR_PARA_MACRO = Object.entries(MACRO_REGIOES).reduce((acc, [macro, config]) => {
  config.cirs.forEach(cir => {
    acc[cir] = macro
  })
  return acc
}, {} as Record<string, string>)

// Regiões flutuantes
const REGIOES_FLUTUANTES = {
  'CIR Itapipoca': ['MACRO_FORTALEZA', 'MACRO_SOBRAL']
}

interface Hospital {
  hospital_nome: string
  municipio: string
  cir: string
  tipo: string
  fila_atual: number
  media_mensal: number
  pressao: number
  pressao_status: string
  confianca?: number // Confiança da classificação CIR
  dias_para_multa?: number // não enviado pelo backend atual (economia de multas fica 0)
}

interface Sugestao {
  origem: Hospital
  destino: Hospital
  especialidade: string
  qtd_sugerida: number
  capacidade_livre: number
  reducao_espera_dias: number
  aih_estimada: number        // simulado: R$ 1.500 fixo por AIH
  aih_estimada_origem?: string
  distancia_km: number | null // ainda não calculada
  cir: string
  macro_origem?: string
  macro_destino?: string
  tipo_transferencia?: 'mesma_regiao' | 'mesma_macro' | 'outra_macro'
  dias_para_multa?: number
}

interface Aprovacao {
  protocolo: string
  hospital_destino: string
  especialidade: string
  qtd_pacientes: number
  aih_estimada: number
  data: string
  economia_multa: number
}

const PRESSAO_COLOR: Record<string, string> = {
  critico: 'var(--red)',
  alerta:  'var(--accent3)',
  normal:  'var(--accent)',
  ocioso:  'var(--accent2)',
}

const PRESSAO_EXPLICACAO: Record<string, string> = {
  critico: 'Pressão crítica: fila > 3× a capacidade mensal',
  alerta:  'Pressão em alerta: fila entre 1.5× e 3× a capacidade',
  normal:  'Pressão normal: fila entre 0.5× e 1.5× a capacidade',
  ocioso:  'Hospital ocioso: fila < 0.5× a capacidade mensal',
}

const PRIORIDADE_CONFIG = {
  mesma_regiao: {
    label: 'Mesma Região (Prioridade 1)',
    icon: '🔵',
    color: 'var(--accent)',
    bgColor: 'rgba(0,194,255,0.05)',
    borderColor: 'rgba(0,194,255,0.2)',
    explicacao: 'Transferência dentro da mesma CIR (Centro Integrado de Região). Prioridade máxima por manter o paciente na sua região de origem, seguindo a hierarquia do SUS.'
  },
  mesma_macro: {
    label: 'Mesma Macrorregião (Prioridade 2)',
    icon: '🟢',
    color: 'var(--accent2)',
    bgColor: 'rgba(0,255,157,0.05)',
    borderColor: 'rgba(0,255,157,0.2)',
    explicacao: 'Transferência para outra CIR, mas dentro da mesma Macrorregião de saúde. Segunda prioridade, pois ainda respeita o planejamento regional.'
  },
  outra_macro: {
    label: 'Outra Macrorregião (Prioridade 3)',
    icon: '🟡',
    color: 'var(--yellow)',
    bgColor: 'rgba(255,215,0,0.05)',
    borderColor: 'rgba(255,215,0,0.2)',
    explicacao: 'Transferência para uma Macrorregião diferente. Última prioridade, usada apenas quando não há capacidade ociosa nas regiões mais próximas.'
  }
}

// Componente de Tooltip para mostrar confiança da classificação
const ConfidenceTooltip = ({ confianca }: { confianca?: number }) => {
  if (!confianca) return null
  const color = confianca > 0.8 ? 'var(--accent2)' : confianca > 0.5 ? 'var(--yellow)' : 'var(--red)'
  return (
    <Tooltip text={`Confiança da classificação CIR: ${(confianca * 100).toFixed(0)}%`} position="top">
      <span className="ml-2 text-xs" style={{ color }}>
        {confianca > 0.8 ? '✓' : confianca > 0.5 ? '?' : '⚠️'}
      </span>
    </Tooltip>
  )
}

/**
 * Aba "Sugestões" da tela Redistribuição (conteúdo da antiga página única).
 * Aprovar depende de `pode_aprovar` retornado por GET /redistribuicao (hoje só SESA);
 * o POST /redistribuicao/aprovar continua protegido por require_sesa no backend.
 */
export default function AbaSugestoesRedistribuicao() {
  const [cirSelecionada, setCirSelecionada] = useState<string>('')
  const [hospitalOrigemSelecionado, setHospitalOrigemSelecionado] = useState<string>('')
  const [filtroPrioridade, setFiltroPrioridade] = useState<string>('')
  const [mostrarApenasMesmaRegiao, setMostrarApenasMesmaRegiao] = useState<boolean>(false)
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [modoSelecao, setModoSelecao] = useState<boolean>(false)
  const [mostrarApenasAltaConfianca, setMostrarApenasAltaConfianca] = useState<boolean>(false)
  const [mostrarExplicacao, setMostrarExplicacao] = useState<boolean>(true)
  
  const { data, isLoading, mutate } = useSWR(
    ['redistribuicao', cirSelecionada],
    () => redistApi.get(cirSelecionada || undefined)
  )
  
  const [aprovadas, setAprovadas] = useState<Aprovacao[]>([])
  const [aprovandoId, setAprovandoId] = useState<string | null>(null)
  const [recusadas, setRecusadas] = useState<Set<string>>(new Set())
  const [modalSugestao, setModalSugestao] = useState<Sugestao | null>(null)
  const [modalMultiplo, setModalMultiplo] = useState<boolean>(false)
  const [loadingAprovar, setLoadingAprovar] = useState(false)
  const [mostrarMetricasAvancadas, setMostrarMetricasAvancadas] = useState<boolean>(true)

  // Aprovação (decisão D11, 29/09/2026): SESA em todo o estado; SMS só entre
  // hospitais da própria CIR. `pode_aprovar` e `escopo_aprovacao` vêm da API e o
  // backend valida de novo (403 fora do escopo). Sem `escopo_aprovacao` (API
  // antiga), `pode_aprovar` só era verdadeiro para a SESA → estado.
  const podeAprovar = data?.pode_aprovar === true
  const escopoAprovacao: string | null = podeAprovar ? (data?.escopo_aprovacao ?? 'estado') : null
  const aprovaNoEstado = escopoAprovacao === 'estado'
  const podeAprovarSugestao = (s: Sugestao) =>
    podeAprovar && (aprovaNoEstado || (!!escopoAprovacao && s.origem.cir === escopoAprovacao && s.destino.cir === escopoAprovacao))
  const [aviso, setAviso] = useState<{ tipo: 'ok' | 'erro'; texto: string } | null>(null)
  const sugestoes: Sugestao[] = data?.sugestoes || []
  const cirsDisponiveis: string[] = data?.cirs_disponiveis || []
  const macros = data?.macros || {}

  // Lista única de hospitais de origem
  const hospitaisOrigem = Array.from(new Set(sugestoes.map(s => s.origem.hospital_nome))).sort()

  // Aplica filtros
  const sugestoesFiltradas = sugestoes
    .filter(s => !filtroPrioridade || s.tipo_transferencia === filtroPrioridade)
    .filter(s => !mostrarApenasMesmaRegiao || s.tipo_transferencia === 'mesma_regiao')
    .filter(s => !hospitalOrigemSelecionado || s.origem.hospital_nome === hospitalOrigemSelecionado)
    .filter(s => !mostrarApenasAltaConfianca || (s.origem.confianca || 0) > 0.7)

  // Métricas avançadas
  const totalRedistribuivel = sugestoesFiltradas.reduce((acc, s) => acc + s.qtd_sugerida, 0)
  const economiaTotalMultas = sugestoesFiltradas.reduce((acc, s) => {
    const diasMulta = Math.max(0, (s.origem.dias_para_multa || 0) - 30)
    return acc + (diasMulta > 0 ? s.qtd_sugerida * 500 : 0)
  }, 0)
  const aihTotal = sugestoesFiltradas.reduce((acc, s) => acc + s.aih_estimada, 0)
  
  // Dados para gráficos
  const dadosPorPrioridade = [
    { label: 'Mesma Região', value: sugestoes.filter(s => s.tipo_transferencia === 'mesma_regiao').length, color: PRIORIDADE_CONFIG.mesma_regiao.color },
    { label: 'Mesma Macro', value: sugestoes.filter(s => s.tipo_transferencia === 'mesma_macro').length, color: PRIORIDADE_CONFIG.mesma_macro.color },
    { label: 'Outra Macro', value: sugestoes.filter(s => s.tipo_transferencia === 'outra_macro').length, color: PRIORIDADE_CONFIG.outra_macro.color },
  ]

  const dadosPorEspecialidade = sugestoesFiltradas.reduce((acc, s) => {
    acc[s.especialidade] = (acc[s.especialidade] || 0) + s.qtd_sugerida
    return acc
  }, {} as Record<string, number>)

  const toggleSelecionado = (id: string) => {
    const s = sugestoesFiltradas[parseInt(id)]
    if (!s || !podeAprovarSugestao(s)) return
    const novoSet = new Set(selecionados)
    if (novoSet.has(id)) {
      novoSet.delete(id)
    } else {
      novoSet.add(id)
    }
    setSelecionados(novoSet)
  }

  const idsElegiveis = sugestoesFiltradas.flatMap((s, i) => (podeAprovarSugestao(s) ? [i.toString()] : []))
  const toggleTodos = () => {
    if (selecionados.size === idsElegiveis.length) {
      setSelecionados(new Set())
    } else {
      setSelecionados(new Set(idsElegiveis))
    }
  }

  const mensagemErroAprovacao = (e: unknown) => {
    const err = e as { response?: { status?: number; data?: { detail?: string } } }
    if (err.response?.status === 403) {
      return aprovaNoEstado
        ? 'Seu perfil não tem permissão para aprovar esta transferência.'
        : `Fora do seu escopo: a SMS aprova apenas transferências entre hospitais da ${escopoAprovacao ?? 'própria CIR'}.`
    }
    return err.response?.data?.detail || 'Falha na aprovação. Tente novamente.'
  }

  const aprovarSelecionados = async () => {
    if (selecionados.size === 0) return
    setModalMultiplo(true)
  }

  const confirmarAprovacoesMultiplas = async () => {
    setLoadingAprovar(true)
    try {
      const promises = Array.from(selecionados).map(async (idxStr) => {
        const s = sugestoesFiltradas[parseInt(idxStr)]
        if (!s) return null
        try {
          const r = await redistApi.aprovar({
            hospital_origem: s.origem.hospital_nome,
            hospital_destino: s.destino.hospital_nome,
            especialidade: s.especialidade,
            qtd_pacientes: s.qtd_sugerida,
          })
          return { ok: true as const, r, s }
        } catch (e) {
          return { ok: false as const, erro: mensagemErroAprovacao(e) }
        }
      })

      const todos = (await Promise.all(promises)).filter(x => x !== null)
      const resultados = todos.flatMap(x => (x && x.ok ? [x] : []))
      const falhas = todos.flatMap(x => (x && !x.ok ? [x.erro] : []))

      const novasAprovacoes = resultados.map(({ r, s }) => ({
        protocolo: r.protocolo,
        hospital_destino: s.destino.hospital_nome,
        especialidade: s.especialidade,
        qtd_pacientes: s.qtd_sugerida,
        aih_estimada: r.aih_estimada,
        data: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        economia_multa: s.qtd_sugerida * 500,
      }))
      
      setAprovadas(prev => [...prev, ...novasAprovacoes])
      setSelecionados(new Set())
      setModalMultiplo(false)
      setAviso(falhas.length === 0
        ? { tipo: 'ok', texto: `${resultados.length} ${resultados.length === 1 ? 'transferência aprovada' : 'transferências aprovadas'}.` }
        : { tipo: 'erro', texto: `${resultados.length} aprovada(s); ${falhas.length} não aprovada(s): ${Array.from(new Set(falhas)).join(' ')}` })
    } catch {
      setAviso({ tipo: 'erro', texto: 'Erro ao aprovar as transferências selecionadas.' })
    } finally {
      setLoadingAprovar(false)
    }
  }

  const confirmarAprovacao = async () => {
    if (!modalSugestao) return
    setLoadingAprovar(true)
    try {
      const res = await redistApi.aprovar({
        hospital_origem: modalSugestao.origem.hospital_nome,
        hospital_destino: modalSugestao.destino.hospital_nome,
        especialidade: modalSugestao.especialidade,
        qtd_pacientes: modalSugestao.qtd_sugerida,
      })
      setAprovadas(prev => [...prev, {
        protocolo: res.protocolo,
        hospital_destino: modalSugestao.destino.hospital_nome,
        especialidade: modalSugestao.especialidade,
        qtd_pacientes: modalSugestao.qtd_sugerida,
        aih_estimada: res.aih_estimada,
        data: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        economia_multa: modalSugestao.qtd_sugerida * 500,
      }])
      setAprovandoId(`${modalSugestao.origem.hospital_nome}-${modalSugestao.especialidade}`)
      setModalSugestao(null)
      setAviso({ tipo: 'ok', texto: `Transferência aprovada. Protocolo ${res.protocolo}.` })
    } catch (e: unknown) {
      setModalSugestao(null)
      setAviso({ tipo: 'erro', texto: mensagemErroAprovacao(e) })
    } finally {
      setLoadingAprovar(false)
    }
  }

  if (isLoading) return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="text-4xl mb-4 animate-pulse">🔄</div>
        <div className="text-sm" style={{ color: 'var(--text2)' }}>Calculando redistribuições...</div>
      </div>
    </div>
  )

  return (
    <div className="animate-fadein">
      {/* Header com métricas principais */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">Sugestões de redistribuição</h2>
            <InfoIcon text="Sugestões automáticas baseadas no índice de pressão dos hospitais e na capacidade ociosa. As transferências são priorizadas pela hierarquia do SUS." position="right" />
          </div>
          <button 
            className="px-4 py-2 rounded-lg text-sm flex items-center gap-2"
            style={{ 
              background: mostrarMetricasAvancadas ? 'rgba(0,194,255,0.1)' : 'var(--surface2)',
              border: '1px solid var(--border)'
            }}
            onClick={() => setMostrarMetricasAvancadas(!mostrarMetricasAvancadas)}
          >
            <span>{mostrarMetricasAvancadas ? '📊' : '📈'}</span>
            {mostrarMetricasAvancadas ? 'Ocultar métricas' : 'Mostrar métricas avançadas'}
          </button>
        </div>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          {!podeAprovar
            ? 'Somente leitura: a aprovação é feita pela SESA (todo o estado) ou pela SMS (dentro da própria CIR).'
            : aprovaNoEstado
              ? 'Você aprova transferências em todo o estado.'
              : `Você aprova transferências entre hospitais da ${escopoAprovacao}; as demais sugestões ficam só para leitura.`}
          {podeAprovar && ' A aprovação registra a decisão; não executa a transferência nem emite AIH.'}
          {podeAprovar && !aprovaNoEstado && sugestoes.length > 0 && !sugestoes.some(podeAprovarSugestao) && (
            <span className="block mt-1" style={{ color: 'var(--yellow)' }}>
              Nenhuma sugestão atual tem origem e destino dentro da {escopoAprovacao}.
            </span>
          )}
        </p>
      </div>

      {aviso && (
        <div
          role={aviso.tipo === 'erro' ? 'alert' : 'status'}
          className="mb-4 px-4 py-3 rounded-lg text-sm flex items-start justify-between gap-3"
          style={{
            background: aviso.tipo === 'ok' ? 'rgba(0,255,157,0.06)' : 'rgba(255,107,107,0.08)',
            border: `1px solid ${aviso.tipo === 'ok' ? 'rgba(0,255,157,0.3)' : 'rgba(255,107,107,0.4)'}`,
            color: aviso.tipo === 'ok' ? 'var(--accent2)' : 'var(--red)',
          }}
        >
          <span>{aviso.texto}</span>
          <button type="button" className="text-xs underline flex-shrink-0" onClick={() => setAviso(null)}>Fechar</button>
        </div>
      )}

      {/* Dashboard de impacto financeiro e operacional */}
      {mostrarMetricasAvancadas && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            label="Economia Potencial (simulado)"
            value={`R$ ${(economiaTotalMultas + aihTotal / 3).toLocaleString('pt-BR')}`}
            icon="💰"
            color="blue"
            tooltip="Simulação com parâmetros fixos (R$ 1.500/AIH, R$ 500/multa); não é valor medido"
            status="simulado"
          />

          <KPICard
            label="Dias de Espera Evitados (simulado)"
            value={`${(sugestoesFiltradas.reduce((acc, s) => acc + s.reducao_espera_dias * s.qtd_sugerida, 0) / 30).toFixed(0)} meses`}
            detail={`${sugestoesFiltradas.reduce((acc, s) => acc + s.reducao_espera_dias, 0)} dias totais`}
            icon="⏱️"
            color="green"
            tooltip="Estimativa heurística (fila ÷ produção mensal); não validada"
            status="simulado"
          />

          <KPICard
            label="Hospitais Beneficiados"
            value={new Set(sugestoesFiltradas.map(s => s.origem.hospital_nome)).size}
            detail={`${new Set(sugestoesFiltradas.map(s => s.destino.hospital_nome)).size} destinos`}
            icon="🏥"
            color="yellow"
            tooltip="Quantos hospitais serão aliviados (origem) e quantos receberão pacientes (destino)"
            status="estimado"
          />

          <KPICard
            label="ROI da Redistribuição"
            value="não validado"
            detail="Sem base de custos medida"
            icon="⚖️"
            color="red"
            tooltip="Não há dados de custo reais para calcular retorno; métrica removida até haver avaliação"
            status="nao_validado"
          />
        </div>
      )}

      {/* Filtros - AGORA COM HOSPITAL DE ORIGEM */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        {/* Seletor de CIR */}
        <div className="flex items-center">
          <select
            value={cirSelecionada}
            onChange={(e) => setCirSelecionada(e.target.value)}
            className="px-3 py-2 rounded-lg text-sm"
            style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              color: 'var(--text1)',
              minWidth: '180px'
            }}
          >
            <option value="">Todas as CIRs</option>
            {cirsDisponiveis.map(cir => (
              <option key={cir} value={cir}>{cir}</option>
            ))}
          </select>
          <InfoIcon text="Filtrar por CIR (Centro Integrado de Região) - unidade de planejamento regional do SUS" />
        </div>

        {/* NOVO: Seletor de Hospital de Origem */}
        <div className="flex items-center">
          <select
            value={hospitalOrigemSelecionado}
            onChange={(e) => setHospitalOrigemSelecionado(e.target.value)}
            className="px-3 py-2 rounded-lg text-sm"
            style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              color: 'var(--text1)',
              minWidth: '250px'
            }}
          >
            <option value="">Todos os hospitais</option>
            {hospitaisOrigem.map(hospital => (
              <option key={hospital} value={hospital}>{hospital}</option>
            ))}
          </select>
          <InfoIcon text="Filtrar sugestões por um hospital de origem específico" />
        </div>

        {/* Filtro de prioridade */}
        <div className="flex items-center">
          <select
            value={filtroPrioridade}
            onChange={(e) => setFiltroPrioridade(e.target.value)}
            className="px-3 py-2 rounded-lg text-sm"
            style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              color: 'var(--text1)',
              minWidth: '160px'
            }}
          >
            <option value="">Todas prioridades</option>
            <option value="mesma_regiao">🔵 Mesma Região</option>
            <option value="mesma_macro">🟢 Mesma Macro</option>
            <option value="outra_macro">🟡 Outra Macro</option>
          </select>
          <InfoIcon text="Filtrar pelo tipo de transferência, conforme hierarquia SUS" />
        </div>

        {/* Checkbox mesma região */}
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={mostrarApenasMesmaRegiao}
            onChange={(e) => setMostrarApenasMesmaRegiao(e.target.checked)}
            className="rounded"
            style={{ accentColor: 'var(--accent)' }}
          />
          <span style={{ color: 'var(--text2)' }}>Apenas mesma região</span>
          <InfoIcon text="Mostrar apenas transferências dentro da mesma CIR (prioridade máxima)" />
        </label>

        {/* Checkbox alta confiança */}
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={mostrarApenasAltaConfianca}
            onChange={(e) => setMostrarApenasAltaConfianca(e.target.checked)}
            className="rounded"
            style={{ accentColor: 'var(--accent2)' }}
          />
          <span style={{ color: 'var(--text2)' }}>Alta confiança {'>'}70%</span>
          <InfoIcon text="Mostrar apenas hospitais com classificação CIR de alta confiança (baseada nos pacientes atendidos)" />
        </label>

        {/* Botões de ação em massa */}
        {podeAprovar && idsElegiveis.length > 0 && (
          <div className="flex gap-2 ml-auto">
            <button
              className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 ${selecionados.size > 0 ? 'btn-primary' : ''}`}
              style={{
                background: selecionados.size > 0 ? 'rgba(0,194,255,0.1)' : 'var(--surface2)',
                border: '1px solid var(--border)'
              }}
              onClick={() => setModoSelecao(!modoSelecao)}
            >
              {modoSelecao ? '🔍 Cancelar seleção' : '✅ Modo seleção'}
            </button>
            
            {modoSelecao && (
              <>
                <button
                  className="px-3 py-1.5 rounded-lg text-sm"
                  style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
                  onClick={toggleTodos}
                >
                  {selecionados.size > 0 && selecionados.size === idsElegiveis.length ? 'Desmarcar todos' : aprovaNoEstado ? 'Selecionar todos' : 'Selecionar todos da minha CIR'}
                </button>
                
                <button
                  className="px-3 py-1.5 rounded-lg text-sm btn-green"
                  disabled={selecionados.size === 0}
                  onClick={aprovarSelecionados}
                >
                  ✅ Aprovar {selecionados.size} selecionada{selecionados.size > 1 ? 's' : ''}
                </button>
              </>
            )}
          </div>
        )}

        <span className="text-xs ml-auto" style={{ color: 'var(--text2)' }}>
          {sugestoesFiltradas.length} de {sugestoes.length} sugestões
        </span>
      </div>

      {/* Nota explicativa da hierarquia - AGORA COM TOOLTIPS */}
      <div className="mb-4 px-4 py-3 rounded-lg flex flex-wrap items-center gap-4 text-sm" style={{ background: 'rgba(0,255,157,0.04)', border: '1px solid rgba(0,255,157,0.15)' }}>
        <div className="flex items-center gap-2">
          <span>📍</span>
          <span style={{ color: 'var(--text2)' }}>Hierarquia SUS:</span>
          <InfoIcon text="Organização do sistema de saúde em níveis: CIR (local) → Macrorregião (regional) → Estado" />
        </div>
        <div className="flex gap-3">
          {Object.entries(PRIORIDADE_CONFIG).map(([key, config]) => (
            <div key={key} className="flex items-center gap-1">
              <span style={{ color: config.color }}>{config.icon}</span>
              <span>{config.label.split(' ')[0]} {config.label.split(' ')[1]}</span>
              <InfoIcon text={config.explicacao} />
            </div>
          ))}
        </div>
        <div className="text-xs flex items-center gap-1" style={{ color: 'var(--text2)' }}>
          Classificação baseada nos municípios atendidos por cada hospital
          <InfoIcon text="A CIR de cada hospital é inferida pelos municípios de origem dos pacientes que ele atende. ✓ = alta confiança, ⚠️ = baixa confiança" />
        </div>
        <button 
          className="ml-auto text-xs flex items-center gap-1"
          style={{ color: 'var(--accent)' }}
          onClick={() => setMostrarExplicacao(!mostrarExplicacao)}
        >
          {mostrarExplicacao ? '🙈 Ocultar' : '👁️ Mostrar explicações'}
        </button>
      </div>

      {/* Explicação expandida */}
      {mostrarExplicacao && (
        <div className="mb-4 p-4 rounded-lg" style={{ background: 'rgba(0,194,255,0.03)', border: '1px solid rgba(0,194,255,0.1)' }}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg" style={{ background: PRIORIDADE_CONFIG.mesma_regiao.bgColor, border: `1px solid ${PRIORIDADE_CONFIG.mesma_regiao.borderColor}` }}>
              <h3 className="text-sm font-semibold mb-2" style={{ color: PRIORIDADE_CONFIG.mesma_regiao.color }}>🔵 Mesma Região (CIR)</h3>
              <p className="text-xs" style={{ color: 'var(--text2)' }}>Transferência dentro da mesma CIR. Prioridade máxima por manter o paciente na sua região de origem, seguindo a hierarquia do SUS e minimizando deslocamentos.</p>
            </div>
            <div className="p-3 rounded-lg" style={{ background: PRIORIDADE_CONFIG.mesma_macro.bgColor, border: `1px solid ${PRIORIDADE_CONFIG.mesma_macro.borderColor}` }}>
              <h3 className="text-sm font-semibold mb-2" style={{ color: PRIORIDADE_CONFIG.mesma_macro.color }}>🟢 Mesma Macrorregião</h3>
              <p className="text-xs" style={{ color: 'var(--text2)' }}>Transferência para outra CIR, mas dentro da mesma Macrorregião de saúde. Segunda prioridade, respeitando o planejamento regional.</p>
            </div>
            <div className="p-3 rounded-lg" style={{ background: PRIORIDADE_CONFIG.outra_macro.bgColor, border: `1px solid ${PRIORIDADE_CONFIG.outra_macro.borderColor}` }}>
              <h3 className="text-sm font-semibold mb-2" style={{ color: PRIORIDADE_CONFIG.outra_macro.color }}>🟡 Outra Macrorregião</h3>
              <p className="text-xs" style={{ color: 'var(--text2)' }}>Transferência para uma Macrorregião diferente. Última prioridade, usada apenas quando não há capacidade ociosa nas regiões mais próximas.</p>
            </div>
          </div>
        </div>
      )}

      {/* Lista de sugestões */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold">🗺️ Sugestões de Redistribuição</h2>
            <InfoIcon text="Sugestões geradas pelo algoritmo de IA baseado no índice de pressão e capacidade ociosa" />
          </div>
          <div className="flex gap-2">
            <span className="badge badge-blue">{sugestoesFiltradas.length} sugestões</span>
            <span className="badge" style={{ background: 'rgba(0,255,157,0.1)', color: 'var(--accent2)' }}>
              {totalRedistribuivel} pacientes
            </span>
          </div>
        </div>

        {sugestoesFiltradas.length === 0 ? (
          <div className="text-center py-12" style={{ color: 'var(--text2)' }}>
            <div className="text-4xl mb-3">✅</div>
            <div className="text-sm">Nenhuma redistribuição necessária</div>
            <div className="text-xs mt-2">O sistema está equilibrado ou não há hospitais com capacidade ociosa compatível</div>
          </div>
        ) : (
          <div className="space-y-3">
            {sugestoesFiltradas.map((s, idx) => {
              const rowId = idx.toString()
              const isAprovada = aprovandoId === `${s.origem.hospital_nome}-${s.especialidade}` || 
                                aprovadas.some(a => a.especialidade === s.especialidade && a.hospital_destino === s.destino.hospital_nome)
              const isRecusada = recusadas.has(rowId)
              const tipoTransf = s.tipo_transferencia || 'mesma_regiao'
              const prioridade = PRIORIDADE_CONFIG[tipoTransf]
              const isSelected = selecionados.has(rowId)
              const noEscopo = podeAprovarSugestao(s)

              return (
                <div 
                  key={idx} 
                  className="redis-row rounded-lg px-4 py-3 transition-all group relative"
                  style={{
                    opacity: isAprovada || isRecusada ? 0.4 : 1,
                    background: isSelected ? 'rgba(0,194,255,0.1)' : prioridade.bgColor,
                    border: isSelected ? '2px solid var(--accent)' : `1px solid ${prioridade.borderColor}`,
                    cursor: modoSelecao ? 'pointer' : 'default'
                  }}
                  onClick={() => modoSelecao && toggleSelecionado(rowId)}
                >
                  {/* Checkbox para modo seleção */}
                  {modoSelecao && noEscopo && (
                    <div className="flex items-center mb-2">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelecionado(rowId)}
                        className="rounded"
                        style={{ accentColor: 'var(--accent)' }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="ml-2 text-xs" style={{ color: 'var(--text2)' }}>Selecionar para aprovação em massa</span>
                    </div>
                  )}

                  {/* Badge de prioridade e confiança */}
                  <div className="flex items-center gap-2 mb-2">
                    <Tooltip text={prioridade.explicacao}>
                      <span className="text-xs font-medium" style={{ color: prioridade.color }}>
                        {prioridade.icon} {prioridade.label}
                      </span>
                    </Tooltip>
                    {s.origem.confianca && (
                      <span 
                        className="text-xs px-2 py-0.5 rounded-full flex items-center gap-1"
                        style={{ 
                          background: s.origem.confianca > 0.8 ? 'rgba(0,255,157,0.1)' : 'rgba(255,215,0,0.1)',
                          color: s.origem.confianca > 0.8 ? 'var(--accent2)' : 'var(--yellow)'
                        }}
                      >
                        {s.origem.confianca > 0.8 ? '✓' : '⚠️'} 
                        {s.origem.confianca > 0.8 ? 'Alta confiança' : 'Confiança média'}
                        <InfoIcon text={`Classificação CIR baseada em ${s.origem.confianca > 0.8 ? 'muitos pacientes' : 'poucos pacientes'} atendidos`} />
                      </span>
                    )}
                    {s.dias_para_multa && s.dias_para_multa < 30 && (
                      <Tooltip text="Dias restantes para o hospital entrar em regime de multa por descumprimento de prazos">
                        <span className="px-2 py-0.5 rounded-full text-xs font-bold flex items-center gap-1" style={{ background: 'rgba(255,68,68,0.2)', color: 'var(--red)' }}>
                          ⚠️ {s.dias_para_multa} dias para multa
                        </span>
                      </Tooltip>
                    )}
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    {/* Origem */}
                    <div className="lg:col-span-5">
                      <div className="redis-hospital text-sm font-semibold flex items-center">
                        {s.origem.hospital_nome}
                        <ConfidenceTooltip confianca={s.origem.confianca} />
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs" style={{ color: 'var(--text2)' }}>{s.origem.cir}</span>
                        <Tooltip text={PRESSAO_EXPLICACAO[s.origem.pressao_status]}>
                          <span className="text-xs cursor-help" style={{ color: PRESSAO_COLOR[s.origem.pressao_status] }}>
                            {s.origem.pressao}×
                          </span>
                        </Tooltip>
                        <span className="text-xs" style={{ color: 'var(--text2)' }}>
                          {s.origem.municipio}
                        </span>
                      </div>
                      <div className="text-xs mt-1" style={{ color: 'var(--text2)' }}>
                        {s.origem.fila_atual} na fila · {s.especialidade}
                      </div>
                    </div>

                    {/* Arrow e quantidade */}
                    <div className="lg:col-span-2 flex flex-col items-center justify-center">
                      <div className="text-2xl" style={{ color: prioridade.color }}>→</div>
                      <Tooltip text={`${s.qtd_sugerida} pacientes serão transferidos para aliviar a pressão`}>
                        <div className="text-sm font-bold font-mono cursor-help" style={{ color: prioridade.color }}>
                          {s.qtd_sugerida} pacientes
                        </div>
                      </Tooltip>
                      <Tooltip text={`Redução estimada de ${s.reducao_espera_dias} dias na fila de espera`}>
                        <div className="text-xs cursor-help" style={{ color: 'var(--text2)' }}>
                          ↓ {s.reducao_espera_dias}d espera
                        </div>
                      </Tooltip>
                    </div>

                    {/* Destino */}
                    <div className="lg:col-span-5">
                      <div className="redis-hospital text-sm font-semibold">{s.destino.hospital_nome}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs" style={{ color: 'var(--text2)' }}>{s.destino.cir}</span>
                        <Tooltip text={PRESSAO_EXPLICACAO[s.destino.pressao_status]}>
                          <span className="text-xs cursor-help" style={{ color: PRESSAO_COLOR[s.destino.pressao_status] }}>
                            {s.destino.pressao}×
                          </span>
                        </Tooltip>
                        {s.destino.tipo === 'particular' && (
                          <Tooltip text="Hospital particular contratado pela SESA">
                            <span className="text-xs" style={{ color: 'var(--yellow)' }}>★ particular</span>
                          </Tooltip>
                        )}
                        <span className="text-xs" style={{ color: 'var(--text2)' }}>
                          {s.destino.municipio}
                        </span>
                      </div>
                      <Tooltip text="Capacidade livre considerando fila atual e transferências já aprovadas este mês">
                        <div className="text-xs mt-1 cursor-help" style={{ color: 'var(--text2)' }}>
                          {s.capacidade_livre} vagas livres
                        </div>
                      </Tooltip>
                      <Tooltip text="Simulado: R$ 1.500 fixo por AIH (não é valor pago pelo SUS)">
                        <div className="text-xs mt-1 font-mono cursor-help" style={{ color: 'var(--accent2)' }}>
                          AIH (simulado): R$ {s.aih_estimada.toLocaleString('pt-BR')}
                        </div>
                      </Tooltip>

                      {/* Botões de ação */}
                      {podeAprovar && !noEscopo && !isAprovada && !isRecusada && (
                        <div className="text-xs mt-3" style={{ color: 'var(--text2)' }}>
                          Fora da {escopoAprovacao}: aprovação pela SESA
                        </div>
                      )}
                      {noEscopo && !isAprovada && !isRecusada && !modoSelecao && (
                        <div className="flex gap-2 mt-3">
                          <button 
                            className="btn-green text-xs px-3 py-1.5"
                            onClick={(e) => {
                              e.stopPropagation()
                              setModalSugestao(s)
                            }}
                          >
                            ✅ Aprovar
                          </button>
                          <button 
                            className="btn-red text-xs px-3 py-1.5"
                            onClick={(e) => {
                              e.stopPropagation()
                              setRecusadas(p => new Set(Array.from(p).concat(rowId)))
                            }}
                          >
                            ✕ Recusar
                          </button>
                        </div>
                      )}
                      {(isAprovada) && (
                        <div className="text-xs mt-2" style={{ color: 'var(--accent2)', fontWeight: 600 }}>✅ Aprovado</div>
                      )}
                      {(isRecusada) && (
                        <div className="text-xs mt-2" style={{ color: 'var(--red)' }}>✕ Recusado</div>
                      )}
                    </div>
                  </div>

                  {/* Métricas de impacto */}
                  <div className="grid grid-cols-4 gap-2 mt-3 pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
                    <div>
                      <div className="text-[10px]" style={{ color: 'var(--text2)' }}>AIH (simulado)</div>
                      <Tooltip text="Simulado: R$ 1.500 fixo por AIH (não é valor pago pelo SUS)">
                        <div className="text-xs font-mono cursor-help" style={{ color: 'var(--accent)' }}>R$ {s.aih_estimada.toLocaleString('pt-BR')}</div>
                      </Tooltip>
                    </div>
                    <div>
                      <div className="text-[10px]" style={{ color: 'var(--text2)' }}>Multa Evitada (simulado)</div>
                      <Tooltip text="Simulado: R$ 500 fixo por paciente; não há base de multas medida">
                        <div className="text-xs font-mono cursor-help" style={{ color: 'var(--accent2)' }}>R$ {(s.qtd_sugerida * 500).toLocaleString('pt-BR')}</div>
                      </Tooltip>
                    </div>
                    <div>
                      <div className="text-[10px]" style={{ color: 'var(--text2)' }}>Dias Espera</div>
                      <Tooltip text="Estimativa heurística (simulado), não medida">
                        <div className="text-xs font-mono cursor-help" style={{ color: 'var(--yellow)' }}>{s.reducao_espera_dias}d</div>
                      </Tooltip>
                    </div>
                    <div>
                      <div className="text-[10px]" style={{ color: 'var(--text2)' }}>Distância</div>
                      <Tooltip text="Distância entre os hospitais ainda não calculada">
                        <div className="text-xs font-mono cursor-help" style={{ color: 'var(--text2)' }}>{s.distancia_km != null ? `${s.distancia_km}km` : 'n/d'}</div>
                      </Tooltip>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Histórico de aprovações */}
      {aprovadas.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold">📋 Histórico de Aprovações</h2>
              <InfoIcon text="Transferências já aprovadas pela SESA neste mês" />
            </div>
            <span className="badge badge-green">{aprovadas.length} aprovada{aprovadas.length > 1 ? 's' : ''}</span>
          </div>
          
          {/* Gráfico de impacto das aprovações */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <KPICard
              label="Pacientes realocados"
              value={aprovadas.reduce((acc, a) => acc + a.qtd_pacientes, 0)}
              icon="✅"
              color="green"
              tooltip="Total de pacientes já transferidos"
            />

            <KPICard
              label="AIH total (simulado)"
              value={`R$ ${aprovadas.reduce((acc, a) => acc + a.aih_estimada, 0).toLocaleString('pt-BR')}`}
              icon="💰"
              color="blue"
              tooltip="Simulado: R$ 1.500 fixo por AIH"
            />

            <KPICard
              label="Multas evitadas"
              value={`R$ ${aprovadas.reduce((acc, a) => acc + (a.economia_multa || 0), 0).toLocaleString('pt-BR')}`}
              icon="⚖️"
              color="red"
              tooltip="Multas que os hospitais deixaram de pagar"
            />
          </div>

          <table className="table-predmed">
            <thead>
              <tr>
                <th>Protocolo</th>
                <th>Destino</th>
                <th>Especialidade</th>
                <th className="text-right">Pacientes</th>
                <th className="text-right">AIH</th>
                <th className="text-right">Multa evitada</th>
                <th>Hora</th>
              </tr>
            </thead>
            <tbody>
              {aprovadas.map(a => (
                <tr key={a.protocolo}>
                  <td className="font-mono text-xs" style={{ color: 'var(--accent)' }}>{a.protocolo}</td>
                  <td className="text-xs">{a.hospital_destino}</td>
                  <td><span className="badge badge-blue text-[10px]">{a.especialidade}</span></td>
                  <td className="text-right font-mono" style={{ color: 'var(--accent2)' }}>{a.qtd_pacientes}</td>
                  <td className="text-right font-mono text-xs" style={{ color: 'var(--yellow)' }}>R$ {a.aih_estimada.toLocaleString('pt-BR')}</td>
                  <td className="text-right font-mono text-xs" style={{ color: 'var(--red)' }}>R$ {(a.economia_multa || 0).toLocaleString('pt-BR')}</td>
                  <td className="text-xs" style={{ color: 'var(--text2)' }}>{a.data}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de confirmação individual */}
      {modalSugestao && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.75)' }} onClick={() => setModalSugestao(null)}>
          <div className="rounded-2xl p-6 max-w-2xl w-full mx-4" style={{ background: '#0F1E35', border: '1px solid rgba(0,194,255,0.3)' }} onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-1">Confirmar Alocação</h2>
            <p className="text-xs mb-6" style={{ color: 'var(--text2)' }}>Ação da SESA — aprovação definitiva</p>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="p-4 rounded-lg" style={{ background: 'rgba(255,68,68,0.06)', border: '1px solid rgba(255,68,68,0.2)' }}>
                <div className="text-xs mb-2" style={{ color: 'var(--text2)' }}>ORIGEM</div>
                <div className="text-sm font-semibold mb-1">{modalSugestao.origem.hospital_nome}</div>
                <div className="text-xs" style={{ color: 'var(--red)' }}>Pressão {modalSugestao.origem.pressao}×</div>
                <div className="text-xs mt-2" style={{ color: 'var(--text2)' }}>{modalSugestao.origem.fila_atual} pacientes · {modalSugestao.especialidade}</div>
                {modalSugestao.origem.confianca && (
                  <div className="text-xs mt-1" style={{ color: modalSugestao.origem.confianca > 0.8 ? 'var(--accent2)' : 'var(--yellow)' }}>
                    Confiança: {(modalSugestao.origem.confianca * 100).toFixed(0)}%
                  </div>
                )}
              </div>
              <div className="p-4 rounded-lg" style={{ background: 'rgba(0,255,157,0.06)', border: '1px solid rgba(0,255,157,0.2)' }}>
                <div className="text-xs mb-2" style={{ color: 'var(--text2)' }}>DESTINO</div>
                <div className="text-sm font-semibold mb-1">{modalSugestao.destino.hospital_nome}</div>
                <div className="text-xs" style={{ color: 'var(--accent2)' }}>{modalSugestao.capacidade_livre} vagas livres</div>
                <div className="text-xs mt-2" style={{ color: 'var(--text2)' }}>{modalSugestao.destino.cir}</div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-6">
              {[
                { label: 'Pacientes', val: modalSugestao.qtd_sugerida, color: 'var(--accent2)' },
                { label: 'AIH (simulado)', val: `R$ ${modalSugestao.aih_estimada.toLocaleString('pt-BR')}`, color: 'var(--yellow)' },
                { label: 'Multa evitada (simulado)', val: `R$ ${(modalSugestao.qtd_sugerida * 500).toLocaleString('pt-BR')}`, color: 'var(--red)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="p-3 rounded-lg text-center" style={{ background: 'var(--surface2)' }}>
                  <div className="text-xs mb-1" style={{ color: 'var(--text2)' }}>{label}</div>
                  <div className="font-mono font-bold text-sm" style={{ color }}>{val}</div>
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-3">
              <button className="btn-primary px-4 py-2" onClick={() => setModalSugestao(null)}>Cancelar</button>
              <button className="btn-green px-4 py-2" onClick={confirmarAprovacao} disabled={loadingAprovar}>
                {loadingAprovar ? 'Aprovando...' : '✅ Confirmar Aprovação'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de aprovação múltipla */}
      {modalMultiplo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.75)' }} onClick={() => setModalMultiplo(false)}>
          <div className="rounded-2xl p-6 max-w-lg w-full mx-4" style={{ background: '#0F1E35', border: '1px solid rgba(0,194,255,0.3)' }} onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-1">Aprovar {selecionados.size} Transferências</h2>
            <p className="text-xs mb-6" style={{ color: 'var(--text2)' }}>Ação em massa da SESA</p>

            <div className="space-y-2 max-h-60 overflow-y-auto mb-4 p-2" style={{ border: '1px solid var(--border)', borderRadius: 8 }}>
              {Array.from(selecionados).map(idxStr => {
                const s = sugestoesFiltradas[parseInt(idxStr)]
                if (!s) return null
                return (
                  <div key={idxStr} className="text-xs p-2 rounded" style={{ background: 'var(--surface2)' }}>
                    {s.origem.hospital_nome} → {s.destino.hospital_nome} · {s.qtd_sugerida} pacientes
                  </div>
                )
              })}
            </div>

            <div className="grid grid-cols-2 gap-3 mb-6">
              <div className="p-3 rounded-lg text-center" style={{ background: 'var(--surface2)' }}>
                <div className="text-xs" style={{ color: 'var(--text2)' }}>Total pacientes</div>
                <div className="font-mono font-bold" style={{ color: 'var(--accent2)' }}>
                  {Array.from(selecionados).reduce((acc, idx) => acc + (sugestoesFiltradas[parseInt(idx)]?.qtd_sugerida || 0), 0)}
                </div>
              </div>
              <div className="p-3 rounded-lg text-center" style={{ background: 'var(--surface2)' }}>
                <div className="text-xs" style={{ color: 'var(--text2)' }}>AIH total</div>
                <div className="font-mono font-bold" style={{ color: 'var(--yellow)' }}>
                  R$ {Array.from(selecionados).reduce((acc, idx) => acc + (sugestoesFiltradas[parseInt(idx)]?.aih_estimada || 0), 0).toLocaleString('pt-BR')}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button className="btn-primary px-4 py-2" onClick={() => setModalMultiplo(false)}>Cancelar</button>
              <button className="btn-green px-4 py-2" onClick={confirmarAprovacoesMultiplas} disabled={loadingAprovar}>
                {loadingAprovar ? 'Aprovando...' : `✅ Aprovar ${selecionados.size} transferências`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}