import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useUIStore } from '../../store/uiStore'
import { LayoutDashboard, Receipt, PiggyBank, Target, TrendingUp, RefreshCw, FileText, Flame, Bot, Bell, Settings, LogOut, Moon, Sun, Search, Sparkles, Shield } from 'lucide-react'
import { useState } from 'react'

const nav = [
  {to:'/', label:'Dashboard', icon: LayoutDashboard},
  {to:'/transactions', label:'Transactions', icon: Receipt},
  {to:'/budgets', label:'Budgets', icon: PiggyBank},
  {to:'/goals', label:'Goals', icon: Target},
  {to:'/investments', label:'Investments', icon: TrendingUp},
  {to:'/subscriptions', label:'Subscriptions', icon: RefreshCw},
  {to:'/reports', label:'Reports', icon: FileText},
  {to:'/fire', label:'FIRE', icon: Flame},
  {to:'/advisor', label:'AI Advisor', icon: Bot},
  {to:'/notifications', label:'Notifications', icon: Bell},
]

export default function Layout({children}:any){
  const loc=useLocation(); const nav2=useNavigate()
  const {user, logout} = useAuthStore()
  const {dark, toggle} = useUIStore()
  const [mobileOpen, setMobileOpen]=useState(false)
  if(!user) return <div className={dark?'dark':''}>{children}</div>
  return (
    <div className={dark?'dark':''}>
      <div className="min-h-screen flex bg-[rgb(var(--bg))]">
        {/* Sidebar */}
        <aside className={`${mobileOpen?'flex':'hidden'} md:flex w-[280px] shrink-0 flex-col bg-white dark:bg-slate-900 border-r border-slate-200/70 dark:border-slate-800 sticky top-0 h-screen`}>
          <div className="px-6 py-6 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-600 flex items-center justify-center text-white"><Sparkles size={18}/></div>
            <div><div className="font-bold tracking-tight">FinSense</div><div className="text-xs text-slate-500">AI Finance</div></div>
          </div>
          <div className="px-3 flex-1 overflow-auto">
            <div className="section-title px-3 mb-2">Overview</div>
            <nav className="space-y-1">
              {nav.map(n=>{
                const active = loc.pathname===n.to
                const Icon=n.icon
                return <Link key={n.to} to={n.to} onClick={()=>setMobileOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${active?'bg-slate-900 text-white dark:bg-white dark:text-slate-900':'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}><Icon size={18}/>{n.label}</Link>
              })}
            </nav>
            <div className="mt-6 section-title px-3">Account</div>
            <nav className="space-y-1">
              <Link to="/settings" className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm ${loc.pathname==='/settings'?'bg-slate-900 text-white dark:bg-white dark:text-slate-900':'text-slate-600 hover:bg-slate-100'}`}><Settings size={18}/> Settings</Link>
            </nav>
            <div className="mt-6 mx-3 p-4 rounded-2xl bg-gradient-to-br from-sky-600 to-violet-600 text-white">
              <div className="text-sm font-semibold flex items-center gap-2"><Shield size={16}/> Secure & private</div>
              <div className="text-xs opacity-80 mt-1">Your data is encrypted and isolated per user.</div>
            </div>
          </div>
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center text-sm font-bold">{(user.email||'U')[0].toUpperCase()}</div>
            <div className="flex-1 min-w-0"><div className="text-sm font-medium truncate">{user.full_name||user.email}</div><div className="text-xs text-slate-500 truncate">{user.email}</div></div>
            <button onClick={async()=>{await logout(); nav2('/login')}} className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800"><LogOut size={16}/></button>
          </div>
        </aside>

        <div className="flex-1 min-w-0 flex flex-col">
          {/* Topbar */}
          <header className="h-[64px] sticky top-0 z-20 bg-white/80 dark:bg-slate-900/80 backdrop-blur border-b border-slate-200/70 dark:border-slate-800 flex items-center justify-between px-4 md:px-6">
            <div className="flex items-center gap-3">
              <button onClick={()=>setMobileOpen(!mobileOpen)} className="md:hidden p-2 rounded-xl border">☰</button>
              <div className="hidden md:flex items-center gap-2 text-sm text-slate-500"><Search size={16}/> <span>Search transactions, budgets...</span></div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={toggle} className="w-9 h-9 grid place-items-center rounded-xl border bg-white dark:bg-slate-800">{dark?<Sun size={16}/>:<Moon size={16}/>}</button>
              <Link to="/notifications" className="w-9 h-9 grid place-items-center rounded-xl border bg-white dark:bg-slate-800"><Bell size={16}/></Link>
              <Link to="/settings" className="w-9 h-9 rounded-full bg-slate-900 text-white grid place-items-center text-sm">{(user.email||'U')[0].toUpperCase()}</Link>
            </div>
          </header>
          <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-[1400px] w-full mx-auto">{children}</main>
        </div>
      </div>
    </div>
  )
}
