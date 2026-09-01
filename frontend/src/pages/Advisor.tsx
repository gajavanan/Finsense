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
    onSuccess:(d)=>{ setResponse(d); setMsg(''); qc.invalidateQueries({queryKey:['advisor-history']})}
  })

  const suggestions = [
    "Where am I spending the most?",
    "How can I save ₹10,000 per month?",
    "Am I on track with my goals?",
    "Analyze my spending this month.",
    "How much should I budget for food?",
    "Can I retire early?"
  ]

  const handleSend = (text: string) => {
    if(!text || chatMut.isPending) return
    chatMut.mutate(text)
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Financial Advisor</h1>
        <p className="text-sm text-slate-500">Ask questions about your transactions, budgets, savings goals, and financial health.</p>
      </div>

      {/* Suggested Questions */}
      <div className="card">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Suggested Questions</h3>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={chatMut.isPending}
              className="text-xs px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-sky-50 dark:hover:bg-sky-950/40 hover:text-sky-600 border border-slate-200 dark:border-slate-700 transition-colors text-left"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <Card>
        <div className="space-y-3 max-h-[420px] overflow-auto p-2">
          {(history||[]).map((m:any)=>(
            <div key={m.id} className={`p-3 rounded-2xl text-sm max-w-[85%] ${m.role==='user'?'bg-sky-600 text-white ml-auto':'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 mr-auto border border-slate-200 dark:border-slate-700'}`}>
              <div className="text-[10px] font-semibold opacity-70 mb-1 uppercase">{m.role==='user'?'You':'FinSense Advisor'}</div>
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          ))}
          {(!history || history.length===0) && !response && (
            <div className="text-center py-10 text-slate-400 text-sm">
              No previous chat history. Click a suggested question above or type your prompt below to start.
            </div>
          )}
        </div>

        {response && (
          <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-sky-500/30">
            <div className="text-xs text-sky-600 dark:text-sky-400 font-semibold mb-1">
              Latest Insight ({response.provider} {response.fallback ? '• Rule-based fallback' : '• Live AI'})
            </div>
            <div className="text-sm whitespace-pre-wrap text-slate-700 dark:text-slate-300">{response.response}</div>
          </div>
        )}

        <div className="flex gap-2 mt-4 pt-3 border-t border-slate-200 dark:border-slate-800">
          <input 
            value={msg} 
            onChange={e=>setMsg(e.target.value)} 
            placeholder="Ask your AI advisor anything about your finances..." 
            className="input flex-1" 
            onKeyDown={e=> e.key==='Enter' && handleSend(msg)}
          />
          <button 
            disabled={chatMut.isPending || !msg.trim()} 
            onClick={()=> handleSend(msg)} 
            className="btn-primary shrink-0"
          >
            {chatMut.isPending ? 'Thinking...' : 'Send Prompt'}
          </button>
        </div>
      </Card>
    </div>
  )
}
