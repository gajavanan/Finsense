import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Card } from '../components/ui/Card'
import { toast } from 'sonner'

const CATEGORIES = ["Food","Groceries","Transport","Shopping","Entertainment","Bills","Utilities","Rent","EMI","Healthcare","Education","Travel","Investment","Salary","Transfer","Other"]
const PAYMENTS = ["UPI","Debit Card","Credit Card","Cash","Bank Transfer","Other"]

export default function AddTransaction(){
  const qc = useQueryClient()
  const [form,setForm]=useState<any>({
    date: new Date().toISOString().slice(0,10),
    description:'',
    merchant:'',
    amount:'',
    transaction_type:'expense',
    category:'',
    payment_method:'UPI'
  })
  const [msg,setMsg]=useState('')

  const mut = useMutation({
    mutationFn: async (payload:any)=> (await api.post('/transactions', payload)).data,
    onSuccess: (res)=>{
      toast.success('Transaction created')
      setMsg(`Success: ${res.category} • Confidence ${res.confidence_score||res.category?'' :''} • ID ${res.id.slice(0,8)}`)
      qc.invalidateQueries({queryKey:['transactions']})
      qc.invalidateQueries({queryKey:['dashboard']})
      // reset but keep date
      setForm((f:any)=>({...f, description:'', merchant:'', amount:'', category:''}))
    },
    onError:(e:any)=>{
      const m = e.message || 'Failed'
      setMsg(m)
      toast.error(m)
    }
  })

  const predict = async()=>{
    if(!form.description){ toast.error('Enter description first'); return}
    try{
      const r=await api.post('/ml/predict/category',{description: form.description, merchant: form.merchant, amount: parseFloat(form.amount)||0, payment_method: form.payment_method})
      if(r.data.category) setForm((f:any)=>({...f, category: r.data.category}))
      toast.success(`Predicted: ${r.data.category} (${r.data.confidence})`)
    }catch(e:any){ toast.error(e.message)}
  }

  const onSubmit = ()=>{
    setMsg('')
    if(!form.description.trim()){ setMsg('Description required'); return}
    const amt = parseFloat(form.amount)
    if(isNaN(amt) || amt<=0){ setMsg('Amount must be positive'); return}
    if(!form.date){ setMsg('Date required'); return}
    mut.mutate({
      date: form.date,
      description: form.description,
      merchant: form.merchant || undefined,
      amount: amt,
      transaction_type: form.transaction_type,
      category: form.category || undefined,
      payment_method: form.payment_method,
      source: 'manual'
    })
  }

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold">Add Transaction</h1>
      <Card>
        <div className="grid md:grid-cols-2 gap-4">
          <div><label className="text-sm font-medium">Date</label><input type="date" value={form.date} onChange={e=>setForm({...form,date:e.target.value})} className="input mt-1 w-full"/></div>
          <div><label className="text-sm font-medium">Amount (₹)</label><input type="number" min="0" step="0.01" placeholder="250" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})} className="input mt-1 w-full"/></div>
          <div className="md:col-span-2"><label className="text-sm font-medium">Description</label><input placeholder="Dinner at restaurant" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} className="input mt-1 w-full"/></div>
          <div><label className="text-sm font-medium">Merchant</label><input placeholder="A2B" value={form.merchant} onChange={e=>setForm({...form,merchant:e.target.value})} className="input mt-1 w-full"/></div>
          <div><label className="text-sm font-medium">Income / Expense</label><select value={form.transaction_type} onChange={e=>setForm({...form,transaction_type:e.target.value})} className="input mt-1 w-full"><option value="expense">Expense</option><option value="income">Income</option></select></div>
          <div><label className="text-sm font-medium">Category</label><div className="flex gap-2 mt-1"><select value={form.category} onChange={e=>setForm({...form,category:e.target.value})} className="input flex-1"><option value="">Auto (ML + rule)</option>{CATEGORIES.map(c=><option key={c} value={c}>{c}</option>)}</select><button onClick={predict} className="px-3 py-2 border rounded text-xs whitespace-nowrap">ML Predict</button></div></div>
          <div><label className="text-sm font-medium">Payment Method</label><select value={form.payment_method} onChange={e=>setForm({...form,payment_method:e.target.value})} className="input mt-1 w-full">{PAYMENTS.map(p=><option key={p}>{p}</option>)}</select></div>
        </div>
        <button onClick={onSubmit} disabled={mut.isPending} className="btn-primary mt-4 w-full">{mut.isPending?'Saving...':'Save Transaction'}</button>
        {msg && <div className={`mt-3 p-2 rounded text-sm ${msg.startsWith('Success')?'bg-green-50 text-green-700':'bg-red-50 text-red-700'}`}>{msg}</div>}
        <div className="text-xs text-slate-500 mt-2">Dashboard will refresh automatically after creation (no reload needed).</div>
      </Card>
    </div>
  )
}
