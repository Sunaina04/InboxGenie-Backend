from rest_framework.decorators import api_view, renderer_classes, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.core.mail import send_mail
from .utils import fetch_emails, delete_email
# fetch_sent_emails, delete_email, is_inquiry_email
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings 
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib.auth import get_user_model, get_user  
import os
import json
from django.views.decorators.csrf import csrf_exempt
from .services.gemini_ai import generate_manual_response
from .services.embeddings import delete_manual_embeddings
from django.contrib.auth import login
from rest_framework.renderers import JSONRenderer
from .models import Manual
from .services.tasks import generate_manual_embeddings_task
from .services.redis_utils import fetch_from_redis_cache
import sys

# from rest_framework_simplejwt.tokens import RefreshToken

load_dotenv()
User = get_user_model()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# def get_tokens_for_user(user):
#     refresh = RefreshToken.for_user(user)
#     return {
#         'refresh': str(refresh),
#         'access': str(refresh.access_token),
#     }

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
        # breakpoint()
        login(request, user)
        # tokens = get_tokens_for_user(user)
     
        return Response({
            "message": "Logged in successfully",
            # "tokens": tokens,
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
        # Category-based cache fetch
        for category in ['inquiry', 'support', 'grievance']:
            if request.GET.get(category) == 'true':
                cached_emails = fetch_from_redis_cache(f'emails:{category}')
                # Ensure emails is always a list
                if cached_emails:
                    if isinstance(cached_emails, dict):
                        cached_emails = [cached_emails]
                    elif not isinstance(cached_emails, list):
                        cached_emails = []
                else:
                    cached_emails = []

                return Response({
                    "emails": cached_emails,
                    "user_info": {"source": "cache", "category": category}
                })
        emails, user_info = fetch_emails(access_token)
        
        # Debug information
        print(f"Total emails fetched: {len(emails)}")
        read_emails = [email for email in emails if email.get("is_read", False)]
        # print(f"Read emails count: {len(read_emails)}")
        # print("Email read statuses:", [email.get("is_read", False) for email in emails])
      
        if request.GET.get("read") == "true":
            emails = [email for email in emails if email.get("is_read", False)]  # Show read emails
            # print(f"Filtered read emails count: {len(emails)}")
        elif request.GET.get("read") == "false":
            emails = [email for email in emails if not email.get("is_read", False)]  # Show unread emails
            # print(f"Filtered unread emails count: {len(emails)}")
       
        # elif request.GET.get("inquiry") == "true":
        #     emails = [email for email in emails if "inquiry" in email.get("categories", [])]
        # elif request.GET.get("support") == "true":
        #     emails = [email for email in emails if "support" in email.get("categories", [])]
        # elif request.GET.get("grievance") == "true":
        #     emails = [email for email in emails if "grievance" in email.get("categories", [])]

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
          user_email = data.get("user_email")

          if not email_body:
              return JsonResponse({"error": "Email body is required."}, status=400)
          
          print("user email", user_email)

          ai_response = generate_manual_response(email_body, user_email)

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
def auto_reply_emails(request):
    """Send AI-generated replies to selected emails."""
    try:
        # Extract access token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Invalid Authorization header'}, status=400)
        
        access_token = auth_header.split('Bearer ')[1]

        selected_emails = request.data.get('emails', [])
        user_email = request.data.get('user_email')
        
        # Check if selected_emails is a dictionary and convert it to a list
        if isinstance(selected_emails, dict):
            selected_emails = [selected_emails]

        if not selected_emails:
            return Response({'error': 'No emails provided'}, status=400)

        sender_email = settings.EMAIL_HOST_USER
        responses_sent = []

        for email in selected_emails:
            if not isinstance(email, dict):
                continue

            from_header = email.get("from", "")
            recipient = (
                from_header[from_header.find("<")+1:from_header.find(">")]
                if "<" in from_header and ">" in from_header
                else from_header
            )

            subject = email.get("subject", "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            body = email.get("body", "")
            try:
                ai_response = generate_manual_response(body, user_email)
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

            except Exception as e:
                responses_sent.append({
                    "to": recipient,
                    "subject": subject,
                    "status": "error",
                    "error": str(e)
                })

        return Response({
            "message": f"Processed {len(responses_sent)} selected emails",
            "responses_sent": responses_sent
        }, status=200)

    except Exception as e:
        return Response({'error': str(e)}, status=500)

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
@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])    
def upload_manual(request):
    uploaded_file = request.FILES.get('file')
    filename = request.data.get('filename', uploaded_file.name)
    email = request.data.get('email')

    if not uploaded_file or not email:
        return Response({'error': 'Missing file or email.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User not found with given email.'}, status=status.HTTP_404_NOT_FOUND)

    # Check for duplicate filename for this user
    if Manual.objects.filter(user=user, filename=filename).exists():
        return Response({'error': 'A manual with the same filename already exists.'}, status=status.HTTP_409_CONFLICT)

    # Save the manual
    manual = Manual.objects.create(
        user=user,
        file=uploaded_file,
        filename=filename,
        embedding_status='pending'
    )

    # Call the task to generate embeddings
    generate_manual_embeddings_task.delay(manual.id, user.id)

    # Check for orphaned files in the directory and clean them up
    try:
        clean_orphaned_files()
    except Exception as e:
        # Log the error in case file cleanup fails
        print(f"Error cleaning orphaned files: {str(e)}")

    return Response({'message': 'Manual uploaded successfully', 'manual_id': manual.id})


def clean_orphaned_files():
    """Cleanup orphaned manual files in the media directory."""
    media_dir = os.path.join(settings.MEDIA_ROOT, 'manuals')
    all_files = os.listdir(media_dir)
    
    # Get the IDs of all manuals from the database
    manual_files = Manual.objects.values_list('file', flat=True)
    manual_file_names = [os.path.basename(file) for file in manual_files]

    # Delete orphaned files (files that are in the folder but not in the database)
    for file_name in all_files:
        if file_name not in manual_file_names:
            file_path = os.path.join(media_dir, file_name)
            try:
                os.remove(file_path)
                print(f"Orphaned file deleted: {file_name}")
            except Exception as e:
                print(f"Failed to delete orphaned file {file_name}: {str(e)}")

@api_view(['GET'])
def list_manuals(request):
    email = request.query_params.get('email')
    
    if not email:
        return Response({'error': 'Email is required as a query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User not found with given email.'}, status=status.HTTP_404_NOT_FOUND)
    
    manuals = Manual.objects.filter(user=user).values('id', 'filename', 'file', 'uploaded_at', 'embedding_status')
    return Response({'manuals': list(manuals)}, status=status.HTTP_200_OK)

@api_view(['DELETE'])
def delete_manual(request, manual_id):
    email = request.query_params.get('email') 

    if not email:
        return Response({'error': 'Email is required as a query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User not found with given email.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        manual = Manual.objects.get(id=manual_id)
        delete_manual_embeddings(user.id, manual_id)
        manual.delete()
        return Response({'message': 'Manual deleted successfully'}, status=status.HTTP_200_OK)
    except Manual.DoesNotExist:
        return Response({'error': 'Manual not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PATCH'])
def rename_manual(request, manual_id):
    try:
        print(manual_id, "....................manual id")
        manual = Manual.objects.get(id=manual_id)
        print("manual....................", manual)
    except Manual.DoesNotExist:
        return Response({'error': 'Manual not found'}, status=status.HTTP_404_NOT_FOUND)

    new_filename = request.data.get('filename')
    if not new_filename:
        print("here................")
        return Response({'error': 'New filename is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Optional: check for duplicates
    if Manual.objects.filter(user=manual.user, filename=new_filename).exclude(id=manual.id).exists():
        print("here 2......................")
        return Response({'error': 'Filename already exists.'}, status=status.HTTP_409_CONFLICT)

    manual.filename = new_filename
    manual.save()
    return Response({'message': 'Filename updated successfully', 'filename': new_filename})

print(sys.path)

@api_view(['POST'])
def retry_embedding(request, manual_id):
    # Extract the user_email from the request body
    user_email = request.data.get('user_email')

    if not user_email:
        return Response({"error": "User email is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Retrieve the manual from the database
        manual = Manual.objects.get(id=manual_id)
    except Manual.DoesNotExist:
        return Response({"error": "Manual not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Update the status of the manual to 'queued'
        manual.embedding_status = 'queued'
        manual.save()

        # Call the Celery task again, passing manual_id and user_email
        generate_manual_embeddings_task.delay(manual.id, user_email)

        return Response({"message": "Embedding retry task queued"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)