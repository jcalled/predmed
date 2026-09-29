'use client'
import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Wordmark from '@/components/marca/Wordmark'

const DEMO_USERS = [
  { label: '🏛️ SESA (Secretaria)', email: 'sesa@predmed.com', role: 'Gestor Estadual — vê tudo, aprova transferências' },
  { label: '🏙️ SMS Sobral (Secretaria Municipal)', email: 'sms@predmed.com', role: 'Gestor CIR Sobral — aprova redistribuições na sua CIR' },
  { label: '🏥 Hospital Público', email: 'hgf@predmed.com',   role: 'HGF — leitura, fila do próprio hospital' },
  { label: '🏢 Hospital Particular', email: 'particular@predmed.com', role: 'São Raimundo — configura vagas SUS' },
]

// Atalhos de demonstração: só em `next dev` ou com NEXT_PUBLIC_MOSTRAR_DEMO=1.
// A senha de demo só funciona com o backend em APP_ENV=dev (ver README).
const MOSTRAR_DEMO =
  process.env.NODE_ENV !== 'production' || process.env.NEXT_PUBLIC_MOSTRAR_DEMO === '1'
const SENHA_DEMO = process.env.NEXT_PUBLIC_SENHA_DEMO || 'predmed123'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      router.replace('/dashboard')
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      setError(axiosErr.response?.data?.detail || 'Email ou senha inválidos')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden" style={{ background: 'var(--bg)' }}>
      {/* Background decorativo */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full opacity-5" style={{ background: 'radial-gradient(circle, #00C2FF, transparent)' }} />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full opacity-5" style={{ background: 'radial-gradient(circle, #00FF9D, transparent)' }} />
      </div>

      <div className="w-full max-w-md mx-4 z-10 animate-slideup">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="mb-4 flex justify-center">
            <Wordmark tamanho="lg" />
            <span className="sr-only"> — acesso</span>
          </h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>IA para Previsão e Redistribuição de Filas Cirúrgicas</p>
        </div>

        {/* Card login */}
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="login-email" className="block text-xs font-medium mb-2" style={{ color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>E-mail</label>
              <input
                id="login-email"
                autoComplete="username"
                type="email"
                className="input-dark"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                autoFocus
              />
            </div>
            <div>
              <label htmlFor="login-senha" className="block text-xs font-medium mb-2" style={{ color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Senha</label>
              <input
                id="login-senha"
                autoComplete="current-password"
                type="password"
                className="input-dark"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div role="alert" className="text-sm px-3 py-2 rounded-lg" style={{ background: 'rgba(255,107,107,0.08)', border: '1px solid rgba(255,68,68,0.2)', color: 'var(--red)' }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg font-semibold text-sm transition-all"
              style={{ background: 'rgba(0,194,255,0.15)', border: '1px solid rgba(0,194,255,0.35)', color: 'var(--accent)', opacity: loading ? 0.6 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
            >
              {loading ? 'Entrando...' : 'Entrar no PREDMED'}
            </button>
          </form>
        </div>

        {/* Demo users (somente desenvolvimento) */}
        {MOSTRAR_DEMO && (
        <div className="mt-6">
          <p className="text-xs text-center mb-3" style={{ color: 'var(--text2)' }}>Usuários de demonstração (ambiente de desenvolvimento) — senha: <span className="font-mono" style={{ color: 'var(--accent)' }}>{SENHA_DEMO}</span></p>
          <div className="space-y-2">
            {DEMO_USERS.map(u => (
              <button
                key={u.email}
                type="button"
                onClick={() => { setEmail(u.email); setPassword(SENHA_DEMO) }}
                className="w-full text-left px-4 py-3 rounded-lg transition-all"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <div className="text-sm font-medium text-text1">{u.label}</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--text2)' }}>{u.role}</div>
              </button>
            ))}
          </div>
        </div>
        )}

        <p className="text-center text-xs mt-6" style={{ color: 'var(--text2)' }}>
          Programa Centelha 3 — FUNCAP/CE · MVP local
        </p>
      </div>
    </div>
  )
}
