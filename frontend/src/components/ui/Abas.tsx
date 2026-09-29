'use client'
import { Suspense, useEffect, useRef, type KeyboardEvent, type ReactNode } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import clsx from 'clsx'
import { Carregando } from './Estados'

/* ------------------------------------------------------------------
   Abas acessíveis (padrão WAI-ARIA "tabs", ativação manual por
   Enter/Espaço ou clique; setas movem o foco entre as abas).
   A aba ativa fica na URL (?aba=id) para que links salvos e os
   redirecionamentos das rotas antigas abram a aba certa.
   Só o painel ativo é montado: cada aba busca seus dados ao abrir.
   ------------------------------------------------------------------ */

export interface Aba {
  id: string
  rotulo: string
  icone?: ReactNode
  conteudo: ReactNode
}

interface AbasProps {
  abas: Aba[]
  /** Nome acessível do grupo de abas, ex.: "Seções da previsão de demanda". */
  rotulo: string
  /** Nome do parâmetro de URL (padrão: "aba"). */
  parametro?: string
}

export default function Abas(props: AbasProps) {
  return (
    <Suspense fallback={<Carregando />}>
      <AbasInterno {...props} />
    </Suspense>
  )
}

function AbasInterno({ abas, rotulo, parametro = 'aba' }: AbasProps) {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})

  const pedida = params.get(parametro)
  const ativa = abas.find(a => a.id === pedida) ?? abas[0]

  const selecionar = (id: string) => {
    const novos = new URLSearchParams(params.toString())
    if (id === abas[0]?.id) novos.delete(parametro)
    else novos.set(parametro, id)
    const qs = novos.toString()
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const aoTeclar = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    let alvo: number | null = null
    if (e.key === 'ArrowRight') alvo = (i + 1) % abas.length
    else if (e.key === 'ArrowLeft') alvo = (i - 1 + abas.length) % abas.length
    else if (e.key === 'Home') alvo = 0
    else if (e.key === 'End') alvo = abas.length - 1
    if (alvo === null) return
    e.preventDefault()
    refs.current[abas[alvo].id]?.focus()
  }

  // Em telas estreitas a lista rola na horizontal: mantém a aba ativa visível.
  const idAtiva = ativa?.id
  useEffect(() => {
    if (idAtiva) refs.current[idAtiva]?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [idAtiva])

  if (!ativa) return null

  return (
    <div>
      <div
        role="tablist"
        aria-label={rotulo}
        className="flex gap-1 mb-5 overflow-x-auto border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        {abas.map((aba, i) => {
          const selecionada = aba.id === ativa.id
          return (
            <button
              key={aba.id}
              ref={el => { refs.current[aba.id] = el }}
              type="button"
              role="tab"
              id={`aba-${aba.id}`}
              aria-selected={selecionada}
              aria-controls={`painel-${aba.id}`}
              tabIndex={selecionada ? 0 : -1}
              onClick={() => selecionar(aba.id)}
              onKeyDown={e => aoTeclar(e, i)}
              className={clsx(
                'inline-flex items-center gap-2 px-4 py-2.5 text-sm whitespace-nowrap border-b-2 -mb-px rounded-t-md transition-colors',
                selecionada ? 'font-semibold' : 'hover:bg-white/5',
              )}
              style={selecionada
                ? { color: 'var(--accent)', borderColor: 'var(--accent)' }
                : { color: 'var(--text2)', borderColor: 'transparent' }}
            >
              {aba.icone && <span aria-hidden="true" className="inline-flex">{aba.icone}</span>}
              {aba.rotulo}
            </button>
          )
        })}
      </div>

      <div
        role="tabpanel"
        id={`painel-${ativa.id}`}
        aria-labelledby={`aba-${ativa.id}`}
        tabIndex={0}
        className="rounded-md"
      >
        {ativa.conteudo}
      </div>
    </div>
  )
}
