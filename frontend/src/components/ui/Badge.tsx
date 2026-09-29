import type { ReactNode } from 'react'

export type BadgeTom = 'vermelho' | 'laranja' | 'amarelo' | 'azul' | 'verde' | 'cinza'

const CLASSE: Record<BadgeTom, string> = {
  vermelho: 'badge-red',
  laranja:  'badge-orange',
  amarelo:  'badge-yellow',
  azul:     'badge-blue',
  verde:    'badge-green',
  cinza:    'badge-gray',
}

interface BadgeProps {
  tom?: BadgeTom
  /** Ícone opcional (lucide-react). É decorativo: o texto precisa bastar sozinho. */
  icone?: ReactNode
  /** Texto completo para leitores de tela quando o rótulo visível é abreviado (ex.: "A1"). */
  rotuloAcessivel?: string
  title?: string
  className?: string
  children: ReactNode
}

/**
 * Badge de status. Nunca comunique só pela cor (WCAG 1.4.1):
 * o texto do badge precisa dizer o estado.
 */
export default function Badge({ tom = 'cinza', icone, rotuloAcessivel, title, className = '', children }: BadgeProps) {
  return (
    <span className={`badge ${CLASSE[tom]} ${className}`} title={title}>
      {icone && <span aria-hidden="true" className="inline-flex">{icone}</span>}
      {rotuloAcessivel ? (
        <>
          <span aria-hidden="true">{children}</span>
          <span className="sr-only">{rotuloAcessivel}</span>
        </>
      ) : children}
    </span>
  )
}

/* ---------- SWALIS ---------- */

const SWALIS_TOM: Record<string, BadgeTom> = {
  'Categoria A1': 'vermelho',
  'Categoria A2': 'laranja',
  'Categoria B':  'amarelo',
  'Categoria C':  'azul',
  'Categoria D':  'cinza',
}

export const SWALIS_DESCRICAO: Record<string, string> = {
  'Categoria A1': 'A1 — risco imediato',
  'Categoria A2': 'A2 — alta prioridade',
  'Categoria B':  'B — prioridade intermediária',
  'Categoria C':  'C — baixa prioridade',
  'Categoria D':  'D — sem limite de tempo definido',
  'Não Informada': 'Categoria não informada',
}

export const SWALIS_CATEGORIAS = ['Categoria A1', 'Categoria A2', 'Categoria B', 'Categoria C', 'Categoria D', 'Não Informada']

export function swalisTom(categoria?: string | null): BadgeTom {
  return (categoria && SWALIS_TOM[categoria]) || 'cinza'
}

/** Badge SWALIS: rótulo curto visível ("A1"), descrição completa para leitor de tela. */
export function BadgeSwalis({ categoria }: { categoria?: string | null }) {
  const curto = categoria ? categoria.replace('Categoria ', '') : '—'
  const desc = (categoria && SWALIS_DESCRICAO[categoria]) || 'Categoria não informada'
  return (
    <Badge tom={swalisTom(categoria)} rotuloAcessivel={`SWALIS ${desc}`} title={desc}>
      {curto === 'Não Informada' ? 'N/I' : curto}
    </Badge>
  )
}
