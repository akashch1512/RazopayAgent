import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  Building2,
  MessageSquareText,
} from 'lucide-react'

export default function RoleSelect() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#0f1115] text-white">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl items-center px-6 py-12">
        <div className="w-full">
          {/* Header */}
          <div className="mb-10">
            <div className="mb-3 flex items-center gap-2 text-xs font-medium text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Recovery Agent
            </div>

            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Choose how to continue
            </h1>

            <p className="mt-3 max-w-lg text-sm leading-6 text-zinc-400">
              Select the environment you want to explore.
            </p>
          </div>

          {/* Cards */}
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Business */}
            <button
              type="button"
              onClick={() => navigate('/business')}
              className="group rounded-2xl border border-zinc-800 bg-[#15181d] p-6 text-left transition-all duration-200 hover:border-zinc-700 hover:bg-[#191c22]"
            >
              <div className="mb-8 flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-900 text-zinc-200 ring-1 ring-zinc-800">
                  <Building2 className="h-5 w-5" />
                </div>

                <ArrowRight className="h-4 w-4 text-zinc-600 transition-transform group-hover:translate-x-1 group-hover:text-emerald-400" />
              </div>

              <h2 className="text-lg font-semibold">
                Business
              </h2>

              <p className="mt-2 text-sm leading-6 text-zinc-400">
                Manage recovery cases, invoices, onboarding, agent settings,
                and payment operations.
              </p>

              <div className="mt-6 border-t border-zinc-800 pt-4">
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    navigate('/business/login')
                  }}
                  className="text-xs font-medium text-zinc-500 transition-colors hover:text-emerald-400"
                >
                  Already onboarded? Log in
                </button>
              </div>
            </button>

            {/* Customer */}
            <button
              type="button"
              onClick={() => navigate('/customer')}
              className="group rounded-2xl border border-zinc-800 bg-[#15181d] p-6 text-left transition-all duration-200 hover:border-zinc-700 hover:bg-[#191c22]"
            >
              <div className="mb-8 flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
                  <MessageSquareText className="h-5 w-5" />
                </div>

                <ArrowRight className="h-4 w-4 text-zinc-600 transition-transform group-hover:translate-x-1 group-hover:text-emerald-400" />
              </div>

              <h2 className="text-lg font-semibold">
                Customer
              </h2>

              <p className="mt-2 text-sm leading-6 text-zinc-400">
                Experience recovery messages, payment links, calls, and the
                customer inbox.
              </p>

              <div className="mt-6 border-t border-zinc-800 pt-4 text-xs text-zinc-500">
                Customer experience
              </div>
            </button>
          </div>

          {/* Footer */}
          <div className="mt-8 text-xs text-zinc-600">
            Demo environment
          </div>
        </div>
      </div>
    </div>
  )
}
