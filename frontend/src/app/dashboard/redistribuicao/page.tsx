'use client'
import { Lightbulb, Building2, Rocket } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import Abas, { type Aba } from '@/components/ui/Abas'
import AbaSugestoesRedistribuicao from '@/components/telas/AbaSugestoesRedistribuicao'
import AbaPressaoHospitais from '@/components/telas/AbaPressaoHospitais'
import AbaMutirao from '@/components/telas/AbaMutirao'

/*
 * Redistribuição — docs/ux/arquitetura-telas.md, item 5.
 * - Sugestões: todos os perfis; aprovar só com `pode_aprovar` (SESA).
 * - Pressão por hospital: todos; escopo aplicado por GET /hospitais.
 * - Simulação de mutirão (ex-Prog. Zerar Filas): só SESA e SMS.
 */
export default function RedistribuicaoPage() {
  const { isGestor } = useAuth()

  const abas: Aba[] = [
    { id: 'sugestoes', rotulo: 'Sugestões', icone: <Lightbulb size={16} />, conteudo: <AbaSugestoesRedistribuicao /> },
    { id: 'pressao', rotulo: 'Pressão por hospital', icone: <Building2 size={16} />, conteudo: <AbaPressaoHospitais /> },
  ]
  if (isGestor) {
    abas.push({ id: 'mutirao', rotulo: 'Simulação de mutirão', icone: <Rocket size={16} />, conteudo: <AbaMutirao /> })
  }

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">Redistribuição</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Hospitais com capacidade ociosa estimada (CNES + produção SIH) na mesma CIR para aliviar filas sob pressão.
          A capacidade precisa ser confirmada com o hospital. Apoio à decisão: nenhuma transferência é executada pelo sistema.
        </p>
      </div>
      <Abas abas={abas} rotulo="Seções da redistribuição" />
    </div>
  )
}
