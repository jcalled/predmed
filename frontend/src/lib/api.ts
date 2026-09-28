import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Injeta token JWT em todas as requisições
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('predmed_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redireciona para login se 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('predmed_token')
      localStorage.removeItem('predmed_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }).then(r => r.data),
  me: () => api.get('/auth/me').then(r => r.data),
}

// ── Dashboard ──────────────────────────────────────────
export const dashboardApi = {
  get: () => api.get('/dashboard').then(r => r.data),
}

// ── Fila ──────────────────────────────────────────────
export const filaApi = {
  get: (params?: Record<string, unknown>) =>
    api.get('/fila', { params }).then(r => r.data),
}

// ── Hospitais ──────────────────────────────────────────
export const hospitaisApi = {
  get: () => api.get('/hospitais').then(r => r.data),
}

// ── Redistribuição ──────────────────────────────────────
export const redistApi = {
  // Aceita parâmetro opcional cir
  get: (cir?: string) => {
    const params = cir ? { cir } : {}
    return api.get('/redistribuicao', { params }).then(r => r.data)
  },
  aprovar: (data: Record<string, unknown>) =>
    api.post('/redistribuicao/aprovar', data).then(r => r.data),
  historico: () => api.get('/redistribuicao/historico').then(r => r.data),
}

// ── Priorização ──────────────────────────────────────────
export const priorizacaoApi = {
  get: () => api.get('/priorizacao').then(r => r.data),
}

// ── Judicializados ──────────────────────────────────────
export const judicializadosApi = {
  get: () => api.get('/judicializados').then(r => r.data),
}

// ── Configurações ──────────────────────────────────────
export const configApi = {
  getVagas: () => api.get('/configuracoes/vagas').then(r => r.data),
  updateVaga: (data: { especialidade: string; vagas_mes: number; ativo: boolean }) =>
    api.put('/configuracoes/vagas', data).then(r => r.data),
}

// ── Relatórios ──────────────────────────────────────────
export const relatoriosApi = {
  resumo: () => api.get('/relatorios/resumo').then(r => r.data),
}

// ── Admin Import ──────────────────────────────────────────
export const adminApi = {
  importIntegrasus: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/admin/import/integrasus', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
  },
  importDataSus: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/admin/import/datasus', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
  },
}

// ── Previsões ──────────────────────────────────────────
export const previsoesApi = {
  get: (especialidade?: string) =>
    api.get('/previsoes', { params: especialidade ? { especialidade } : {} }).then(r => r.data),
  todas: () => api.get('/previsoes/todas').then(r => r.data),
  recalcular: () => api.post('/previsoes/recalcular').then(r => r.data),
}

// ── Zerar Filas ──────────────────────────────────────────
export const zerarFilasApi = {
  get: () => api.get('/zerarfilas').then(r => r.data),
}

export const previsoesMlApi = {
  // Previsão Holt-Winters para uma especialidade (série histórica simulada)
  previsao: (especialidade?: string, horizonte: number = 6) =>
    api.get('/previsoes/ml', { 
      params: { 
        ...(especialidade && { especialidade }),
        horizonte 
      } 
    }).then(r => r.data),
  
  // Resumo de todas as especialidades
  todas: () =>
    api.get('/previsoes/ml/todas').then(r => r.data),
}


// ── Analytics ──────────────────────────────────────────
export const analyticsApi = {
  resumo: () => api.get('/analytics/resumo').then(r => r.data),
  sazonalidade: () => api.get('/analytics/sazonalidade').then(r => r.data),
  mortalidade: (ano: number) =>
    api.get('/analytics/mortalidade', { params: { ano } }).then(r => r.data),
  pressaoHistorica: () => api.get('/analytics/pressao-historica').then(r => r.data),

  // ✅ Simulador
  simuladorReceita: (vagas: Record<string, number>) =>
    api.post('/analytics/simulador-receita', vagas).then(r => r.data),

  // ✅ Validação (MAPE)
  validacaoMape: (especialidade: string, meses: number) =>
    api.get('/analytics/validacao-mape', { params: { especialidade, meses } }).then(r => r.data),
}