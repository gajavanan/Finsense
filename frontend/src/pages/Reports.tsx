import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { useState } from 'react'
import { Card } from '../components/ui/Card'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function Reports(){
  const [month,setMonth]=useState(new Date().toISOString().slice(0,7))
  const [year,setYear]=useState(String(new Date().getFullYear()))
  const monthly = useQuery({queryKey:['report-monthly',month], queryFn: async()=> (await api.get('/reports/monthly',{params:{month}})).data})
  const annual = useQuery({queryKey:['report-annual',year], queryFn: async()=> (await api.get('/reports/annual',{params:{year}})).data})

  const exportCSV=(data:any, name:string)=>{
    const rows = [['Period', data.period], ['Income', data.income], ['Expenses', data.expenses], ['Savings', data.savings]]
    const csv = rows.map(r=> r.join(',')).join('\n') + '\nCategory,Amount\n' + (data.category_breakdown||[]).map((c:any)=> `${c.category},${c.amount}`).join('\n')
    const blob=new Blob([csv], {type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=`${name}.csv`; a.click()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Reports</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold">Monthly Report <input type="month" value={month} onChange={e=>setMonth(e.target.value)} className="input w-40 inline ml-2"/></h3>
          {monthly.isLoading? <div>Loading...</div> : <div className="mt-2 text-sm space-y-1">
            <div>Income: ₹{monthly.data?.income}</div><div>Expenses: ₹{monthly.data?.expenses}</div><div>Savings: ₹{monthly.data?.savings}</div>
            <div>Transactions: {monthly.data?.transaction_count}</div>
            <div className="mt-2">{(monthly.data?.category_breakdown||[]).map((c:any)=><div key={c.category}>{c.category}: ₹{c.amount}</div>)}</div>
            <button onClick={()=>exportCSV(monthly.data, `monthly-${month}`)} className="btn-primary mt-2">Export CSV</button>
          </div>}
        </Card>
        <Card>
          <h3 className="font-semibold">Annual Report <input type="number" value={year} onChange={e=>setYear(e.target.value)} className="input w-24 inline ml-2"/></h3>
          {annual.isLoading? <div>Loading...</div> : <div className="mt-2">
            <div className="text-sm">Income: ₹{annual.data?.income} • Expenses: ₹{annual.data?.expenses} • Savings: ₹{annual.data?.savings}</div>
            <div className="h-48 mt-2"><ResponsiveContainer width="100%" height="100%"><BarChart data={annual.data?.monthly_trend||[]}><XAxis dataKey="month"/><YAxis/><Tooltip/><Bar dataKey="income" fill="#10b981"/><Bar dataKey="expenses" fill="#ef4444"/></BarChart></ResponsiveContainer></div>
            <button onClick={()=>exportCSV(annual.data, `annual-${year}`)} className="btn-primary mt-2">Export CSV</button>
          </div>}
        </Card>
      </div>
    </div>
  )
}
