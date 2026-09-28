// components/ui/KPICard.tsx
import { useState } from 'react'
import clsx from 'clsx'

// Componente Tooltip local (ou importado de um arquivo compartilhado)
const Tooltip = ({ children, text }: { children: React.ReactNode, text: string }) => {
  const [show, setShow] = useState(false)
  
  return (
    <div className="relative inline-block" onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      {children}
      {show && (
        <div className="absolute -top-12 left-1/2 transform -translate-x-1/2 z-50 w-44 p-2 rounded-lg text-xs whitespace-normal"
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
              bottom: '-5px',
              left: '50%',
              marginLeft: '-4px'
            }} />
          </div>
        </div>
      )}
    </div>
  )
}

type Color = 'blue' | 'green' | 'red' | 'yellow' | 'default'

interface KPICardProps {
  label: string
  value: string | number
  detail?: string
  color?: Color
  tooltip?: string
  icon?: string
}

const colorMap: Record<Color, { val: string; border: string }> = {
  blue:    { val: 'var(--accent)',  border: 'rgba(0,194,255,0.2)' },
  green:   { val: 'var(--accent2)', border: 'rgba(0,255,157,0.2)' },
  red:     { val: 'var(--red)',     border: 'rgba(255,68,68,0.2)' },
  yellow:  { val: 'var(--yellow)',  border: 'rgba(255,215,0,0.2)' },
  default: { val: 'var(--text1)',   border: 'var(--border)' },
}

export default function KPICard({ label, value, detail, color = 'default', icon, tooltip }: KPICardProps) {
  const { val, border } = colorMap[color]
  
  const content = (
    <div className="kpi-card" style={{ borderColor: border }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text2)', letterSpacing: '0.5px' }}>
          {icon && <span className="mr-1">{icon}</span>}
          {label}
        </span>
        {tooltip && (
          <span className="w-4 h-4 rounded-full text-xs flex items-center justify-center" 
            style={{ border: '1px solid var(--text2)', color: 'var(--text2)', fontSize: 10 }}>
            ?
          </span>
        )}
      </div>
      <div className="text-3xl font-bold font-mono" style={{ color: val }}>
        {typeof value === 'number' ? value.toLocaleString('pt-BR') : value}
      </div>
      {detail && <div className="text-xs mt-1" style={{ color: 'var(--text2)' }}>{detail}</div>}
    </div>
  )

  // Se tiver tooltip, envolve com o componente Tooltip customizado
  if (tooltip) {
    return (
      <Tooltip text={tooltip}>
        {content}
      </Tooltip>
    )
  }

  return content
}