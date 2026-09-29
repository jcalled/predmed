'use client'
import useSWR from 'swr'
import { dashboardApi, filaApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'

function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-text1">{title}</h1>
      {subtitle && <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>{subtitle}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const { user, isSesa, isParticular } = useAuth()
  const { data: kpis, isLoading } = useSWR('dashboard', dashboardApi.get)
  const { data: filaData } = useSWR('fila-stats', () => filaApi.get({ limit: 1 }))

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Dashboard" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="kpi-card animate-pulse" style={{ height: 100 }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fadein">
      <PageHeader
        title="Dashboard"
        subtitle={
          isSesa ? 'Visão geral do Ceará — última importação IntegraSUS + DATASUS' :
          user?.role === 'sms' ? `${user.tenant_nome} — ${user.tenant_cir}` :
          user?.role === 'hospital_publico' ? `${user?.tenant_nome} — ${user?.tenant_cir}` :
          `${user?.tenant_nome} — ${user?.tenant_cir}`
        }
      />

      {/* Alertas */}
      {kpis?.judicializados > 0 && (
        <div className="mb-4 px-4 py-3 rounded-lg flex items-center gap-3 text-sm font-medium" style={{ background: 'rgba(255,68,68,0.06)', border: '1px solid rgba(255,68,68,0.2)', color: 'var(--red)' }}>
          <span className="text-lg">⚖️</span>
          <span><strong>{kpis.judicializados}</strong> casos judicializados ativos exigem atenção imediata</span>
        </div>
      )}

      {/* KPIs principais */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          label="Pacientes na Fila"
          value={kpis?.total_fila ?? '—'}
          detail="Total SUS Ceará"
          color="red"
          tooltip="Total de pacientes aguardando cirurgia eletiva registrados no IntegraSUS (SESA-CE), conforme a última importação de dados."
        />
        <KPICard
          label="Categoria A1 (Urgente)"
          value={kpis?.a1_urgentes ?? '—'}
          detail="Risco imediato"
          color="yellow"
          tooltip="Pacientes SWALIS A1 — prioridade máxima, risco de vida. Incluem oncológicos fora do prazo da Lei 12.732/2012."
        />
        <KPICard
          label="Espera Média Oncologia"
          value={kpis?.espera_media_oncologia_dias != null ? `${kpis.espera_media_oncologia_dias}d` : 'não disponível'}
          detail="Lei 12.732 permite 60d"
          color="red"
          tooltip="Lei 12.732/2012: até 60 dias após o diagnóstico. A fila importada não traz data de entrada confiável, então a espera ainda não é calculada."
        />
        <KPICard
          label="Hospitais Monitorados"
          value={kpis?.hospitais_monitorados ?? '—'}
          detail={`${kpis?.hospitais_ociosos ?? 0} com capacidade ociosa`}
          color="blue"
          tooltip="Hospitais identificados na fila do IntegraSUS com cruzamento de dados do DATASUS."
        />
      </div>

      {/* KPIs secundários */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          label="Casos Judicializados"
          value={kpis?.judicializados ?? '—'}
          detail="Ordens judiciais ativas"
          color="red"
        />
        <KPICard
          label="Sobrecarregados"
          value={kpis?.hospitais_sobrecarregados ?? '—'}
          detail="Índice ≥ 1.5×"
          color="yellow"
        />
        <KPICard
          label="Redução Potencial"
          value={kpis?.reducao_estimada_pct != null ? `${kpis.reducao_estimada_pct}%` : 'não validado'}
          detail={`Meta do projeto: −${kpis?.meta_reducao_espera_pct ?? 40}% na espera`}
          color="green"
          tooltip="Meta da proposta, ainda não comprovada. Não é resultado medido."
        />
        <KPICard
          label="Acurácia do Modelo"
          value={kpis?.acuracia_mape != null ? `${kpis.acuracia_mape}%` : 'não validado'}
          detail={`MAPE — meta do projeto < ${kpis?.meta_mape_pct ?? 15}%`}
          color="blue"
          tooltip="Sem avaliação em dados reais até o momento. A validação por holdout no SIH está na tela Validação."
        />
      </div>

      {/* Especialidades */}
      {kpis?.especialidades_top?.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Fila por Especialidade</h2>
            <span className="badge badge-red">Top {kpis.especialidades_top.length}</span>
          </div>
          <div className="space-y-3">
            {kpis.especialidades_top.map((esp: { nome: string; total: number }, i: number) => {
              const max = kpis.especialidades_top[0]?.total || 1
              const pct = Math.round((esp.total / max) * 100)
              const colors = ['var(--red)', 'var(--accent3)', 'var(--yellow)', 'var(--accent)', 'var(--accent2)']
              const color = colors[i] || 'var(--text2)'
              return (
                <div key={esp.nome}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-text1">{esp.nome}</span>
                    <span className="font-mono" style={{ color }}>{esp.total.toLocaleString('pt-BR')}</span>
                  </div>
                  <div className="pressure-bar-bg">
                    <div className="pressure-bar" style={{ width: `${pct}%`, background: color }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Info de papel do usuário */}
      <div className="card" style={{ borderColor: isParticular ? 'rgba(255,215,0,0.2)' : user?.role === 'sms' ? 'rgba(255,102,0,0.2)' : 'rgba(0,194,255,0.15)' }}>
        <div className="flex items-start gap-3">
          <div className="text-2xl">
            {isSesa ? '🏛️' : user?.role === 'sms' ? '🏙️' : user?.role === 'hospital_publico' ? '🏥' : '🏢'}
          </div>
          <div>
            <div className="font-semibold mb-1">
              {isSesa ? 'Visão Secretaria de Saúde — acesso total' :
               user?.role === 'sms' ? `Secretaria Municipal — ${user.tenant_cir}` :
               user?.role === 'hospital_publico' ? `Hospital Público — ${user.tenant_cir}` :
               `Hospital Particular Credenciado — ${user?.tenant_cir}`}
            </div>
            <div className="text-sm" style={{ color: 'var(--text2)' }}>
              {isSesa && 'Você vê dados de todo o Ceará, pode aprovar redistribuições e importar dados do IntegraSUS.'}
              {user?.role === 'sms' && `Você gerencia hospitais de ${user.tenant_cir}. Pode propor e aprovar redistribuições dentro da sua CIR. Transferências para outras CIRs precisam de aprovação da SESA.`}
              {user?.role === 'hospital_publico' && 'Você vê dados públicos do Ceará e a fila filtrada para o seu hospital. Redistribuições são aprovadas pela SESA ou SMS.'}
              {isParticular && 'Você vê a demanda pública da sua CIR e gerencia suas vagas SUS em Configurações. A SESA ou SMS aloca os pacientes — seu papel é declarar disponibilidade.'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}