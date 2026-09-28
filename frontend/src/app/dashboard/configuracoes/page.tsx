'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { configApi, adminApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

interface Vaga {
  id: number
  especialidade: string
  vagas_mes: number
  aceito_mes: number
  disponivel: number
  ativo: boolean
  lotado: boolean
}

export default function ConfiguracoesPage() {
  const { isSesa, isParticular, user } = useAuth()
  const { data, isLoading, mutate } = useSWR(
    isParticular ? 'config-vagas' : null,
    configApi.getVagas
  )
  const [saving, setSaving] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [uploading, setUploading] = useState<string | null>(null)

  const updateVaga = async (vaga: Vaga, novoValor: number, novoAtivo: boolean) => {
    setSaving(vaga.especialidade)
    try {
      await configApi.updateVaga({ especialidade: vaga.especialidade, vagas_mes: novoValor, ativo: novoAtivo })
      setSaved(vaga.especialidade)
      mutate()
      setTimeout(() => setSaved(null), 2000)
    } catch { /* */ }
    setSaving(null)
  }

  const handleImport = async (tipo: 'integrasus' | 'datasus', file: File) => {
    setUploading(tipo)
    try {
      if (tipo === 'integrasus') {
        const r = await adminApi.importIntegrasus(file)
        alert(`✅ IntegraSUS importado: ${r.pacientes_importados.toLocaleString('pt-BR')} pacientes`)
      } else {
        const r = await adminApi.importDataSus(file)
        alert(`✅ DATASUS importado: ${r.hospitais_importados} hospitais`)
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert('Erro: ' + (err.response?.data?.detail || 'Falha no import'))
    }
    setUploading(null)
  }

  return (
    <div className="animate-fadein max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Configurações</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>Parâmetros do sistema, integrações e alertas</p>
      </div>

      {/* ── VAGAS SUS (Particular) ──────────────────────── */}
      {isParticular && (
        <div className="card mb-6" style={{ borderColor: 'rgba(0,255,157,0.2)' }}>
          <h2 className="text-base font-semibold mb-1" style={{ color: 'var(--accent2)' }}>
            🏥 Hospital Particular — Oferta de Vagas SUS
          </h2>
          <p className="text-xs mb-4" style={{ color: 'var(--text2)' }}>
            Configure quantas vagas cirúrgicas por mês você disponibiliza para pacientes do SUS por especialidade.
            A SESA vê essas vagas no mapa de redistribuição e aloca os pacientes. Você nunca recebe mais do que o limite aqui configurado.
          </p>

          {/* Status credenciamento */}
          <div className="flex items-center gap-3 mb-4 px-4 py-3 rounded-lg" style={{ background: 'rgba(0,255,157,0.05)', border: '1px solid rgba(0,255,157,0.2)' }}>
            <span className="text-lg">✅</span>
            <div>
              <div className="text-sm font-semibold" style={{ color: 'var(--accent2)' }}>Credenciado — {user?.tenant_cir}</div>
              <div className="text-xs" style={{ color: 'var(--text2)' }}>{user?.tenant_nome} · AIH habilitada · Chamamento Público nº 04/2025</div>
            </div>
          </div>

          {isLoading ? (
            <div className="text-sm" style={{ color: 'var(--text2)' }}>Carregando vagas...</div>
          ) : (
            <table className="table-predmed">
              <thead>
                <tr>
                  <th>Especialidade</th>
                  <th className="text-center">Vagas/mês</th>
                  <th className="text-center">Aceito</th>
                  <th className="text-center">Disponível</th>
                  <th className="text-center">Ocupação</th>
                  <th className="text-center">Ativo</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(data?.vagas || []).map((v: Vaga) => {
                  const pct = v.vagas_mes > 0 ? Math.round((v.aceito_mes / v.vagas_mes) * 100) : 0
                  const isSav = saving === v.especialidade
                  const isSvd = saved === v.especialidade
                  return (
                    <tr key={v.especialidade}>
                      <td className="font-medium">{v.especialidade}</td>
                      <td className="text-center">
                        <input
                          type="number"
                          defaultValue={v.vagas_mes}
                          min={0}
                          max={500}
                          className="input-dark text-center font-mono"
                          style={{ width: 70, padding: '4px 8px' }}
                          onBlur={e => updateVaga(v, parseInt(e.target.value) || 0, v.ativo)}
                        />
                      </td>
                      <td className="text-center font-mono" style={{ color: 'var(--accent)' }}>{v.aceito_mes}</td>
                      <td className="text-center font-mono font-bold" style={{ color: v.lotado ? 'var(--red)' : 'var(--accent2)' }}>
                        {v.lotado ? '🔴 0' : v.disponivel}
                      </td>
                      <td className="text-center">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 pressure-bar-bg" style={{ minWidth: 60 }}>
                            <div className="pressure-bar" style={{ width: `${Math.min(pct, 100)}%`, background: pct >= 100 ? 'var(--red)' : pct >= 70 ? 'var(--yellow)' : 'var(--accent2)' }} />
                          </div>
                          <span className="text-xs font-mono" style={{ color: 'var(--text2)', minWidth: 28 }}>{pct}%</span>
                        </div>
                      </td>
                      <td className="text-center">
                        <button
                          className={`toggle ${v.ativo ? 'on' : ''}`}
                          onClick={() => updateVaga(v, v.vagas_mes, !v.ativo)}
                        />
                      </td>
                      <td className="text-xs text-right" style={{ color: isSvd ? 'var(--accent2)' : 'var(--text2)' }}>
                        {isSav ? 'Salvando...' : isSvd ? '✅ Salvo' : ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          <div className="mt-4 px-3 py-2 rounded-lg text-xs" style={{ background: 'rgba(255,215,0,0.04)', border: '1px solid rgba(255,215,0,0.15)', color: 'var(--text2)' }}>
            💡 Ao atingir o limite do mês, você some automaticamente do mapa de redistribuição da SESA para aquela especialidade. No primeiro dia do mês, o contador de &quot;aceito&quot; zera automaticamente.
          </div>
        </div>
      )}

      {/* ── IMPORTAÇÃO DE DADOS (SESA) ──────────────────── */}
      {isSesa && (
        <div className="card mb-6">
          <h2 className="text-base font-semibold mb-4">📂 Importação de Dados</h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
              <div className="text-sm font-semibold mb-1">IntegraSUS — SESA/CE</div>
              <div className="text-xs mb-3" style={{ color: 'var(--text2)' }}>CSV diário da fila de espera cirúrgica. Atualiza todos os pacientes.</div>
              <label className="btn-primary text-sm cursor-pointer inline-flex items-center gap-2">
                {uploading === 'integrasus' ? '⏳ Importando...' : '⬆ Fazer upload'}
                <input type="file" accept=".csv" hidden onChange={e => {
                  if (e.target.files?.[0]) handleImport('integrasus', e.target.files[0])
                }} />
              </label>
            </div>
            <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
              <div className="text-sm font-semibold mb-1">DATASUS — TabNet SIH/SUS</div>
              <div className="text-xs mb-3" style={{ color: 'var(--text2)' }}>CSV de internações por hospital. Atualização anual ou semestral.</div>
              <label className="btn-primary text-sm cursor-pointer inline-flex items-center gap-2">
                {uploading === 'datasus' ? '⏳ Importando...' : '⬆ Fazer upload'}
                <input type="file" accept=".csv" hidden onChange={e => {
                  if (e.target.files?.[0]) handleImport('datasus', e.target.files[0])
                }} />
              </label>
            </div>
          </div>
        </div>
      )}

      {/* ── INTEGRAÇÕES ──────────────────────────────────── */}
      <div className="card mb-6">
        <h2 className="text-base font-semibold mb-4">🔌 Integrações</h2>
        {[
          { label: 'IntegraSUS — SESA/CE', detail: 'API pública · Atualização diária', on: true },
          { label: 'DATASUS TabNet — SIH/SUS', detail: 'Importação manual · Semestral', on: true },
          { label: 'SISREG', detail: 'Previsto para pós-MVP · Fase 2', on: false },
          { label: 'Tasy / MV — FHIR R4', detail: 'Previsto para pós-MVP · Hospitais privados', on: false },
        ].map(item => (
          <div key={item.label} className="flex items-center justify-between py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <div>
              <div className="text-sm font-medium">{item.label}</div>
              <div className="text-xs" style={{ color: 'var(--text2)' }}>{item.detail}</div>
            </div>
            <button className={`toggle ${item.on ? 'on' : ''}`} />
          </div>
        ))}
      </div>

      {/* ── ALERTAS ──────────────────────────────────────── */}
      <div className="card mb-6">
        <h2 className="text-base font-semibold mb-4">🔔 Alertas Automáticos</h2>
        {[
          { label: 'Alerta de casos judicializados', detail: 'Notificação imediata por e-mail ao gestor', on: true },
          { label: 'Alerta Lei 12.732/2012 — Oncologia', detail: 'Avisar quando paciente oncológico superar 50 dias', on: true },
          { label: 'Relatório semanal automático', detail: 'Toda segunda-feira às 8h', on: true },
          { label: 'Alerta de hospital sobrecarregado', detail: 'Quando índice de pressão superar 3.5×', on: true },
        ].map(item => (
          <div key={item.label} className="flex items-center justify-between py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <div>
              <div className="text-sm font-medium">{item.label}</div>
              <div className="text-xs" style={{ color: 'var(--text2)' }}>{item.detail}</div>
            </div>
            <button className="toggle on" />
          </div>
        ))}
      </div>

      {/* ── PARÂMETROS IA ─────────────────────────────────── */}
      <div className="card">
        <h2 className="text-base font-semibold mb-4">🤖 Parâmetros do Modelo IA</h2>
        {[
          { label: 'Meta de acurácia (MAPE)', val: '15%' },
          { label: 'Horizonte de previsão', val: '90 dias' },
          { label: 'Índice de pressão crítico', val: '3.0×' },
          { label: 'Distância máxima CIR', val: '~120 km' },
        ].map(item => (
          <div key={item.label} className="flex items-center justify-between py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="text-sm">{item.label}</div>
            <div className="font-mono text-sm" style={{ color: 'var(--accent)' }}>{item.val}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
