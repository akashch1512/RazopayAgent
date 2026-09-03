export const icons = {
  whatsapp: '◔',
  sms: '✦',
  email: '✉',
}

export const labels = {
  whatsapp: 'WhatsApp',
  sms: 'SMS',
  email: 'Email',
}

export const channelColor = {
  whatsapp: '#25D366',
  sms: '#007AFF',
  email: '#EA4335',
}

export function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    day: 'numeric',
    month: 'short',
  }).format(new Date(value))
}

export function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export function paymentSummary(caseData) {
  const payment = caseData?.context?.payment ?? {}

  return String(payment.amount || caseData?.payment_id || 'No payment context')
}

export function agentState(caseData) {
  if (!caseData) return 'Waiting for case'

  return String(caseData.current_step || caseData.status || 'Waiting for case').replaceAll('_', ' ')
}

export function agentJsonOutput(caseData) {
  if (!caseData) return {}

  return {
    decision: caseData.decision,
    decision_reason: caseData.decision_reason,
    next_action: caseData.next_action,
    current_step: caseData.current_step,
    priority_score: caseData.priority_score,
    attempt_count: caseData.attempt_count,
  }
}
