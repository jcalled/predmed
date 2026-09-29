import { CheckCircle2, Calculator, FlaskConical, Flag, AlertTriangle } from 'lucide-react'

/**
 * Natureza do número exibido. Regra do projeto (CLAUDE.md): nunca apresentar
 * número simulado/sintético como resultado medido.
 *
 * - medido:        contagem ou cálculo direto sobre dado de fonte (IntegraSUS, SIH, CNES).
 * - estimado:      saída de modelo ou heurística aplicada a dado real.
 * - simulado:      usa parâmetros fixos/sintéticos (ex.: R$ 1.500 por AIH).
 * - meta:          alvo do projeto, não é resultado.
 * - nao_validado:  regra ou modelo ainda sem validação (clínica ou estatística).
 */
export type NaturezaDado = 'medido' | 'estimado' | 'simulado' | 'meta' | 'nao_validado'

const CONFIG: Record<NaturezaDado, { rotulo: string; cor: string; Icone: typeof CheckCircle2; explicacao: string }> = {
  medido:       { rotulo: 'Medido',       cor: 'var(--selo-medido)',      Icone: CheckCircle2,  explicacao: 'Calculado diretamente a partir do dado de origem.' },
  estimado:     { rotulo: 'Estimado',     cor: 'var(--selo-estimado)',    Icone: Calculator,    explicacao: 'Resultado de modelo ou heurística sobre dados reais; tem margem de erro.' },
  simulado:     { rotulo: 'Simulado',     cor: 'var(--selo-simulado)',    Icone: FlaskConical,  explicacao: 'Usa parâmetros fixos ou sintéticos; não é valor observado.' },
  meta:         { rotulo: 'Meta',         cor: 'var(--selo-meta)',        Icone: Flag,          explicacao: 'Alvo do projeto; ainda não é resultado.' },
  nao_validado: { rotulo: 'Não validado', cor: 'var(--selo-naovalidado)', Icone: AlertTriangle, explicacao: 'Regra ou modelo ainda sem validação clínica ou estatística.' },
}

export function explicacaoNatureza(n: NaturezaDado) {
  return CONFIG[n].explicacao
}

export default function SeloDado({ natureza, className = '' }: { natureza: NaturezaDado; className?: string }) {
  const { rotulo, cor, Icone, explicacao } = CONFIG[natureza]
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-2xs font-semibold whitespace-nowrap ${className}`}
      style={{ color: cor, border: `1px solid ${cor}`, background: 'rgba(255,255,255,0.03)' }}
      title={explicacao}
    >
      <Icone size={11} aria-hidden="true" strokeWidth={2.5} />
      <span><span className="sr-only">Natureza do dado: </span>{rotulo}</span>
    </span>
  )
}
