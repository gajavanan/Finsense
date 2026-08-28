import { useState } from 'react'
import api from '../lib/api'
import { Card } from '../components/ui/Card'

export default function FIRE(){
  const [form,setForm]=useState({current_age:'30', current_savings:'500000', monthly_savings:'20000', monthly_expenses:'40000', expected_return:'12', inflation:'6', target_retirement_age:'45'})
  const [res,setRes]=useState<any>(null)
  const calc=async()=>{
    const payload={current_age: parseInt(form.current_age), current_savings: parseFloat(form.current_savings), monthly_savings: parseFloat(form.monthly_savings), monthly_expenses: parseFloat(form.monthly_expenses), expected_return: parseFloat(form.expected_return), inflation: parseFloat(form.inflation), target_retirement_age: form.target_retirement_age? parseInt(form.target_retirement_age): undefined}
    const r=await api.post('/fire/calculate', payload); setRes(r.data)
  }
  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold">FIRE Calculator</h1>
      <Card>
        <div className="grid md:grid-cols-2 gap-2">
          <label>Current age<input value={form.current_age} onChange={e=>setForm({...form,current_age:e.target.value})} className="input"/></label>
          <label>Current savings<input value={form.current_savings} onChange={e=>setForm({...form,current_savings:e.target.value})} className="input"/></label>
          <label>Monthly savings<input value={form.monthly_savings} onChange={e=>setForm({...form,monthly_savings:e.target.value})} className="input"/></label>
          <label>Monthly expenses<input value={form.monthly_expenses} onChange={e=>setForm({...form,monthly_expenses:e.target.value})} className="input"/></label>
          <label>Expected return %<input value={form.expected_return} onChange={e=>setForm({...form,expected_return:e.target.value})} className="input"/></label>
          <label>Inflation %<input value={form.inflation} onChange={e=>setForm({...form,inflation:e.target.value})} className="input"/></label>
          <label>Target retirement age<input value={form.target_retirement_age} onChange={e=>setForm({...form,target_retirement_age:e.target.value})} className="input"/></label>
        </div>
        <button onClick={calc} className="btn-primary mt-3">Calculate</button>
        {res && <div className="mt-4 text-sm space-y-1">
          <div>Annual expenses: ₹{res.annual_expenses}</div>
          <div>Required corpus (today): ₹{res.required_corpus_today?.toLocaleString()}</div>
          <div>Required corpus (inflated): ₹{res.required_corpus_inflated?.toLocaleString()}</div>
          <div>Projected corpus: ₹{res.projected_corpus?.toLocaleString()}</div>
          <div>Years to FIRE: {res.estimated_years_to_fire ?? '—'}</div>
          <div>On track: {res.on_track? 'Yes':'No'}</div>
          <div className="text-xs text-slate-500 mt-2">Mathematically correct 4% rule calculation. Estimates only.</div>
        </div>}
      </Card>
    </div>
  )
}
