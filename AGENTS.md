# AGENTS.md

This project is an AI automation console scaffold. It uses a Vite React frontend for the operator experience and a Django backend as a proxy between the browser and an external n8n webhook.

## Architecture

- `src/` contains the React frontend.
- `src/App.tsx` owns the chat-style workflow UI, local transcript state, request submission, loading state, and inline error display.
- `src/main.tsx` mounts the React application.
- `src/styles.css` defines Tailwind CSS imports and global dark-mode styling.
- `backend/` contains the Django service.
- `backend/agent_api/views.py` exposes `POST /api/trigger-agent/`.
- `backend/agent_backend/settings.py` loads backend environment variables from `backend/.env`.

## Request Flow

The frontend posts JSON to `/api/trigger-agent/` with this shape:

```json
{ "message": "Operator instruction" }
```

During local development, Vite proxies `/api/*` to the Django server at `http://localhost:8000`. Django validates the payload, forwards the message to `N8N_WEBHOOK_URL`, and returns the n8n response. If the webhook target is missing, unavailable, or returns a request error, the backend responds with `System busy`.

## Environment

Use `backend/.env` for backend runtime configuration. Do not commit real secret values.

Required:

```bash
N8N_WEBHOOK_URL=...
```

Optional:

```bash
N8N_TIMEOUT_SECONDS=15
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

## Conventions

- Keep frontend components in TypeScript and use React hooks for local UI state.
- Use Tailwind utility classes for styling.
- Keep the backend proxy thin; workflow logic belongs in n8n.
- Return generic availability errors from the backend so webhook infrastructure details are not exposed to users.
- Never print, log, or commit webhook URLs, API keys, tokens, or other secret values.

## Non-Obvious Decisions

- The Django endpoint is CSRF-exempt because it is designed as a JSON API consumed by the Vite app rather than a browser-rendered Django form.
- SQLite remains configured only as Django's default local database; this starter does not persist application data.
- Vite is kept as the frontend development server and delegates API traffic to Django through the dev proxy.
