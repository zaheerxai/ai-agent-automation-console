import json
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def trigger_agent(request):
    # 1. Parse the incoming request from React
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON payload"}, status=400)

    # 2. Validate the message content
    user_message = str(body.get("message", "")).strip()
    if not user_message:
        return JsonResponse({"message": "Message is required"}, status=400)

    # 3. Securely fetch the Webhook URL from Vercel Environment Variables
    n8n_url = os.environ.get('N8N_WEBHOOK_URL')
    if not n8n_url:
        print("ERROR: N8N_WEBHOOK_URL is missing from Vercel environment variables.")
        return JsonResponse({"message": "System configuration error"}, status=503)

    # 4. Forward the payload to n8n
    try:
        # Hard cap at 9 seconds to avoid Vercel's 10-second serverless crash limit
        n8n_response = requests.post(
            n8n_url,
            json={"User message": user_message},
            timeout=9, 
        )
        print(f"n8n status: {n8n_response.status_code}")
    except requests.RequestException as e:
        print(f"n8n request failed: {e}")
        return JsonResponse({"message": "Agent timeout or connection error"}, status=503)

    # 5. Parse the n8n response safely
    text = n8n_response.text.strip()
    if not text:
        response_data = {"message": "Webhook received but no content returned"}
    else:
        try:
            response_data = n8n_response.json()
        except ValueError:
            response_data = {"message": text}

    # 6. Send the data back to the React UI
    return JsonResponse({"status": "ok", "response": response_data})