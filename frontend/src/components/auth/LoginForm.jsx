import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '../../services/api'
import { useAuth } from '../../context/AuthContext'
import TOTPSetup from './TOTPSetup'

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

const totpSchema = z.object({
  totp_code: z.string().regex(/^\d{6}$/, 'Enter the 6-digit code from your authenticator app'),
})

export default function LoginForm() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState('credentials') // 'credentials' | 'totp_setup' | 'totp_verify'
  const [tempToken, setTempToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const credForm = useForm({ resolver: zodResolver(loginSchema) })
  const totpForm = useForm({ resolver: zodResolver(totpSchema) })

  async function onCredentials(data) {
    setError('')
    setLoading(true)
    try {
      const res = await authApi.login(data)
      const { access_token, user_id, username, temp_token, totp_enrolled } = res.data
      // When TOTP is disabled the server returns an access_token directly
      if (access_token) {
        login({ id: user_id, username }, access_token)
        navigate('/transactions', { replace: true })
        return
      }
      setTempToken(temp_token)
      if (!totp_enrolled) {
        setStep('totp_setup')
      } else {
        setStep('totp_verify')
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  async function onTOTPVerify(data) {
    setError('')
    setLoading(true)
    try {
      const res = await authApi.totpVerify({ totp_code: data.totp_code, temp_token: tempToken })
      const { access_token, user_id, username } = res.data
      login({ id: user_id, username }, access_token)
      navigate('/transactions', { replace: true })
    } catch (e) {
      setError(e.response?.data?.detail || 'Invalid code. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Called by TOTPSetup after QR enrollment is confirmed — access_token already issued
  function onEnrollmentComplete(access_token, user_id, username) {
    login({ id: user_id, username }, access_token)
    navigate('/transactions', { replace: true })
  }

  if (step === 'totp_setup') {
    return (
      <TOTPSetup
        tempToken={tempToken}
        onComplete={onEnrollmentComplete}
      />
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="card">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Expense Tracker</h1>
            <p className="text-gray-500 text-sm mt-1">
              {step === 'credentials' ? 'Sign in to your account' : 'Enter your authenticator code'}
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {step === 'credentials' && (
            <form onSubmit={credForm.handleSubmit(onCredentials)} className="space-y-4">
              <div>
                <label className="label">Username</label>
                <input
                  {...credForm.register('username')}
                  className="input-field"
                  placeholder="your_username"
                  autoComplete="username"
                />
                {credForm.formState.errors.username && (
                  <p className="text-red-600 text-xs mt-1">{credForm.formState.errors.username.message}</p>
                )}
              </div>
              <div>
                <label className="label">Password</label>
                <input
                  {...credForm.register('password')}
                  type="password"
                  className="input-field"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                {credForm.formState.errors.password && (
                  <p className="text-red-600 text-xs mt-1">{credForm.formState.errors.password.message}</p>
                )}
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          )}

          {step === 'totp_verify' && (
            <form onSubmit={totpForm.handleSubmit(onTOTPVerify)} className="space-y-4">
              <div className="text-center mb-4">
                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <p className="text-sm text-gray-600">Open your authenticator app and enter the 6-digit code.</p>
              </div>
              <div>
                <label className="label">Authenticator Code</label>
                <input
                  {...totpForm.register('totp_code')}
                  className="input-field text-center tracking-widest text-lg font-mono"
                  placeholder="000000"
                  maxLength={6}
                  autoComplete="one-time-code"
                  inputMode="numeric"
                />
                {totpForm.formState.errors.totp_code && (
                  <p className="text-red-600 text-xs mt-1">{totpForm.formState.errors.totp_code.message}</p>
                )}
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Verifying…' : 'Verify'}
              </button>
              <button
                type="button"
                onClick={() => { setStep('credentials'); setError('') }}
                className="btn-secondary w-full"
              >
                Back
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
