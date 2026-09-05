const API_BASE_URL = (
  import.meta.env.VITE_BACKEND_API_BASE_URL || 'http://localhost:8000/api'
).replace(/\/$/, '')

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

  if (response.status === 204) return null
  return response.json()
}

export const get = (path) => request(path)
export const post = (path, body) =>
  request(path, { method: 'POST', body: JSON.stringify(body ?? {}) })
export const put = (path, body) =>
  request(path, { method: 'PUT', body: JSON.stringify(body ?? {}) })
