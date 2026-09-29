'use client'
import { useEffect, useState } from 'react'
import { LineChart as IconeLinha, ClipboardCheck, CalendarRange } from 'lucide-react'
import Abas, { type Aba } from '@/components/ui/Abas'
import PrevisaoLinear from '@/components/telas/PrevisaoLinear'
import PrevisaoHoltWinters from '@/components/telas/PrevisaoHoltWinters'
import AbaValidacaoModelo from '@/components/telas/AbaValidacaoModelo'
import AbaSazonalidade from '@/components/telas/AbaSazonalidade'

/*
 * Previsão de demanda — docs/ux/arquitetura-telas.md, item 4. Todos os perfis.
 * Une as antigas Previsões (regressão linear) e Previsões ML (Holt-Winters),
 * a Validação (MAPE) e a sazonalidade que ficava no Analytics.
 */

const MODELOS = [
  { id: 'linear', rotulo: 'Tendência (regressão linear)' },
  { id: 'holt', rotulo: 'Sazonal (Holt-Winters)' },
] as const

function AbaPrevisao() {
  const [modelo, setModelo] = useState<(typeof MODELOS)[number]['id']>('linear')
  // Link antigo /dashboard/previsoes-ml chega com ?modelo=holt
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('modelo') === 'holt') setModelo('holt')
  }, [])
  return (
    <div>
      <fieldset className="mb-5">
        <legend className="text-xs mb-2" style={{ color: 'var(--text2)' }}>Modelo de previsão</legend>
        <div className="inline-flex flex-wrap rounded-lg p-1 gap-1" style={{ background: 'var(--surface2)', border: '1px solid var(--border-strong)' }}>
          {MODELOS.map(m => {
            const ativo = modelo === m.id
            return (
              <label
                key={m.id}
                className="px-3 py-1.5 rounded-md text-sm cursor-pointer has-[:focus-visible]:outline has-[:focus-visible]:outline-2"
                style={ativo ? { background: 'rgba(0,194,255,0.15)', color: 'var(--accent)', fontWeight: 600 } : { color: 'var(--text2)' }}
              >
                <input type="radio" name="modelo-previsao" value={m.id} checked={ativo} onChange={() => setModelo(m.id)} className="sr-only" />
                {m.rotulo}
              </label>
            )
          })}
        </div>
      </fieldset>
      {modelo === 'linear' ? <PrevisaoLinear /> : <PrevisaoHoltWinters />}
    </div>
  )
}

export default function PrevisaoDemandaPage() {
  const abas: Aba[] = [
    { id: 'previsao', rotulo: 'Previsão', icone: <IconeLinha size={16} />, conteudo: <AbaPrevisao /> },
    { id: 'validacao', rotulo: 'Validação do modelo', icone: <ClipboardCheck size={16} />, conteudo: <AbaValidacaoModelo /> },
    { id: 'sazonalidade', rotulo: 'Sazonalidade', icone: <CalendarRange size={16} />, conteudo: <AbaSazonalidade /> },
  ]

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">Previsão de demanda</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Evolução esperada da fila cirúrgica por especialidade. As projeções ainda usam série histórica simulada
          e não foram validadas contra a fila real; confira a aba Validação do modelo.
        </p>
      </div>
      <Abas abas={abas} rotulo="Seções da previsão de demanda" />
    </div>
  )
}
