import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuthStore } from '../../store/authStore'

const schema=z.object({ name: z.string().min(2), email: z.string().email(), password: z.string().min(6), confirm: z.string().min(6)}).refine(d=>d.password===d.confirm, {message:'Passwords do not match', path:['confirm']})

export default function Register(){
  const nav=useNavigate(); const [loading,setLoading]=useState(false); const [err,setErr]=useState('')
  const registerFn = useAuthStore(s=>s.register)
  const {register, handleSubmit, formState:{errors}} = useForm({resolver: zodResolver(schema)})
  const onSubmit=async (data:any)=>{
    setLoading(true); setErr('')
    try{
      const res = await registerFn(data.name, data.email, data.password)
      toast.success('Account created. Check email to verify.')
      nav('/login')
    }catch(e:any){ setErr(e.message); toast.error(e.message)} finally{ setLoading(false)}
  }
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900">
      <form onSubmit={handleSubmit(onSubmit)} className="card w-full max-w-md space-y-3">
        <div className="text-center"><h1 className="text-2xl font-bold">Create account</h1><p className="text-sm text-slate-500">Start your FinSense journey</p></div>
        {err && <div className="bg-red-50 text-red-700 p-2.5 rounded-xl text-sm">{err}</div>}
        <div><label className="text-sm font-medium">Full name</label><input {...register('name')} className="input mt-1"/><p className="text-xs text-red-500">{errors.name?.message as any}</p></div>
        <div><label className="text-sm font-medium">Email</label><input {...register('email')} className="input mt-1"/><p className="text-xs text-red-500">{errors.email?.message as any}</p></div>
        <div><label className="text-sm font-medium">Password</label><input type="password" {...register('password')} className="input mt-1"/><p className="text-xs text-red-500">{errors.password?.message as any}</p></div>
        <div><label className="text-sm font-medium">Confirm password</label><input type="password" {...register('confirm')} className="input mt-1"/><p className="text-xs text-red-500">{errors.confirm?.message as any}</p></div>
        <button disabled={loading} className="btn-primary w-full">{loading?'Creating...':'Create account'}</button>
        <div className="text-sm text-center"><Link to="/login" className="text-sky-600">Already have account? Sign in</Link></div>
      </form>
    </div>
  )
}
