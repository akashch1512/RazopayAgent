import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCase, retryCase } from '../../api/businessApi'
import { Button, Card, ErrorBanner, Skeleton } from '../../components/business/Primitives'
import StatusBadge from '../../components/business/StatusBadge'
import Timeline from '../../components/business/Timeline'

function Field({ label, value }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-0.5 truncate text-sm font-semibold text-slate-800">{value ?? '—'}</div>
    </div>
  )
}

export default function CaseDetail() {
  const { caseId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [retrying, setRetrying] = useState(false)

  const load = useCallback(() => {
    getCase(caseId)
      .then(setData)
      .catch((reason) => setError(reason.message))
  }, [caseId])

  useEffect(() => {
    setData(null)
    load()
  }, [load])

  const handleRetry = async () => {
    setRetrying(true)
    try {
      await retryCase(caseId)
      await load()
    } catch (reason) {
      setError(reason.message)
    } finally {
      setRetrying(false)
    }
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <Link to="/business/cases" className="text-xs font-semibold text-slate-400 hover:text-slate-700">
          ← Back to cases
        </Link>
        <ErrorBanner message={error} />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  const canRetry = data.processingStatus === 'DEAD' || data.processingStatus === 'FAILED'

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/business/cases" className="text-xs font-semibold text-slate-400 hover:text-slate-700">
          ← Back to cases
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Case #{data.id}</h1>
          <StatusBadge status={data.processingStatus} />
          {canRetry && (
            <Button variant="secondary" onClick={handleRetry} disabled={retrying} className="ml-auto">
              {retrying ? 'Retrying…' : '↻ Retry case'}
            </Button>
          )}
        </div>
      </div>

      <Card>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field label="Priority" value={data.priority} />
          <Field label="Retries merged" value={data.eventCount} />
          <Field label="Latest event" value={data.latestEventType} />
          <Field label="Entity status" value={data.latestEntityStatus} />
          <Field label="Customer email" value={data.customerEmail} />
          <Field label="Customer phone" value={data.customerContact} />
          <Field label="Case key" value={data.caseKey} />
          <Field label="Razorpay account" value={data.razorpayAccountId} />
        </div>
        {data.priorityReason && (
          <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <span className="font-semibold text-slate-600">Priority reason: </span>
            {data.priorityReason}
          </p>
        )}
        {data.lastError && (
          <p className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">
            <span className="font-semibold">Last error: </span>
            {data.lastError}
          </p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-bold text-slate-700">Audit trail</h2>
        <p className="mb-4 text-xs text-slate-400">
          Everything that happened on this case, in order - what Razorpay told us, and what the agent
          did about it. Click any step for the full detail.
        </p>
        <Timeline history={data.history} actions={data.actions} />
      </Card>
    </div>
  )
}
