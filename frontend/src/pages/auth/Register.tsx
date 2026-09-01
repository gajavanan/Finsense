import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { useAuthStore } from '../../store/authStore'
import { auth, RecaptchaVerifier, signInWithPhoneNumber, ConfirmationResult } from '../../lib/firebase'

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  phone_number: z.string().min(10, 'Please enter a valid mobile number'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirm: z.string().min(6, 'Please confirm your password')
}).refine(d => d.password === d.confirm, {
  message: 'Passwords do not match',
  path: ['confirm']
})

type FormData = z.infer<typeof schema>

declare global {
  interface Window {
    recaptchaVerifier?: RecaptchaVerifier
  }
}

export default function Register() {
  const nav = useNavigate()
  const registerFn = useAuthStore(s => s.register)

  const [otpStage, setOtpStage] = useState(false)
  const [confirmationResult, setConfirmationResult] = useState<ConfirmationResult | null>(null)
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendingOtp, setSendingOtp] = useState(false)
  const [err, setErr] = useState('')
  const [maskedPhone, setMaskedPhone] = useState('')

  const recaptchaContainerRef = useRef<HTMLDivElement>(null)

  const { register, handleSubmit, getValues, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema)
  })

  // Clean up reCAPTCHA verifier on unmount
  useEffect(() => {
    return () => {
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear()
        } catch {}
        window.recaptchaVerifier = undefined
      }
    }
  }, [])

  const formatPhoneNumber = (raw: string): string => {
    const trimmed = raw.trim().replace(/[\s\-\(\)]/g, '')
    if (trimmed.startsWith('+')) {
      return trimmed
    }
    const digits = trimmed.replace(/\D/g, '')
    if (digits.length === 10) {
      return `+91${digits}`
    }
    if (digits.length === 12 && digits.startsWith('91')) {
      return `+${digits}`
    }
    return `+${digits}`
  }

  const maskPhone = (phone: string): string => {
    if (phone.length >= 8) {
      return `${phone.slice(0, 3)} ******${phone.slice(-4)}`
    }
    return phone
  }

  const mapFirebaseError = (error: any): string => {
    const code = error?.code || ''
    const msg = error?.message || ''

    if (code === 'auth/invalid-phone-number') {
      return 'Invalid mobile number format. Please check and include country code.'
    }
    if (code === 'auth/missing-phone-number') {
      return 'Mobile number is required.'
    }
    if (code === 'auth/quota-exceeded') {
      return 'SMS quota exceeded for today. Please try again later.'
    }
    if (code === 'auth/too-many-requests') {
      return 'Too many SMS requests sent. Please wait a few minutes before retrying.'
    }
    if (code === 'auth/invalid-verification-code') {
      return 'Invalid 6-digit verification code. Please check and re-enter.'
    }
    if (code === 'auth/code-expired') {
      return 'Verification code has expired. Please click "Change or Resend Code".'
    }
    if (code === 'auth/captcha-check-failed') {
      return 'reCAPTCHA verification failed. Please refresh the page and try again.'
    }
    if (code === 'auth/network-request-failed') {
      return 'Network error communicating with Firebase. Please check your connection.'
    }
    return msg || 'Failed to verify phone number. Please try again.'
  }

  const setupRecaptcha = (): RecaptchaVerifier => {
    if (window.recaptchaVerifier) {
      try {
        window.recaptchaVerifier.clear()
      } catch {}
      window.recaptchaVerifier = undefined
    }

    const verifier = new RecaptchaVerifier(auth, 'recaptcha-container', {
      size: 'invisible',
      callback: () => {
        // reCAPTCHA solved
      },
      'expired-callback': () => {
        setErr('reCAPTCHA expired. Please try requesting OTP again.')
      }
    })

    window.recaptchaVerifier = verifier
    return verifier
  }

  const handleSendOtp = async () => {
    setErr('')
    const values = getValues()

    if (!values.name || values.name.length < 2) {
      setErr('Please enter your full name.')
      return
    }
    if (!values.email || !values.email.includes('@')) {
      setErr('Please enter a valid email address.')
      return
    }
    if (!values.phone_number || values.phone_number.trim().length < 10) {
      setErr('Please enter a valid 10-digit mobile number.')
      return
    }
    if (!values.password || values.password.length < 6) {
      setErr('Password must be at least 6 characters.')
      return
    }
    if (values.password !== values.confirm) {
      setErr('Passwords do not match.')
      return
    }

    const formatted = formatPhoneNumber(values.phone_number)
    setSendingOtp(true)

    try {
      const verifier = setupRecaptcha()
      const confirmation = await signInWithPhoneNumber(auth, formatted, verifier)
      setConfirmationResult(confirmation)
      setMaskedPhone(maskPhone(formatted))
      setOtpStage(true)
      toast.success('Verification code sent via SMS!')
    } catch (e: any) {
      console.error('Firebase send OTP error:', e)
      const friendlyMsg = mapFirebaseError(e)
      setErr(friendlyMsg)
      toast.error(friendlyMsg)
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear()
        } catch {}
        window.recaptchaVerifier = undefined
      }
    } finally {
      setSendingOtp(false)
    }
  }

  const handleVerifyAndRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')

    const cleanOtp = otp.trim().replace(/\D/g, '')
    if (cleanOtp.length !== 6) {
      setErr('Please enter the complete 6-digit verification code.')
      return
    }
    if (!confirmationResult) {
      setErr('Verification session expired. Please request OTP again.')
      setOtpStage(false)
      return
    }

    setLoading(true)
    try {
      // 1. Confirm OTP with Firebase
      const userCredential = await confirmationResult.confirm(cleanOtp)

      // 2. Retrieve verified Firebase ID token
      const idToken = await userCredential.user.getIdToken()
      if (!idToken) {
        throw new Error('Failed to retrieve verified authentication token from Firebase.')
      }

      // 3. Submit registration to FastAPI backend
      const values = getValues()
      const res = await registerFn(
        values.name.trim(),
        values.email.trim().toLowerCase(),
        values.password,
        idToken
      )

      toast.success(res.message || 'Account created successfully! Please sign in.')
      nav('/login')
    } catch (e: any) {
      console.error('Registration verification error:', e)
      const friendlyMsg = e?.response?.data?.detail || mapFirebaseError(e)
      setErr(typeof friendlyMsg === 'string' ? friendlyMsg : 'Registration failed. Please try again.')
      toast.error(typeof friendlyMsg === 'string' ? friendlyMsg : 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-sky-50 to-violet-50 dark:from-slate-950 dark:to-slate-900">
      {/* Invisible container for Firebase reCAPTCHA */}
      <div id="recaptcha-container" ref={recaptchaContainerRef} />

      <div className="card w-full max-w-md space-y-4 p-6 sm:p-8">
        <div className="text-center">
          <div className="w-10 h-10 rounded-xl bg-sky-600 text-white grid place-items-center mx-auto text-lg font-bold">●</div>
          <h1 className="text-2xl font-bold mt-2">Create account</h1>
          <p className="text-sm text-slate-500">
            {otpStage ? 'Verify your mobile number' : 'Start your FinSense journey'}
          </p>
        </div>

        {err && (
          <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 p-3 rounded-xl text-sm">
            {err}
          </div>
        )}

        {!otpStage ? (
          /* Stage 1: Registration Form */
          <form onSubmit={handleSubmit(handleSendOtp)} className="space-y-3.5">
            <div>
              <label className="text-sm font-medium">Full Name</label>
              <input
                {...register('name')}
                className="input mt-1"
                placeholder="Alex Morgan"
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
                  {...register('phone_number')}
                  className="input rounded-l-none flex-1"
                  placeholder="9876543210"
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">Firebase will send an SMS code to verify this number</p>
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
              type="button"
              disabled={sendingOtp}
              onClick={handleSendOtp}
              className="btn-primary w-full py-2.5 mt-2 font-medium"
            >
              {sendingOtp ? 'Sending Verification Code...' : 'Send SMS Verification Code'}
            </button>

            <div className="text-sm text-center pt-2">
              <Link to="/login" className="text-sky-600 hover:text-sky-700 dark:text-sky-400 font-medium">
                Already have an account? Sign in
              </Link>
            </div>
          </form>
        ) : (
          /* Stage 2: OTP Verification & Final Account Creation */
          <form onSubmit={handleVerifyAndRegister} className="space-y-4">
            <div className="bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 p-3.5 rounded-xl text-sm text-sky-900 dark:text-sky-200">
              <p className="font-semibold">SMS Code Sent!</p>
              <p className="text-xs mt-1 text-sky-700 dark:text-sky-300">
                Enter the 6-digit code sent to <strong>{maskedPhone}</strong>
              </p>
            </div>

            <div>
              <label className="text-sm font-medium">6-Digit Verification Code</label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={otp}
                onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                className="input mt-1 text-center text-2xl font-bold tracking-widest"
                placeholder="••••••"
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="btn-primary w-full py-2.5 font-medium"
            >
              {loading ? 'Verifying & Creating Account...' : 'Verify & Create Account'}
            </button>

            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => {
                  setOtpStage(false)
                  setOtp('')
                  setErr('')
                }}
                className="text-xs text-slate-500 hover:text-sky-600 font-medium"
              >
                ← Edit details or resend code
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
