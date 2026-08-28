import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { useState, useEffect } from 'react'
import { Card } from '../components/ui/Card'
import { createWS } from '../lib/ws'
import { toast } from 'sonner'

export default function Transactions(){
  const qc=useQueryClient()
  const [page,setPage]=useState(1); const [search,setSearch]=useState(''); const [category,setCategory]=useState(''); const [type,setType]=useState('')
  const [showAdd,setShowAdd]=useState(false)
  const [form,setForm]=useState<any>({date: new Date().toISOString().slice(0,10), description:'', amount:'', type:'expense', category:'', payment_method:'UPI', merchant:'', notes:''})
  const [predict,setPredict]=useState<any>(null)

  const {data, isLoading, error} = useQuery({
    queryKey:['transactions',page,search,category,type],
    queryFn: async()=> (await api.get('/transactions', {params:{page, limit:20, search: search||undefined, category: category||undefined, type: type||undefined}})).data
  })

  useEffect(()=>{
    const ws = createWS((evt)=>{ if(evt==='transaction_created' || evt==='transaction_updated' || evt==='transaction_deleted') qc.invalidateQueries({queryKey:['transactions']}) })
    return ()=> ws?.close()
  },[])

  const createMut = useMutation({
    mutationFn: async (payload:any)=> (await api.post('/transactions', payload)).data,
    onSuccess: async (res)=>{
      toast.success('Transaction created')
      // anomaly check already done backend, but also run explicit
      try{ const a=await api.post('/ml/detect/anomaly',{amount: parseFloat(form.amount), category: res.category}); if(a.data.is_anomaly) toast.warning('Anomaly: '+a.data.reason)}catch{}
      qc.invalidateQueries({queryKey:['transactions']}); qc.invalidateQueries({queryKey:['dashboard']}); setShowAdd(false)
    },
    onError:(e:any)=> toast.error(e.message)
  })

  const deleteMut=useMutation({
    mutationFn: async(id:string)=> (await api.delete(`/transactions/${id}`)).data,
    onSuccess:()=> {toast.success('Deleted'); qc.invalidateQueries({queryKey:['transactions']}); qc.invalidateQueries({queryKey:['dashboard']})}
  })

  const doPredict=async()=>{
    try{ const r=await api.post('/ml/predict/category',{description: form.description, merchant: form.merchant, amount: parseFloat(form.amount)||0, payment_method: form.payment_method}); setPredict(r.data); if(r.data.category) setForm((f:any)=>({...f, category: r.data.category})) }catch(e:any){ toast.error(e.message)}
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center"><h1 className="text-2xl font-bold">Transactions</h1><button onClick={()=>setShowAdd(!showAdd)} className="btn-primary">{showAdd?'Close':'Add Transaction'}</button></div>

      {showAdd && <Card><h3 className="font-semibold mb-2">Add Transaction</h3>
        <div className="grid md:grid-cols-3 gap-2">
          <input type="date" value={form.date} onChange={e=>setForm({...form,date:e.target.value})} className="input"/>
          <input placeholder="Description" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} className="input"/>
          <input placeholder="Amount" type="number" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})} className="input"/>
          <select value={form.type} onChange={e=>setForm({...form,type:e.target.value})} className="input"><option value="expense">expense</option><option value="income">income</option><option value="transfer">transfer</option></select>
          <div className="flex gap-1"><input placeholder="Category" value={form.category} onChange={e=>setForm({...form,category:e.target.value})} className="input"/><button onClick={doPredict} className="px-2 bg-slate-200 rounded text-xs">ML Predict</button></div>
          <input placeholder="Merchant" value={form.merchant} onChange={e=>setForm({...form,merchant:e.target.value})} className="input"/>
          <select value={form.payment_method} onChange={e=>setForm({...form,payment_method:e.target.value})} className="input"><option>UPI</option><option>Card</option><option>Cash</option><option>Transfer</option></select>
          <input placeholder="Notes" value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} className="input"/>
        </div>
        {predict && <div className="text-xs mt-2">Predicted: <b>{predict.category}</b> confidence {predict.confidence}</div>}
        <button onClick={()=> createMut.mutate({...form, amount: parseFloat(form.amount)})} disabled={createMut.isPending} className="btn-primary mt-3">{createMut.isPending?'Saving...':'Save'}</button>
      </Card>}

      <Card>
        <div className="flex flex-wrap gap-2 mb-3">
          <input placeholder="Search description" value={search} onChange={e=>setSearch(e.target.value)} className="input w-48"/>
          <select value={category} onChange={e=>setCategory(e.target.value)} className="input w-40"><option value="">All categories</option><option>Food</option><option>Shopping</option><option>Transport</option><option>Bills</option><option>Entertainment</option><option>Healthcare</option><option>Education</option><option>Travel</option><option>Investment</option><option>Rent</option><option>Salary</option><option>Subscriptions</option><option>Other</option></select>
          <select value={type} onChange={e=>setType(e.target.value)} className="input w-36"><option value="">All types</option><option value="income">income</option><option value="expense">expense</option><option value="transfer">transfer</option></select>
        </div>
        {isLoading ? <div>Loading...</div> : error ? <div className="text-red-600">Unable to load your financial data. {(error as any).message}</div> :
          (data?.data?.length===0 ? <div className="text-sm text-slate-500">No transactions found. Add your first transaction above.</div> :
            <div className="overflow-auto"><table className="w-full text-sm"><thead><tr className="text-left text-slate-500 border-b"><th>Date</th><th>Description</th><th>Amount</th><th>Type</th><th>Category</th><th>Merchant</th><th></th></tr></thead><tbody>{data.data.map((t:any)=><tr key={t.id} className="border-b"><td>{t.date}</td><td>{t.description}</td><td className={t.type==='income'?'text-green-600':'text-red-600'}>₹{t.amount}</td><td>{t.type}</td><td>{t.category}</td><td>{t.merchant}</td><td><button onClick={()=>deleteMut.mutate(t.id)} className="text-red-600 text-xs">Delete</button></td></tr>)}</tbody></table>
            <div className="flex gap-2 mt-3"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="px-3 py-1 border rounded">Prev</button><span className="text-sm">Page {page} • Total {data.count}</span><button onClick={()=>setPage(p=>p+1)} className="px-3 py-1 border rounded">Next</button></div></div>
          )}
      </Card>
    </div>
  )
}
