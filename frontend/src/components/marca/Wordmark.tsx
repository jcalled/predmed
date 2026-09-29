/**
 * Wordmark PREDMED — "por MedOps".
 * Texto + SVG inline (sem imagens nem fontes externas além da DM Sans já usada).
 * O símbolo é decorativo (aria-hidden); o nome acessível vem do texto.
 */
type Tamanho = 'sm' | 'lg'

const TAMANHOS: Record<Tamanho, { nome: string; sub: string; simbolo: number; gap: string }> = {
  sm: { nome: 'text-base', sub: 'text-2xs', simbolo: 28, gap: 'gap-2.5' },
  lg: { nome: 'text-2xl',  sub: 'text-xs',  simbolo: 40, gap: 'gap-3' },
}

export function SimboloPredmed({ tamanho = 28 }: { tamanho?: number }) {
  // Três barras de fila decrescentes + seta de tendência: "fila que anda".
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
      className="flex-shrink-0"
    >
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="rgba(0,194,255,0.10)" stroke="rgba(0,194,255,0.35)" />
      <rect x="7"  y="9"  width="4" height="15" rx="1.5" fill="var(--accent)" />
      <rect x="14" y="13" width="4" height="11" rx="1.5" fill="var(--accent)" opacity="0.75" />
      <rect x="21" y="17" width="4" height="7"  rx="1.5" fill="var(--accent)" opacity="0.5" />
      <path d="M7 7.5 L25 14" stroke="var(--accent2)" strokeWidth="1.8" strokeLinecap="round" fill="none" />
    </svg>
  )
}

export default function Wordmark({ tamanho = 'sm', className = '' }: { tamanho?: Tamanho; className?: string }) {
  const t = TAMANHOS[tamanho]
  return (
    <span className={`inline-flex items-center ${t.gap} ${className}`}>
      <SimboloPredmed tamanho={t.simbolo} />
      <span className="block leading-none text-left">
        <span className={`block ${t.nome} font-bold tracking-tight text-text1`}>
          PRED<span style={{ color: 'var(--accent)' }}>MED</span>
        </span>
        <span className={`block ${t.sub} mt-1 font-medium`} style={{ color: 'var(--text2)' }}>
          por MedOps
        </span>
      </span>
    </span>
  )
}
