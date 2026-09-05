import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listBusinessCases } from '../../api/businessApi'
import { useBusiness } from '../../context/BusinessContext'
import { Card, EmptyState, ErrorBanner, Skeleton } from '../../components/business/Primitives'
import StatusBadge from '../../components/business/StatusBadge'

const STATUS_FILTERS = ['ALL', 'RECEIVED', 'QUEUED', 'PROCESSING', 'PROCESSED', 'RESOLVED', 'FAILED', 'DEAD']

export default function CasesList() {
  const { businessId } = useBusiness()
  const [cases, setCases] = useState(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    let cancelled = false
    setCases(null)
    listBusinessCases(businessId, { limit: 100 })
      .then((data) => !cancelled && setCases(data))
      .catch((reason) => !cancelled && setError(reason.message))
    return () => {
      cancelled = true
    }
  }, [businessId])

  const visible = cases ? cases.filter((c) => filter === 'ALL' || c.processingStatus === filter) : []

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Recovery cases</h1>
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`rounded-full px-3 py-1.5 text-xs font-bold transition-colors ${
              filter === status
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-500 border border-slate-200 hover:border-slate-300'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      <ErrorBanner message={error} />

      {!cases ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <EmptyState icon="☰" title="No cases match this filter" />
      ) : (
        <Card className="!p-0">
          <ul className="divide-y divide-slate-100">
            {visible.map((c, i) => (
              <li key={c.id} className="stagger-item" style={{ '--i': i }}>
                <Link
                  to={`/business/cases/${c.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-800">#{c.id}</span>
                      <span className="truncate text-sm text-slate-600">{c.latestEventType}</span>
                    </div>
                    <div className="mt-0.5 truncate text-xs text-slate-400">
                      {c.customerContact || c.customerEmail || 'Unknown customer'} · {c.eventCount} event(s) ·
                      priority {c.priority}
                    </div>
                  </div>
                  <StatusBadge status={c.processingStatus} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
