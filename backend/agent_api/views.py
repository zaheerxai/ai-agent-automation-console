import json
import os
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Import the synchronous Turso client
from libsql_client import create_client_sync

@csrf_exempt
@require_POST
def clerk_webhook(request):
    """
    Handles incoming webhooks from Clerk (e.g., user.created, session.created).
    """
    try:
        payload = json.loads(request.body)
        event_type = payload.get("type")
        data = payload.get("data")

        # Log the event for debugging in Vercel logs
        print(f"Clerk Webhook Received: {event_type}")

        # Add your logic here (e.g., sync user to your Turso DB)
        # if event_type == "user.created":
        #     ...

        return HttpResponse("Webhook processed", status=200)
    except Exception as e:
        print(f"Clerk Webhook Error: {e}")
        return HttpResponse("Internal Server Error", status=500)

@csrf_exempt
@require_POST
def trigger_agent(request):
    # 1. Parse incoming request
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

    # 2. Connect to Turso to fetch Chat History
    db = None
    try:
        # Use a timeout so one slow DB call doesn't kill your Vercel function
        db = create_client_sync(
            url=os.environ.get("TURSO_DATABASE_URL"),
            auth_token=os.environ.get("TURSO_AUTH_TOKEN")
        )
    except Exception as e:
        print(f"Turso Connection Error: {e}")

    chat_history_str = ""
    if db:
        try:
            result = db.execute(
                "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY created_at DESC LIMIT 6",
                [session_id]
            )
            history_rows = result.rows[::-1] 
            for row in history_rows:
                speaker = "Operator" if row[0] == "user" else "Mojo"
                chat_history_str += f"{speaker}: {row[1]}\n"
        except Exception as e:
            print(f"Turso Fetch Error: {e}")

    # 3. Forward to n8n
    try:
        n8n_payload = {
            "User message": user_message,
            "sessionId": session_id,
            "chat_history": chat_history_str 
        }
        n8n_response = requests.post(n8n_url, json=n8n_payload, timeout=10)
    except requests.RequestException:
        if db: db.close() # Clean up if we fail here
        return JsonResponse({"message": "Agent timeout"}, status=503)

    # 4. Parse n8n response
    text = n8n_response.text.strip()
    try:
        response_data = n8n_response.json()
        agent_text = response_data.get("output", text) 
    except ValueError:
        response_data = {"message": text}
        agent_text = text

    # 5. Save to Turso and Close
    if db:
        try:
            db.execute_batch([
                {"sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, 'user', ?)", "args": [session_id, user_message]},
                {"sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, 'agent', ?)", "args": [session_id, agent_text]}
            ])
        except Exception as e:
            print(f"Turso Insert Error: {e}")
        finally:
            db.close()

    return JsonResponse({"status": "ok", "response": response_data})