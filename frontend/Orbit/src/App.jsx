import { useEffect, useState } from "react";
import { ApiError, api } from "./api/client";
import "./App.css";

function postIdFromHash() {
  const match = window.location.hash.match(/^#\/posts\/(\d+)$/);
  return match ? Number(match[1]) : null;
}

function isSettingsHash() {
  return window.location.hash === "#/settings";
}

function CommentSection({ post, currentUser, showError }) {
  const [comments, setComments] = useState([]);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!Number.isInteger(post.id)) return;
    let active = true;
    api
      .getComments(post.id)
      .then((items) => {
        if (active) setComments(items);
      })
      .catch(showError)
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [post.id]);

  async function submit(event) {
    event.preventDefault();
    const body = comment.trim();
    if (!body || !currentUser || submitting) return;
    const optimistic = {
      id: `pending-${crypto.randomUUID()}`,
      post_id: post.id,
      owner: currentUser.username,
      comment: body,
      likes_count: 0,
      is_owned_by_current_user: true,
      created_at: new Date().toISOString(),
      pending: true,
    };
    setSubmitting(true);
    setComments((items) => [...items, optimistic]);
    setComment("");
    try {
      const created = await api.createComment(post.id, body);
      setComments((items) =>
        items.map((item) => (item.id === optimistic.id ? created : item)),
      );
    } catch (error) {
      setComments((items) => items.filter((item) => item.id !== optimistic.id));
      showError(error);
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleCommentLike(item) {
    if (
      !currentUser ||
      item.is_owned_by_current_user ||
      item.pending ||
      item.likeBusy
    )
      return;
    const original = {
      liked_by_current_user: Boolean(item.liked_by_current_user),
      likes_count: item.likes_count || 0,
    };
    const optimistic = {
      liked_by_current_user: !original.liked_by_current_user,
      likes_count:
        original.likes_count + (original.liked_by_current_user ? -1 : 1),
      likeBusy: true,
    };
    setComments((items) =>
      items.map((current) =>
        current.id === item.id ? { ...current, ...optimistic } : current,
      ),
    );
    try {
      const state = original.liked_by_current_user
        ? await api.unlikeComment(item.id)
        : await api.likeComment(item.id);
      setComments((items) =>
        items.map((current) =>
          current.id === item.id ? { ...current, ...state } : current,
        ),
      );
    } catch (error) {
      setComments((items) =>
        items.map((current) =>
          current.id === item.id ? { ...current, ...original } : current,
        ),
      );
      showError(error);
    } finally {
      window.setTimeout(
        () =>
          setComments((items) =>
            items.map((current) =>
              current.id === item.id
                ? { ...current, likeBusy: false }
                : current,
            ),
          ),
        300,
      );
    }
  }

  return (
    <section className="comments" aria-label="Comments">
      <h3>Comments {comments.length ? `(${comments.length})` : ""}</h3>
      {loading ? (
        <p className="comments-status">Loading comments…</p>
      ) : comments.length ? (
        <div className="comment-list">
          {comments.map((item) => {
            const isOwner = item.is_owned_by_current_user;
            return (
              <article
                className={`comment-card${item.pending ? " comment-card--pending" : ""}`}
                key={item.id}
              >
                <header>
                  <strong>{item.owner}</strong>
                  <time dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString()}
                  </time>
                </header>
                <p>{item.comment}</p>
                <button
                  className={`comment-like-button${item.liked_by_current_user ? " comment-like-button--active" : ""}`}
                  type="button"
                  onClick={() => toggleCommentLike(item)}
                  disabled={
                    !currentUser || isOwner || item.pending || item.likeBusy
                  }
                  aria-pressed={Boolean(item.liked_by_current_user)}
                >
                  {item.liked_by_current_user ? "♥ Liked" : "♡ Like"}{" "}
                  {item.likes_count || 0}
                </button>
                {isOwner && (
                  <span className="comment-self-like-note">Your comment</span>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <p className="comments-status">No comments yet.</p>
      )}
      {currentUser?.username ? (
        <form className="comment-form" onSubmit={submit}>
          <label>
            Add a comment
            <textarea
              required
              maxLength="5000"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              disabled={submitting}
              placeholder="Join the conversation…"
            />
          </label>
          <button type="submit" disabled={submitting || !comment.trim()}>
            {submitting ? "Posting…" : "Post comment"}
          </button>
        </form>
      ) : currentUser ? (
        <p className="comments-status">
          Choose a username in Settings to add a comment.
        </p>
      ) : (
        <p className="comments-status">Sign in to add a comment.</p>
      )}
    </section>
  );
}

function PostCard({ post, currentUser, onToggleLike, showError }) {
  const isOwner = post.is_owned_by_current_user;
  const [likeBusy, setLikeBusy] = useState(false);

  async function toggleLike() {
    if (!currentUser || isOwner || likeBusy || post.pending) return;
    setLikeBusy(true);
    try {
      await onToggleLike(post);
    } finally {
      window.setTimeout(() => setLikeBusy(false), 300);
    }
  }

  return (
    <article
      className={`post-card${post.pending ? " post-card--pending" : ""}`}
    >
      <header className="post-owner">
        <div className="avatar" aria-hidden="true">
          {post.owner?.[0]?.toUpperCase() || "?"}
        </div>
        <div>
          <p className="eyebrow">Post owner</p>
          <strong>{post.owner}</strong>
        </div>
        {isOwner && <span className="owner-badge">Your post</span>}
        {post.pending && <span className="pending-badge">Sending…</span>}
      </header>
      <div className="post-body">
        <h2>{post.title}</h2>
        <p>{post.content}</p>
      </div>
      <footer>
        <time dateTime={post.created_at}>
          {post.created_at
            ? new Date(post.created_at).toLocaleString()
            : "Sending now"}
        </time>
        <button
          className={`like-button${post.liked_by_current_user ? " like-button--active" : ""}`}
          type="button"
          onClick={toggleLike}
          disabled={!currentUser || isOwner || post.pending || likeBusy}
          aria-pressed={Boolean(post.liked_by_current_user)}
        >
          {post.liked_by_current_user ? "♥ Liked" : "♡ Like"}{" "}
          {post.likes_count || 0}
        </button>
      </footer>
      {isOwner && (
        <p className="self-like-note">You cannot like your own post.</p>
      )}
      <CommentSection
        post={post}
        currentUser={currentUser}
        showError={showError}
      />
    </article>
  );
}

function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}

function LoginPanel({ onLogin, onShowSignup, pending }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function submit(event) {
    event.preventDefault();
    onLogin(email, password);
  }

  return (
    <form className="login-panel" onSubmit={submit}>
      <p className="eyebrow">Account access</p>
      <h2>Sign in to publish</h2>
      <label>
        Email
        <input
          required
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>
      <label>
        Password
        <input
          required
          minLength="8"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      <button disabled={pending} type="submit">
        {pending ? "Signing in…" : "Sign in"}
      </button>
      <button className="text-button" type="button" onClick={onShowSignup}>
        Need an account? Sign up
      </button>
    </form>
  );
}

function SignupPanel({ onSignup, onShowLogin, pending }) {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const isStrong =
    password.length >= 12 &&
    /[a-z]/.test(password) &&
    /[A-Z]/.test(password) &&
    /\d/.test(password);
  const passwordsMatch =
    confirmPassword.length > 0 && password === confirmPassword;

  function submit(event) {
    event.preventDefault();
    if (isStrong && passwordsMatch && /^[a-z0-9_]{3,30}$/.test(username))
      onSignup(email, username, password);
  }

  return (
    <form className="login-panel" onSubmit={submit}>
      <p className="eyebrow">Create account</p>
      <h2>Join the conversation</h2>
      <label>
        Email
        <input
          required
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </label>
      <label>
        Username
        <input
          required
          minLength="3"
          maxLength="30"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value.toLowerCase())}
          placeholder="lowercase_name"
        />
      </label>
      <p
        className={`field-hint${username && !/^[a-z0-9_]{3,30}$/.test(username) ? " field-hint--error" : ""}`}
      >
        3–30 lowercase letters, numbers, or underscores.
      </p>
      <label>
        Password
        <input
          required
          minLength="12"
          maxLength="256"
          autoComplete="new-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      <p
        className={`field-hint${password && !isStrong ? " field-hint--error" : ""}`}
      >
        Use 12+ characters with uppercase, lowercase, and a number.
      </p>
      <label>
        Confirm password
        <input
          required
          minLength="12"
          autoComplete="new-password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
        />
      </label>
      {confirmPassword && (
        <p
          className={`field-hint${!passwordsMatch ? " field-hint--error" : ""}`}
        >
          {passwordsMatch ? "Passwords match." : "Passwords do not match."}
        </p>
      )}
      <button
        disabled={
          pending ||
          !/^[a-z0-9_]{3,30}$/.test(username) ||
          !isStrong ||
          !passwordsMatch
        }
        type="submit"
      >
        {pending ? "Creating account…" : "Create account"}
      </button>
      <button className="text-button" type="button" onClick={onShowLogin}>
        Already have an account? Sign in
      </button>
    </form>
  );
}

function SettingsPage({ user, onUpdateUsername, onUpdatePassword, pending }) {
  const [username, setUsername] = useState(user?.username || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const usernameValid = /^[a-z0-9_]{3,30}$/.test(username);
  const passwordStrong =
    newPassword.length >= 12 &&
    /[a-z]/.test(newPassword) &&
    /[A-Z]/.test(newPassword) &&
    /\d/.test(newPassword);

  return (
    <section className="settings-page">
      <a className="back-to-feed" href="#/">
        ← Back to feed
      </a>
      <p className="eyebrow">Account</p>
      <h1>Settings</h1>
      <form
        className="login-panel"
        onSubmit={(event) => {
          event.preventDefault();
          if (usernameValid) onUpdateUsername(username);
        }}
      >
        <h2>Public username</h2>
        <p className="settings-copy">
          This name appears on new posts and comments.
        </p>
        <label>
          Username
          <input
            required
            minLength="3"
            maxLength="30"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value.toLowerCase())}
          />
        </label>
        <p
          className={`field-hint${username && !usernameValid ? " field-hint--error" : ""}`}
        >
          3–30 lowercase letters, numbers, or underscores.
        </p>
        <button disabled={pending || !usernameValid} type="submit">
          Save username
        </button>
      </form>
      <form
        className="login-panel"
        onSubmit={async (event) => {
          event.preventDefault();
          if (
            passwordStrong &&
            newPassword === confirmPassword &&
            (await onUpdatePassword(currentPassword, newPassword))
          ) {
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
          }
        }}
      >
        <h2>Change password</h2>
        <label>
          Current password
          <input
            required
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
        </label>
        <label>
          New password
          <input
            required
            minLength="12"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
        </label>
        <p
          className={`field-hint${newPassword && !passwordStrong ? " field-hint--error" : ""}`}
        >
          Use 12+ characters with uppercase, lowercase, and a number.
        </p>
        <label>
          Confirm new password
          <input
            required
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </label>
        {confirmPassword && newPassword !== confirmPassword && (
          <p className="field-hint field-hint--error">
            Passwords do not match.
          </p>
        )}
        <button
          disabled={
            pending ||
            !currentPassword ||
            !passwordStrong ||
            newPassword !== confirmPassword
          }
          type="submit"
        >
          Change password
        </button>
      </form>
    </section>
  );
}

function App() {
  const [posts, setPosts] = useState([]);
  const [popularPosts, setPopularPosts] = useState([]);
  const [selectedPostId, setSelectedPostId] = useState(postIdFromHash);
  const [settingsOpen, setSettingsOpen] = useState(isSettingsHash);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(
    () => window.localStorage.getItem("orbit-theme") === "dark",
  );
  const [selectedPost, setSelectedPost] = useState(null);
  const [selectedPostLoading, setSelectedPostLoading] = useState(false);
  const [nextCursor, setNextCursor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [user, setUser] = useState(null);
  const [authPending, setAuthPending] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [postPending, setPostPending] = useState(false);
  const [toast, setToast] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  function showError(error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Something went wrong. Please try again.";
    setToast(message);
  }

  async function loadFeed(cursor = null, signal) {
    const page = await api.getPosts(cursor, signal);
    setPosts((current) => (cursor ? [...current, ...page.items] : page.items));
    setNextCursor(page.next_cursor);
  }

  async function loadPopular() {
    setPopularPosts(await api.getPopularPosts());
  }

  useEffect(() => {
    const controller = new AbortController();
    loadFeed(null, controller.signal)
      .catch(showError)
      .finally(() => setLoading(false));
    loadPopular().catch(showError);
    api
      .getCurrentUser()
      .then(setUser)
      .catch((error) => {
        if (error.status !== 401) showError(error);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    window.localStorage.setItem("orbit-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    const syncSelectedPost = () => {
      setSelectedPostId(postIdFromHash());
      setSettingsOpen(isSettingsHash());
      setAccountMenuOpen(false);
    };
    window.addEventListener("hashchange", syncSelectedPost);
    return () => window.removeEventListener("hashchange", syncSelectedPost);
  }, []);

  useEffect(() => {
    if (!selectedPostId) {
      setSelectedPost(null);
      return;
    }
    let active = true;
    setSelectedPostLoading(true);
    api
      .getPost(selectedPostId)
      .then((post) => {
        if (active) setSelectedPost(post);
      })
      .catch((error) => {
        if (active) {
          setSelectedPost(null);
          showError(error);
        }
      })
      .finally(() => {
        if (active) setSelectedPostLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedPostId, user?.email]);

  async function handleLogin(email, password) {
    setAuthPending(true);
    try {
      setUser(await api.login(email, password));
      await loadFeed();
      await loadPopular();
      setToast("You are signed in.");
    } catch (error) {
      showError(error);
    } finally {
      setAuthPending(false);
    }
  }

  async function handleSignup(email, username, password) {
    setAuthPending(true);
    try {
      await api.signup(email, username, password);
      setAuthMode("login");
      setToast("Account created. Sign in to publish and join the discussion.");
    } catch (error) {
      showError(error);
    } finally {
      setAuthPending(false);
    }
  }

  async function handleLogout() {
    if (authPending) return;
    setAuthPending(true);
    try {
      await api.logout();
      setUser(null);
      setAuthMode("login");
      await loadFeed();
      await loadPopular();
      setToast("You have been signed out.");
    } catch (error) {
      showError(error);
    } finally {
      setAuthPending(false);
    }
  }

  async function handleUpdateUsername(username) {
    setAuthPending(true);
    try {
      setUser(await api.updateUsername(username));
      setToast("Username saved. New posts and comments will use it.");
      await loadFeed();
    } catch (error) {
      showError(error);
    } finally {
      setAuthPending(false);
    }
  }

  async function handleUpdatePassword(currentPassword, newPassword) {
    setAuthPending(true);
    try {
      await api.updatePassword(currentPassword, newPassword);
      setToast("Password changed.");
      return true;
    } catch (error) {
      showError(error);
      return false;
    } finally {
      setAuthPending(false);
    }
  }

  async function handleToggleLike(post) {
    const original = {
      liked_by_current_user: Boolean(post.liked_by_current_user),
      likes_count: post.likes_count || 0,
    };
    const optimistic = {
      liked_by_current_user: !original.liked_by_current_user,
      likes_count:
        original.likes_count + (original.liked_by_current_user ? -1 : 1),
    };
    setPosts((items) =>
      items.map((item) =>
        item.id === post.id ? { ...item, ...optimistic } : item,
      ),
    );
    try {
      const state = original.liked_by_current_user
        ? await api.unlikePost(post.id)
        : await api.likePost(post.id);
      setPosts((items) =>
        items.map((item) =>
          item.id === post.id ? { ...item, ...state } : item,
        ),
      );
      setPopularPosts((items) =>
        items.map((item) =>
          item.id === post.id ? { ...item, ...state } : item,
        ),
      );
      setSelectedPost((current) =>
        current?.id === post.id ? { ...current, ...state } : current,
      );
    } catch (error) {
      setPosts((items) =>
        items.map((item) =>
          item.id === post.id ? { ...item, ...original } : item,
        ),
      );
      showError(error);
    }
  }

  async function handleCreatePost(event) {
    event.preventDefault();
    if (!user || postPending) return;
    const optimistic = {
      id: `pending-${crypto.randomUUID()}`,
      owner: user.username,
      title,
      content,
      likes_count: 0,
      liked_by_current_user: false,
      is_owned_by_current_user: true,
      created_at: new Date().toISOString(),
      pending: true,
    };
    setPostPending(true);
    setPosts((current) => [optimistic, ...current]);
    setTitle("");
    setContent("");
    try {
      const created = await api.createPost({
        title: optimistic.title,
        content: optimistic.content,
        published: true,
      });
      setPosts((current) =>
        current.map((post) => (post.id === optimistic.id ? created : post)),
      );
    } catch (error) {
      setPosts((current) =>
        current.filter((post) => post.id !== optimistic.id),
      );
      showError(error);
    } finally {
      setPostPending(false);
    }
  }

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      await loadFeed(nextCursor);
    } catch (error) {
      showError(error);
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="/">
          Orbit<span>•</span>
        </a>
        <p>A thoughtful place to share ideas.</p>
        {user && (
          <div className="account-actions">
            <button
              className="account-button"
              type="button"
              aria-haspopup="menu"
              aria-expanded={accountMenuOpen}
              onClick={() => setAccountMenuOpen((open) => !open)}
            >
              {user.username || "Set username"} ▾
            </button>
            {accountMenuOpen && (
              <div className="account-menu" role="menu">
                <a href="#/settings" role="menuitem">
                  Settings
                </a>
                <button
                  role="menuitem"
                  type="button"
                  onClick={() => setDarkMode((enabled) => !enabled)}
                >
                  {darkMode ? "Light mode" : "Dark mode"}
                </button>
                <button
                  className="logout-button"
                  role="menuitem"
                  type="button"
                  onClick={handleLogout}
                  disabled={authPending}
                >
                  {authPending ? "Signing out…" : "Log out"}
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      {toast && (
        <div className="toast" role="status">
          {toast}
          <button onClick={() => setToast("")} aria-label="Dismiss message">
            ×
          </button>
        </div>
      )}

      <section
        className={`feed-layout${selectedPostId || settingsOpen ? " feed-layout--detail" : ""}`}
        aria-label="Orbit post feed"
      >
        <div className="feed-column">
          {settingsOpen ? (
            user ? (
              <SettingsPage
                user={user}
                onUpdateUsername={handleUpdateUsername}
                onUpdatePassword={handleUpdatePassword}
                pending={authPending}
              />
            ) : (
              <LoginPanel
                onLogin={handleLogin}
                onShowSignup={() => setAuthMode("signup")}
                pending={authPending}
              />
            )
          ) : selectedPostId ? (
            <>
              <section className="feed-heading">
                <a className="back-to-feed" href="#/">
                  ← Back to feed
                </a>
                <p className="eyebrow">Post discussion</p>
                <h1>Conversation</h1>
              </section>
              {selectedPostLoading ? (
                <SkeletonCard />
              ) : selectedPost ? (
                <PostCard
                  post={selectedPost}
                  currentUser={user}
                  onToggleLike={handleToggleLike}
                  showError={showError}
                />
              ) : (
                <p className="empty-state">This post is no longer available.</p>
              )}
            </>
          ) : (
            <>
              <section className="feed-heading">
                <p className="eyebrow">Community feed</p>
                <h1>Fresh from Orbit</h1>
              </section>
              {user?.username ? (
                <form className="composer" onSubmit={handleCreatePost}>
                  <label>
                    Title
                    <input
                      required
                      maxLength="255"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="Give your post a clear title"
                      disabled={postPending}
                    />
                  </label>
                  <label>
                    What are you thinking?
                    <textarea
                      required
                      maxLength="10000"
                      value={content}
                      onChange={(event) => setContent(event.target.value)}
                      placeholder="Share an idea, lesson, or question…"
                      disabled={postPending}
                    />
                  </label>
                  <button disabled={postPending} type="submit">
                    {postPending ? "Publishing…" : "Publish post"}
                  </button>
                </form>
              ) : user ? (
                <section className="login-panel">
                  <h2>Choose your public username</h2>
                  <p className="settings-copy">
                    You need a username before publishing or commenting.
                  </p>
                  <a className="text-button" href="#/settings">
                    Open Settings
                  </a>
                </section>
              ) : authMode === "signup" ? (
                <SignupPanel
                  onSignup={handleSignup}
                  onShowLogin={() => setAuthMode("login")}
                  pending={authPending}
                />
              ) : (
                <LoginPanel
                  onLogin={handleLogin}
                  onShowSignup={() => setAuthMode("signup")}
                  pending={authPending}
                />
              )}
              <section className="post-list" aria-live="polite">
                {loading ? (
                  <>
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                  </>
                ) : (
                  posts.map((post) => (
                    <PostCard
                      key={post.id}
                      post={post}
                      currentUser={user}
                      onToggleLike={handleToggleLike}
                      showError={showError}
                    />
                  ))
                )}
              </section>
              {!loading && !posts.length && (
                <p className="empty-state">
                  No posts yet. Be the first to publish one.
                </p>
              )}
              {nextCursor && (
                <button
                  className="load-more"
                  onClick={loadMore}
                  disabled={loadingMore}
                >
                  {loadingMore ? "Loading…" : "Load more posts"}
                </button>
              )}
            </>
          )}
        </div>
        {!selectedPostId && !settingsOpen && (
          <aside className="side-note">
            <p className="eyebrow">Orbit beta</p>
            <h2>Built for calm conversation.</h2>
            <p>
              Posts are tied to their owners, and slow server responses are
              handled without losing your work.
            </p>
            <section className="popular-posts">
              <div className="popular-heading">
                <h3>Top 10 popular</h3>
                <button
                  type="button"
                  onClick={() => loadPopular().catch(showError)}
                >
                  Refresh
                </button>
              </div>
              <p>Ranked by likes and comments.</p>
              {popularPosts.length ? (
                <ol>
                  {popularPosts.map((post) => (
                    <li key={post.id}>
                      <a href={`#/posts/${post.id}`}>{post.title}</a>
                      <span>
                        ♥ {post.likes_count} · {post.comments_count} comments
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p>No engagement yet.</p>
              )}
            </section>
          </aside>
        )}
      </section>
    </main>
  );
}

export default App;
