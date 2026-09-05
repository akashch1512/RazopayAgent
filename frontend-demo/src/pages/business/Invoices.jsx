import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listInvoices, startInvoiceChase } from '../../api/businessApi'
import { useBusiness } from '../../context/BusinessContext'
import { Button, Card, EmptyState, ErrorBanner, Skeleton } from '../../components/business/Primitives'

function formatMoney(paise, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format((paise || 0) / 100)
}

const STATUS_STYLES = {
  paid: 'bg-emerald-100 text-emerald-700',
  issued: 'bg-amber-100 text-amber-700',
  partially_paid: 'bg-amber-100 text-amber-700',
  expired: 'bg-rose-100 text-rose-700',
  cancelled: 'bg-slate-100 text-slate-500',
}

export default function Invoices() {
  const { businessId } = useBusiness()
  const [invoices, setInvoices] = useState(null)
  const [error, setError] = useState('')
  const [chasing, setChasing] = useState(null)
  const [chased, setChased] = useState({})

  useEffect(() => {
    listInvoices(businessId, { count: 25 })
      .then(setInvoices)
      .catch((reason) => setError(reason.message))
  }, [businessId])

  const chase = async (invoice) => {
    setChasing(invoice.id)
    setError('')
    try {
      const result = await startInvoiceChase(businessId, invoice.id, {
        reason: `B2B chase started from dashboard for invoice ${invoice.invoiceNumber || invoice.id}`,
      })
      setChased((prev) => ({ ...prev, [invoice.id]: result.caseId }))
    } catch (reason) {
      setError(reason.message)
    } finally {
      setChasing(null)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Invoices</h1>
        <p className="text-sm text-slate-400">
          Live from Razorpay. Start a B2B chase to have the agent follow up on an unpaid invoice.
        </p>
      </div>

      <ErrorBanner message={error} />

      {!invoices ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : invoices.length === 0 ? (
        <EmptyState icon="₹" title="No invoices found" description="Nothing came back from Razorpay yet." />
      ) : (
        <Card className="!p-0">
          <ul className="divide-y divide-slate-100">
            {invoices.map((invoice, i) => (
              <li
                key={invoice.id}
                className="stagger-item flex flex-wrap items-center justify-between gap-3 px-5 py-4"
                style={{ '--i': i }}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-800">
                      {invoice.invoiceNumber ? `#${invoice.invoiceNumber}` : invoice.id}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                        STATUS_STYLES[invoice.status] || 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {invoice.status}
                    </span>
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    {invoice.customerDetails?.name || invoice.customerDetails?.email || 'Unknown customer'} ·
                    due {formatMoney(invoice.amountDue, invoice.currency)} of{' '}
                    {formatMoney(invoice.amount, invoice.currency)}
                  </div>
                </div>

                {chased[invoice.id] ? (
                  <Link
                    to={`/business/cases/${chased[invoice.id]}`}
                    className="text-xs font-bold text-emerald-600 hover:underline"
                  >
                    Case #{chased[invoice.id]} started →
                  </Link>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={() => chase(invoice)}
                    disabled={chasing === invoice.id || invoice.status === 'paid'}
                  >
                    {chasing === invoice.id ? 'Starting…' : 'Start B2B chase'}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
