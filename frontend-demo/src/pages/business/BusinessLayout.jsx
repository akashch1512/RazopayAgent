import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useBusiness } from '../../context/BusinessContext'

const NAV_ITEMS = [
  { to: '/business', label: 'Overview', icon: '◱', end: true },
  { to: '/business/cases', label: 'Recovery cases', icon: '☰' },
  { to: '/business/invoices', label: 'Invoices (B2B)', icon: '₹' },
  { to: '/business/start-recovery', label: 'Start recovery', icon: '+' },
  { to: '/business/settings', label: 'Agent settings', icon: '⚙' },
]

function navClass({ isActive }) {
  return `flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all ${
    isActive ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
  }`
}

export default function BusinessLayout() {
  const { businessId, business, loading, setBusinessId } = useBusiness()
  const navigate = useNavigate()

  if (!businessId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="animate-pop-in max-w-sm rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <div className="mb-3 text-3xl">🏢</div>
          <h1 className="mb-1 text-lg font-bold text-slate-800">No business selected</h1>
          <p className="mb-5 text-sm text-slate-400">
            Onboard a business or switch to one you already onboarded.
          </p>
          <button
            onClick={() => navigate('/business/login')}
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
          >
            Log in with reference ID
          </button>
          <button
            onClick={() => navigate('/business/onboard')}
            className="mt-2 w-full rounded-lg px-4 py-2.5 text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
          >
            Onboard a new business
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="animate-fade-in flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-5">
        <div className="mb-8 flex items-center gap-2 px-1">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-900 font-serif text-lg text-emerald-400">
            R
          </span>
          <span className="text-sm font-extrabold tracking-tight text-slate-800">Recovery</span>
          <span className="ml-auto rounded bg-emerald-100 px-1.5 py-0.5 font-mono text-[8px] font-bold text-emerald-700">
            BUSINESS
          </span>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
              <span className="text-base leading-none">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-3 border-t border-slate-100 pt-4">
          <div className="rounded-xl bg-slate-50 p-3">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Current business
            </div>
            <div className="mt-1 truncate text-sm font-bold text-slate-800">
              {loading ? 'Loading…' : business?.name || `#${businessId}`}
            </div>
            <div className="truncate font-mono text-[10px] text-slate-400">
              {business?.status || '—'}
            </div>
          </div>
          <button
            onClick={() => {
              setBusinessId('')
              navigate('/')
            }}
            className="w-full rounded-lg px-3 py-2 text-left text-xs font-semibold text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          >
            ← Switch business
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="animate-fade-in-up mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
