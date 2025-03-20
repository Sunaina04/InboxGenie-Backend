from django.http import JsonResponse
from django.core.mail import send_mail
from .utils import fetch_emails
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from django.views.decorators.csrf import csrf_exempt

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_emails(request):
    """Django view to return fetched emails"""
    emails = fetch_emails()
    return JsonResponse({"emails": emails})

def generate_ai_response(email_body):
    """Generate an AI response using Gemini"""
    if not email_body.strip():
        return "No content to generate a response."

    model = genai.GenerativeModel('gemini-1.5-flash')  
    response = model.generate_content(f"Reply to this email in a professional and helpful tone:\n\n{email_body}")

    return response.text     
    
@csrf_exempt  #NEED to check later

def generate_email_reply(request):
    """API to generate AI response with email details"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email_body = data.get("email_body", "")
            sender = data.get("from", "")  # Sender's email (who sent the email)
            recipient = data.get("to", "")  # Your email (receiving the email)
            subject = data.get("subject", "Re: No Subject")  # Reply subject

            if not email_body:
                return JsonResponse({"error": "Email body is required."}, status=400)

            ai_response = generate_ai_response(email_body)

            return JsonResponse({
                "from": recipient,   # You become the sender
                "to": sender,        # Reply goes to original sender
                "subject": f"Re: {subject}",
                "body": ai_response
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

 
@csrf_exempt
def send_ai_email(request):
    """Send AI-generated email reply using Django send_mail"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            sender = data.get("from", "")  
            recipient = data.get("to", "")
            subject = data.get("subject", "AI Response")  
            email_body = data.get("body", "")

            if not sender or not recipient or not email_body:
                return JsonResponse({"error": "Missing required fields."}, status=400)

            # Sending email using Django send_mail
            send_mail(
                subject,
                email_body,
                sender,
                [recipient],
                fail_silently=False,
            )

            return JsonResponse({"message": "Email sent successfully."})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)