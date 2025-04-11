from rest_framework.decorators import api_view, renderer_classes, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.core.mail import send_mail
from .utils import fetch_emails, fetch_sent_emails, delete_email, is_inquiry_email
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings 
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib.auth import get_user_model   
import os
import json
from django.views.decorators.csrf import csrf_exempt
from .services.gemini_ai import generate_manual_response
from django.contrib.auth import login
from rest_framework.renderers import JSONRenderer
from .models import Manual

load_dotenv()
User = get_user_model()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@csrf_exempt
@api_view(['POST'])
@renderer_classes([JSONRenderer])
def google_login(request):
    token = request.data.get('id_token')

    if not token:
        return Response({'error': 'ID token is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Verify ID Token with clock skew tolerance
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10  # Allow 10 seconds of clock skew
        )

        email = idinfo['email']
        name = idinfo.get('name', '')

        # 2. Get or Create User
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "first_name": name}
        )

        # 3. Log in User
        login(request, user)

        return Response({
            "message": "Logged in successfully",
            "user": {
                "email": email,
                "name": name,
                "is_new": created
            }
        })

    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@renderer_classes([JSONRenderer])
def get_emails(request):
    """Django view to return fetched emails"""
    # Get access token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response({'error': 'Invalid Authorization header format'}, status=status.HTTP_400_BAD_REQUEST)
    
    access_token = auth_header.split('Bearer ')[1]
    if not access_token:
        return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Fetch emails using the access token
        emails, user_info = fetch_emails(access_token)
        
        # Debug information
        # print(f"Total emails fetched: {len(emails)}")
        read_emails = [email for email in emails if email.get("is_read", False)]
        # print(f"Read emails count: {len(read_emails)}")
        # print("Email read statuses:", [email.get("is_read", False) for email in emails])

        # Filter by read status if specified
        if request.GET.get("read") == "true":
            emails = [email for email in emails if email.get("is_read", False)]  # Show read emails
            # print(f"Filtered read emails count: {len(emails)}")
        elif request.GET.get("read") == "false":
            emails = [email for email in emails if not email.get("is_read", False)]  # Show unread emails
            # print(f"Filtered unread emails count: {len(emails)}")
        # Filter by category if specified
        elif request.GET.get("inquiry") == "true":
            emails = [email for email in emails if "inquiry" in email.get("categories", [])]
        elif request.GET.get("support") == "true":
            emails = [email for email in emails if "support" in email.get("categories", [])]
        elif request.GET.get("grievance") == "true":
            emails = [email for email in emails if "grievance" in email.get("categories", [])]

        return Response({
            "emails": emails,
            "user_info": user_info
        })
    except Exception as e:
        # print(f"Error fetching emails: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@renderer_classes([JSONRenderer])
def sent_emails_view(request):
    """Fetch and return sent emails as JSON"""
    # Get access token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response({'error': 'Invalid Authorization header format'}, status=status.HTTP_400_BAD_REQUEST)
    
    access_token = auth_header.split('Bearer ')[1]
    if not access_token:
        return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        sent_emails = fetch_sent_emails(access_token)
        return Response({"sent_emails": sent_emails})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

 
@api_view(['POST'])
@renderer_classes([JSONRenderer])
def send_ai_email(request):
    """Send AI-generated email reply using Django send_mail"""
    try:
        recipient = request.data.get("to", "")
        subject = request.data.get("subject", "AI Response")  
        email_body = request.data.get("body", "")

        if not recipient or not email_body:
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)
        
        sender_email = settings.EMAIL_HOST_USER

        # Sending email using Django send_mail
        send_mail(
            subject,
            email_body,
            sender_email,
            [recipient],
            fail_silently=False,
        )

        return Response({"message": "Email sent successfully."})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@renderer_classes([JSONRenderer])
def auto_reply_inquiry_emails(request):
  """Automatically reply to all filtered inquiry emails with AI-generated responses.""" 
  if request.method == "POST":
    try:
        # Get access token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Invalid Authorization header format'}, status=status.HTTP_400_BAD_REQUEST)
        
        access_token = auth_header.split('Bearer ')[1]
        if not access_token:
            return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch emails using the access token
        emails, _ = fetch_emails(access_token)
        sent_emails = fetch_sent_emails(access_token)

        # Filter Inquiry Emails
        inquiry_emails = [email for email in emails if is_inquiry_email(email)]
        print(f"Found {len(inquiry_emails)} inquiry emails")

        if not inquiry_emails:
            return Response({"message": "No inquiry emails found."}, status=status.HTTP_200_OK)

        sender_email = settings.EMAIL_HOST_USER
        responses_sent = []
        replied_to = set()  # Track unique recipient+subject combinations we've replied to

        for email in inquiry_emails:
            # Extract email address from the "From" field which might contain name <email>
            from_header = email["from"]
            # Extract email address if it's in the format "Name <email@example.com>"
            if "<" in from_header and ">" in from_header:
                recipient = from_header[from_header.find("<")+1:from_header.find(">")]
            else:
                recipient = from_header.strip()

            # Get the subject and normalize it
            subject = email["subject"]
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            
            # Create a unique key combining recipient and subject
            email_key = f"{recipient}_{subject}"
            
            # Check if we've already replied to this email
            if email_key in replied_to:
                print(f"Skipping already replied email: {subject}")
                continue

            # Check if this email is in the sent emails list
            if any(sent["to"] == recipient and sent["subject"] == subject for sent in sent_emails):
                print(f"Skipping already replied email (found in sent): {subject}")
                replied_to.add(email_key)
                continue

            try:
                # Generate AI response
                ai_response = generate_manual_response(email["body"])
                
                # Send the email
                send_mail(
                    subject,
                    ai_response,
                    sender_email,
                    [recipient],
                    fail_silently=False,
                )
                
                responses_sent.append({
                    "to": recipient,
                    "subject": subject,
                    "status": "sent"
                })
                replied_to.add(email_key)
                print(f"Sent reply to: {recipient} - {subject}")
                
            except Exception as e:
                print(f"Error processing email {subject}: {str(e)}")
                responses_sent.append({
                    "to": recipient,
                    "subject": subject,
                    "status": "error",
                    "error": str(e)
                })

        return Response({
            "message": f"Processed {len(inquiry_emails)} inquiry emails",
            "responses_sent": responses_sent
        })

    except Exception as e:
        print(f"Error in auto_reply_inquiry_emails: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@renderer_classes([JSONRenderer])
def delete_email_view(request, message_id):
    """
    Delete an email from Gmail account
    """
    # Get access token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response({'error': 'Invalid Authorization header format'}, status=status.HTTP_400_BAD_REQUEST)
    
    access_token = auth_header.split('Bearer ')[1]
    if not access_token:
        return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        success, message = delete_email(message_id, access_token)
        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@renderer_classes([JSONRenderer])
def logout_view(request):
    """Logout the current user"""
    try:
        logout(request)
        return Response({
            "message": "Logged out successfully"
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_manual(request):
    print(f"User: {request.user}")  # Log the user
    uploaded_file = request.FILES.get('file')
    filename = request.data.get('filename', uploaded_file.name)

    if not uploaded_file:
        return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

    manual = Manual.objects.create(
        user=request.user,
        file=uploaded_file,
        filename=filename
    )

    return Response({'message': 'Manual uploaded successfully', 'manual_id': manual.id})