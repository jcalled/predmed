'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import clsx from 'clsx'

interface NavItem {
  href: string
  icon: string
  label: string
  roles?: string[]  // se definido, só aparece para esses roles
}

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard',                  icon: '📊', label: 'Dashboard' },
  { href: '/dashboard/fila',             icon: '🗂',  label: 'Fila Cirúrgica' },
  { href: '/dashboard/priorizacao',      icon: '🎯', label: 'Priorização' },
  { href: '/dashboard/redistribuicao',   icon: '🗺️',  label: 'Redistribuição' },
  { href: '/dashboard/previsoes',        icon: '📈', label: 'Previsões' },
  {
    label: 'Previsões ML',
    href: '/dashboard/previsoes-ml',
    icon: '📈',
    roles: ['sesa', 'sms', 'hospital_publico', 'hospital_particular']
  },
  { href: '/dashboard/hospitais',        icon: '🏥', label: 'Hospitais' },
  { href: '/dashboard/judicializados',   icon: '⚖️',  label: 'Judicializados' },
  { href: '/dashboard/zerarfilas',       icon: '🚀', label: 'Prog. Zerar Filas', roles: ['sesa', 'sms'] },
  { href: '/dashboard/relatorios',       icon: '📄', label: 'Relatórios' },
  { href: '/dashboard/configuracoes',    icon: '⚙️',  label: 'Configurações', roles: ['hospital_particular', 'sesa', 'sms'] },
]

const ROLE_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  sesa:               { label: 'SESA — Gestor Estadual',    color: 'var(--accent)',  icon: '🏛️' },
  sms:                { label: 'SMS — Gestor Municipal',     color: 'var(--accent3)', icon: '🏙️' },
  hospital_publico:   { label: 'Hospital Público',           color: 'var(--accent2)', icon: '🏥' },
  hospital_particular:{ label: 'Hospital Particular',        color: 'var(--yellow)',  icon: '🏢' },
}

export default function Sidebar() {
  const { user, logout, isSesa, isSms, isGestor, isPublico, isParticular } = useAuth()
  const pathname = usePathname()

  const roleInfo = ROLE_LABELS[user?.role || ''] || ROLE_LABELS.sesa

  const visibleItems = NAV_ITEMS.filter(item =>
    !item.roles || item.roles.includes(user?.role || '')
  )

  return (
    <aside className="fixed left-0 top-0 h-full w-60 flex flex-col z-40" style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}>
      {/* Logo */}
      <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center text-lg flex-shrink-0" style={{ background: 'rgba(0,194,255,0.1)', border: '1px solid rgba(0,194,255,0.2)' }}>
            🧠
          </div>
          <div>
            <div className="text-base font-bold tracking-tight">PREDMED</div>
            <div className="text-xs" style={{ color: 'var(--text2)' }}>eKLICK Healthcare AI</div>
          </div>
        </div>
      </div>

      {/* Perfil */}
      <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)', background: 'rgba(0,0,0,0.15)' }}>
        <div className="flex items-center gap-2 mb-1">
          <span style={{ color: roleInfo.color }}>{roleInfo.icon}</span>
          <span className="text-xs font-semibold" style={{ color: roleInfo.color }}>{roleInfo.label}</span>
        </div>
        <div className="text-xs font-medium text-text1 truncate">{user?.nome}</div>
        <div className="text-xs truncate" style={{ color: 'var(--text2)' }}>{user?.tenant_nome}</div>
        {user?.tenant_cir && (
          <div className="text-xs mt-1 font-mono" style={{ color: 'var(--text2)', fontSize: 10 }}>📍 {user.tenant_cir}</div>
        )}
      </div>

      {/* Navegação */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {visibleItems.map((item) => {
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-all mb-0.5',
                active ? 'font-semibold' : 'hover:bg-white/5'
              )}
              style={active ? {
                background: `rgba(${roleInfo.color === 'var(--accent)' ? '0,194,255' : roleInfo.color === 'var(--accent3)' ? '255,102,0' : '0,255,136'},0.1)`,
                color: roleInfo.color,
                border: `1px solid ${roleInfo.color === 'var(--accent)' ? 'rgba(0,194,255,0.2)' : 'rgba(255,255,255,0.1)'}`,
              } : { color: 'var(--text2)' }}
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Permissões do role */}
      <div className="px-4 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="text-xs mb-2" style={{ color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Permissões
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs" style={{ color: isGestor ? 'var(--accent2)' : 'var(--text2)' }}>
            <span>{isGestor ? '✅' : '⬜'}</span>
            {isSesa ? 'Aprovar transferências (global)' : isSms ? 'Aprovar na sua CIR' : 'Aprovar transferências'}
          </div>
          <div className="flex items-center gap-2 text-xs" style={{ color: isParticular ? 'var(--accent2)' : 'var(--text2)' }}>
            <span>{isParticular ? '✅' : '⬜'}</span> Configurar vagas SUS
          </div>
          <div className="flex items-center gap-2 text-xs" style={{ color: isGestor ? 'var(--accent2)' : 'var(--text2)' }}>
            <span>{isGestor ? '✅' : '⬜'}</span> Importar dados
          </div>
          {isSms && (
            <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--accent3)' }}>
              <span>📍</span> Escopo: CIR {user?.tenant_cir?.replace('CIR ', '')}
            </div>
          )}
        </div>
      </div>

      {/* Logout */}
      <div className="px-4 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
        <button
          onClick={logout}
          className="w-full text-left text-sm py-2 px-3 rounded-lg transition-all"
          style={{ color: 'var(--text2)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text2)')}
        >
          ↪ Sair
        </button>
      </div>
    </aside>
  )
}