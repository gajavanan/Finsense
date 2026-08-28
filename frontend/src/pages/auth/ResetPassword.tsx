import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useSearchParams, useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import { toast } from 'sonner'
const schema=z.object({new_password: z.string().min(6), confirm: z.string().min(6)}).refine(d=>d.new_password===d.confirm,{message:'Mismatch', path:['confirm']})
export default function Reset(){
  const [params]=useSearchParams(); const token=params.get('token')||''; const nav=useNavigate()
  const {register, handleSubmit, formState:{errors}} = useForm({resolver: zodResolver(schema)})
  const onSubmit=async (data:any)=>{
    try{ await api.post('/auth/reset-password',{token, new_password: data.new_password}); toast.success('Password reset'); nav('/login')}catch(e:any){ toast.error(e.message)}
  }
  return <div className="min-h-screen grid place-items-center p-4"><form onSubmit={handleSubmit(onSubmit)} className="card max-w-md w-full space-y-3"><h1 className="font-bold">Reset password</h1><input type="password" {...register('new_password')} placeholder="New password" className="input"/><p className="text-xs text-red-500">{errors.new_password?.message as any}</p><input type="password" {...register('confirm')} placeholder="Confirm" className="input"/><p className="text-xs text-red-500">{errors.confirm?.message as any}</p><button className="btn-primary w-full">Reset</button></form></div>
}
