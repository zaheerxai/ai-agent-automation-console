# Agent Automation Console

A starter project for an AI-driven automation tool that connects a React frontend to a Django proxy API for triggering external n8n workflows.

## Technology

- React 19 with Vite
- Tailwind CSS 4
- Django 5
- n8n webhook integration through environment configuration

## Project Structure

- `src/` contains the Vite React application and dark-mode chat interface.
- `backend/` contains the Django API service.
- `backend/agent_api/views.py` exposes `/api/trigger-agent/` and forwards messages to n8n.
- `backend/.env.example` documents the environment variables required by the Django service.

## Local Development

Install frontend dependencies:

```bash
npm install
```

Install backend dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `N8N_WEBHOOK_URL` in `backend/.env`, then start Django:

```bash
python manage.py runserver 8000
```

In a second terminal, start the frontend:

```bash
npm run dev
```

Vite proxies `/api/*` requests to `http://localhost:8000` during local development.
