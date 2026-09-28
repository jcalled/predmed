'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  useEffect(() => {
    const token = localStorage.getItem('predmed_token')
    router.replace(token ? '/dashboard' : '/login')
  }, [router])
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-text2 text-sm">Carregando...</div>
    </div>
  )
}
