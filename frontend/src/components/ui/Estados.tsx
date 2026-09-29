'use client'
import type { ReactNode } from 'react'
import { Inbox, AlertTriangle, Lock, Loader2, RefreshCw } from 'lucide-react'

/* ------------------------------------------------------------------
   Estados de tela: Carregando, EstadoVazio, EstadoErro (inclui "sem
   permissão"). Use-os em vez de mensagens soltas para que toda tela
   tenha os mesmos padrões e anúncios para leitor de tela.
   ------------------------------------------------------------------ */

interface CarregandoProps {
  mensagem?: string
  /** "linhas" desenha um esqueleto de tabela; "compacto" só o indicador. */
  variante?: 'compacto' | 'linhas'
  linhas?: number
}

export function Carregando({ mensagem = 'Carregando...', variante = 'compacto', linhas = 6 }: CarregandoProps) {
  return (
    <div role="status" aria-live="polite" className="py-6">
      <div className="flex items-center justify-center gap-2 text-sm" style={{ color: 'var(--text2)' }}>
        <Loader2 size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
        <span>{mensagem}</span>
      </div>
      {variante === 'linhas' && (
        <div className="mt-4 space-y-2" aria-hidden="true">
          {Array.from({ length: linhas }).map((_, i) => (
            <div key={i} className="h-8 rounded-md animate-pulse" style={{ background: 'var(--surface2)', opacity: 1 - i * 0.12 }} />
          ))}
        </div>
      )}
    </div>
  )
}

interface EstadoVazioProps {
  titulo: string
  descricao?: ReactNode
  /** Ação sugerida, ex.: botão "Limpar filtros". */
  acao?: ReactNode
  icone?: ReactNode
}

export function EstadoVazio({ titulo, descricao, acao, icone }: EstadoVazioProps) {
  return (
    <div className="text-center py-10 px-4" role="status">
      <div className="flex justify-center mb-3" style={{ color: 'var(--text2)' }} aria-hidden="true">
        {icone ?? <Inbox size={32} strokeWidth={1.5} />}
      </div>
      <div className="text-sm font-semibold">{titulo}</div>
      {descricao && <div className="text-sm mt-1 max-w-md mx-auto" style={{ color: 'var(--text2)' }}>{descricao}</div>}
      {acao && <div className="mt-4">{acao}</div>}
    </div>
  )
}

interface EstadoErroProps {
  /** Erro vindo do axios/SWR. Status 403 vira "sem permissão". */
  erro?: unknown
  titulo?: string
  descricao?: string
  aoTentarNovamente?: () => void
}

function statusHttp(erro: unknown): number | undefined {
  return (erro as { response?: { status?: number } } | undefined)?.response?.status
}

export function EstadoErro({ erro, titulo, descricao, aoTentarNovamente }: EstadoErroProps) {
  const status = statusHttp(erro)
  const semPermissao = status === 403
  const semConexao = erro != null && status === undefined

  const tituloFinal = titulo ?? (semPermissao
    ? 'Você não tem permissão para ver estes dados'
    : 'Não foi possível carregar os dados')
  const descricaoFinal = descricao ?? (semPermissao
    ? 'Seu perfil não dá acesso a esta informação. Se precisar, peça acesso ao gestor responsável.'
    : semConexao
      ? 'O servidor não respondeu. Verifique sua conexão e tente novamente.'
      : `O servidor retornou um erro${status ? ` (código ${status})` : ''}. Tente novamente em instantes.`)

  const cor = semPermissao ? 'var(--yellow)' : 'var(--red)'

  return (
    <div className="text-center py-10 px-4" role="alert">
      <div className="flex justify-center mb-3" style={{ color: cor }} aria-hidden="true">
        {semPermissao ? <Lock size={32} strokeWidth={1.5} /> : <AlertTriangle size={32} strokeWidth={1.5} />}
      </div>
      <div className="text-sm font-semibold">{tituloFinal}</div>
      <div className="text-sm mt-1 max-w-md mx-auto" style={{ color: 'var(--text2)' }}>{descricaoFinal}</div>
      {aoTentarNovamente && !semPermissao && (
        <button type="button" className="btn-primary text-xs mt-4 inline-flex items-center gap-2" onClick={aoTentarNovamente}>
          <RefreshCw size={14} aria-hidden="true" /> Tentar novamente
        </button>
      )}
    </div>
  )
}

/**
 * Container de tabela com rolagem horizontal própria (a página não estoura
 * em telas estreitas). Focável e rotulado para quem navega por teclado.
 */
export function TabelaRolavel({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="tabela-rolavel" role="region" aria-label={rotulo} tabIndex={0}>
      {children}
    </div>
  )
}
