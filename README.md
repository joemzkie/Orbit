# Orbit

> **Status: Work in progress.**
>
> Orbit is a learning project and an actively developed FastAPI backend for posts and user accounts.

## What this project does

The current backend provides a PostgreSQL-backed API that can:

- Create, read, update, delete, and list posts.
- Create user accounts with an email address as the primary key.
- Hash user passwords with Argon2 before saving them.
- Record when each user account was created.

The frontend and user login/token authentication are still in progress.

## Technology

- Python 3
- FastAPI for HTTP APIs
- PostgreSQL for persistent data
- SQLAlchemy for Python-to-database mapping
- Pydantic for request validation and response models
- Alembic for versioned database migrations
- pwdlib with Argon2 for password hashing

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
```

Do not commit `.env`, because it contains credentials.

### 4. Apply database migrations

Run this command from the `backend` directory:

```powershell
cd backend
..\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

Alembic applies each migration once and remembers the current version in PostgreSQL's `alembic_version` table.

### 5. Start the API server

From the `backend` directory:

```powershell
..\venv\Scripts\python.exe -m uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

- Interactive API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI JSON description: `http://127.0.0.1:8000/openapi.json`

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

## API endpoints

### Posts

| Method | URL | Purpose |
| --- | --- | --- |
| `GET` | `/posts` | Return all posts. |
| `POST` | `/posts` | Create a post. |
| `GET` | `/posts/latest` | Return up to ten newest posts. |
| `GET` | `/posts/{post_id}` | Return one post. |
| `PUT` | `/put/{post_id}` | Replace a post's fields. |
| `DELETE` | `/posts/{post_id}` | Delete a post. |

### Users

| Method | URL | Purpose |
| --- | --- | --- |
| `POST` | `/users` | Register a user. |

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

Registration returns `409 Conflict` if an account already uses the email address. Passwords must contain at least eight characters.

## Password security

The backend hashes passwords through `security.py` before they reach the database. A hash cannot be converted back into the original password.

When login is added, it must:

1. Find the user by email.
2. Verify the submitted password against the stored hash using `password_hasher.verify()`.
3. Return the same generic `401 Unauthorized` response for an unknown email or an incorrect password.

Do not compare plaintext passwords or return a password/hash in an API response.

## Database migrations

Alembic tracks intentional database changes as Python files in `backend/alembic/versions/`.

- `20260722_01_create_users_table.py` created the `users` table with `email` as its primary key.
- `20260722_02_add_users_created_at.py` added the non-null `created_at` timestamp while preserving existing users.

To create future migrations, first update the SQLAlchemy model, then create and review a migration before applying it. Never manually change a production table without recording the equivalent migration.

## Current limitations and next steps

- No frontend has been added yet.
- Login, JWT tokens, and protected routes have not been implemented.
- CORS must be configured before a frontend running on another port can call this API from a browser.
- Automated tests should be added as the API grows.

## Git workflow

The default GitHub branch is `main`. Use this basic workflow for future work:

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

Keep secrets such as `backend/.env` out of Git commits.
