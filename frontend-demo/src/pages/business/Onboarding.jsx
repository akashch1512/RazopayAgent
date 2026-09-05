import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startOnboarding } from '../../api/businessApi'
import { Button, ErrorBanner, Input } from '../../components/business/Primitives'

export default function Onboarding() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', referenceId: '', contactEmail: '' })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const update = (field) => (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await startOnboarding({
        name: form.name,
        referenceId: form.referenceId,
        contactEmail: form.contactEmail || null,
      })
      setResult(data)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start onboarding.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="animate-fade-in-up w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-bold text-slate-800">Onboard your business</h1>
        <p className="mb-6 text-sm text-slate-400">
          We'll register a case with Razorpay and hand you off to authorize access.
        </p>

        {!result ? (
          <form onSubmit={submit} className="flex flex-col gap-4">
            <Input
              label="Business name"
              value={form.name}
              onChange={update('name')}
              placeholder="Acme Coffee Roasters"
              required
            />
            <Input
              label="Reference ID (your own identifier)"
              value={form.referenceId}
              onChange={update('referenceId')}
              placeholder="acme-coffee-01"
              required
            />
            <Input
              label="Contact email (optional)"
              type="email"
              value={form.contactEmail}
              onChange={update('contactEmail')}
              placeholder="ops@acme.example"
            />
            <ErrorBanner message={error} />
            <Button type="submit" disabled={loading}>
              {loading ? 'Starting…' : 'Continue'}
            </Button>
            <p className="text-center text-xs text-slate-400">
              Already onboarded?{' '}
              <button
                type="button"
                onClick={() => navigate('/business/login')}
                className="font-semibold text-slate-700 hover:underline"
              >
                Log in with your reference ID
              </button>
            </p>
          </form>
        ) : (
          <div className="animate-pop-in flex flex-col gap-4 text-center">
            <div className="text-3xl">✅</div>
            <p className="text-sm text-slate-600">
              Business <strong>#{result.businessId}</strong> registered. Authorize with Razorpay to
              finish - you'll land back on the dashboard automatically.
            </p>
            <a
              href={result.authorizationUrl}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-slate-700"
            >
              Authorize with Razorpay →
            </a>
            <p className="text-xs text-slate-400">
              Business ID: <span className="font-mono">{result.businessId}</span> - keep it handy in
              case you need to switch back to it later.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
