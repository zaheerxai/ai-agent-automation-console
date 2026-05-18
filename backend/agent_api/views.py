import json
import os
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


# --- Turso HTTP API helper (replaces libsql_client entirely) ---

def turso_execute(statements: list[dict]) -> list | None:
    """
    statements = [
        {"sql": "SELECT ...", "args": ["val1"]},
        {"sql": "INSERT ...", "args": ["val1", "val2"]},
    ]
    Returns list of result objects or None on failure.
    """
    url = os.environ.get("TURSO_DATABASE_URL", "").rstrip("/")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")

    if not url or not token:
        print("Turso: missing env vars")
        return None

    pipeline_url = f"{url}/v2/pipeline"
    requests_payload = []
    for stmt in statements:
        requests_payload.append({
            "type": "execute",
            "stmt": {
                "sql": stmt["sql"],
                "named_args": [],
                "args": [{"type": "text", "value": str(v)} for v in stmt.get("args", [])],
            }
        })
    requests_payload.append({"type": "close"})

    try:
        resp = requests.post(
            pipeline_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"requests": requests_payload},
            timeout=8,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        print(f"Turso HTTP Error: {e}")
        return None


def ensure_table():
    turso_execute([{
        "sql": """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER DEFAULT (unixepoch())
            )
        """,
        "args": []
    }])

# Add these functions after ensure_table()

def ensure_profile_table():
    turso_execute([{
        "sql": """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                preferences TEXT DEFAULT '{}',   -- JSON string for flexibility
                bio TEXT,
                timezone TEXT,
                favorite_tools TEXT DEFAULT '[]',
                created_at INTEGER DEFAULT (unixepoch()),
                updated_at INTEGER DEFAULT (unixepoch())
            )
        """,
        "args": []
    }])


def get_user_profile(user_id: str) -> dict:
    ensure_profile_table()
    results = turso_execute([{
        "sql": """
            SELECT name, preferences, bio, timezone, favorite_tools 
            FROM user_profiles 
            WHERE user_id = ?
        """,
        "args": [user_id]
    }])
    
    if results and results[0]["response"]["result"]["rows"]:
        row = results[0]["response"]["result"]["rows"][0]
        try:
            prefs = json.loads(row[1]["value"]) if row[1] and row[1]["value"] else {}
        except:
            prefs = {}
            
        return {
            "name": row[0]["value"] if row[0] else None,
            "preferences": prefs,
            "bio": row[2]["value"] if row[2] else None,
            "timezone": row[3]["value"] if row[3] else None,
            "favorite_tools": json.loads(row[4]["value"]) if row[4] and row[4]["value"] else []
        }
    return {"name": None, "preferences": {}, "bio": None, "timezone": None, "favorite_tools": []}


def save_user_profile(user_id: str, name: str = None, preferences: dict = None, 
                     bio: str = None, timezone: str = None, favorite_tools: list = None):
    ensure_profile_table()
    now = int(__import__('time').time())
    
    pref_json = json.dumps(preferences) if preferences is not None else None
    tools_json = json.dumps(favorite_tools) if favorite_tools is not None else None

    sql = """
        INSERT INTO user_profiles (user_id, name, preferences, bio, timezone, favorite_tools, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            name = COALESCE(excluded.name, user_profiles.name),
            preferences = COALESCE(excluded.preferences, user_profiles.preferences),
            bio = COALESCE(excluded.bio, user_profiles.bio),
            timezone = COALESCE(excluded.timezone, user_profiles.timezone),
            favorite_tools = COALESCE(excluded.favorite_tools, user_profiles.favorite_tools),
            updated_at = ?
    """
    
    args = [user_id, name, pref_json, bio, timezone, tools_json, now, now]
    
    turso_execute([{"sql": sql, "args": args}])

def fetch_history(session_id: str) -> str:
    # Fetch user profile
    profile = get_user_profile(session_id)
    profile_info = ""
    if profile.get("name"):
        profile_info = f"User Profile:\n- Name: {profile['name']}\n"
        # You can extend this later with more fields (preferences, etc.)
    
    # Fetch chat history
    results = turso_execute([{
        "sql": (
            "SELECT role, content FROM chat_history "
            "WHERE session_id = ? "
            "ORDER BY created_at ASC"
        ),
        "args": [session_id]
    }])

    if not results:
        return profile_info  # Return at least the profile

    try:
        rows = results[0]["response"]["result"]["rows"]
        history = profile_info  # ← Profile always at the top
        
        # last N rows (you can increase this)
        for row in rows[-10:]:   # Increased from 6 → 10 (recommended)
            role_val = row[0]["value"]
            content_val = row[1]["value"]
            speaker = "Operator" if role_val == "user" else "Mojo"
            history += f"{speaker}: {content_val}\n"
        
        return history.strip()
    except (KeyError, IndexError, TypeError) as e:
        print(f"Turso parse history error: {e}")
        return profile_info


def save_turns(session_id: str, user_message: str, agent_text: str):
    results = turso_execute([
        {
            "sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
            "args": [session_id, "user", user_message]
        },
        {
            "sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
            "args": [session_id, "agent", agent_text]
        },
    ])
    if results is None:
        print("Turso: save_turns returned None")
    else:
        print(f"Turso: saved 2 turns for session {session_id}")


# --- Django views ---

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
def get_chat_history(request):
    """Fetch chat history for a given session ID"""
    if request.method != 'GET':
        return JsonResponse({"message": "Method not allowed"}, status=405)

    session_id = request.headers.get('X-Session-ID', 'anonymous_session')
    
    if not session_id:
        return JsonResponse({"message": "Session ID is required"}, status=400)

    results = turso_execute([{
        "sql": (
            "SELECT role, content FROM chat_history "
            "WHERE session_id = ? "
            "ORDER BY created_at ASC"
        ),
        "args": [session_id]
    }])

    if not results:
        return JsonResponse({"history": []}, status=200)

    try:
        rows = results[0]["response"]["result"]["rows"]
        history = []
        for row in rows:
            role_val = row[0]["value"]
            content_val = row[1]["value"]
            history.append({
                "role": role_val,
                "content": content_val
            })
        return JsonResponse({"history": history}, status=200)
    except (KeyError, IndexError, TypeError) as e:
        print(f"Turso parse history error: {e}")
        return JsonResponse({"history": []}, status=200)


@csrf_exempt
@require_POST
def trigger_agent(request):
    # 1. Parse
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON payload"}, status=400)

    user_message = str(body.get("message", "")).strip()
    session_id = body.get("sessionId", "anonymous_session")

    if not user_message:
        return JsonResponse({"message": "Message is required"}, status=400)

    if not profile["name"] and ("my name is" in user_message.lower() or "i am" in user_message.lower()):
        # You could use LLM to extract name, or simple string parsing
        # For now, let the agent handle it and save later
        pass

    n8n_url = os.environ.get("N8N_WEBHOOK_URL")
    if not n8n_url:
        return JsonResponse({"message": "System configuration error"}, status=503)

    # 2. Ensure table + fetch history (parallel-ish, sequential is fine here)
    ensure_table()
    chat_history_str = fetch_history(session_id)

# === NEW: Fetch user profile ===
    profile = get_user_profile(session_id)
    profile_info = ""
    if profile["name"]:
        profile_info = f"User's name is {profile['name']}. "

    # Send richer context to n8n
    n8n_payload = {
        "User message": user_message,
        "sessionId": session_id,
        "chat_history": chat_history_str,
        "user_profile": profile_info,          # ← New field
        "full_profile": profile                # Optional: send more data
    }

    # 3. Forward to n8n
    try:
        n8n_response = requests.post(
            n8n_url,
            json={
                "User message": user_message,
                "sessionId": session_id,
                "chat_history": chat_history_str,
            },
            timeout=10,
        )
    except requests.RequestException:
        return JsonResponse({"message": "Agent timeout"}, status=503)

    # 4. Parse n8n response
    text = n8n_response.text.strip()
    try:
        response_data = n8n_response.json()
        agent_text = response_data.get("output", text)
    except ValueError:
        response_data = {"message": text}
        agent_text = text

    # 5. Persist both turns
    save_turns(session_id, user_message, agent_text)

    return JsonResponse({"status": "ok", "response": response_data})
