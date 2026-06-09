import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '../../services/api'

const schema = z.object({
  totp_code: z.string().regex(/^\d{6}$/, 'Enter the 6-digit code from your authenticator app'),
})

export default function TOTPSetup({ tempToken, onComplete }) {
  const [qrCode, setQrCode] = useState(null)
  const [secret, setSecret] = useState('')
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState('')

  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })

  useEffect(() => {
    authApi.totpSetup(tempToken)
      .then((res) => {
        setQrCode(res.data.qr_code_url)
        setSecret(res.data.secret)
      })
      .catch(() => setError('Failed to load QR code. Please log in again.'))
      .finally(() => setLoading(false))
  }, [tempToken])

  async function onVerify(data) {
    setError('')
    setVerifying(true)
    try {
      const res = await authApi.totpVerify({ totp_code: data.totp_code, temp_token: tempToken })
      const { access_token, user_id, username } = res.data
      onComplete(access_token, user_id, username)
    } catch (e) {
      setError(e.response?.data?.detail || 'Invalid code. Please try again.')
    } finally {
      setVerifying(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Set Up Two-Factor Authentication</h2>
          <p className="text-sm text-gray-600 mb-6">
            Scan this QR code with Google Authenticator, Authy, or any TOTP app.
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {qrCode && (
            <div className="flex justify-center mb-4">
              <img src={qrCode} alt="TOTP QR Code" className="w-48 h-48 border border-gray-200 rounded-lg" />
            </div>
          )}

          <details className="mb-6">
            <summary className="text-sm text-indigo-600 cursor-pointer hover:text-indigo-800 select-none">
              Can't scan? Enter code manually
            </summary>
            <div className="mt-2 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Manual entry key:</p>
              <code className="text-sm font-mono text-gray-800 break-all">{secret}</code>
            </div>
          </details>

          <form onSubmit={handleSubmit(onVerify)} className="space-y-4">
            <div>
              <label className="label">Enter the 6-digit code to confirm setup</label>
              <input
                {...register('totp_code')}
                className="input-field text-center tracking-widest text-lg font-mono"
                placeholder="000000"
                maxLength={6}
                inputMode="numeric"
                autoComplete="one-time-code"
              />
              {errors.totp_code && (
                <p className="text-red-600 text-xs mt-1">{errors.totp_code.message}</p>
              )}
            </div>
            <button type="submit" disabled={verifying} className="btn-primary w-full">
              {verifying ? 'Verifying…' : 'Confirm & Continue'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
