import json
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Import the synchronous Turso client
from libsql_client import create_client_sync

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
    try:
        db = create_client_sync(
            url=os.environ.get("TURSO_DATABASE_URL"),
            auth_token=os.environ.get("TURSO_AUTH_TOKEN")
        )
    except Exception as e:
        print(f"Turso Connection Error: {e}")
        db = None

    chat_history_str = ""
    if db:
        try:
            # Fetch the last 6 messages (3 interactions back-and-forth)
            result = db.execute(
                "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY created_at DESC LIMIT 6",
                [session_id]
            )
            # Reverse the results so the oldest is at the top, newest at the bottom
            history_rows = result.rows[::-1] 
            for row in history_rows:
                # Format the history so the AI understands who said what
                speaker = "Operator" if row[0] == "user" else "Mojo"
                chat_history_str += f"{speaker}: {row[1]}\n"
        except Exception as e:
            print(f"Turso Fetch Error: {e}")

    # 3. Forward the payload AND the History to n8n
    try:
        n8n_payload = {
            "User message": user_message,
            "sessionId": session_id,
            "chat_history": chat_history_str # Sending memory as a string!
        }
        n8n_response = requests.post(n8n_url, json=n8n_payload, timeout=9)
    except requests.RequestException:
        return JsonResponse({"message": "Agent timeout or connection error"}, status=503)

    # 4. Parse the n8n response safely
    text = n8n_response.text.strip()
    try:
        response_data = n8n_response.json()
        # n8n's Groq node usually outputs the final text in the "output" key
        agent_text = response_data.get("output", text) 
    except ValueError:
        response_data = {"message": text}
        agent_text = text

    # 5. Save BOTH messages to Turso
    if db:
        try:
            # We use execute_batch to save both rows in one fast transaction
            db.execute_batch([
                {"sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, 'user', ?)", "args": [session_id, user_message]},
                {"sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, 'agent', ?)", "args": [session_id, agent_text]}
            ])
        except Exception as e:
            print(f"Turso Insert Error: {e}")
        finally:
            db.close() # Always close the connection!

    return JsonResponse({"status": "ok", "response": response_data})