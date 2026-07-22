const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
// Production uses the Render URL ending in /api. Local development can use the
// Vite proxy by leaving VITE_API_URL unset.
const API_BASE = (configuredApiUrl || "/api").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 65_000;
const WAKE_UP_NOTICE_MS = 4_000;

let slowRequestCount = 0;
let networkStatusListener = () => {};

export function subscribeNetworkStatus(listener) {
  networkStatusListener = listener;
  return () => {
    if (networkStatusListener === listener) networkStatusListener = () => {};
  };
}

function apiUrl(path) {
  const endpoint = path.replace(/^\/+/, "");
  return `${API_BASE}/${endpoint}`;
}

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function idempotencyKey() {
  return crypto.randomUUID();
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let isSlow = false;
  const wakeUpNotice = window.setTimeout(() => {
    isSlow = true;
    slowRequestCount += 1;
    networkStatusListener(true);
  }, WAKE_UP_NOTICE_MS);
  const abort = () => controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });

  try {
    const response = await fetch(apiUrl(path), {
      ...options,
      signal: controller.signal,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
    });
    const text = await response.text();
    let payload = null;

    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        // Render proxies can return a non-JSON HTML error page during an outage.
        // Preserve a useful error rather than letting JSON.parse crash the UI.
        payload = { detail: "The server returned an unexpected response." };
      }
    }

    if (!response.ok) {
      throw new ApiError(
        payload?.detail || "The request could not be completed.",
        response.status,
        payload?.code,
      );
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError(
        "The server did not respond within 65 seconds. Please try again.",
        504,
        "request_timeout",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
    window.clearTimeout(wakeUpNotice);
    if (isSlow) {
      slowRequestCount -= 1;
      networkStatusListener(slowRequestCount > 0);
    }
    options.signal?.removeEventListener("abort", abort);
  }
}

function mutation(path, method, body) {
  return request(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

export const api = {
  getCurrentUser: () => request("/auth/me"),
  signup: (email, username, password) =>
    mutation("/auth/signup", "POST", { email, username, password }),
  login: (email, password) =>
    mutation("/auth/login", "POST", { email, password }),
  logout: () => mutation("/auth/logout", "POST"),
  updateUsername: (username) =>
    mutation("/auth/me/profile", "PATCH", { username }),
  updatePassword: (current_password, new_password) =>
    mutation("/auth/me/password", "PUT", { current_password, new_password }),
  getPosts: (cursor, signal) =>
    request(`/posts?limit=20${cursor ? `&cursor=${cursor}` : ""}`, { signal }),
  getPost: (postId) => request(`/posts/${postId}`),
  getPopularPosts: () => request("/posts/popular"),
  createPost: (post) => mutation("/posts", "POST", post),
  getComments: (postId) => request(`/posts/${postId}/comments`),
  createComment: (postId, comment) =>
    mutation(`/posts/${postId}/comments`, "POST", { comment }),
  likePost: (postId) => mutation(`/posts/${postId}/like`, "POST"),
  unlikePost: (postId) => mutation(`/posts/${postId}/like`, "DELETE"),
  likeComment: (commentId) => mutation(`/comments/${commentId}/like`, "POST"),
  unlikeComment: (commentId) =>
    mutation(`/comments/${commentId}/like`, "DELETE"),
};
