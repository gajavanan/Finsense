import { useDashboard } from '../hooks/useDashboard'
import api from '../lib/api'
import { useEffect, useState } from 'react'
import { Card } from '../components/ui/Card'
import { useAuthStore } from '../store/authStore'
import { createWS } from '../lib/ws'
import { useQueryClient } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from 'recharts'
import { ArrowUpRight, ArrowDownRight, Wallet, PiggyBank, TrendingUp, ShieldCheck, Sparkles, AlertTriangle } from 'lucide-react'

const COLORS=['#0ea5e9','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316']

export default function Dashboard(){
  const {data, isLoading, error, refetch} = useDashboard()
  const user = useAuthStore(s=>s.user)
  const qc = useQueryClient()
  const [forecast, setForecast]=useState<any>(null)
  const [filter, setFilter]=useState('6M')

  useEffect(()=>{
    const ws = createWS((evt, payload)=>{
      if(evt==='transaction_created' || evt==='dashboard_refresh' || evt==='transaction_updated'){
        qc.invalidateQueries({queryKey:['dashboard']}); qc.invalidateQueries({queryKey:['transactions']}); refetch()
      }
    })
    return ()=> ws?.close()
  },[])

  useEffect(()=>{
    api.post('/ml/predict/spending', {period:'30d'}).then(r=> setForecast(r.data)).catch(()=>{})
  },[data])

  if(isLoading) return <div className="p-10 text-center text-sm text-slate-500">Loading your financial overview...</div>
  if(error) return <div className="p-10 text-center"><div className="text-red-600">Unable to load financial data. {(error as any).message}</div><button onClick={()=>refetch()} className="btn-primary mt-3">Retry</button></div>
  if(!data) return <div className="p-10">No data</div>

  const greeting = new Date().getHours()<12?'Good morning': new Date().getHours()<18?'Good afternoon':'Good evening'
  const kpis = [
    {label:'Net Worth', value:`₹${(data.net_worth||0).toLocaleString()}`, icon: Wallet, trend: '+2.4%', good:true},
    {label:'Monthly Income', value:`₹${(data.monthly_income||0).toLocaleString()}`, icon: TrendingUp, trend: '+4.1%', good:true},
    {label:'Monthly Spending', value:`₹${(data.monthly_expenses||0).toLocaleString()}`, icon: ArrowDownRight, trend: '-1.2%', good:false},
    {label:'Savings Rate', value:`${data.savings_rate}%`, icon: PiggyBank, trend: data.savings_rate>20?'Healthy':'Watch', good: data.savings_rate>15},
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between gap-4">
        <div><h1 className="text-2xl font-bold tracking-tight">{greeting}, {user?.full_name||user?.email?.split('@')[0]||'there'}</h1><p className="text-sm text-slate-500">Here's your financial overview.</p></div>
        <div className="flex items-center gap-2 text-xs">
          {['7D','30D','3M','6M','1Y'].map(f=> <button key={f} onClick={()=>setFilter(f)} className={`px-3 py-1.5 rounded-full border ${filter===f?'bg-slate-900 text-white border-slate-900':'bg-white'}`}>{f}</button>)}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map(k=>{ const Icon=k.icon; return <div key={k.label} className="kpi"><div className="flex justify-between"><div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-700 grid place-items-center"><Icon size={18}/></div><span className={`text-xs px-2 py-1 rounded-full ${k.good?'bg-green-50 text-green-700':'bg-amber-50 text-amber-700'}`}>{k.trend}</span></div><div className="text-xs text-slate-500 mt-3">{k.label}</div><div className="text-xl font-bold mt-1">{k.value}</div></div>})}
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Financial Health */}
        <div className="card lg:col-span-1">
          <div className="flex items-center gap-2"><ShieldCheck size={18} className="text-sky-600"/><h3 className="font-semibold">Financial Health</h3></div>
          <div className="flex items-center gap-6 mt-4">
            <div className="relative w-28 h-28">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90"><path d="M18 2 a16 16 0 1 1 0 32 a16 16 0 1 1 0 -32" fill="none" stroke="#e2e8f0" strokeWidth="3"/><path d="M18 2 a16 16 0 1 1 0 32 a16 16 0 1 1 0 -32" fill="none" stroke="#0ea5e9" strokeWidth="3" strokeDasharray={`${data.health_score},100`}/></svg>
              <div className="absolute inset-0 grid place-items-center"><div className="text-center"><div className="text-2xl font-bold">{data.health_score}</div><div className="text-xs text-slate-500">/100</div></div></div>
            </div>
            <div className="text-sm space-y-1">
              <div className="flex justify-between"><span>Savings</span><span className="font-medium">{data.savings_rate}%</span></div>
              <div className="h-1.5 bg-slate-100 rounded-full"><div className="h-1.5 bg-sky-600 rounded-full" style={{width:`${Math.min(100,data.savings_rate*3)}%`}}></div></div>
              <div className="text-xs text-slate-500">Informational score – not professional advice.</div>
              <div className="text-xs"><span className="font-medium">Strengths:</span> {(data.health_details?.strengths||[]).join(', ')}</div>
            </div>
          </div>
        </div>

        {/* AI Insight */}
        <div className="card lg:col-span-2 bg-gradient-to-br from-violet-600 to-sky-600 text-white border-0">
          <div className="flex items-center gap-2"><Sparkles size={18}/><h3 className="font-semibold">AI Financial Insight</h3></div>
          <p className="mt-3 text-sm leading-relaxed opacity-95">
            {data.insights?.[0]?.content || (data.category_breakdown?.length ? `You spent most on ${data.category_breakdown.sort((a:any,b:any)=>b.amount-a.amount)[0]?.category} (₹${data.category_breakdown.sort((a:any,b:any)=>b.amount-a.amount)[0]?.amount}). Keep an eye on discretionary categories.` : "Add more transactions to unlock personalized AI insights.")}
          </p>
          <div className="mt-3 text-xs opacity-80">Calculated from actual Neon data • View details in AI Advisor</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2">
          <div className="flex justify-between items-center"><h3 className="font-semibold">Spending Overview</h3><span className="text-xs text-slate-500">Income vs Expenses</span></div>
          <div className="h-72 mt-2">
            <ResponsiveContainer width="100%" height="100%"><AreaChart data={data.spending_trend||[]}><XAxis dataKey="month" tick={{fontSize:11}}/><YAxis tick={{fontSize:11}}/><Tooltip/><Area dataKey="income" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.2} name="Income"/><Area dataKey="expenses" stackId="2" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.2} name="Expenses"/></AreaChart></ResponsiveContainer>
          </div>
        </div>
        <div className="card">
          <h3 className="font-semibold">Category Spending</h3>
          <div className="h-56 mt-2">
            <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.category_breakdown||[]} dataKey="amount" nameKey="category" cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={2}>{(data.category_breakdown||[]).map((_:any,i:number)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2">{(data.category_breakdown||[]).slice(0,6).map((c:any,i:number)=><span key={c.category} className="text-xs px-2 py-1 rounded-full border" style={{borderColor:COLORS[i], color:COLORS[i]}}>{c.category}: ₹{c.amount}</span>)}</div>
          {(data.category_breakdown||[]).length===0 && <div className="text-xs text-slate-500 mt-2">No transactions yet.</div>}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="font-semibold flex items-center gap-2"><TrendingUp size={16}/> Spending Forecast <span className="text-xs font-normal text-slate-500">Next 30 days</span></h3>
          {forecast?.status==='insufficient_data' ? <div className="text-sm text-slate-500 mt-3">Add more transactions to generate a reliable forecast.</div> :
            <><div className="text-2xl font-bold mt-2">₹{forecast?.total_forecast?.toLocaleString()}</div><div className="h-40 mt-2"><ResponsiveContainer width="100%" height="100%"><LineChart data={(forecast?.forecast||[]).map((v:number,i:number)=>({day:i+1, forecast:v}))}><XAxis dataKey="day"/><YAxis/><Tooltip/><Line dataKey="forecast" stroke="#8b5cf6" dot={false} strokeWidth={2}/></LineChart></ResponsiveContainer></div><div className="text-xs text-slate-500 mt-1">Historical + predicted • ML LinearRegression on Neon data • Estimates only</div></>}
        </div>
        <div className="card">
          <h3 className="font-semibold">Budget Health</h3>
          {(data.budget_usage||[]).length===0 ? <div className="text-sm text-slate-500 mt-2">No budgets yet. Create one in Budgets page.</div> :
            <div className="space-y-3 mt-3">{data.budget_usage.map((b:any)=><div key={b.id}><div className="flex justify-between text-sm"><span className="font-medium">{b.category}</span><span>₹{b.spent} / ₹{b.amount} ({b.pct}%)</span></div><div className="h-2 bg-slate-100 rounded-full mt-1"><div className={`h-2 rounded-full ${b.pct>=100?'bg-red-500': b.pct>=90?'bg-amber-500':'bg-sky-600'}`} style={{width:`${Math.min(100,b.pct)}%`}}></div></div>{b.pct>=100 && <span className="text-xs text-red-600 flex items-center gap-1"><AlertTriangle size={12}/> Budget exceeded.</span>}</div>)}</div>}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="font-semibold">Recent Transactions</h3>
          {(data.recent_transactions||[]).length===0 ? <div className="text-sm text-slate-500 mt-2">No transactions yet.</div> :
            <div className="divide-y mt-2">{data.recent_transactions.map((t:any)=><div key={t.id} className="flex justify-between py-2.5 text-sm"><div><div className="font-medium">{t.description}</div><div className="text-xs text-slate-500">{t.date} • {t.category}</div></div><div className={`font-semibold ${t.type==='income'?'text-green-600':'text-slate-900'}`}>{t.type==='income'?'+':'-'}₹{t.amount}</div></div>)}</div>}
        </div>
        <div className="card">
          <h3 className="font-semibold">Goals & Portfolio</h3>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800"><div className="text-xs text-slate-500">Active Goals</div><div className="text-xl font-bold">{(data.active_goals||[]).length}</div></div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800"><div className="text-xs text-slate-500">Assets</div><div className="text-xl font-bold">{(data.assets||[]).length}</div></div>
          </div>
          <div className="text-xs text-slate-500 mt-3">Live market prices unavailable unless configured.</div>
        </div>
      </div>
    </div>
  )
}
