import json
import re
import os
import requests
import time
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


# ==================== PROFILE EXTRACTION ====================

def extract_profile_with_llm(user_message: str, current_profile: dict) -> dict:
    """Use Groq LLM to intelligently extract profile updates"""
    prompt = f"""
You are an expert JSON extractor specialized in user profile information.

Current user profile (may be empty):
{json.dumps(current_profile, indent=2)}

User's latest message: "{user_message}"

Your task:
- Carefully extract any information the user shared about themselves.
- Pay special attention to the user's **name** (especially if they say "my name is", "I am", "call me").
- If the user clearly mentions their name, you **must** include it.

Return **only valid JSON**. No explanations, no markdown.

Possible fields:
- name
- bio
- timezone  
- preferences (object)
- favorite_tools (array of strings)

Examples of good output:

{{
  "name": "Ali"
}}

{{
  "name": "Ali",
  "preferences": {{
    "tone": "friendly",
    "response_length": "concise"
  }}
}}

{{
  "bio": "Building AI automation tools from Pakistan"
}}
"""

    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise JSON extractor. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=400
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean markdown
        if "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            if content.startswith("json"):
                content = content[4:].strip()
                
        updates = json.loads(content)
        return updates if isinstance(updates, dict) else {}
        
    except Exception as e:
        print(f"LLM Profile Extraction Error: {e}")
        return {}


def extract_profile_updates(user_message: str, current_profile: dict) -> dict:
    """Improved rule-based extraction"""
    updates = {}
    msg_lower = user_message.lower().strip()

    # Stronger Name Detection
    name_patterns = [
        r"my name is (\w+)",
        r"i am (\w+)",
        r"call me (\w+)",
        r"name is (\w+)",
        r"this is (\w+)",          # new
        r"hi.?i.?m (\w+)",         # new
        r"hello.?i.?m (\w+)"       # new
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            name = match.group(1).strip().capitalize()
            if len(name) >= 3:
                updates["name"] = name
                break

    # Force name if user says "Zaheer" clearly
    if "zaheer" in msg_lower and not updates.get("name"):
        updates["name"] = "Zaheer"

    # Preferences
    if any(word in msg_lower for word in ["prefer", "like", "love", "want", "remember", "usually"]):
        updates["preferences"] = current_profile.get("preferences", {}).copy()

    return updates


# ==================== TURSO HELPERS ====================

def turso_execute(statements: list[dict]) -> list | None:
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
                "args": [{"type": "text", "value": str(v)} for v in stmt.get("args", [])]
            }
        })
    requests_payload.append({"type": "close"})

    try:
        resp = requests.post(
            pipeline_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"requests": requests_payload},
            timeout=10,
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


def ensure_profile_table():
    turso_execute([{
        "sql": """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                preferences TEXT DEFAULT '{}',
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
    
    if not results or not results[0]["response"]["result"]["rows"]:
        return {"name": None, "preferences": {}, "bio": None, "timezone": None, "favorite_tools": []}

    try:
        row = results[0]["response"]["result"]["rows"][0]
        
        # Safe JSON parsing with fallbacks
        def safe_json_loads(val, default):
            if not val or val == "None" or val == "null":
                return default
            try:
                return json.loads(val)
            except:
                return default

        return {
            "name": row[0]["value"] if row[0] and row[0]["value"] != "None" else None,
            "preferences": safe_json_loads(row[1]["value"] if row[1] else None, {}),
            "bio": row[2]["value"] if row[2] and row[2]["value"] != "None" else None,
            "timezone": row[3]["value"] if row[3] and row[3]["value"] != "None" else None,
            "favorite_tools": safe_json_loads(row[4]["value"] if row[4] else None, [])
        }
    except Exception as e:
        print(f"❌ Error parsing user profile: {e}")
        return {"name": None, "preferences": {}, "bio": None, "timezone": None, "favorite_tools": []}


def save_user_profile(user_id: str, name=None, preferences=None, 
                     bio=None, timezone=None, favorite_tools=None):
    ensure_profile_table()
    now = int(time.time())
    
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
    args = [user_id, name, pref_json, bio, timezone, tools_json, now]
    
    turso_execute([{"sql": sql, "args": args}])


def fetch_history(session_id: str) -> str:
    profile = get_user_profile(session_id)
    
    profile_info = "=== USER PROFILE ===\n"
    if profile.get("name"): profile_info += f"Name: {profile['name']}\n"
    if profile.get("bio"): profile_info += f"Bio: {profile['bio']}\n"
    if profile.get("timezone"): profile_info += f"Timezone: {profile['timezone']}\n"
    if profile.get("favorite_tools"): 
        profile_info += f"Favorite Tools: {', '.join(profile['favorite_tools'])}\n"
    if profile.get("preferences"):
        profile_info += "Preferences:\n"
        for k, v in profile["preferences"].items():
            profile_info += f"  • {k}: {v}\n"

    # Chat History
    results = turso_execute([{
        "sql": "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY created_at ASC",
        "args": [session_id]
    }])

    if not results or not results[0]["response"]["result"]["rows"]:
        return profile_info.strip()

    history = profile_info + "\n=== CONVERSATION HISTORY ===\n"
    rows = results[0]["response"]["result"]["rows"]
    
    for row in rows[-12:]:
        role = "User" if row[0]["value"] == "user" else "Mojo"
        history += f"{role}: {row[1]['value']}\n"

    return history.strip()


# ==================== VIEWS ====================

@csrf_exempt
@require_POST
def update_profile(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        user_id = body.get("user_id") or body.get("sessionId")
        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)

        save_user_profile(
            user_id=user_id,
            name=body.get("name"),
            bio=body.get("bio"),
            timezone=body.get("timezone"),
            preferences=body.get("preferences"),
            favorite_tools=body.get("favorite_tools")
        )

        return JsonResponse({
            "success": True,
            "message": "Profile updated",
            "profile": get_user_profile(user_id)
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def save_turns(session_id: str, user_message: str, agent_text: str):
    turso_execute([
        {"sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", "args": [session_id, "user", user_message]},
        {"sql": "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", "args": [session_id, "agent", agent_text]},
    ])


@csrf_exempt
@require_POST
def trigger_agent(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    user_message = str(body.get("message", "")).strip()
    session_id = body.get("sessionId") or body.get("user_id") or "anonymous"

    if not user_message:
        return JsonResponse({"message": "Message required"}, status=400)

    try:
        n8n_url = os.environ.get("N8N_WEBHOOK_URL")
        if not n8n_url:
            return JsonResponse({"message": "Config error"}, status=503)

        ensure_table()

        # Auto Profile Update
        current_profile = get_user_profile(session_id)
        updates = extract_profile_updates(user_message, current_profile)
        
        if not updates:
            updates = extract_profile_with_llm(user_message, current_profile)

        if updates:
            save_user_profile(
                user_id=session_id,
                name=updates.get("name"),
                bio=updates.get("bio"),
                timezone=updates.get("timezone"),
                preferences=updates.get("preferences"),
                favorite_tools=updates.get("favorite_tools")
            )
            print(f"✅ Profile updated for {session_id}: {updates}")

        chat_history_str = fetch_history(session_id)

        n8n_payload = {
            "User message": user_message,
            "sessionId": session_id,
            "chat_history": chat_history_str,
        }

        n8n_response = requests.post(n8n_url, json=n8n_payload, timeout=60)
        n8n_response.raise_for_status()
        
        try:
            response_data = n8n_response.json()
        except ValueError:
            response_data = {"output": n8n_response.text}

        agent_text = response_data.get("output", n8n_response.text)

        save_turns(session_id, user_message, agent_text)

        return JsonResponse({"status": "ok", "response": response_data})

    except Exception as e:
        print(f"❌ Trigger agent error: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": "Something went wrong. Please try again."
        }, status=500)


# Clerk Webhook + get_chat_history (unchanged)
@csrf_exempt
@require_POST
def clerk_webhook(request):
    # ... your existing code
    pass


@csrf_exempt
def get_chat_history(request):
    """Fetch chat history for a given session ID"""
    if request.method != 'GET':
        return JsonResponse({"message": "Method not allowed"}, status=405)

    session_id = request.headers.get('X-Session-ID')

    if not session_id:
        return JsonResponse({"history": []}, status=200)

    ensure_table()   # ← Use this instead of ensure_chat_table()

    results = turso_execute([{
        "sql": """
            SELECT role, content 
            FROM chat_history 
            WHERE session_id = ? 
            ORDER BY created_at ASC
        """,
        "args": [session_id]
    }])

    if not results or not results[0]["response"]["result"]["rows"]:
        return JsonResponse({"history": []}, status=200)

    try:
        rows = results[0]["response"]["result"]["rows"]
        history = []
        for row in rows:
            history.append({
                "role": row[0]["value"],
                "content": row[1]["value"]
            })
        return JsonResponse({"history": history}, status=200)
    except Exception as e:
        print(f"[v0] Get chat history error: {e}")
        return JsonResponse({"history": []}, status=200)
