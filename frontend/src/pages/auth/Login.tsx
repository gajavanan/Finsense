import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuthStore } from '../../store/authStore'

const schema=z.object({ email: z.string().email(), password: z.string().min(6)})

export default function Login(){
  const nav=useNavigate(); const [loading,setLoading]=useState(false); const [err,setErr]=useState(''); const [showResend,setShowResend]=useState(false); const [resendLoading,setResendLoading]=useState(false); const [resendMsg,setResendMsg]=useState('')
  const login = useAuthStore(s=>s.login)
  const {register, handleSubmit, formState:{errors}, getValues} = useForm({resolver: zodResolver(schema)})
  const onSubmit=async (data:any)=>{
    setLoading(true); setErr('')
    // safe dev log (no password)
    console.log("Login email:", data.email);
    console.log("Login endpoint:", import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1');
    try{
      const emailNorm = data.email.trim().toLowerCase();
      await login(emailNorm, data.password)
      toast.success('Login successful')
      nav('/')
    }catch(e:any){
      const msg = e.message || '';
      const status = (e as any).status;
      const code = (e as any).code;
      // distinguish according to PHASE 10 spec
      if(status===0 || code==='ERR_CONNECTION_REFUSED' || msg.includes('Failed to fetch') || msg.includes('Network Error') || msg.includes('Unable to connect')){
        setErr('Unable to connect to FinSense backend. Ensure backend is running on http://localhost:8000 (uvicorn app.main:app --reload --host 127.0.0.1 --port 8000)');
        toast.error('FinSense server is unavailable.');
      } else if(code==='EMAIL_NOT_VERIFIED' || status===403 || msg.includes('Email not verified') || msg.includes('verify your email')){
        setErr('Please verify your email before signing in. Check your inbox for verification link.');
        toast.error('Email not verified. Check your inbox.');
        setShowResend(true)
      } else if(status===401 || msg.includes('Invalid email or password')){
        setErr('Invalid email or password');
        toast.error('Invalid email or password');
      } else if(status===422){
        setErr('Invalid request. Check email/password format.');
        toast.error('Invalid request.');
      } else if(status===500){
        setErr('Server error. Try again later.');
        toast.error('Server error.');
      } else {
        setErr(msg || 'Invalid email or password');
        toast.error(msg || 'Invalid email or password');
      }
    } finally{ setLoading(false)}
  }
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900">
      <form onSubmit={handleSubmit(onSubmit)} className="card w-full max-w-md space-y-4">
        <div className="text-center"><div className="w-10 h-10 rounded-xl bg-sky-600 text-white grid place-items-center mx-auto">●</div><h1 className="text-2xl font-bold mt-3">Welcome back</h1><p className="text-sm text-slate-500">Sign in to FinSense</p></div>
        {err && <div className="bg-red-50 text-red-700 p-2.5 rounded-xl text-sm">{err}</div>}
        <div><label className="text-sm font-medium">Email</label><input {...register('email')} className="input mt-1" placeholder="you@example.com"/><p className="text-xs text-red-500">{errors.email?.message as any}</p></div>
        <div><label className="text-sm font-medium">Password</label><input type="password" {...register('password')} className="input mt-1" placeholder="••••••••"/><p className="text-xs text-red-500">{errors.password?.message as any}</p></div>
        <button disabled={loading} className="btn-primary w-full">{loading?'Signing in...':'Sign in'}</button>
        {showResend && <div className="bg-amber-50 border border-amber-200 p-3 rounded-xl text-sm space-y-2"><p className="text-amber-800">Your email is not verified.</p><button type="button" disabled={resendLoading} onClick={async()=>{setResendLoading(true); setResendMsg(''); try{ const em=getValues('email'); if(!em){setResendMsg('Enter email first'); return} const api=(await import('../../lib/api')).default; await api.post('/auth/resend-verification',{email:em}); setResendMsg('If an account exists, a new verification email has been sent. Check inbox/spam.'); toast.success('Verification email resent')}catch(e:any){setResendMsg(e.message)} finally{setResendLoading(false)}} } className="btn-primary w-full text-sm">{resendLoading?'Sending...':'Resend verification email'}</button>{resendMsg && <p className="text-xs text-slate-600">{resendMsg}</p>}</div>}
        <div className="text-sm text-center flex justify-between"><Link to="/register" className="text-sky-600 font-medium">Create account</Link><Link to="/forgot-password" className="text-slate-500">Forgot password?</Link></div>
      </form>
    </div>
  )
}
