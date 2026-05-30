import axios from 'axios'

// Vazio = usar proxy do Vite (/api -> localhost:8000), evita CORS
const API_URL = (import.meta.env.VITE_API_URL || '').trim()
const baseURL = API_URL ? `${API_URL}/api` : '/api'

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor: 401 em chamadas autenticadas → limpa token e volta ao login.
// NÃO redirecionar em 401 do POST /auth/login (senha errada), senão a página recarrega e some a mensagem de erro.
function _isAuthFailureOnLoginEndpoint(error) {
  const url = String(error.config?.url || '')
  return (
    url.includes('/auth/login') ||
    url.includes('/auth/sso-exchange') ||
    url.includes('/auth/oidc/exchange') ||
    url.includes('/auth/register-portal')
  )
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !_isAuthFailureOnLoginEndpoint(error)) {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      const path = typeof window !== 'undefined' ? window.location.pathname || '' : ''
      window.location.href = path.startsWith('/portal') ? '/portal/login' : '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }).then((res) => res.data),

  registerPortal: (data) =>
    api.post('/auth/register-portal', data).then((res) => res.data),
  
  ssoExchange: (sso_code) =>
    api.post('/auth/sso-exchange', { sso_code }).then((res) => res.data),

  oidcStatus: () => api.get('/auth/oidc/status').then((res) => res.data),

  oidcExchange: (oidc_code) =>
    api.post('/auth/oidc/exchange', { oidc_code }).then((res) => res.data),

  oidcLogoutUrl: () => api.get('/auth/oidc/logout-url').then((res) => res.data),

  refresh: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }).then((res) => res.data),
  
  getMe: () => api.get('/auth/me').then((res) => res.data),
}

export const usersAPI = {
  getAll: (params) => api.get('/users', { params }).then((res) => res.data),
  getFromManagement: (search) =>
    api.get('/users/gerenciamento', { params: { search: search || '' } }).then((res) => res.data),
  getManagementDiagnosis: () => api.get('/users/gerenciamento-diagnostico').then((res) => res.data),
  getById: (id) => api.get(`/users/${id}`).then((res) => res.data),
  create: (data) => api.post('/users', data).then((res) => res.data),
  update: (id, data) => api.put(`/users/${id}`, data).then((res) => res.data),
  delete: (id, opts = {}) => {
    const params = opts.permanent ? { permanent: true } : {}
    return api.delete(`/users/${id}`, { params }).then((res) => res.data)
  },
  updatePassword: (id, data) =>
    api.put(`/users/${id}/password`, data).then((res) => res.data),
}

export const desligamentoAPI = {
  getSnipeStatus: () => {
    const url = `${api.defaults.baseURL}/desligamento/snipe-status?t=${Date.now()}`
    if (typeof window !== 'undefined') console.log('[api] getSnipeStatus ->', url)
    return api.get('/desligamento/snipe-status', { params: { t: Date.now() } }).then((res) => res.data)
  },
  getStatusLabels: () => api.get('/desligamento/statuslabels').then((res) => res.data),
  getSnipeUsers: (search) =>
    api.get('/desligamento/usuarios-snipe', { params: { search: search || '' } }).then((res) => res.data),
  getSnipeDiagnostics: () => api.get('/desligamento/snipe-diagnostico').then((res) => res.data),
  findSnipeUser: (name, email) =>
    api.get('/desligamento/buscar-usuario-snipe', { params: { name: name || '', email: email || '' } }).then((res) => res.data),
  getAssetsForUser: (snipeUserId) =>
    api.get(`/desligamento/ativos/${snipeUserId}`).then((res) => res.data),
  getAvailableAssets: () => api.get('/desligamento/ativos-disponiveis').then((res) => res.data),
  checkin: (data) => api.post('/desligamento/checkin', data).then((res) => res.data),
  checkout: (data) => api.post('/desligamento/checkout', data).then((res) => res.data),
  checkoutByTag: (data) => api.post('/desligamento/checkout-por-patrimonio', data).then((res) => res.data),
  getLogs: (params) => api.get('/desligamento/logs', { params }).then((res) => res.data),
  getAssignments: (params) => api.get('/desligamento/atribuicoes', { params }).then((res) => res.data),
}

export const ticketsAPI = {
  getAll: (params) => api.get('/tickets', { params }).then((res) => res.data),
  /** Admin/técnico: chamados do portal ainda abertos (não encerrados). */
  getStaffRequesterAlerts: () =>
    api.get('/tickets/staff-requester-alerts').then((res) => res.data),
  create: (data) => api.post('/tickets', data).then((res) => res.data),
  createOffboarding: (data) => api.post('/tickets/offboarding', data).then((res) => res.data),
  getOffboardingPrefill: (employeeName) =>
    api.get('/tickets/offboarding-prefill', { params: { employee_name: employeeName } }).then((res) => res.data),
  update: (ticketId, data) =>
    api.put(`/tickets/${ticketId}`, data).then((res) => res.data),
  updateStatus: (ticketId, data) =>
    api.put(`/tickets/${ticketId}/status`, data).then((res) => res.data),
}

export const telefonesAPI = {
  opcoes: () =>
    api.get('/telefones/opcoes').then((res) => res.data),

  buscarLinha: (codigo, nome) =>
    api
      .get('/telefones/buscar-linha', { params: { codigo: codigo || '', nome: nome || '' } })
      .then((res) => res.data),

  buscarLinhaPorNumero: (numero) =>
    api
      .get('/telefones/buscar-linha-numero', { params: { numero: numero || '' } })
      .then((res) => res.data),

  novaLinha: (data) =>
    api.post('/telefones/nova-linha', data).then((res) => res.data),

  onboarding: (data) =>
    api.post('/telefones/onboarding', data).then((res) => res.data),

  manutencao: (data) =>
    api.post('/telefones/manutencao', data).then((res) => res.data),

  rouboPenda: (data) =>
    api.post('/telefones/roubo-perda', data).then((res) => res.data),

  transferencia: (data) =>
    api.post('/telefones/transferencia', data).then((res) => res.data),

  linkGerenciamento: (params) =>
    api.get('/telefones/link-gerenciamento', { params }).then((res) => res.data),
}

export default api

