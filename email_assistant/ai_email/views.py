from django.http import JsonResponse
from django.core.mail import send_mail
from .utils import fetch_emails, fetch_sent_emails
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings 
import os
import json
from django.views.decorators.csrf import csrf_exempt
from .services.gemini_ai import generate_manual_response

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_emails(request):
  """Django view to return fetched emails"""
  emails = fetch_emails()

  if request.GET.get("inquiry") == "true":
      emails = [email for email in emails if is_inquiry_email(email)]

  return JsonResponse({"emails": emails})

def is_inquiry_email(email):
  """Check if an email is an inquiry email based on subject or content."""
  inquiry_keywords = ["inquiry", "question", "help", "support", "request", "info"]
  subject = email.get("subject", "").lower()
  body = email.get("body", "").lower()

  return any(keyword in subject or keyword in body for keyword in inquiry_keywords)

def sent_emails_view(request):
  """Fetch and return sent emails as JSON"""
  sent_emails = fetch_sent_emails()
  return JsonResponse({"sent_emails": sent_emails})

# For Raw AI responses
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
          print(request.body)
          email_body = data.get("email_body", "")
          sender = data.get("from", "")
          recipient = data.get("to", "")
          subject = data.get("subject", "Re: No Subject")

          if not email_body:
              return JsonResponse({"error": "Email body is required."}, status=400)

          ai_response = generate_manual_response(email_body)

          return JsonResponse({
              "from": recipient,  
              "to": sender,
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
          recipient = data.get("to", "")
          subject = data.get("subject", "AI Response")  
          email_body = data.get("body", "")

          if not recipient or not email_body:
              return JsonResponse({"error": "Missing required fields."}, status=400)
          
          sender_email = settings.EMAIL_HOST_USER

          # Sending email using Django send_mail
          send_mail(
              subject,
              email_body,
              sender_email,
              [recipient],
              fail_silently=False,
          )

          return JsonResponse({"message": "Email sent successfully."})

      except json.JSONDecodeError:
          return JsonResponse({"error": "Invalid JSON format."}, status=400)
      except Exception as e:
          return JsonResponse({"error": str(e)}, status=500)

  return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

def auto_reply_inquiry_emails(request):
  """Automatically reply to all filtered inquiry emails with AI-generated responses."""
  if request.method == "POST":
      try:
          emails = fetch_emails()

          # Filter Inquiry Emails
          inquiry_emails = [email for email in emails if is_inquiry_email(email)]

          if not inquiry_emails:
              return JsonResponse({"message": "No inquiry emails found."}, status=200)

          sender_email = settings.EMAIL_HOST_USER  # Your configured email
          responses_sent = []

          for email in inquiry_emails:
              sender = email["from"]
              subject = f"Re: {email['subject']}"
              email_body = email["body"]

              # Generate AI Response
              ai_response = generate_manual_response(email_body)

              # Send Email
              send_mail(
                  subject,
                  ai_response,
                  sender_email,
                  [sender],
                  fail_silently=False,
              )

              responses_sent.append({
                  "to": sender,
                  "subject": subject,
                  "body": ai_response
              })

          return JsonResponse({"message": "AI responses sent successfully.", "responses": responses_sent})

      except Exception as e:
          return JsonResponse({"error": str(e)}, status=500)

  return JsonResponse({"error": "Only POST requests are allowed."}, status=405)