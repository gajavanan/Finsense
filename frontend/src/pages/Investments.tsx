import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { useState } from 'react'
import { Card } from '../components/ui/Card'
import { toast } from 'sonner'

export default function Investments(){
  const qc=useQueryClient()
  const {data} = useQuery({queryKey:['investments'], queryFn: async()=> (await api.get('/investments')).data})
  const [form,setForm]=useState({name:'', symbol:'', type:'Stocks', quantity:'', purchase_price:'', current_price:''})
  const createMut=useMutation({
    mutationFn: async(p:any)=> (await api.post('/investments', p)).data,
    onSuccess:()=>{ toast.success('Asset added'); qc.invalidateQueries({queryKey:['investments']})},
    onError:(e:any)=> toast.error(e.message)
  })
  const totalInvested = (data||[]).reduce((s:any,a:any)=> s+ (a.invested||0),0)
  const totalCurrent = (data||[]).reduce((s:any,a:any)=> s+ (a.current_value||0),0)
  const pnl = totalCurrent-totalInvested
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Investments</h1>
      <div className="grid grid-cols-3 gap-4">
        <Card><div className="text-xs text-slate-500">Invested</div><div className="font-bold">₹{totalInvested.toLocaleString()}</div></Card>
        <Card><div className="text-xs text-slate-500">Current</div><div className="font-bold">₹{totalCurrent.toLocaleString()}</div></Card>
        <Card><div className={`font-bold ${pnl>=0?'text-green-600':'text-red-600'}`}>{pnl>=0?'+':''}₹{pnl.toLocaleString()} ({totalInvested? (pnl/totalInvested*100).toFixed(1):0}%)</div><div className="text-xs text-slate-500">P/L</div></Card>
      </div>
      <Card>
        <div className="grid md:grid-cols-6 gap-2">
          <input placeholder="Asset name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} className="input"/>
          <input placeholder="Symbol" value={form.symbol} onChange={e=>setForm({...form,symbol:e.target.value})} className="input"/>
          <select value={form.type} onChange={e=>setForm({...form,type:e.target.value})} className="input"><option>Stocks</option><option>Mutual funds</option><option>Bonds</option><option>Cash</option><option>Crypto</option></select>
          <input placeholder="Qty" type="number" value={form.quantity} onChange={e=>setForm({...form,quantity:e.target.value})} className="input"/>
          <input placeholder="Purchase" type="number" value={form.purchase_price} onChange={e=>setForm({...form,purchase_price:e.target.value})} className="input"/>
          <input placeholder="Current" type="number" value={form.current_price} onChange={e=>setForm({...form,current_price:e.target.value})} className="input"/>
        </div>
        <div className="text-xs text-slate-500 mt-1">Live market prices unavailable unless configured.</div>
        <button onClick={()=> createMut.mutate({name: form.name, symbol: form.symbol||undefined, type: form.type, quantity: parseFloat(form.quantity), purchase_price: parseFloat(form.purchase_price), current_price: form.current_price? parseFloat(form.current_price): undefined})} className="btn-primary mt-2">Add Asset</button>
      </Card>
      <Card>
        {(data||[]).length===0 ? <div className="text-sm text-slate-500">No investments yet.</div> :
          <table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Name</th><th>Type</th><th>Qty</th><th>Invested</th><th>Current</th><th>P/L</th></tr></thead><tbody>{(data||[]).map((a:any)=><tr key={a.id} className="border-t"><td>{a.name} {a.symbol && `(${a.symbol})`}</td><td>{a.type}</td><td>{a.quantity}</td><td>₹{a.invested}</td><td>₹{a.current_value}</td><td className={a.pnl>=0?'text-green-600':'text-red-600'}>{a.pnl} ({a.pct}%)</td></tr>)}</tbody></table>}
      </Card>
    </div>
  )
}
