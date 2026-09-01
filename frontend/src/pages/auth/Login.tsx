import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuthStore } from '../../store/authStore'
import api, { API_URL } from '../../lib/api'

const schema=z.object({ email: z.string().email(), password: z.string().min(6)})

export default function Login(){
  const nav=useNavigate(); const [loading,setLoading]=useState(false); const [err,setErr]=useState(''); const [showResend,setShowResend]=useState(false); const [resendLoading,setResendLoading]=useState(false); const [resendMsg,setResendMsg]=useState('')
  const login = useAuthStore(s=>s.login)
  const {register, handleSubmit, formState:{errors}, getValues} = useForm({resolver: zodResolver(schema)})

  const handleResend = async () => {
    console.log("Resend verification clicked");
    const base = (api.defaults.baseURL as string) || API_URL;
    const endpoint = `${base}/auth/resend-verification`;
    console.log("Resend endpoint:", endpoint);
    console.log("Resend method: POST");
    setResendLoading(true);
    setResendMsg('');
    try {
      const raw = getValues('email');
      console.log("Resend email field present:", !!raw);
      if (!raw || !String(raw).trim()) {
        const msg = 'Enter email first';
        console.log("Resend abort:", msg);
        setResendMsg(msg);
        return;
      }
      const em = String(raw).trim().toLowerCase();
      console.log("Resend request body email:", em);
      console.log("Resend sending POST to", endpoint, "with body {email: <email>}");
      const res = await api.post('/auth/resend-verification', { email: em });
      console.log("Resend response status:", res.status);
      console.log("Resend response data:", res.data);
      setResendMsg('If an account exists, a new verification email has been sent. Check inbox/spam.');
      toast.success('Verification email resent');
    } catch (e: any) {
      console.error("Resend verification failed:", e);
      console.log("Resend error status:", (e as any).status);
      console.log("Resend error message:", e.message);
      // Do not swallow - show to user
      const msg = e.message || 'Failed to resend verification email';
      setResendMsg(msg);
      // also surface via toast for visibility
      if ((e as any).status === 429) {
        toast.error(msg);
      } else if ((e as any).status === 0) {
        toast.error('Unable to connect to backend at ' + base);
      }
    } finally {
      setResendLoading(false);
      console.log("Resend loading cleared");
    }
  };
  const onSubmit=async (data:any)=>{
    setLoading(true); setErr('')
    // safe dev log (no password)
    console.log("Login email:", data.email);
    console.log("Login endpoint:", API_URL);
    try{
      const emailNorm = data.email.trim().toLowerCase();
      await login(emailNorm, data.password)
      toast.success('Login successful')
      nav('/dashboard')
    }catch(e:any){
      const msg = e.message || '';
      const status = (e as any).status;
      const code = (e as any).code;
      // distinguish according to PHASE 10 spec
      if(status===0 || code==='ERR_CONNECTION_REFUSED' || msg.includes('Failed to fetch') || msg.includes('Network Error') || msg.includes('Unable to connect')){
        setErr('Unable to connect to FinSense backend. Please verify your network connection or check if the server is running.');
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
        {showResend && <div className="bg-amber-50 border border-amber-200 p-3 rounded-xl text-sm space-y-2"><p className="text-amber-800">Your email is not verified.</p><button type="button" disabled={resendLoading} onClick={handleResend} className="btn-primary w-full text-sm">{resendLoading?'Sending...':'Resend verification email'}</button>{resendMsg && <p className="text-xs text-slate-600">{resendMsg}</p>}</div>}
        <div className="text-sm text-center flex justify-between"><Link to="/register" className="text-sky-600 font-medium">Create account</Link><Link to="/forgot-password" className="text-slate-500">Forgot password?</Link></div>
      </form>
    </div>
  )
}
