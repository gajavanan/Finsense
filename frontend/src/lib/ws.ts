import { getToken } from './auth'

export function createWS(onEvent: (evt:string, data:any)=>void){
  const token = getToken()
  if(!token) return null
  const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1','').replace('http','ws')
  const url = `${base}/api/v1/ws?token=${token}`
  const ws = new WebSocket(url)
  ws.onmessage = (e)=>{
    try{
      const msg = JSON.parse(e.data)
      onEvent(msg.event, msg.data)
    }catch{}
  }
  ws.onopen = ()=> console.log('WS connected')
  ws.onclose = ()=> console.log('WS closed')
  return ws
}
