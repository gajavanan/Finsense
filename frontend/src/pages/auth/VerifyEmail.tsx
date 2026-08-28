import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import api from '../../lib/api'
export default function VerifyEmail(){
  const [params]=useSearchParams(); const token=params.get('token'); const [msg,setMsg]=useState('Verifying...'); const [status,setStatus]=useState<'loading'|'success'|'error'>('loading')
  const [resendEmail,setResendEmail]=useState(''); const [resendMsg,setResendMsg]=useState(''); const [resendLoading,setResendLoading]=useState(false)
  useEffect(()=>{
    if(!token){ setMsg('Missing token'); setStatus('error'); return}
    api.get('/auth/verify-email',{params:{token}}).then(()=> {setMsg('Email verified successfully.'); setStatus('success')}).catch(e=> {setMsg(e.message || 'Verification failed'); setStatus('error')})
  },[token])
  const handleResend = async()=>{
    if(!resendEmail){ setResendMsg('Enter your email'); return}
    setResendLoading(true); setResendMsg('')
    try{ await api.post('/auth/resend-verification',{email:resendEmail}); setResendMsg('If an account exists, a new verification email has been sent. Check inbox & spam.')}catch(e:any){ setResendMsg(e.message)} finally{ setResendLoading(false)}
  }
  return <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900">
    <div className="card max-w-md w-full text-center space-y-4 p-6">
      <h1 className="font-bold text-xl">Email verification</h1>
      <p className={`text-sm ${status==='success' ? 'text-green-600' : status==='error' ? 'text-red-600' : 'text-slate-500'}`}>{msg}</p>
      {status==='success' && <Link to="/login" className="btn-primary inline-block">Sign in</Link>}
      {status==='error' && <Link to="/login" className="btn-primary inline-block">Go to sign in</Link>}
      <div className="pt-4 border-t mt-4 space-y-3 text-left">
        <h2 className="font-semibold text-sm">Didn't receive email?</h2>
        <p className="text-xs text-slate-500">Enter your email to resend verification (link expires in 24h, 60s cooldown).</p>
        <div className="flex gap-2">
          <input value={resendEmail} onChange={e=>setResendEmail(e.target.value)} placeholder="you@example.com" className="input flex-1"/>
          <button onClick={handleResend} disabled={resendLoading} className="btn-primary text-sm">{resendLoading?'Sending...':'Resend'}</button>
        </div>
        {resendMsg && <p className="text-xs text-slate-600">{resendMsg}</p>}
      </div>
    </div>
  </div>
}
