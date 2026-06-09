import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

export default function GmailCallbackPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('Connecting Gmail…')
  const [error, setError] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const errorParam = params.get('error')

    if (errorParam) {
      setError(`Google denied access: ${errorParam}`)
      return
    }

    if (!code) {
      setError('No authorization code received from Google.')
      return
    }

    api.post('/gmail/exchange', { code })
      .then(() => {
        setStatus('Gmail connected!')
        setTimeout(() => navigate('/transactions?gmail=connected'), 1000)
      })
      .catch((e) => {
        setError(e.response?.data?.detail || 'Failed to connect Gmail. Please try again.')
      })
  }, [navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="card max-w-sm w-full text-center">
        {!error ? (
          <>
            <svg className="w-10 h-10 animate-spin text-indigo-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <p className="text-gray-700 font-medium">{status}</p>
          </>
        ) : (
          <>
            <p className="text-red-600 font-medium mb-4">{error}</p>
            <button onClick={() => navigate('/transactions')} className="btn-secondary w-full">
              Back to Transactions
            </button>
          </>
        )}
      </div>
    </div>
  )
}
