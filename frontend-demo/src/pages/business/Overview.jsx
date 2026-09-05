import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listBusinessCases } from '../../api/businessApi'
import { useBusiness } from '../../context/BusinessContext'
import { Card, ErrorBanner, Skeleton, StatCard } from '../../components/business/Primitives'
import StatusBadge from '../../components/business/StatusBadge'

const ACTIVE_STATUSES = new Set(['RECEIVED', 'QUEUED', 'PROCESSING'])
const DONE_STATUSES = new Set(['PROCESSED', 'RESOLVED'])
const NEEDS_ATTENTION = new Set(['FAILED', 'DEAD'])

export default function Overview() {
  const { businessId, business } = useBusiness()
  const [cases, setCases] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    listBusinessCases(businessId, { limit: 100 })
      .then((data) => !cancelled && setCases(data))
      .catch((reason) => !cancelled && setError(reason.message))
    return () => {
      cancelled = true
    }
  }, [businessId])

  const stats = useMemo(() => {
    if (!cases) return null
    return {
      total: cases.length,
      active: cases.filter((c) => ACTIVE_STATUSES.has(c.processingStatus)).length,
      resolved: cases.filter((c) => DONE_STATUSES.has(c.processingStatus)).length,
      needsAttention: cases.filter((c) => NEEDS_ATTENTION.has(c.processingStatus)).length,
    }
  }, [cases])

  const recent = useMemo(
    () => (cases ? [...cases].sort((a, b) => new Date(b.lastEventAt) - new Date(a.lastEventAt)).slice(0, 6) : []),
    [cases],
  )

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
          {business?.name || 'Dashboard'}
        </h1>
        <p className="text-sm text-slate-400">Live view of what your recovery agent is doing.</p>
      </div>

      <ErrorBanner message={error} />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats ? (
          <>
            <StatCard label="Total cases" value={stats.total} />
            <StatCard label="Active" value={stats.active} accent="#d97706" />
            <StatCard label="Resolved" value={stats.resolved} accent="#059669" />
            <StatCard label="Needs attention" value={stats.needsAttention} accent="#dc2626" />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
        )}
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-700">Recently active cases</h2>
          <Link to="/business/cases" className="text-xs font-semibold text-slate-400 hover:text-slate-700">
            View all →
          </Link>
        </div>

        {!cases ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">No recovery cases yet.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-slate-100">
            {recent.map((c, i) => (
              <li key={c.id} className="stagger-item" style={{ '--i': i }}>
                <Link
                  to={`/business/cases/${c.id}`}
                  className="flex items-center justify-between gap-3 py-3 transition-colors hover:bg-slate-50"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-800">
                      Case #{c.id} · {c.latestEventType}
                    </div>
                    <div className="truncate text-xs text-slate-400">
                      {c.customerContact || c.customerEmail || 'Unknown customer'} · priority {c.priority}
                    </div>
                  </div>
                  <StatusBadge status={c.processingStatus} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
