from django.http import JsonResponse
from .utils import fetch_emails
import openai
from dotenv import load_dotenv
import os
import json
from django.views.decorators.csrf import csrf_exempt

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_emails(request):
    """Django view to return fetched emails"""
    emails = fetch_emails()
    return JsonResponse({"emails": emails})

def generate_ai_response(email_body):
    """Generate an AI response to an email message"""
    if not email_body.strip():
      return "No content to generate a response."
    prompt = f"Reply to this email in a professional and helpful tone:\n\n{email_body}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a helpful email assistant."},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

@csrf_exempt  #NEED to check later
def generate_email_reply(request):
    """API endpoint to generate AI response"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email_body = data.get("email_body", "")

            if not email_body:
                return JsonResponse({"error": "Email body is required."}, status=400)

            ai_response = generate_ai_response(email_body)
            return JsonResponse({"ai_response": ai_response})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)