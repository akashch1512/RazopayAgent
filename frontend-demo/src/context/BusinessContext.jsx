import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getBusiness } from '../api/businessApi'

const BusinessContext = createContext(null)

const STORAGE_KEY = 'recovery-dashboard-business-id'

export function BusinessProvider({ children }) {
  const [businessId, setBusinessIdState] = useState(() => localStorage.getItem(STORAGE_KEY) || '')
  const [business, setBusiness] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const setBusinessId = useCallback((id) => {
    if (id) {
      localStorage.setItem(STORAGE_KEY, id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
    setBusinessIdState(id)
  }, [])

  const refresh = useCallback(async () => {
    if (!businessId) {
      setBusiness(null)
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await getBusiness(businessId)
      setBusiness(data)
    } catch (reason) {
      setBusiness(null)
      setError(reason instanceof Error ? reason.message : 'Could not load business.')
    } finally {
      setLoading(false)
    }
  }, [businessId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return (
    <BusinessContext.Provider
      value={{ businessId, setBusinessId, business, loading, error, refresh }}
    >
      {children}
    </BusinessContext.Provider>
  )
}

export function useBusiness() {
  const ctx = useContext(BusinessContext)
  if (!ctx) throw new Error('useBusiness must be used inside <BusinessProvider>')
  return ctx
}
