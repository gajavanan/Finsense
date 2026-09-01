import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { useState, useEffect } from 'react'
import { Card } from '../components/ui/Card'
import { createWS } from '../lib/ws'
import { toast } from 'sonner'
import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

export default function Transactions(){
  const qc=useQueryClient()
  const [page,setPage]=useState(1); const [search,setSearch]=useState(''); const [category,setCategory]=useState(''); const [type,setType]=useState('')
  const [dateFrom,setDateFrom]=useState(''); const [dateTo,setDateTo]=useState('')
  const [editing,setEditing]=useState<any>(null)
  const [editCat,setEditCat]=useState('')

  const {data, isLoading, error} = useQuery({
    queryKey:['transactions',page,search,category,type,dateFrom,dateTo],
    queryFn: async()=> (await api.get('/transactions', {params:{
      page, limit:20,
      search: search||undefined,
      category: category||undefined,
      transaction_type: type||undefined,
      date_from: dateFrom||undefined,
      date_to: dateTo||undefined
    }})).data
  })

  useEffect(()=>{
    const ws = createWS((evt)=>{ if(evt==='transaction_created' || evt==='transaction_updated' || evt==='transaction_deleted' || evt==='transactions_imported') qc.invalidateQueries({queryKey:['transactions']}) })
    return ()=> ws?.close()
  },[])

  const deleteMut=useMutation({
    mutationFn: async(id:string)=> (await api.delete(`/transactions/${id}`)).data,
    onSuccess:()=> {toast.success('Deleted'); qc.invalidateQueries({queryKey:['transactions']}); qc.invalidateQueries({queryKey:['dashboard']})},
    onError:(e:any)=> toast.error(e.message)
  })

  const editMut=useMutation({
    mutationFn: async({id, category}:{id:string, category:string})=> (await api.put(`/transactions/${id}`, {category})).data,
    onSuccess:()=> {toast.success('Category updated'); setEditing(null); qc.invalidateQueries({queryKey:['transactions']}); qc.invalidateQueries({queryKey:['dashboard']})},
    onError:(e:any)=> toast.error(e.message)
  })

  const recategorizeMut = useMutation({
    mutationFn: async() => (await api.post('/transactions/recategorize')).data,
    onSuccess: (res: any) => {
      toast.success(`Re-categorized ${res.changed} transactions (${res.unchanged} unchanged)`)
      qc.invalidateQueries({queryKey: ['transactions']})
      qc.invalidateQueries({queryKey: ['dashboard']})
    },
    onError: (e: any) => toast.error(e.message || 'Failed to re-categorize')
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <h1 className="text-2xl font-bold">Transactions</h1>
        <div className="flex gap-2 items-center">
          <button 
            onClick={() => recategorizeMut.mutate()} 
            disabled={recategorizeMut.isPending} 
            className="px-4 py-2 border rounded-lg text-sm bg-gradient-to-r from-sky-50 to-indigo-50 hover:from-sky-100 hover:to-indigo-100 dark:from-slate-800 dark:to-slate-700 text-sky-700 dark:text-sky-300 font-medium flex items-center gap-1.5 transition"
          >
            <Sparkles size={16} className={recategorizeMut.isPending ? "animate-spin" : "text-sky-500"} />
            {recategorizeMut.isPending ? 'Categorizing...' : 'Re-categorize with AI'}
          </button>
          <Link to="/add-transaction" className="btn-primary">Add Transaction</Link>
          <Link to="/import" className="px-4 py-2 border rounded-lg text-sm">Import Statement</Link>
        </div>
      </div>

      <Card>
        <div className="flex flex-wrap gap-2 mb-3">
          <input placeholder="Search description/merchant" value={search} onChange={e=>setSearch(e.target.value)} className="input w-48"/>
          <select value={category} onChange={e=>setCategory(e.target.value)} className="input w-40">
            <option value="">All categories</option>
            <option>Food</option><option>Groceries</option><option>Transport</option><option>Shopping</option><option>Entertainment</option>
            <option>Bills</option><option>Utilities</option><option>Rent</option><option>EMI</option><option>Healthcare</option><option>Education</option>
            <option>Travel</option><option>Investment</option><option>Salary</option><option>Transfer</option><option>Other</option>
          </select>
          <select value={type} onChange={e=>setType(e.target.value)} className="input w-36">
            <option value="">All</option><option value="income">Income</option><option value="expense">Expense</option>
          </select>
          <input type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)} className="input w-40"/>
          <input type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)} className="input w-40"/>
          {(search||category||type||dateFrom||dateTo) && <button onClick={()=>{setSearch('');setCategory('');setType('');setDateFrom('');setDateTo('')}} className="px-3 py-1 text-xs border rounded">Clear</button>}
        </div>
        {isLoading ? <div>Loading...</div> : error ? <div className="text-red-600">Unable to load your financial data. {(error as any).message}</div> :
          (data?.data?.length===0 ? <div className="text-sm text-slate-500">No transactions found. <Link to="/add-transaction" className="text-sky-600">Add your first</Link> or <Link to="/import" className="text-sky-600">import CSV</Link>.</div> :
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-slate-500 border-b">
                  <th className="py-2">Date</th><th>Merchant</th><th>Description</th><th>Category</th><th>Payment Method</th><th>Amount</th><th></th>
                </tr></thead>
                <tbody>{data.data.map((t:any)=>{
                  const tt = t.transaction_type || t.type
                  const isInc = tt==='income'
                  return (
                    <tr key={t.id} className="border-b">
                      <td className="py-2">{t.date}</td>
                      <td>{t.merchant||'-'}</td>
                      <td>{t.description} {t.is_anomaly && <span className="ml-1 text-xs px-1 py-0.5 bg-amber-100 text-amber-700 rounded">Unusual</span>}</td>
                      <td>
                        {editing?.id===t.id ? (
                          <div className="flex gap-1">
                            <select value={editCat} onChange={e=>setEditCat(e.target.value)} className="input text-xs py-1">
                              <option>Food</option><option>Groceries</option><option>Transport</option><option>Shopping</option><option>Entertainment</option><option>Bills</option><option>Utilities</option><option>Rent</option><option>EMI</option><option>Healthcare</option><option>Education</option><option>Travel</option><option>Investment</option><option>Salary</option><option>Transfer</option><option>Other</option>
                            </select>
                            <button onClick={()=>editMut.mutate({id:t.id, category:editCat})} className="text-xs bg-sky-600 text-white px-2 rounded">Save</button>
                            <button onClick={()=>setEditing(null)} className="text-xs px-2">Cancel</button>
                          </div>
                        ) : (
                          <span className="cursor-pointer hover:underline" onClick={()=>{setEditing(t); setEditCat(t.category)}}>{t.category||'Other'}</span>
                        )}
                      </td>
                      <td>{t.payment_method||'-'}</td>
                      <td className={isInc?'text-green-600 font-semibold':'text-red-600 font-semibold'}>
                        {isInc?'+':'-'}₹{Number(t.amount).toLocaleString()}
                      </td>
                      <td>
                        <button onClick={()=>deleteMut.mutate(t.id)} className="text-red-600 text-xs">Delete</button>
                      </td>
                    </tr>
                  )
                })}</tbody>
              </table>
              <div className="flex gap-2 mt-3"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="px-3 py-1 border rounded">Prev</button><span className="text-sm">Page {page} • Total {data.count}</span><button onClick={()=>setPage(p=>p+1)} className="px-3 py-1 border rounded">Next</button></div>
            </div>
          )}
      </Card>
    </div>
  )
}
