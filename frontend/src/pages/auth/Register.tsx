import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { toast } from 'sonner'
import { useAuthStore } from '../../store/authStore'

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  phone_number: z.string()
    .transform(v => v.trim().replace(/\D/g, ''))
    .refine(v => v.length === 10 && /^[6-9]/.test(v), {
      message: 'Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9'
    }),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirm: z.string().min(6, 'Please confirm your password')
}).refine(d => d.password === d.confirm, {
  message: 'Passwords do not match',
  path: ['confirm']
})

type FormData = z.infer<typeof schema>

export default function Register() {
  const nav = useNavigate()
  const registerFn = useAuthStore(s => s.register)

  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema)
  })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    setErr('')

    try {
      const formattedPhone = `+91${data.phone_number}`
      const res = await registerFn(
        data.name.trim(),
        data.email.trim().toLowerCase(),
        formattedPhone,
        data.password
      )

      toast.success(res.message || 'Account created successfully! Please sign in.')
      nav('/login')
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e.message || 'Registration failed. Please try again.'
      const displayMsg = typeof msg === 'string' ? msg : 'Registration failed. Please try again.'
      setErr(displayMsg)
      toast.error(displayMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900">
      <div className="card w-full max-w-md space-y-4 p-6 sm:p-8">
        <div className="text-center">
          <div className="w-10 h-10 rounded-xl bg-sky-600 text-white grid place-items-center mx-auto text-lg font-bold">●</div>
          <h1 className="text-2xl font-bold mt-2">Create account</h1>
          <p className="text-sm text-slate-500">Start managing your finances with FinSense</p>
        </div>

        {err && (
          <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 p-3 rounded-xl text-sm">
            {err}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
          <div>
            <label className="text-sm font-medium">Full Name</label>
            <input
              {...register('name')}
              className="input mt-1"
              placeholder="Alex Morgan"
              autoFocus
            />
            {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium">Email Address</label>
            <input
              type="email"
              {...register('email')}
              className="input mt-1"
              placeholder="alex@example.com"
            />
            {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="text-sm font-medium">Mobile Number</label>
            <div className="flex mt-1">
              <span className="inline-flex items-center px-3 rounded-l-xl border border-r-0 border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-semibold select-none">
                🇮🇳 +91
              </span>
              <input
                type="tel"
                inputMode="numeric"
                maxLength={10}
                {...register('phone_number')}
                className="input rounded-l-none flex-1"
                placeholder="9876543210"
              />
            </div>
            {errors.phone_number && <p className="text-xs text-red-500 mt-1">{errors.phone_number.message}</p>}
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

          <div>
            <label className="text-sm font-medium">Confirm Password</label>
            <input
              type="password"
              {...register('confirm')}
              className="input mt-1"
              placeholder="••••••••"
            />
            {errors.confirm && <p className="text-xs text-red-500 mt-1">{errors.confirm.message}</p>}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-2.5 mt-2 font-medium"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>

          <div className="text-sm text-center pt-2">
            <Link to="/login" className="text-sky-600 hover:text-sky-700 dark:text-sky-400 font-medium">
              Already have an account? Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
