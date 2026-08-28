import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Card } from '../components/ui/Card'

export default function Advisor(){
  const [msg,setMsg]=useState('')
  const qc=useQueryClient()
  const {data: history} = useQuery({queryKey:['advisor-history'], queryFn: async()=> (await api.get('/advisor/history')).data})
  const [response,setResponse]=useState<any>(null)
  const chatMut=useMutation({
    mutationFn: async (m:string)=> (await api.post('/advisor/chat',{message:m})).data,
    onSuccess:(d)=>{ setResponse(d); qc.invalidateQueries({queryKey:['advisor-history']})}
  })
  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-bold">AI Financial Advisor</h1>
      <Card><div className="text-xs text-slate-500">Provider: {import.meta.env.VITE_API_URL ? 'Configured via backend' : 'Not configured'} • Responses use your real financial data from Neon via FastAPI.</div></Card>
      <Card>
        <div className="space-y-2 max-h-96 overflow-auto">
          {(history||[]).map((m:any)=><div key={m.id} className={`p-2 rounded ${m.role==='user'?'bg-sky-50 ml-8':'bg-slate-100 mr-8'}`}><div className="text-xs text-slate-500">{m.role}</div><div className="text-sm">{m.content}</div></div>)}
          {history?.length===0 && <div className="text-sm text-slate-500">No messages yet. Try: How much did I spend on food this month?</div>}
        </div>
        {response && <div className="mt-3 p-3 border rounded bg-white"><div className="text-xs text-slate-500">Response from {response.provider} {response.fallback? '(Rule-based fallback – AI unavailable)':'(AI)'}</div><div className="text-sm whitespace-pre-wrap">{response.response}</div></div>}
        <div className="flex gap-2 mt-3">
          <input value={msg} onChange={e=>setMsg(e.target.value)} placeholder="Ask about your finances..." className="input flex-1" onKeyDown={e=> e.key==='Enter' && msg && chatMut.mutate(msg)}/>
          <button disabled={chatMut.isPending || !msg} onClick={()=> chatMut.mutate(msg)} className="btn-primary">{chatMut.isPending?'Thinking...':'Send'}</button>
        </div>
      </Card>
    </div>
  )
}
