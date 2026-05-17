import json
import os
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from libsql_client import create_client_sync

def get_db():
    return create_client_sync(
        url=os.environ.get("TURSO_DATABASE_URL"),
        auth_token=os.environ.get("TURSO_AUTH_TOKEN")
    )

def ensure_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER DEFAULT (unixepoch())
        )
    """)

@csrf_exempt
@require_POST
def clerk_webhook(request):
    try:
        payload = json.loads(request.body)
        event_type = payload.get("type")
        print(f"Clerk Webhook Received: {event_type}")
        return HttpResponse("Webhook processed", status=200)
    except Exception as e:
        print(f"Clerk Webhook Error: {e}")
        return HttpResponse("Internal Server Error", status=500)

@csrf_exempt
@require_POST
def trigger_agent(request):
    # 1. Parse request
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON payload"}, status=400)

    user_message = str(body.get("message", "")).strip()
    session_id = body.get("sessionId", "anonymous_session")

    if not user_message:
        return JsonResponse({"message": "Message is required"}, status=400)

    n8n_url = os.environ.get('N8N_WEBHOOK_URL')
    if not n8n_url:
        return JsonResponse({"message": "System configuration error"}, status=503)

    # 2. Connect + ensure table exists
    db = None
    try:
        db = get_db()
        ensure_table(db)
    except Exception as e:
        print(f"Turso Connection Error: {e}")

    # 3. Fetch chat history
    chat_history_str = ""
    if db:
        try:
            result = db.execute(
                "SELECT role, content FROM chat_history "
                "WHERE session_id = ? ORDER BY created_at ASC",
                [session_id]
            )
            # Take last 6 turns for context window
            rows = list(result.rows)[-6:]
            for row in rows:
                speaker = "Operator" if row[0] == "user" else "Mojo"
                chat_history_str += f"{speaker}: {row[1]}\n"
        except Exception as e:
            print(f"Turso Fetch Error: {e}")

    # 4. Forward to n8n
    try:
        n8n_payload = {
            "User message": user_message,
            "sessionId": session_id,
            "chat_history": chat_history_str
        }
        n8n_response = requests.post(n8n_url, json=n8n_payload, timeout=10)
    except requests.RequestException:
        if db:
            db.close()
        return JsonResponse({"message": "Agent timeout"}, status=503)

    # 5. Parse n8n response
    text = n8n_response.text.strip()
    try:
        response_data = n8n_response.json()
        agent_text = response_data.get("output", text)
    except ValueError:
        response_data = {"message": text}
        agent_text = text

    # 6. Save BOTH turns — FIX: two separate execute() calls, not execute_batch()
    if db:
        try:
            db.execute(
                "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
                [session_id, "user", user_message]
            )
            db.execute(
                "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
                [session_id, "agent", agent_text]
            )
        except Exception as e:
            print(f"Turso Insert Error: {e}")
        finally:
            db.close()

    return JsonResponse({"status": "ok", "response": response_data})