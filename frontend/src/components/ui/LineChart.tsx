'use client'

import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

interface LineChartProps {
  data: any[]
  xKey: string
  yKey: string
  color?: string
  title?: string
  tooltip?: string
  height?: number
}

export default function LineChart({ 
  data, 
  xKey, 
  yKey, 
  color = 'var(--accent)',
  title,
  tooltip,
  height = 400
}: LineChartProps) {
  
  // Formata os valores para o tooltip
  const formatYAxis = (value: number) => {
    if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
    return value.toString()
  }

  const formatTooltip = (value: number) => {
    return value.toLocaleString('pt-BR')
  }

  const formatXAxis = (value: string) => {
    // Ex: "2024-01" -> "Jan/24"
    const [ano, mes] = value.split('-')
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    return `${meses[parseInt(mes) - 1]}/${ano.slice(2)}`
  }

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div
          className="p-3 rounded-lg shadow-lg"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text1)'
          }}
        >
          <p className="text-xs mb-1" style={{ color: 'var(--text2)' }}>
            {label}
          </p>
          <p className="text-sm font-bold" style={{ color: payload[0].color }}>
            {payload[0].name}: {formatTooltip(payload[0].value)} pacientes
          </p>
          {tooltip && (
            <p className="text-xs mt-1" style={{ color: 'var(--text2)' }}>
              {tooltip}
            </p>
          )}
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full">
      {title && (
        <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text1)' }}>
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsLineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="var(--border)" 
            opacity={0.3}
          />
          <XAxis 
            dataKey={xKey}
            tickFormatter={formatXAxis}
            stroke="var(--text2)"
            tick={{ fill: 'var(--text2)', fontSize: 12 }}
          />
          <YAxis 
            tickFormatter={formatYAxis}
            stroke="var(--text2)"
            tick={{ fill: 'var(--text2)', fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ color: 'var(--text2)' }}
            formatter={(value) => <span style={{ color: 'var(--text2)' }}>{value}</span>}
          />
          <Line
            type="monotone"
            dataKey={yKey}
            name="Fila de pacientes"
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, r: 3 }}
            activeDot={{ r: 6, fill: color }}
          />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  )
}