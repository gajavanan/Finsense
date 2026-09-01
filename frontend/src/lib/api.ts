import axios from 'axios'
import { getToken } from './auth'

// Centralized and normalized API URLs
const rawUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').trim().replace(/\/$/, '')
export const API_BASE_URL = rawUrl.replace(/\/api\/v1$/, '')
export const API_URL = rawUrl.endsWith('/api/v1') ? rawUrl : `${rawUrl}/api/v1`

const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    // detail may be string or object {code, message}
    const detailStr = typeof detail === 'string' ? detail : (detail?.message || detail?.code || '')
    const detailCode = typeof detail === 'object' ? detail?.code : undefined
    const msg = detailStr || err.response?.data?.message || err.message

    if (status === 403) {
      const isNotVerified =
        detailCode === 'EMAIL_NOT_VERIFIED' ||
        (typeof detailStr === 'string' && detailStr.includes('Email not verified')) ||
        (typeof detailStr === 'string' && detailStr.includes('verify'))
      if (isNotVerified) {
        const e: any = new Error(detailStr || 'Please verify your email before signing in.')
        e.status = 403
        e.code = 'EMAIL_NOT_VERIFIED'
        return Promise.reject(e)
      }
    }

    if (status === 401) {
      const detailMsg = typeof detail === 'string' ? detail : detailStr
      const e: any = new Error(detailMsg || 'Invalid email or password')
      e.status = 401
      return Promise.reject(e)
    }

    if (!err.response) {
      const e: any = new Error(
        'Unable to connect to FinSense server. Please verify your connection or check if the backend service is running.'
      )
      e.status = 0
      e.code = 'ERR_CONNECTION_REFUSED'
      return Promise.reject(e)
    }

    const e: any = new Error(msg)
    e.status = status
    if (detailCode) e.code = detailCode
    return Promise.reject(e)
  }
)

export default api
