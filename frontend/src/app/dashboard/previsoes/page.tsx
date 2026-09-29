'use client'
import { LineChart as IconeLinha, ClipboardCheck, CalendarRange } from 'lucide-react'
import Abas, { type Aba } from '@/components/ui/Abas'
import PrevisaoProducaoSIH from '@/components/telas/PrevisaoProducaoSIH'
import AbaValidacaoModelo from '@/components/telas/AbaValidacaoModelo'
import AbaSazonalidade from '@/components/telas/AbaSazonalidade'

/*
 * Previsão de demanda — docs/ux/arquitetura-telas.md, item 4. Todos os perfis.
 * Aba Previsão: produção cirúrgica SIH (modelo validado fora da amostra; não é a fila).
 * As antigas projeções sobre série histórica simulada (regressão linear e Holt-Winters da fila)
 * saíram da tela em 29/09/2026 (código no histórico do git).
 */

export default function PrevisaoDemandaPage() {
  const abas: Aba[] = [
    { id: 'previsao', rotulo: 'Previsão', icone: <IconeLinha size={16} />, conteudo: <PrevisaoProducaoSIH /> },
    { id: 'validacao', rotulo: 'Validação do modelo', icone: <ClipboardCheck size={16} />, conteudo: <AbaValidacaoModelo /> },
    { id: 'sazonalidade', rotulo: 'Sazonalidade', icone: <CalendarRange size={16} />, conteudo: <AbaSazonalidade /> },
  ]

  return (
    <div className="animate-fadein">
      <div className="mb-4">
        <h1 className="text-xl sm:text-2xl font-bold">Previsão de demanda</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Cirurgias SUS previstas por especialidade em 30, 60 e 90 dias, a partir da produção real registrada no SIH/DATASUS
          (2019 em diante). O alvo é a produção cirúrgica, não a fila: a previsão da fila depende do histórico do IntegraSUS,
          coletado desde 09/2026.
        </p>
      </div>
      <Abas abas={abas} rotulo="Seções da previsão de demanda" />
    </div>
  )
}
