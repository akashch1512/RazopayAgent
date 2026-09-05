import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useBusiness } from '../../context/BusinessContext'

export default function OnboardComplete() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { setBusinessId, refresh } = useBusiness()

  const businessId = params.get('business_id')
  const error = params.get('error')

  useEffect(() => {
    if (businessId) {
      setBusinessId(businessId)
      refresh()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [businessId])

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="animate-pop-in max-w-sm rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        {error ? (
          <>
            <div className="mb-3 text-3xl">⚠️</div>
            <h1 className="mb-1 text-lg font-bold text-slate-800">Onboarding didn't complete</h1>
            <p className="mb-5 text-sm text-slate-400">{error}</p>
          </>
        ) : (
          <>
            <div className="mb-3 text-3xl">🎉</div>
            <h1 className="mb-1 text-lg font-bold text-slate-800">Business connected!</h1>
            <p className="mb-5 text-sm text-slate-400">
              Razorpay access granted and a webhook registered. Your dashboard is ready.
            </p>
          </>
        )}
        <button
          onClick={() => navigate('/business')}
          className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
        >
          {error ? 'Back to dashboard' : 'Go to dashboard →'}
        </button>
      </div>
    </div>
  )
}
