const STATUS_STYLES = {
  RECEIVED: 'bg-slate-100 text-slate-600',
  QUEUED: 'bg-amber-100 text-amber-700',
  PROCESSING: 'bg-amber-100 text-amber-700 animate-pulse',
  PROCESSED: 'bg-emerald-100 text-emerald-700',
  RESOLVED: 'bg-emerald-100 text-emerald-700',
  FAILED: 'bg-rose-100 text-rose-700',
  DEAD: 'bg-rose-200 text-rose-800',
}

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || 'bg-slate-100 text-slate-600'
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${style}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  )
}
