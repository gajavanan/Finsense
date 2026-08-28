import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { useState } from 'react'
import { Card } from '../components/ui/Card'
import { toast } from 'sonner'

export default function Budgets(){
  const qc=useQueryClient()
  const {data, isLoading} = useQuery({queryKey:['budgets'], queryFn: async()=> (await api.get('/budgets')).data})
  const [form,setForm]=useState({category:'Food', amount:'', period:'monthly'})
  const [rec,setRec]=useState<any>(null)

  const createMut=useMutation({
    mutationFn: async(payload:any)=> (await api.post('/budgets', payload)).data,
    onSuccess:()=>{ toast.success('Budget created'); qc.invalidateQueries({queryKey:['budgets']}); qc.invalidateQueries({queryKey:['dashboard']}) },
    onError:(e:any)=> toast.error(e.message)
  })
  const delMut=useMutation({mutationFn: async(id:string)=> (await api.delete(`/budgets/${id}`)).data, onSuccess:()=> qc.invalidateQueries({queryKey:['budgets']})})

  const getRec=async()=>{
    try{ const r=await api.post('/ml/recommend/budget', {}); setRec(r.data)}catch(e:any){ toast.error(e.message)}
  }

  if(isLoading) return <div>Loading...</div>
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Budgets</h1>
      <Card>
        <div className="flex flex-wrap gap-2">
          <select value={form.category} onChange={e=>setForm({...form, category:e.target.value})} className="input w-40"><option>Food</option><option>Shopping</option><option>Transport</option><option>Bills</option><option>Entertainment</option><option>Healthcare</option><option>Education</option><option>Travel</option><option>Investment</option><option>Rent</option><option>Subscriptions</option><option>Other</option></select>
          <input placeholder="Amount" type="number" value={form.amount} onChange={e=>setForm({...form, amount:e.target.value})} className="input w-32"/>
          <select value={form.period} onChange={e=>setForm({...form,period:e.target.value})} className="input w-32"><option value="monthly">Monthly</option><option value="weekly">Weekly</option></select>
          <button onClick={()=> createMut.mutate({category: form.category, amount: parseFloat(form.amount), period: form.period})} className="btn-primary">Create</button>
          <button onClick={getRec} className="px-4 py-2 border rounded text-sm">ML Recommend</button>
        </div>
        {rec && <div className="mt-3 text-sm">{rec.status==='insufficient_data' ? <span>{rec.message}</span> : <div><div>Total recommended: ₹{rec.total_recommended}</div>{Object.entries(rec.recommendations||{}).map(([k,v]:any)=><div key={k}>{k}: ₹{v as any} – {rec.explanations?.[k]}</div>)}</div>}</div>}
      </Card>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(data||[]).map((b:any)=>
          <Card key={b.id}>
            <div className="font-semibold">{b.category} <span className="text-xs text-slate-500">{b.period}</span></div>
            <div className="text-sm">₹{b.spent||0} / ₹{b.amount} <span className={b.pct>=100?'text-red-600': b.pct>=75?'text-amber-600':'text-green-600'}>({b.pct||0}%)</span></div>
            <div className="h-2 bg-slate-200 rounded mt-1"><div className={`h-2 rounded ${b.pct>=100?'bg-red-500': b.pct>=90?'bg-amber-500':'bg-sky-500'}`} style={{width:`${Math.min(100,b.pct||0)}%`}}></div></div>
            {b.pct>=100 ? <div className="text-xs text-red-600 mt-1">Budget exceeded.</div> : b.pct>=50 && <div className="text-xs text-amber-600">Threshold: {b.pct>=90?'90%': b.pct>=75?'75%':'50%'} used.</div>}
            <button onClick={()=>delMut.mutate(b.id)} className="text-xs text-red-600 mt-2">Delete</button>
          </Card>
        )}
        {(data||[]).length===0 && <Card>Empty: No budgets yet.</Card>}
      </div>
    </div>
  )
}
