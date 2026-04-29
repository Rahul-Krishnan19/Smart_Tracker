import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
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

// --- Transactions ---
export const transactionsApi = {
  list: (params) => api.get('/transactions', { params }),
  create: (data) => api.post('/transactions', data),
  get: (id) => api.get(`/transactions/${id}`),
  update: (id, data) => api.put(`/transactions/${id}`, data),
  delete: (id) => api.delete(`/transactions/${id}`),
  summary: (params) => api.get('/transactions/summary', { params }),
  export: (params) => api.get('/transactions/export', { params, responseType: 'blob' }),
  paymentSources: () => api.get('/transactions/payment-sources'),
  merchants: (q) => api.get('/transactions/merchants', { params: { q } }),
  bulkCategorize: (data) => api.post('/transactions/bulk-categorize', data),
  updateCategory: (id, data) => api.put(`/transactions/${id}/category`, data),
  merchantBreakdown: (params) => api.get('/transactions/merchant-breakdown', { params }),
}

export const analyticsApi = {
  trend: (params) => api.get('/analytics/trend', { params }),
  getSpendingLimit: (granularity) =>
    api.get('/analytics/spending-limit', { params: { granularity } }),
  putSpendingLimit: (data) => api.put('/analytics/spending-limit', data),
  deleteSpendingLimit: (granularity) =>
    api.delete('/analytics/spending-limit', { params: { granularity } }),
}

export default api
