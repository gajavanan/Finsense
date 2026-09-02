import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuthStore } from '../../store/authStore'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters')
})

type LoginFormData = z.infer<typeof loginSchema>

export default function Login() {
  const nav = useNavigate()
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const login = useAuthStore(s => s.login)

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema)
  })

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true)
    setErr('')

    try {
      const emailNorm = data.email.trim().toLowerCase()
      await login(emailNorm, data.password)
      toast.success('Login successful')
      nav('/dashboard')
    } catch (e: any) {
      const msg = e.message || ''
      const status = (e as any).status || (e as any).response?.status
      const detail = (e as any).response?.data?.detail
      const code = typeof detail === 'object' ? detail?.code : (e as any).code

      if (code === 'INVALID_CREDENTIALS' || status === 401 || msg.includes('Invalid email or password')) {
        setErr('Invalid email or password')
        toast.error('Invalid email or password')
      } else if (status === 0 || msg.includes('Failed to fetch') || msg.includes('Network Error')) {
        setErr('Unable to connect to FinSense backend. Please check your internet connection.')
        toast.error('Server unreachable.')
      } else if (status === 422) {
        setErr('Invalid email or password format.')
      } else {
        setErr(msg || 'Login failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900">
      <div className="card w-full max-w-md space-y-4 p-6 sm:p-8">
        <div className="text-center">
          <div className="w-10 h-10 rounded-xl bg-sky-600 text-white grid place-items-center mx-auto text-lg font-bold">●</div>
          <h1 className="text-2xl font-bold mt-3">Welcome back</h1>
          <p className="text-sm text-slate-500">Sign in to your FinSense account</p>
        </div>

        {err && (
          <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 p-3 rounded-xl text-sm">
            {err}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Email Address</label>
            <input
              type="email"
              {...register('email')}
              className="input mt-1"
              placeholder="you@example.com"
            />
            {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium">Password</label>
            <input
              type="password"
              {...register('password')}
              className="input mt-1"
              placeholder="••••••••"
            />
            {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
          </div>

          <button disabled={loading} className="btn-primary w-full py-2.5 font-medium">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="text-sm text-center flex justify-between pt-2">
          <Link to="/register" className="text-sky-600 hover:text-sky-700 dark:text-sky-400 font-medium">
            Create account
          </Link>
          <Link to="/forgot-password" className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
            Forgot password?
          </Link>
        </div>
      </div>
    </div>
  )
}
