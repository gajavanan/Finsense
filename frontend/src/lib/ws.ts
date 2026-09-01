import { getToken } from './auth'
import { API_BASE_URL } from './api'

export function createWS(onEvent: (evt: string, data: any) => void) {
  const token = getToken()
  if (!token) return null

  const wsBase = API_BASE_URL.replace(/^http/, 'ws')
  const url = `${wsBase}/api/v1/ws?token=${token}`
  const ws = new WebSocket(url)

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      onEvent(msg.event, msg.data)
    } catch {}
  }
  ws.onopen = () => console.log('WS connected')
  ws.onclose = () => console.log('WS closed')
  return ws
}
