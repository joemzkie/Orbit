import { useEffect, useState } from 'react'
import { ApiError, api } from './api/client'
import './App.css'

function PostCard({ post, currentUser }) {
  const isOwner = post.owner === currentUser?.email
  return (
    <article className={`post-card${post.pending ? ' post-card--pending' : ''}`}>
      <header className="post-owner">
        <div className="avatar" aria-hidden="true">{post.owner?.[0]?.toUpperCase() || '?'}</div>
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
        <time dateTime={post.created_at}>{post.created_at ? new Date(post.created_at).toLocaleString() : 'Sending now'}</time>
        <span>Discussion and voting are coming soon</span>
      </footer>
    </article>
  )
}

function SkeletonCard() {
  return <div className="skeleton-card" aria-hidden="true"><span /><span /><span /><span /></div>
}

function LoginPanel({ onLogin, pending }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function submit(event) {
    event.preventDefault()
    onLogin(email, password)
  }

  return (
    <form className="login-panel" onSubmit={submit}>
      <p className="eyebrow">Account access</p>
      <h2>Sign in to publish</h2>
      <label>Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>Password<input required minLength="8" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <button disabled={pending} type="submit">{pending ? 'Signing in…' : 'Sign in'}</button>
    </form>
  )
}

function App() {
  const [posts, setPosts] = useState([])
  const [nextCursor, setNextCursor] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [user, setUser] = useState(null)
  const [authPending, setAuthPending] = useState(false)
  const [postPending, setPostPending] = useState(false)
  const [toast, setToast] = useState('')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  function showError(error) {
    const message = error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
    setToast(message)
  }

  async function loadFeed(cursor = null, signal) {
    const page = await api.getPosts(cursor, signal)
    setPosts((current) => cursor ? [...current, ...page.items] : page.items)
    setNextCursor(page.next_cursor)
  }

  useEffect(() => {
    const controller = new AbortController()
    loadFeed(null, controller.signal).catch(showError).finally(() => setLoading(false))
    api.getCurrentUser().then(setUser).catch((error) => {
      if (error.status !== 401) showError(error)
    })
    return () => controller.abort()
  }, [])

  async function handleLogin(email, password) {
    setAuthPending(true)
    try {
      setUser(await api.login(email, password))
      setToast('You are signed in.')
    } catch (error) {
      showError(error)
    } finally {
      setAuthPending(false)
    }
  }

  async function handleCreatePost(event) {
    event.preventDefault()
    if (!user || postPending) return
    const optimistic = {
      id: `pending-${crypto.randomUUID()}`,
      owner: user.email,
      title,
      content,
      created_at: new Date().toISOString(),
      pending: true,
    }
    setPostPending(true)
    setPosts((current) => [optimistic, ...current])
    setTitle('')
    setContent('')
    try {
      const created = await api.createPost({ title: optimistic.title, content: optimistic.content, published: true })
      setPosts((current) => current.map((post) => post.id === optimistic.id ? created : post))
    } catch (error) {
      setPosts((current) => current.filter((post) => post.id !== optimistic.id))
      showError(error)
    } finally {
      setPostPending(false)
    }
  }

  async function loadMore() {
    if (!nextCursor || loadingMore) return
    setLoadingMore(true)
    try {
      await loadFeed(nextCursor)
    } catch (error) {
      showError(error)
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="/">Orbit<span>•</span></a>
        <p>A thoughtful place to share ideas.</p>
        {user && <span className="signed-in">{user.email}</span>}
      </header>

      {toast && <div className="toast" role="status">{toast}<button onClick={() => setToast('')} aria-label="Dismiss message">×</button></div>}

      <section className="feed-layout" aria-label="Orbit post feed">
        <div className="feed-column">
          <section className="feed-heading"><p className="eyebrow">Community feed</p><h1>Fresh from Orbit</h1></section>
          {user ? (
            <form className="composer" onSubmit={handleCreatePost}>
              <label>Title<input required maxLength="255" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Give your post a clear title" disabled={postPending} /></label>
              <label>What are you thinking?<textarea required maxLength="10000" value={content} onChange={(event) => setContent(event.target.value)} placeholder="Share an idea, lesson, or question…" disabled={postPending} /></label>
              <button disabled={postPending} type="submit">{postPending ? 'Publishing…' : 'Publish post'}</button>
            </form>
          ) : <LoginPanel onLogin={handleLogin} pending={authPending} />}

          <section className="post-list" aria-live="polite">
            {loading ? <><SkeletonCard /><SkeletonCard /><SkeletonCard /></> : posts.map((post) => <PostCard key={post.id} post={post} currentUser={user} />)}
          </section>
          {!loading && !posts.length && <p className="empty-state">No posts yet. Be the first to publish one.</p>}
          {nextCursor && <button className="load-more" onClick={loadMore} disabled={loadingMore}>{loadingMore ? 'Loading…' : 'Load more posts'}</button>}
        </div>
        <aside className="side-note"><p className="eyebrow">Orbit beta</p><h2>Built for calm conversation.</h2><p>Posts are tied to their owners, and slow server responses are handled without losing your work.</p></aside>
      </section>
    </main>
  )
}

export default App
