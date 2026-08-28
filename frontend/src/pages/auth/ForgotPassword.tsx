import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import api from '../../lib/api'
const schema=z.object({email: z.string().email()})
export default function Forgot(){
  const [msg,setMsg]=useState('')
  const {register, handleSubmit} = useForm({resolver: zodResolver(schema)})
  const onSubmit=async (data:any)=>{
    try{
      const {data:res}=await api.post('/auth/forgot-password', {email: data.email})
      setMsg(res.message); toast.success('If account exists, email sent')
    }catch(e:any){ toast.error(e.message)}
  }
  return <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900"><form onSubmit={handleSubmit(onSubmit)} className="card w-full max-w-md space-y-3"><h1 className="text-xl font-bold">Forgot password</h1><p className="text-sm text-slate-500">We will send reset link if account exists.</p><input {...register('email')} placeholder="Email" className="input"/>{msg && <div className="text-sm text-green-600 bg-green-50 p-2 rounded-xl">{msg}</div>}<button className="btn-primary w-full">Send reset link</button><Link to="/login" className="text-sm text-sky-600">Back to sign in</Link></form></div>
}
