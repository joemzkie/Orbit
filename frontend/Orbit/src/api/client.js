const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message)
    this.status = status
    this.code = code
  }
}

function idempotencyKey() {
  return crypto.randomUUID()
}

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 9000)
  const abort = () => controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...options.headers,
      },
    })
    const text = await response.text()
    const payload = text ? JSON.parse(text) : null

    if (!response.ok) {
      throw new ApiError(payload?.detail || 'The request could not be completed.', response.status, payload?.code)
    }
    return payload
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new ApiError('Server is taking longer than usual to respond. Please try again in a moment.', 504, 'request_timeout')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abort)
  }
}

function mutation(path, method, body) {
  return request(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey(),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
}

export const api = {
  getCurrentUser: () => request('/auth/me'),
  login: (email, password) => mutation('/auth/login', 'POST', { email, password }),
  logout: () => mutation('/auth/logout', 'POST'),
  getPosts: (cursor, signal) => request(`/posts?limit=20${cursor ? `&cursor=${cursor}` : ''}`, { signal }),
  createPost: (post) => mutation('/posts', 'POST', post),
}
