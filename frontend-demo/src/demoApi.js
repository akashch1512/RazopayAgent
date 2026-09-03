const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed (${response.status})`

    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      // Keep the HTTP error when the server does not return JSON.
    }

    throw new Error(detail)
  }

  return response.json()
}

export function getUserDashboard(userId) {
  return request(`/dashboard/users/${encodeURIComponent(userId)}`)
}

export function sendDashboardMessage(userId, payload) {
  return request(`/dashboard/users/${encodeURIComponent(userId)}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function markDashboardPaymentComplete(userId, caseId) {
  return request(`/dashboard/users/${encodeURIComponent(userId)}/pay`, {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId }),
  })
}
