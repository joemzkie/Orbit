const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

function apiBaseUrl(value) {
  // Local development can use the Vite proxy by leaving VITE_API_URL unset.
  if (!value) return "/api";

  const base = value.replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(base)) return base;

  const url = new URL(base);
  // Render is served over TLS. Avoid an HTTP request that Render would redirect.
  if (import.meta.env.PROD) url.protocol = "https:";
  // Orbit's FastAPI routers are all mounted below /api. This also makes a
  // host-only Render URL resolve to the correct API prefix exactly once.
  if (!url.pathname || url.pathname === "/") url.pathname = "/api";
  return url.toString().replace(/\/+$/, "");
}

const API_BASE = apiBaseUrl(configuredApiUrl);
const REQUEST_TIMEOUT_MS = 65_000;
const WAKE_UP_NOTICE_MS = 4_000;
const API_DEBUG = import.meta.env.VITE_API_DEBUG === "true";

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

function logApiDiagnostic(event, details) {
  const failedResponse = event === "response_received" && (
    details.redirected || details.status >= 400
  );
  if (API_DEBUG || event === "request_failed" || failedResponse) {
    // Never include headers, cookies, or request bodies in browser diagnostics.
    console.info(`[Orbit API] ${event}`, details);
  }
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
  const url = apiUrl(path);
  const method = options.method || "GET";
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
    logApiDiagnostic("request_started", { method, url });
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
    });
    logApiDiagnostic("response_received", {
      method,
      requestUrl: url,
      responseUrl: response.url,
      status: response.status,
      redirected: response.redirected,
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
    logApiDiagnostic("request_failed", {
      method,
      url,
      error: error instanceof Error ? error.message : String(error),
    });
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
