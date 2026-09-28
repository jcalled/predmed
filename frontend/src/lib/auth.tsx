'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi } from './api'

export type UserRole = 'sesa' | 'sms' | 'hospital_publico' | 'hospital_particular'

export interface AuthUser {
  id: number
  nome: string
  email: string
  role: UserRole
  tenant_id: number
  tenant_nome: string
  tenant_cir: string
}

interface AuthCtx {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isSesa: boolean
  isSms: boolean
  isGestor: boolean   // SESA ou SMS
  isPublico: boolean
  isParticular: boolean
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('predmed_user')
    if (stored) {
      try { setUser(JSON.parse(stored)) } catch {}
    }
    setLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    const data = await authApi.login(email, password)
    localStorage.setItem('predmed_token', data.access_token)
    localStorage.setItem('predmed_user', JSON.stringify(data.user))
    setUser(data.user)
  }

  const logout = () => {
    localStorage.removeItem('predmed_token')
    localStorage.removeItem('predmed_user')
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <Ctx.Provider value={{
      user, loading, login, logout,
      isSesa: user?.role === 'sesa',
      isSms: user?.role === 'sms',
      isGestor: user?.role === 'sesa' || user?.role === 'sms',
      isPublico: user?.role === 'hospital_publico',
      isParticular: user?.role === 'hospital_particular',
    }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}