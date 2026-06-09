import axios from 'axios'

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || ''}/api`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401: clear token and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// --- Auth ---
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  totpSetup: (tempToken) => api.post(`/auth/totp/setup?temp_token=${tempToken}`),
  totpVerify: (data) => api.post('/auth/totp/verify', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

// Strip params that are empty strings, null, or undefined before sending.
function cleanParams(params) {
  const out = {}
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== '' && v !== null && v !== undefined) out[k] = v
  }
  return out
}

// --- Transactions ---
export const transactionsApi = {
  list: (params) => api.get('/transactions', { params: cleanParams(params) }),
  create: (data) => api.post('/transactions', data),
  get: (id) => api.get(`/transactions/${id}`),
  update: (id, data) => api.put(`/transactions/${id}`, data),
  delete: (id) => api.delete(`/transactions/${id}`),
  summary: (params) => api.get('/transactions/summary', { params: cleanParams(params) }),
  export: (params) => api.get('/transactions/export', { params: cleanParams(params), responseType: 'blob' }),
  paymentSources: () => api.get('/transactions/payment-sources'),
  merchants: (q) => api.get('/transactions/merchants', { params: { q } }),
  bulkCategorize: (data) => api.post('/transactions/bulk-categorize', data),
  updateCategory: (id, data) => api.put(`/transactions/${id}/category`, data),
  merchantBreakdown: (params) => api.get('/transactions/merchant-breakdown', { params: cleanParams(params) }),
  categories: () => api.get('/transactions/categories'),
}

export const analyticsApi = {
  trend: (params) => api.get('/analytics/trend', { params: cleanParams(params) }),
  getSpendingLimit: (granularity) =>
    api.get('/analytics/spending-limit', { params: { granularity } }),
  putSpendingLimit: (data) => api.put('/analytics/spending-limit', data),
  deleteSpendingLimit: (granularity) =>
    api.delete('/analytics/spending-limit', { params: { granularity } }),
}

export const gmailSourcesApi = {
  list: () => api.get('/gmail/sources'),
  add: (data) => api.post('/gmail/sources', data),
  toggle: (id, enabled) => api.put(`/gmail/sources/${id}`, { enabled }),
  remove: (id) => api.delete(`/gmail/sources/${id}`),
}

export const insightsApi = {
  getAnomalies: () => api.get('/insights/anomalies').then(r => r.data),
  updateAnomaly: (id, status) => api.patch(`/insights/anomalies/${id}`, { status }).then(r => r.data),
  getSubscriptions: () => api.get('/insights/subscriptions').then(r => r.data),
  updateSubscription: (id, status) => api.patch(`/insights/subscriptions/${id}`, { status }).then(r => r.data),
  getInsights: () => api.get('/insights/insights').then(r => r.data),
  dismissInsight: (id) => api.post(`/insights/insights/${id}/dismiss`).then(r => r.data),
  getSummary: () => api.get('/insights/summary').then(r => r.data),
}

export default api
