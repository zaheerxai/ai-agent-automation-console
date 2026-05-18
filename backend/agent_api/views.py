import json
import re
import os
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def extract_profile_with_llm(user_message: str, current_profile: dict) -> dict:
    """Use Groq LLM to intelligently extract profile updates from user message"""
    
    prompt = f"""
You are an expert at extracting user information from casual chat messages.

Current user profile:
{json.dumps(current_profile, indent=2)}

User's latest message: "{user_message}"

Extract any new or updated information about the user. 
Return **only valid JSON**. Do not add any explanation.

Possible fields you can update:
- name
- bio
- timezone
- preferences (object)
- favorite_tools (array of strings)

Examples of good output:

{{
  "name": "Zaheer",
  "preferences": {{
    "response_style": "concise",
    "tone": "professional but friendly"
  }}
}}

{{
  "bio": "Founder building AI automation tools, based in Pakistan"
}}

{{
  "preferences": {{
    "language": "English",
    "max_response_length": "short"
  }},
  "favorite_tools": ["web search", "google sheets"]
}}
"""

    try:
        # Using Groq directly (fast and cheap)
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",   # or whichever model you're using
            messages=[
                {"role": "system", "content": "You are a precise JSON extractor. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=400
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean possible markdown code blocks
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0]
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0]
            
        updates = json.loads(content)
        return updates if isinstance(updates, dict) else {}
        
    except Exception as e:
        print(f"LLM Profile Extraction Error: {e}")
        return {}



def extract_profile_updates(user_message: str, current_profile: dict) -> dict:
    """
    Extract profile updates from user message using simple + robust rules.
    Returns dict with fields that should be updated.
    """
    updates = {}
    msg_lower = user_message.lower().strip()

    # === Name Extraction ===
    name_patterns = [
        r"my name is (\w+)",
        r"i am (\w+)",
        r"call me (\w+)",
        r"name is (\w+)"
    ]
    for pattern in name_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            extracted_name = match.group(1).capitalize()
            if len(extracted_name) > 2:  # avoid short words
                updates["name"] = extracted_name
            break

    # === Preferences Extraction (key-value style) ===
    pref_patterns = [
        (r"i (like|love|prefer) (.+?)(?:\.|$)", "preferences"),
        (r"remember that i (.+?)(?:\.|$)", "preferences"),
        (r"i want (.+?)(?:\.|$)", "preferences"),
    ]

    for pattern, key in pref_patterns:
        matches = re.findall(pattern, msg_lower)
        if matches:
            if "preferences" not in updates:
                updates["preferences"] = current_profile.get("preferences", {}).copy()
            
            for match in matches:
                value = match[1] if isinstance(match, tuple) else match
                # Simple key generation
                pref_key = value.split()[0] if value else "general"
                updates["preferences"][pref_key] = value.strip()

    # === Bio / Location ===
    if any(word in msg_lower for word in ["based in", "live in", "from ", "i am from"]):
        updates["bio"] = user_message  # You can refine this later

    return updates

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
    
    profile_info = "User Profile:\n"
    if profile.get("name"):
        profile_info += f"- Name: {profile['name']}\n"
    if profile.get("bio"):
        profile_info += f"- Bio: {profile['bio']}\n"
    if profile.get("timezone"):
        profile_info += f"- Timezone: {profile['timezone']}\n"
    if profile.get("favorite_tools"):
        profile_info += f"- Favorite Tools: {', '.join(profile['favorite_tools'])}\n"
    
    # Add preferences (key-value)
    if profile.get("preferences"):
        profile_info += "- Preferences:\n"
        for k, v in profile["preferences"].items():
            profile_info += f"  • {k}: {v}\n"
    
    # Fetch chat history
    results = turso_execute([{
        "sql": (
            "SELECT role, content FROM chat_history "
            "WHERE session_id = ? "
            "ORDER BY created_at ASC"
        ),
        "args": [session_id]
    }])

    if not results or not results[0]["response"]["result"]["rows"]:
        return profile_info.strip()

    try:
        rows = results[0]["response"]["result"]["rows"]
        history = profile_info + "\n--- Conversation History ---\n"
        
        for row in rows[-12:]:   # Increased to 12 (adjust based on your LLM context)
            role_val = row[0]["value"]
            content_val = row[1]["value"]
            speaker = "User" if role_val == "user" else "Mojo"
            history += f"{speaker}: {content_val}\n"
        
        return history.strip()
    except Exception as e:
        print(f"Turso parse history error: {e}")
        return profile_info.strip()

@csrf_exempt
@require_POST
def update_profile(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        user_id = body.get("user_id") or body.get("sessionId")
        
        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)

        name = body.get("name")
        bio = body.get("bio")
        timezone = body.get("timezone")
        preferences = body.get("preferences")   # dict
        favorite_tools = body.get("favorite_tools")  # list

        save_user_profile(
            user_id=user_id,
            name=name,
            bio=bio,
            timezone=timezone,
            preferences=preferences,
            favorite_tools=favorite_tools
        )

        # Return updated profile
        updated_profile = get_user_profile(user_id)
        
        return JsonResponse({
            "success": True,
            "message": "Profile updated successfully",
            "profile": updated_profile
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

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
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    user_message = str(body.get("message", "")).strip()
    session_id = body.get("sessionId") or body.get("user_id") or "anonymous"

    if not user_message:
        return JsonResponse({"message": "Message required"}, status=400)

    n8n_url = os.environ.get("N8N_WEBHOOK_URL")
    if not n8n_url:
        return JsonResponse({"message": "Config error"}, status=503)

    ensure_table()
    
    # === NEW: Auto-update profile ===
    
    current_profile = get_user_profile(session_id)
    # First try rule-based (fast)
    updates = extract_profile_updates(user_message, current_profile)
    
    # If nothing found or for better quality, use LLM
    if not updates or len(updates) == 0:
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
        print(f"✅ LLM Auto-updated profile for {session_id}: {updates}")


    # Fetch updated profile + history
    chat_history_str = fetch_history(session_id)

    n8n_payload = {
        "User message": user_message,
        "sessionId": session_id,
        "chat_history": chat_history_str,
    }

    # 3. Forward to n8n

    try:
        n8n_response = requests.post(n8n_url, json=n8n_payload, timeout=60)
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
