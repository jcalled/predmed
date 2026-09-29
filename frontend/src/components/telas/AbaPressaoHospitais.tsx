'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { MapPin } from 'lucide-react'
import { hospitaisApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import KPICard from '@/components/ui/KPICard'
import Badge, { type BadgeTom } from '@/components/ui/Badge'
import SeloDado from '@/components/ui/SeloDado'
import { Carregando, EstadoErro, EstadoVazio } from '@/components/ui/Estados'

/*
 * Aba "Pressão por hospital" da Redistribuição (ex-/dashboard/hospitais).
 * O escopo é o que GET /hospitais já aplica por perfil:
 * SESA/SMS todos; hospital público a sua CIR; particular os públicos da CIR.
 * Pressão e ociosidade são ESTIMADAS (redistribuição v1: fila IntegraSUS por CNES,
 * produção SIH por CNES e capacidade CNES) — docs/dados/redistribuicao-v1.md.
 */

const STATUS: Record<string, { rotulo: string; tom: BadgeTom; cor: string }> = {
  critico: { rotulo: 'Crítico', tom: 'vermelho', cor: 'var(--red)' },
  alerta:  { rotulo: 'Alerta',  tom: 'laranja',  cor: 'var(--accent3)' },
  normal:  { rotulo: 'Normal',  tom: 'azul',     cor: 'var(--accent)' },
  ocioso:  { rotulo: 'Ocioso',  tom: 'verde',    cor: 'var(--accent2)' },
}

interface Hospital {
  hospital_nome: string
  municipio: string
  cir: string
  tipo: string
  fila_atual: number
  media_mensal: number
  pressao: number
  pressao_status: string
  cnes?: string | null
  vinculo_cnes?: string | null
  vinculo_provisorio?: boolean
  ociosidade_estimada_mes?: number
  ociosidade_limitada_por?: string | null
  queda_producao_recente?: boolean
  salas_cirurgicas?: number
  leitos_cirurgicos_sus?: number
  na_fila_integrasus?: boolean
}

export default function AbaPressaoHospitais() {
  const { isParticular, isPublico } = useAuth()
  const { data, error, isLoading, mutate } = useSWR('hospitais', hospitaisApi.get)
  const [filtroStatus, setFiltroStatus] = useState('')

  const todos: Hospital[] = data?.hospitais || []
  const hospitais = todos.filter(h => !filtroStatus || h.pressao_status === filtroStatus)
  const criticos = todos.filter(h => h.pressao_status === 'critico').length
  const comOciosidade = todos.filter(h => (h.ociosidade_estimada_mes ?? 0) > 0)
  const ociosos = comOciosidade.length
  const ociosidadeTotal = comOciosidade.reduce((a, h) => a + (h.ociosidade_estimada_mes ?? 0), 0)

  const escopo = isParticular
    ? 'Hospitais públicos da sua CIR com demanda reprimida.'
    : isPublico
      ? 'Hospitais da sua região de saúde (CIR).'
      : 'Todos os hospitais monitorados (fila IntegraSUS × produção DATASUS/SIH).'

  return (
    <div>
      <p className="text-sm mb-4" style={{ color: 'var(--text2)' }}>
        {escopo} Pressão = fila atual ÷ média mensal de cirurgias SUS realizadas no SIH (12 meses).
        Ociosidade = folga mensal estimada pelo menor de três limites (produção já demonstrada, salas e leitos cirúrgicos SUS no CNES);
        não é vaga confirmada. <SeloDado natureza="estimado" />
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        <KPICard label="Hospitais" value={data?.total ?? '—'} detail="No seu escopo" color="blue" status="medido" carregando={isLoading} />
        <KPICard label="Alta pressão" value={isLoading ? '—' : criticos} detail="Status crítico" color="red" status="estimado" carregando={isLoading}
          tooltip="Índice calculado sobre a fila atual e a média mensal do SIH; a média é uma aproximação da capacidade." />
        <KPICard label="Com ociosidade estimada" value={isLoading ? '—' : ociosos} detail={`≈ ${ociosidadeTotal.toLocaleString('pt-BR')} cirurgias/mês`} color="green" status="estimado" carregando={isLoading}
          tooltip="Hospitais com folga mensal estimada (CNES + SIH). Não considera agenda, equipe nem cirurgias ambulatoriais; precisa de confirmação do hospital." />
        <KPICard label="Exibindo" value={isLoading ? '—' : hospitais.length} detail="Após o filtro" carregando={isLoading} />
      </div>

      <div className="flex gap-2 flex-wrap mb-4" role="group" aria-label="Filtrar por status de pressão">
        {['', 'critico', 'alerta', 'normal', 'ocioso'].map(s => {
          const ativo = filtroStatus === s
          return (
            <button
              key={s}
              type="button"
              aria-pressed={ativo}
              onClick={() => setFiltroStatus(s)}
              className="text-xs px-3 py-1.5 rounded-full transition-colors"
              style={{
                background: ativo ? 'rgba(0,194,255,0.15)' : 'var(--surface2)',
                border: `1px solid ${ativo ? 'rgba(0,194,255,0.45)' : 'var(--border-strong)'}`,
                color: ativo ? 'var(--accent)' : 'var(--text2)',
              }}
            >
              {s === '' ? 'Todos' : STATUS[s].rotulo}
            </button>
          )
        })}
      </div>

      {error && !data ? (
        <EstadoErro erro={error} aoTentarNovamente={() => mutate()} />
      ) : isLoading ? (
        <Carregando mensagem="Carregando hospitais..." />
      ) : hospitais.length === 0 ? (
        <EstadoVazio
          titulo={filtroStatus ? 'Nenhum hospital com este status' : 'Nenhum hospital no seu escopo'}
          acao={filtroStatus ? <button type="button" className="btn-primary text-xs" onClick={() => setFiltroStatus('')}>Mostrar todos</button> : undefined}
        />
      ) : (
        <ul className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {hospitais.map(h => {
            const st = STATUS[h.pressao_status] || STATUS.normal
            const pct = Math.min((h.pressao / 5) * 100, 100)
            const semCapacidade = h.pressao === 99
            return (
              <li key={h.cnes ?? h.hospital_nome} className="card">
                <div className="flex justify-between items-start gap-2 mb-2">
                  <div className="font-semibold text-sm leading-tight">{h.hospital_nome}</div>
                  <Badge tom={st.tom} className="flex-shrink-0">{st.rotulo}</Badge>
                </div>
                <div className="text-xs mb-3 flex items-center gap-1 flex-wrap" style={{ color: 'var(--text2)' }}>
                  <MapPin size={12} aria-hidden="true" /> {h.municipio} · {h.cir}
                  {h.tipo === 'particular' && <span style={{ color: 'var(--yellow)' }}>· particular</span>}
                  {h.cnes && <span>· CNES {h.cnes}</span>}
                </div>
                {(h.vinculo_provisorio || h.queda_producao_recente) && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {h.vinculo_provisorio && (
                      <Badge tom="amarelo" title="O nome da fila foi ligado a este CNES por correspondência não confirmada; revisar.">
                        {h.cnes ? 'vínculo CNES provisório' : 'sem vínculo CNES'}
                      </Badge>
                    )}
                    {h.queda_producao_recente && (
                      <Badge tom="cinza" title="Produção recente abaixo de 50% da já demonstrada: pode ser reforma, fechamento ou atraso de faturamento. Ociosidade não contada.">
                        queda de produção
                      </Badge>
                    )}
                  </div>
                )}

                <dl className="grid grid-cols-3 gap-2 text-center mb-3">
                  <div className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                    <dt className="text-2xs" style={{ color: 'var(--text2)' }}>fila</dt>
                    <dd className="font-mono font-bold text-sm">{h.fila_atual.toLocaleString('pt-BR')}</dd>
                  </div>
                  <div className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                    <dt className="text-2xs" style={{ color: 'var(--text2)' }}>cirurgias/mês</dt>
                    <dd className="font-mono font-bold text-sm">{Math.round(h.media_mensal).toLocaleString('pt-BR')}</dd>
                  </div>
                  <div className="p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                    <dt className="text-2xs" style={{ color: 'var(--text2)' }}>pressão</dt>
                    <dd className="font-mono font-bold text-sm" style={{ color: st.cor }}>
                      {semCapacidade ? <span title="Sem produção registrada no SIH">sem dado</span> : `${h.pressao.toLocaleString('pt-BR')}×`}
                    </dd>
                  </div>
                </dl>

                {(h.ociosidade_estimada_mes ?? 0) > 0 && (
                  <p className="text-xs mb-2" style={{ color: 'var(--accent2)' }}>
                    Ociosidade estimada: <strong className="font-mono">{h.ociosidade_estimada_mes!.toLocaleString('pt-BR')}</strong> cirurgias/mês
                  </p>
                )}
                <div className="pressure-bar-bg" aria-hidden="true">
                  <div className="pressure-bar" style={{ width: `${pct}%`, background: st.cor }} />
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
