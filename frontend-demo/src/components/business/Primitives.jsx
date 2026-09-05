export function StatCard({ label, value, accent = '#0f2027', sub }) {
  return (
    <div className="animate-fade-in-up rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {label}
      </div>
      <div className="mt-2 text-3xl font-extrabold tracking-tight" style={{ color: accent }}>
        {value}
      </div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`skeleton rounded-lg ${className}`} />
}

export function EmptyState({ icon = '◌', title, description, action }) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-16 text-center">
      <div className="text-3xl">{icon}</div>
      <div className="text-sm font-semibold text-slate-600">{title}</div>
      {description && <p className="max-w-sm text-xs text-slate-400">{description}</p>}
      {action}
    </div>
  )
}

export function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="animate-fade-in-up rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {message}
    </div>
  )
}

export function Button({ variant = 'primary', className = '', ...props }) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50'
  const variants = {
    primary: 'bg-slate-900 text-white hover:bg-slate-700 shadow-sm hover:shadow',
    secondary: 'bg-white text-slate-700 border border-slate-200 hover:border-slate-300 hover:bg-slate-50',
    danger: 'bg-rose-600 text-white hover:bg-rose-500',
    ghost: 'text-slate-500 hover:bg-slate-100',
  }
  return <button className={`${base} ${variants[variant] || variants.primary} ${className}`} {...props} />
}

export function Input({ label, className = '', ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      {label && <span className="text-xs font-semibold text-slate-500">{label}</span>}
      <input
        className={`rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition-colors focus:border-slate-400 ${className}`}
        {...props}
      />
    </label>
  )
}

export function TextArea({ label, className = '', ...props }) {
  return (
    <label className="flex flex-col gap-1.5">
      {label && <span className="text-xs font-semibold text-slate-500">{label}</span>}
      <textarea
        className={`rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition-colors focus:border-slate-400 ${className}`}
        {...props}
      />
    </label>
  )
}

export function Card({ className = '', children }) {
  return (
    <div className={`animate-fade-in-up rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </div>
  )
}
