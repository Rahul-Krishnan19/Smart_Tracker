import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '../../services/api'
import { useAuth } from '../../context/AuthContext'

const registerSchema = z.object({
  username: z
    .string()
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username must be at most 50 characters')
    .regex(/^[a-zA-Z0-9_]+$/, 'Only letters, numbers, and underscores allowed'),
  email: z.string().email('Enter a valid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Must contain at least one lowercase letter')
    .regex(/\d/, 'Must contain at least one number'),
  confirmPassword: z.string(),
}).refine((d) => d.password === d.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

export default function RegisterForm() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const form = useForm({ resolver: zodResolver(registerSchema) })

  async function onSubmit(data) {
    setError('')
    setLoading(true)
    try {
      // Register the user
      await authApi.register({
        username: data.username,
        email: data.email,
        password: data.password,
      })
      // Auto-login immediately after registration
      const res = await authApi.login({ username: data.username, password: data.password })
      const { access_token, user_id, username } = res.data
      login({ id: user_id, username }, access_token)
      navigate('/transactions', { replace: true })
    } catch (e) {
      const detail = e.response?.data?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join('. '))
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="card">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
            <p className="text-gray-500 text-sm mt-1">Start tracking your expenses</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Username</label>
              <input
                {...form.register('username')}
                className="input-field"
                placeholder="your_username"
                autoComplete="username"
              />
              {form.formState.errors.username && (
                <p className="text-red-600 text-xs mt-1">{form.formState.errors.username.message}</p>
              )}
            </div>

            <div>
              <label className="label">Email</label>
              <input
                {...form.register('email')}
                type="email"
                className="input-field"
                placeholder="you@example.com"
                autoComplete="email"
              />
              {form.formState.errors.email && (
                <p className="text-red-600 text-xs mt-1">{form.formState.errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="label">Password</label>
              <input
                {...form.register('password')}
                type="password"
                className="input-field"
                placeholder="••••••••"
                autoComplete="new-password"
              />
              {form.formState.errors.password && (
                <p className="text-red-600 text-xs mt-1">{form.formState.errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="label">Confirm Password</label>
              <input
                {...form.register('confirmPassword')}
                type="password"
                className="input-field"
                placeholder="••••••••"
                autoComplete="new-password"
              />
              {form.formState.errors.confirmPassword && (
                <p className="text-red-600 text-xs mt-1">{form.formState.errors.confirmPassword.message}</p>
              )}
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-600 hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
