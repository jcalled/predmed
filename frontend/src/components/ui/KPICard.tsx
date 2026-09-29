'use client'
// components/ui/KPICard.tsx
import { useId, useState } from 'react'
import { HelpCircle } from 'lucide-react'
import SeloDado, { type NaturezaDado } from './SeloDado'

type Color = 'blue' | 'green' | 'red' | 'yellow' | 'default'

interface KPICardProps {
  label: string
  value: string | number
  detail?: string
  color?: Color
  /** Explicação do indicador. Acessível por mouse, teclado e leitor de tela. */
  tooltip?: string
  /** Ícone legado (emoji). Tratado como decorativo. */
  icon?: string
  /**
   * Natureza do número: medido / estimado / simulado / meta / nao_validado.
   * Obrigatório na prática para números que não sejam contagem direta da fonte.
   */
  status?: NaturezaDado
  /** Fonte e/ou data de atualização, ex.: "IntegraSUS · 27/09/2026". */
  fonte?: string
  /** Mostra esqueleto no lugar do valor enquanto os dados carregam. */
  carregando?: boolean
}

const colorMap: Record<Color, { val: string; border: string }> = {
  blue:    { val: 'var(--accent)',  border: 'rgba(0,194,255,0.2)' },
  green:   { val: 'var(--accent2)', border: 'rgba(0,255,157,0.2)' },
  red:     { val: 'var(--red)',     border: 'rgba(255,107,107,0.25)' },
  yellow:  { val: 'var(--yellow)',  border: 'rgba(255,215,0,0.2)' },
  default: { val: 'var(--text)',    border: 'var(--border)' },
}

export default function KPICard({
  label, value, detail, color = 'default', icon, tooltip, status, fonte, carregando = false,
}: KPICardProps) {
  const { val, border } = colorMap[color]
  const [ajudaAberta, setAjudaAberta] = useState(false)
  const idAjuda = useId()

  // Valores textuais longos ("não validado", "não disponível") ficam menores
  // para não quebrar o card em telas estreitas.
  const valorTexto = typeof value === 'number' ? value.toLocaleString('pt-BR') : value
  const valorLongo = typeof value === 'string' && value.length > 10

  return (
    <div className="kpi-card relative h-full flex flex-col" style={{ borderColor: border }}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-xs font-semibold uppercase" style={{ color: 'var(--text2)', letterSpacing: '0.5px' }}>
          {icon && <span className="mr-1" aria-hidden="true">{icon}</span>}
          {label}
        </span>
        {tooltip && (
          <span
            className="relative flex-shrink-0"
            onMouseEnter={() => setAjudaAberta(true)}
            onMouseLeave={() => setAjudaAberta(false)}
          >
            <button
              type="button"
              className="rounded-full p-0.5 -m-0.5"
              style={{ color: 'var(--text2)' }}
              aria-label={`Sobre o indicador ${label}`}
              aria-describedby={idAjuda}
              aria-expanded={ajudaAberta}
              onClick={() => setAjudaAberta(a => !a)}
              onFocus={() => setAjudaAberta(true)}
              onBlur={() => setAjudaAberta(false)}
              onKeyDown={e => { if (e.key === 'Escape') setAjudaAberta(false) }}
            >
              <HelpCircle size={16} aria-hidden="true" />
            </button>
            <span
              id={idAjuda}
              role="tooltip"
              className={`${ajudaAberta ? 'block' : 'sr-only'} absolute right-0 top-7 z-30 w-56 p-2.5 rounded-lg text-xs font-normal normal-case`}
              style={ajudaAberta ? {
                background: 'var(--surface3)',
                border: '1px solid rgba(0,194,255,0.3)',
                color: 'var(--text)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                letterSpacing: 0,
              } : undefined}
            >
              {tooltip}
            </span>
          </span>
        )}
      </div>

      {carregando ? (
        <div className="h-9 w-24 rounded-md animate-pulse" style={{ background: 'var(--surface2)' }} aria-hidden="true" />
      ) : (
        <div
          className={`${valorLongo ? 'text-xl' : 'text-2xl sm:text-3xl'} font-bold font-mono break-words`}
          style={{ color: val }}
        >
          {valorTexto}
        </div>
      )}
      {carregando && <span className="sr-only">Carregando {label}</span>}

      {detail && <div className="text-xs mt-1" style={{ color: 'var(--text2)' }}>{detail}</div>}

      {(status || fonte) && (
        <div className="mt-auto pt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
          {status && <SeloDado natureza={status} />}
          {fonte && <span className="text-2xs" style={{ color: 'var(--text2)' }}>{fonte}</span>}
        </div>
      )}
    </div>
  )
}
