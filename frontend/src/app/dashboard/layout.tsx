'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Menu } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import Sidebar from '@/components/Sidebar'
import Wordmark from '@/components/marca/Wordmark'
import { Carregando } from '@/components/ui/Estados'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [menuAberto, setMenuAberto] = useState(false)
  const botaoMenuRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!loading && !user) router.replace('/login')
  }, [user, loading, router])

  // Ao fechar a gaveta, o foco volta ao botão que a abriu.
  const fecharMenu = useCallback(() => {
    setMenuAberto(aberto => {
      if (aberto) requestAnimationFrame(() => botaoMenuRef.current?.focus())
      return false
    })
  }, [])

  // Se a janela passar para >= lg com a gaveta aberta, fecha (evita body travado).
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const onChange = () => { if (mq.matches) setMenuAberto(false) }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  if (loading || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <Wordmark tamanho="lg" />
        <Carregando mensagem="Carregando PREDMED..." />
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <a href="#conteudo" className="skip-link">Pular para o conteúdo</a>

      {/* Barra superior: só em telas < lg */}
      <header
        className="lg:hidden sticky top-0 z-30 h-topbar flex items-center gap-3 px-3 border-b"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
      >
        <button
          ref={botaoMenuRef}
          type="button"
          className="p-2 rounded-md"
          style={{ color: 'var(--text)' }}
          aria-label="Abrir menu"
          aria-expanded={menuAberto}
          aria-controls="menu-principal"
          onClick={() => setMenuAberto(true)}
        >
          <Menu size={22} aria-hidden="true" />
        </button>
        <Wordmark />
      </header>

      <Sidebar aberta={menuAberto} aoFechar={fecharMenu} />

      <main
        id="conteudo"
        tabIndex={-1}
        className="lg:ml-sidebar min-w-0 min-h-screen focus:outline-none"
        style={{ background: 'var(--bg)' }}
      >
        <div className="p-4 sm:p-6 max-w-screen-xl min-w-0">
          {children}
        </div>
      </main>
    </div>
  )
}
