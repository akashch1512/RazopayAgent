import { get, post, put } from './client'

// ── Onboarding ──────────────────────────────────────────────────────────────
export const startOnboarding = (payload) => post('/onboard-business/', payload)
export const listBusinesses = (params = {}) =>
  get(`/onboard-business/?${new URLSearchParams(params)}`)
export const getBusiness = (businessId) => get(`/onboard-business/${businessId}`)
export const lookupBusinessByReferenceId = (referenceId) =>
  get(`/onboard-business/lookup?${new URLSearchParams({ reference_id: referenceId })}`)
export const getWebhookConfig = (businessId) => get(`/onboard-business/${businessId}/webhooks`)

// ── Agent settings ───────────────────────────────────────────────────────────
export const getAgentSettings = (businessId) => get(`/onboard-business/${businessId}/settings`)
export const updateAgentSettings = (businessId, payload) =>
  put(`/onboard-business/${businessId}/settings`, payload)

// ── Recovery cases ───────────────────────────────────────────────────────────
export const listBusinessCases = (businessId, params = {}) =>
  get(`/onboard-business/${businessId}/recovery-cases?${new URLSearchParams(params)}`)
export const listAllCases = (params = {}) =>
  get(`/recovery-cases/?${new URLSearchParams(params)}`)
export const getCase = (caseId) => get(`/recovery-cases/${caseId}`)
export const retryCase = (caseId) => post(`/recovery-cases/${caseId}/retry`)
export const startCustomRecovery = (businessId, payload) =>
  post(`/onboard-business/${businessId}/recovery-cases/start`, payload)

// ── Invoices / B2B chase ─────────────────────────────────────────────────────
export const listInvoices = (businessId, params = {}) =>
  get(`/onboard-business/${businessId}/invoices?${new URLSearchParams(params)}`)
export const startInvoiceChase = (businessId, invoiceId, payload = {}) =>
  post(`/onboard-business/${businessId}/invoices/${invoiceId}/chase`, payload)
