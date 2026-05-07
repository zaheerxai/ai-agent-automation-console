import json

import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def trigger_agent(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON payload"}, status=400)

    user_message = str(body.get("message", "")).strip()
    if not user_message:
        return JsonResponse({"message": "Message is required"}, status=400)

    if not settings.N8N_WEBHOOK_URL:
        return JsonResponse({"message": "System busy"}, status=503)

    try:
        n8n_response = requests.post(
            settings.N8N_WEBHOOK_URL,
            json={"message": user_message},
            timeout=settings.N8N_TIMEOUT_SECONDS,
        )
        print(f"n8n status: {n8n_response.status_code}")
        print(f"n8n body: {n8n_response.text!r}")
    except requests.RequestException as e:
        print(f"n8n request failed: {e}")
        return JsonResponse({"message": "System busy"}, status=503)

    text = n8n_response.text.strip()
    if not text:
        response_data = {"message": "Webhook received"}
    else:
        try:
            response_data = n8n_response.json()
        except ValueError:
            response_data = {"message": text}

    return JsonResponse({"status": "ok", "response": response_data})