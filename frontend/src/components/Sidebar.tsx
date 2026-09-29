'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef } from 'react'
import clsx from 'clsx'
import {
  LayoutDashboard, ListOrdered, Target, Map as MapIcon, TrendingUp, BrainCircuit,
  Building2, Scale, Rocket, FileText, Settings, LogOut, X, MapPin, Check, Minus,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import Wordmark from '@/components/marca/Wordmark'

interface NavItem {
  href: string
  Icone: LucideIcon
  label: string
  roles?: string[]  // se definido, só aparece para esses roles
}

const NAV_ITEMS: NavItem[] = [
  { href: '/dashboard',                Icone: LayoutDashboard, label: 'Dashboard' },
  { href: '/dashboard/fila',           Icone: ListOrdered,     label: 'Fila Cirúrgica' },
  { href: '/dashboard/priorizacao',    Icone: Target,          label: 'Priorização' },
  { href: '/dashboard/redistribuicao', Icone: MapIcon,         label: 'Redistribuição' },
  { href: '/dashboard/previsoes',      Icone: TrendingUp,      label: 'Previsões' },
  { href: '/dashboard/previsoes-ml',   Icone: BrainCircuit,    label: 'Previsões ML', roles: ['sesa', 'sms', 'hospital_publico', 'hospital_particular'] },
  { href: '/dashboard/hospitais',      Icone: Building2,       label: 'Hospitais' },
  { href: '/dashboard/judicializados', Icone: Scale,           label: 'Judicializados' },
  { href: '/dashboard/zerarfilas',     Icone: Rocket,          label: 'Prog. Zerar Filas', roles: ['sesa', 'sms'] },
  { href: '/dashboard/relatorios',     Icone: FileText,        label: 'Relatórios' },
  { href: '/dashboard/configuracoes',  Icone: Settings,        label: 'Configurações', roles: ['hospital_particular', 'sesa', 'sms'] },
]

const ROLE_LABELS: Record<string, { label: string; color: string; rgb: string }> = {
  sesa:                { label: 'SESA — Gestor Estadual', color: 'var(--accent)',  rgb: '0,194,255' },
  sms:                 { label: 'SMS — Gestor Municipal', color: 'var(--accent3)', rgb: '255,107,53' },
  hospital_publico:    { label: 'Hospital Público',       color: 'var(--accent2)', rgb: '0,255,157' },
  hospital_particular: { label: 'Hospital Particular',    color: 'var(--yellow)',  rgb: '255,215,0' },
}

interface SidebarProps {
  /** Em telas < lg a barra vira gaveta (drawer). */
  aberta: boolean
  aoFechar: () => void
}

const SELETOR_FOCAVEL = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'

export default function Sidebar({ aberta, aoFechar }: SidebarProps) {
  const { user, logout, isSesa, isSms, isGestor, isParticular } = useAuth()
  const pathname = usePathname()
  const ref = useRef<HTMLElement>(null)
  const botaoFecharRef = useRef<HTMLButtonElement>(null)

  const roleInfo = ROLE_LABELS[user?.role || ''] || ROLE_LABELS.sesa
  const visibleItems = NAV_ITEMS.filter(item => !item.roles || item.roles.includes(user?.role || ''))

  // Gaveta: foco inicial no botão fechar, Esc fecha, Tab fica preso dentro.
  useEffect(() => {
    if (!aberta) return
    botaoFecharRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); aoFechar(); return }
      if (e.key !== 'Tab' || !ref.current) return
      const focaveis = Array.from(ref.current.querySelectorAll<HTMLElement>(SELETOR_FOCAVEL))
        .filter(el => el.offsetParent !== null)
      if (focaveis.length === 0) return
      const primeiro = focaveis[0]
      const ultimo = focaveis[focaveis.length - 1]
      if (e.shiftKey && document.activeElement === primeiro) { e.preventDefault(); ultimo.focus() }
      else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primeiro.focus() }
    }
    document.addEventListener('keydown', onKey)
    const overflowAnterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflowAnterior
    }
  }, [aberta, aoFechar])

  const permissoes = [
    { ok: isGestor, texto: isSesa ? 'Aprovar transferências (global)' : isSms ? 'Aprovar na sua CIR' : 'Aprovar transferências' },
    { ok: isParticular, texto: 'Configurar vagas SUS' },
    { ok: isGestor, texto: 'Importar dados' },
  ]

  return (
    <>
      {/* Fundo escurecido da gaveta (só < lg) */}
      <div
        className={clsx('fixed inset-0 z-40 bg-black/60 lg:hidden transition-opacity', aberta ? 'opacity-100' : 'opacity-0 pointer-events-none')}
        aria-hidden="true"
        onClick={aoFechar}
      />

      <aside
        ref={ref}
        id="menu-principal"
        aria-label="Menu principal"
        {...(aberta ? { role: 'dialog', 'aria-modal': true } : {})}
        className={clsx(
          'fixed left-0 top-0 h-full w-sidebar max-w-[85vw] flex flex-col z-50 transition-transform duration-200',
          'lg:translate-x-0 lg:z-30',
          aberta ? 'translate-x-0' : '-translate-x-full invisible lg:visible',
        )}
        style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}
      >
        {/* Marca */}
        <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
          <Link href="/dashboard" aria-label="PREDMED por MedOps — página inicial" className="rounded-md">
            <Wordmark />
          </Link>
          <button
            ref={botaoFecharRef}
            type="button"
            className="lg:hidden p-2 -mr-2 rounded-md"
            style={{ color: 'var(--text2)' }}
            onClick={aoFechar}
            aria-label="Fechar menu"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {/* Perfil */}
        <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)', background: 'rgba(0,0,0,0.15)' }}>
          <div className="text-xs font-semibold mb-1" style={{ color: roleInfo.color }}>{roleInfo.label}</div>
          <div className="text-xs font-medium text-text1 truncate">{user?.nome}</div>
          <div className="text-xs truncate" style={{ color: 'var(--text2)' }}>{user?.tenant_nome}</div>
          {user?.tenant_cir && (
            <div className="text-2xs mt-1 font-mono flex items-center gap-1" style={{ color: 'var(--text2)' }}>
              <MapPin size={11} aria-hidden="true" /> {user.tenant_cir}
            </div>
          )}
        </div>

        {/* Navegação */}
        <nav className="flex-1 py-3 overflow-y-auto" aria-label="Seções">
          <ul>
            {visibleItems.map(({ href, Icone, label }) => {
              const active = pathname === href
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={aoFechar}
                    aria-current={active ? 'page' : undefined}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-colors mb-0.5 border',
                      active ? 'font-semibold' : 'border-transparent hover:bg-white/5 hover:text-text1',
                    )}
                    style={active ? {
                      background: `rgba(${roleInfo.rgb},0.1)`,
                      color: roleInfo.color,
                      borderColor: `rgba(${roleInfo.rgb},0.3)`,
                    } : { color: 'var(--text2)' }}
                  >
                    <Icone size={18} aria-hidden="true" className="flex-shrink-0" />
                    <span>{label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Permissões do perfil */}
        <div className="px-4 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
          <div className="text-2xs mb-2 uppercase" style={{ color: 'var(--text2)', letterSpacing: '0.5px' }} id="titulo-permissoes">
            Permissões
          </div>
          <ul className="space-y-1" aria-labelledby="titulo-permissoes">
            {permissoes.map(p => (
              <li key={p.texto} className="flex items-center gap-2 text-xs" style={{ color: p.ok ? 'var(--accent2)' : 'var(--text2)' }}>
                {p.ok ? <Check size={13} aria-hidden="true" /> : <Minus size={13} aria-hidden="true" />}
                <span className="sr-only">{p.ok ? 'Permitido:' : 'Não permitido:'}</span>
                {p.texto}
              </li>
            ))}
            {isSms && (
              <li className="flex items-center gap-2 text-xs" style={{ color: 'var(--accent3)' }}>
                <MapPin size={13} aria-hidden="true" /> Escopo: CIR {user?.tenant_cir?.replace('CIR ', '')}
              </li>
            )}
          </ul>
        </div>

        {/* Sair */}
        <div className="px-4 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            type="button"
            onClick={logout}
            className="w-full flex items-center gap-2 text-left text-sm py-2 px-3 rounded-lg transition-colors hover:bg-white/5 hover:text-red"
            style={{ color: 'var(--text2)' }}
          >
            <LogOut size={16} aria-hidden="true" /> Sair
          </button>
        </div>
      </aside>
    </>
  )
}
