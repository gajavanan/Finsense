import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import { useUIStore } from './store/uiStore'
import Layout from './components/layout/Layout'
import Protected from './routes/Protected'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import AddTransaction from './pages/AddTransaction'
import ImportStatement from './pages/ImportStatement'
import Budgets from './pages/Budgets'
import Goals from './pages/Goals'
import Investments from './pages/Investments'
import Subscriptions from './pages/Subscriptions'
import Reports from './pages/Reports'
import FIRE from './pages/FIRE'
import Advisor from './pages/Advisor'
import Notifications from './pages/Notifications'
import Settings from './pages/Settings'
import MLModels from './pages/MLModels'
import { Toaster } from 'sonner'

const qc=new QueryClient()

function AppInner(){
  const init=useAuthStore((s:any)=>s.init)
  const dark=useUIStore((s:any)=>s.dark)
  useEffect(()=>{ init(); const d=localStorage.getItem('theme')==='dark'; document.documentElement.classList.toggle('dark', d)},[])
  useEffect(()=>{
    const onOnline=()=> qc.invalidateQueries()
    window.addEventListener('online', onOnline); window.addEventListener('offline', onOnline)
    return ()=>{ window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOnline)}
  },[])
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing/>}/>
        <Route path="/login" element={<Login/>}/>
        <Route path="/register" element={<Register/>}/>
        <Route path="/forgot-password" element={<ForgotPassword/>}/>
        <Route path="/reset-password" element={<ResetPassword/>}/>
        <Route path="/dashboard" element={<Protected><Layout><Dashboard/></Layout></Protected>}/>
        <Route path="/transactions" element={<Protected><Layout><Transactions/></Layout></Protected>}/>
        <Route path="/add-transaction" element={<Protected><Layout><AddTransaction/></Layout></Protected>}/>
        <Route path="/import" element={<Protected><Layout><ImportStatement/></Layout></Protected>}/>
        <Route path="/ml-models" element={<Protected><Layout><MLModels/></Layout></Protected>}/>
        <Route path="/budgets" element={<Protected><Layout><Budgets/></Layout></Protected>}/>
        <Route path="/goals" element={<Protected><Layout><Goals/></Layout></Protected>}/>
        <Route path="/investments" element={<Protected><Layout><Investments/></Layout></Protected>}/>
        <Route path="/subscriptions" element={<Protected><Layout><Subscriptions/></Layout></Protected>}/>
        <Route path="/reports" element={<Protected><Layout><Reports/></Layout></Protected>}/>
        <Route path="/fire" element={<Protected><Layout><FIRE/></Layout></Protected>}/>
        <Route path="/advisor" element={<Protected><Layout><Advisor/></Layout></Protected>}/>
        <Route path="/notifications" element={<Protected><Layout><Notifications/></Layout></Protected>}/>
        <Route path="/settings" element={<Protected><Layout><Settings/></Layout></Protected>}/>
        <Route path="*" element={<Navigate to="/" replace/>}/>
      </Routes>
    </BrowserRouter>
  )
}

export default function App(){
  return <QueryClientProvider client={qc}><AppInner/><Toaster richColors/></QueryClientProvider>
}
