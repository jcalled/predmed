'use client'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

/* Histórico observado (SIH) + previsão com faixa de 80%. Carregado sem SSR. */

interface Props {
  historico: { competencia: string; aihs: number }[]
  previsao: {
    competencia: string
    previsto: number
    intervalo_80_inferior: number | null
    intervalo_80_superior: number | null
  }[]
}

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const rotuloMes = (c: string) => {
  const [a, m] = c.split('-')
  return `${MESES[parseInt(m, 10) - 1]}/${a.slice(2)}`
}
const num = (v: number) => v.toLocaleString('pt-BR')

export default function GraficoPrevisaoProducao({ historico, previsao }: Props) {
  const ultimo = historico[historico.length - 1]
  const dados = [
    ...historico.map(h => ({ mes: h.competencia, observado: h.aihs })),
    ...previsao.map(p => ({
      mes: p.competencia,
      previsto: p.previsto,
      faixa: [p.intervalo_80_inferior ?? p.previsto, p.intervalo_80_superior ?? p.previsto] as [number, number],
    })),
  ]
  // liga a linha prevista ao último mês observado
  if (ultimo) {
    const i = dados.findIndex(d => d.mes === ultimo.competencia)
    if (i >= 0) Object.assign(dados[i], { previsto: ultimo.aihs, faixa: [ultimo.aihs, ultimo.aihs] })
  }

  return (
    <div role="img" aria-label="Gráfico da produção cirúrgica observada nos últimos 24 meses e prevista para 30, 60 e 90 dias com intervalo de 80%">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={dados} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
          <XAxis dataKey="mes" tickFormatter={rotuloMes} stroke="var(--text2)" tick={{ fill: 'var(--text2)', fontSize: 12 }} />
          <YAxis tickFormatter={v => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v))} stroke="var(--text2)" tick={{ fill: 'var(--text2)', fontSize: 12 }} />
          <Tooltip
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
            labelFormatter={l => rotuloMes(String(l))}
            formatter={(v, nome) =>
              Array.isArray(v) ? [`${num(Number(v[0]))} – ${num(Number(v[1]))}`, 'Intervalo 80%'] : [num(Number(v ?? 0)), String(nome)]}
          />
          <Legend wrapperStyle={{ color: 'var(--text2)', fontSize: 12 }} />
          <Area type="monotone" dataKey="faixa" name="Intervalo 80% (estimado)" stroke="none" fill="var(--accent)" fillOpacity={0.15} isAnimationActive={false} />
          <Line type="monotone" dataKey="observado" name="Observado SIH (medido)" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="previsto" name="Previsão (estimado)" stroke="var(--accent2)" strokeWidth={2} strokeDasharray="6 4" dot isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
