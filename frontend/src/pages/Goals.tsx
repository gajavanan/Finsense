import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { useState } from 'react'
import { Card } from '../components/ui/Card'
import { toast } from 'sonner'

export default function Goals(){
  const qc=useQueryClient()
  const {data} = useQuery({queryKey:['goals'], queryFn: async()=> (await api.get('/goals')).data})
  const [form,setForm]=useState({name:'', target_amount:'', current_amount:'0', target_date:''})
  const createMut=useMutation({
    mutationFn: async(p:any)=> (await api.post('/goals', p)).data,
    onSuccess:()=>{ toast.success('Goal created'); qc.invalidateQueries({queryKey:['goals']})},
    onError:(e:any)=> toast.error(e.message)
  })
  const delMut=useMutation({mutationFn: async(id:string)=> (await api.delete(`/goals/${id}`)).data, onSuccess:()=> qc.invalidateQueries({queryKey:['goals']})})
  const predict = async (g:any)=>{
    try{ const r=await api.post('/ml/predict/goal',{target_amount: g.target_amount, current_amount: g.current_amount, monthly_contribution: 5000}); toast.success(`ML: ${r.data.months} months to goal, completion ${r.data.completion_date}`)}catch(e:any){ toast.error(e.message)}
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Savings Goals</h1>
      <Card>
        <div className="grid md:grid-cols-4 gap-2">
          <input placeholder="Goal name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} className="input"/>
          <input placeholder="Target" type="number" value={form.target_amount} onChange={e=>setForm({...form,target_amount:e.target.value})} className="input"/>
          <input placeholder="Current" type="number" value={form.current_amount} onChange={e=>setForm({...form,current_amount:e.target.value})} className="input"/>
          <input type="date" value={form.target_date} onChange={e=>setForm({...form,target_date:e.target.value})} className="input"/>
        </div>
        <button onClick={()=> createMut.mutate({name: form.name, target_amount: parseFloat(form.target_amount), current_amount: parseFloat(form.current_amount), target_date: form.target_date||undefined})} className="btn-primary mt-2">Create Goal</button>
      </Card>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(data||[]).map((g:any)=>{
          const pct = Math.min(100, (g.current_amount/g.target_amount*100)||0)
          const remaining = g.target_amount - g.current_amount
          return <Card key={g.id}>
            <div className="font-semibold">{g.name}</div>
            <div className="w-24 h-24 relative mx-auto my-2">
              <svg viewBox="0 0 36 36" className="w-full h-full"><path d="M18 2 a16 16 0 1 1 0 32 a16 16 0 1 1 0 -32" fill="none" stroke="#e2e8f0" strokeWidth="4"/><path d="M18 2 a16 16 0 1 1 0 32 a16 16 0 1 1 0 -32" fill="none" stroke="#0ea5e9" strokeWidth="4" strokeDasharray={`${pct},100`}/></svg>
              <div className="absolute inset-0 flex items-center justify-center text-sm font-bold">{Math.round(pct)}%</div>
            </div>
            <div className="text-sm text-center">₹{g.current_amount} / ₹{g.target_amount}</div>
            <div className="text-xs text-slate-500 text-center">Remaining: ₹{remaining} • Target: {g.target_date||'—'}</div>
            <div className="flex gap-2 justify-center mt-2"><button onClick={()=>predict(g)} className="text-xs px-2 py-1 border rounded">ML Predict</button><button onClick={()=>delMut.mutate(g.id)} className="text-xs text-red-600">Delete</button></div>
          </Card>
        })}
        {(data||[]).length===0 && <Card>Empty: No goals yet.</Card>}
      </div>
    </div>
  )
}
