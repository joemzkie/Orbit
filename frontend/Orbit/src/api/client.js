const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

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
  const timeout = window.setTimeout(() => controller.abort(), 9000);
  const abort = () => controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
    });
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;

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
        "Server is taking longer than usual to respond. Please try again in a moment.",
        504,
        "request_timeout",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
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
