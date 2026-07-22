# Orbit

> **Status: Work in progress.**
>
> Orbit is a learning project with a React feed and an actively developed FastAPI API for posts and user accounts.

## What this project does

The current backend provides a PostgreSQL-backed API that can:

- Create, read, update, delete, and list posts.
- Create user accounts with an email address as the primary key.
- Hash user passwords with Argon2 before saving them.
- Record when each user account was created.
- Authenticate users with short-lived HttpOnly JWT cookies.
- Attach every post to its authenticated owner.
- Protect mutations with idempotency keys and Redis-backed rate limiting.

Comments and one-like-per-user voting are available for posts and comments. Threaded replies and file uploads are still in progress.

## Technology

- Python 3
- FastAPI for HTTP APIs
- PostgreSQL for persistent data
- SQLAlchemy for Python-to-database mapping
- Pydantic for request validation and response models
- Alembic for versioned database migrations
- pwdlib with Argon2 for password hashing
- Redis for distributed token-bucket rate limiting
- React and Vite for the frontend feed

## Project structure

```text
Orbit/
├── backend/
│   ├── main.py                 # Starts FastAPI and registers API routers.
│   ├── dbconn.py               # Loads database settings and creates SQLAlchemy sessions.
│   ├── security.py             # Creates secure Argon2 password hashes.
│   ├── models/                 # SQLAlchemy definitions of database tables.
│   ├── schemas/                # Pydantic models for API request and response data.
│   ├── routers/                # HTTP endpoints such as /posts and /users.
│   ├── services/               # Database operations called by the routers.
│   ├── alembic/                # Database migration scripts.
│   ├── alembic.ini             # Alembic command-line configuration.
│   └── requirements.txt        # Python dependencies.
└── README.md
```

## How a request moves through the backend

```text
Frontend request
    -> FastAPI application (main.py)
    -> Router (routers/)
    -> Service (services/)
    -> SQLAlchemy model and PostgreSQL database
    -> JSON response to the frontend
```

For example, a frontend sends `POST /users`; the users router validates the request, the user service hashes the password and saves the record, then FastAPI returns a safe response without the password.

## Setup

### 1. Create and activate a virtual environment

From the repository root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r backend\requirements.txt
```

### 3. Configure PostgreSQL

Create `backend/.env` with your local PostgreSQL settings:

```env
DB_NAME="Localorbit"
DB_USER="postgres"
DB_PASSWORD="your-password"
DB_HOST="localhost"
DB_PORT="5432"
JWT_SECRET="replace-with-a-long-random-secret"
REDIS_URL="redis://localhost:6379/0"
CORS_ORIGINS="http://localhost:5173"
COOKIE_SECURE="false"
```

Do not commit `.env`, because it contains credentials.

`JWT_SECRET` must be a long, random value. Set `COOKIE_SECURE="true"` when the application is served over HTTPS in production.

### 4. Start Redis

The mutation endpoints fail closed with `503` when Redis is unavailable. For local development with Docker:

```powershell
docker run --name orbit-redis -p 6379:6379 redis:7-alpine
```

### 5. Apply database migrations

Run this command from the `backend` directory:

```powershell
cd backend
..\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

Alembic applies each migration once and remembers the current version in PostgreSQL's `alembic_version` table.

### 6. Start the API server

From the `backend` directory:

```powershell
..\venv\Scripts\python.exe -m uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

- Interactive API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI JSON description: `http://127.0.0.1:8000/openapi.json`

### 7. Start the frontend

In a second PowerShell terminal:

```powershell
cd frontend\Orbit
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to FastAPI during development.

## Database tables

### `users`

| Column | Type | Rules | Purpose |
| --- | --- | --- | --- |
| `email` | text | Primary key, required | Uniquely identifies a user. |
| `password` | text | Required | Stores an Argon2 hash, never a plaintext password. |
| `created_at` | timestamp with timezone | Required, defaults to current time | Records account creation time. |

### `posts`

| Column | Purpose |
| --- | --- |
| `id` | Integer primary key. |
| `title` | Post title. |
| `content` | Full post text. |
| `published` | Whether the post is published; defaults to `true`. |
| `owner` | Required foreign key to `users.email`; identifies the post owner. |
| `created_at` | Timestamp set by PostgreSQL when the post is created. |
| `likes_count` | Trigger-maintained cached total of durable `post_likes` records. |

### `comments`, `post_likes`, and `comment_likes`

`comments` belongs to a post (`ON DELETE CASCADE`) and stores its author email, body, creation timestamp, and a trigger-maintained `likes_count`. Its `(post_id, created_at, id)` index supports chronological comment rendering, and `owner` is indexed for author lookups.

The two like tables are immutable-style ledgers with composite primary keys: `(user_email, post_id)` and `(user_email, comment_id)`. Those keys make a duplicate like physically impossible, even when requests race. PostgreSQL triggers update the cached counters in the same transaction, avoiding expensive `COUNT()` queries on the feed path.

## API endpoints

### Posts

| Method | URL | Purpose |
| --- | --- | --- |
| `GET` | `/posts?limit=20&cursor=...` | Return one cursor-paginated feed page. |
| `POST` | `/posts` | Create a post for the authenticated user. |
| `GET` | `/posts/latest` | Return up to ten newest posts. |
| `GET` | `/posts/{post_id}` | Return one post. |
| `PUT` | `/posts/{post_id}` | Replace the authenticated owner's post fields. |
| `DELETE` | `/posts/{post_id}` | Delete a post. |
| `GET` | `/posts/{post_id}/comments` | Return chronological comments for a post. |
| `POST` | `/posts/{post_id}/comments` | Add an authenticated user's comment. |
| `POST` | `/posts/{post_id}/like` | Like a post once for the signed-in user. |
| `DELETE` | `/posts/{post_id}/like` | Remove the signed-in user's post like. |
| `POST` | `/comments/{comment_id}/like` | Like a comment once for the signed-in user. |
| `DELETE` | `/comments/{comment_id}/like` | Remove the signed-in user's comment like. |

### Users

| Method | URL | Purpose |
| --- | --- | --- |
| `POST` | `/users` | Register a user. |

### Authentication

| Method | URL | Purpose |
| --- | --- | --- |
| `POST` | `/auth/login` | Verify credentials and set an HttpOnly session cookie. |
| `POST` | `/auth/signup` | Create a user with a validated email and an Argon2 password hash. |
| `POST` | `/auth/logout` | Clear the session cookie. |
| `GET` | `/auth/me` | Return the authenticated user's safe profile. |

Example user registration request:

```json
{
  "email": "person@example.com",
  "password": "at-least-eight-characters"
}
```

Successful response:

```json
{
  "email": "person@example.com",
  "created_at": "2026-07-22T12:00:00+00:00"
}
```

Registration returns `409 Conflict` if an account already uses the email address. Passwords require at least 12 characters, uppercase and lowercase letters, and a number.

## Password security

The backend hashes passwords through `security.py` before they reach the database. A hash cannot be converted back into the original password.

Login finds a user by email, verifies the submitted password through `password_hasher.verify()`, and returns the same generic `401 Unauthorized` response for an unknown email or an incorrect password.

Do not compare plaintext passwords or return a password/hash in an API response.

## Database migrations

Alembic tracks intentional database changes as Python files in `backend/alembic/versions/`.

- `20260722_01_create_users_table.py` created the `users` table with `email` as its primary key.
- `20260722_02_add_users_created_at.py` added the non-null `created_at` timestamp while preserving existing users.
- `20260722_03_add_post_ownership_and_idempotency.py` backfilled existing posts to `user@example.com`, added the owner foreign key/index, and created durable idempotency records.
- `20260722_04_add_comments_and_likes.py` adds comments, durable post/comment like ledgers, and transactionally maintained like counters.

To create future migrations, first update the SQLAlchemy model, then create and review a migration before applying it. Never manually change a production table without recording the equivalent migration.

## Current limitations and next steps

- Threaded replies, file uploads, and display names are not implemented.
- Redis is required before registration, login, posting, updating, or deleting can succeed.
- Every `POST`, `PUT`, and `DELETE` must include a unique `Idempotency-Key` header; the React API client creates this automatically.
- The backend sets a 9-second PostgreSQL statement timeout and a 10-second route timeout, returning structured `503`/`504` errors instead of hanging.

## Git workflow

The default GitHub branch is `main`. Use this basic workflow for future work:

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

Keep secrets such as `backend/.env` out of Git commits.

## Production deployment

The frontend is a Vite app in `frontend/Orbit`; deploy it to Vercel and set `VITE_API_URL` to the Render API URL including `/api`, without a trailing slash. The backend deploys from `backend` using the included `render.yaml` and binds to Render's `$PORT`.

Copy `backend/.env.example` for local production-like testing and configure the same values in Render. `DATABASE_URL` must be the PostgreSQL connection URI from **Supabase Dashboard -> Connect**, not the Supabase REST URL. Set `DB_SSL_MODE=require`, `COOKIE_SECURE=true`, and `COOKIE_SAMESITE=none` for Vercel-to-Render sessions.

Required Render variables: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `REDIS_URL`, `SUPABASE_URL`, and `SUPABASE_KEY`. Keep `SUPABASE_KEY` in Render only. Required Vercel variable: `VITE_API_URL`; optional public Supabase values are listed in `frontend/Orbit/.env.example`.
