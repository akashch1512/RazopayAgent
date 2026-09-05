import { useState } from 'react'
import { Link } from 'react-router-dom'
import { startCustomRecovery } from '../../api/businessApi'
import { useBusiness } from '../../context/BusinessContext'
import { Button, Card, ErrorBanner, Input, TextArea } from '../../components/business/Primitives'

const INITIAL = {
  orderReference: '',
  customerEmail: '',
  customerContact: '',
  amount: '',
  currency: 'INR',
  reason: '',
}

export default function StartRecovery() {
  const { businessId } = useBusiness()
  const [form, setForm] = useState(INITIAL)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const update = (field) => (event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        orderReference: form.orderReference,
        customerEmail: form.customerEmail || null,
        customerContact: form.customerContact || null,
        amount: form.amount ? Math.round(Number(form.amount) * 100) : null,
        currency: form.currency,
        reason: form.reason,
      }
      const data = await startCustomRecovery(businessId, payload)
      setResult(data)
      setForm(INITIAL)
    } catch (reason) {
      setError(reason.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex max-w-xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Start custom recovery</h1>
        <p className="text-sm text-slate-400">
          Manually ask the agent to chase an order or customer that hasn't (yet) triggered anything on
          its own - a support escalation, a manual follow-up.
        </p>
      </div>

      <Card>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <Input
            label="Order / reference ID"
            value={form.orderReference}
            onChange={update('orderReference')}
            placeholder="order_ABC123 or your own reference"
            required
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Customer email"
              type="email"
              value={form.customerEmail}
              onChange={update('customerEmail')}
              placeholder="customer@example.com"
            />
            <Input
              label="Customer phone"
              value={form.customerContact}
              onChange={update('customerContact')}
              placeholder="+919876543210"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Amount (optional)"
              type="number"
              step="0.01"
              value={form.amount}
              onChange={update('amount')}
              placeholder="999.00"
            />
            <Input label="Currency" value={form.currency} onChange={update('currency')} />
          </div>
          <TextArea
            label="Reason - why should the agent chase this?"
            rows={3}
            value={form.reason}
            onChange={update('reason')}
            placeholder="Customer called support asking for a payment retry link"
            required
          />

          <ErrorBanner message={error} />

          <Button type="submit" disabled={loading}>
            {loading ? 'Starting…' : 'Start recovery'}
          </Button>
        </form>
      </Card>

      {result && (
        <div className="animate-pop-in flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
          <span className="text-emerald-700">
            Case queued (<span className="font-mono">{result.status}</span>).
          </span>
          <Link to={`/business/cases/${result.caseId}`} className="font-bold text-emerald-700 hover:underline">
            View case #{result.caseId} →
          </Link>
        </div>
      )}
    </div>
  )
}
