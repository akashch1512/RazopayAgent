import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { lookupBusinessByReferenceId } from '../../api/businessApi'
import { useBusiness } from '../../context/BusinessContext'
import { Button, ErrorBanner, Input } from '../../components/business/Primitives'

export default function Login() {
  const navigate = useNavigate()
  const { setBusinessId } = useBusiness()
  const [referenceId, setReferenceId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const business = await lookupBusinessByReferenceId(referenceId.trim())
      setBusinessId(String(business.id))
      navigate('/business')
    } catch (reason) {
      setError(
        reason instanceof Error && reason.message
          ? reason.message
          : 'No business found for that reference ID.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="animate-fade-in-up w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-bold text-slate-800">Log in to your dashboard</h1>
        <p className="mb-6 text-sm text-slate-400">
          Enter the reference ID you chose when onboarding your business.
        </p>

        <form onSubmit={submit} className="flex flex-col gap-4">
          <Input
            label="Reference ID"
            value={referenceId}
            onChange={(event) => setReferenceId(event.target.value)}
            placeholder="acme-coffee-01"
            required
          />
          <ErrorBanner message={error} />
          <Button type="submit" disabled={loading || !referenceId.trim()}>
            {loading ? 'Looking up…' : 'Continue'}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-400">
          Haven't onboarded yet?{' '}
          <button
            onClick={() => navigate('/business/onboard')}
            className="font-semibold text-slate-700 hover:underline"
          >
            Onboard your business
          </button>
        </p>
      </div>
    </div>
  )
}
