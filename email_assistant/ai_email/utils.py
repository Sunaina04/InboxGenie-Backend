import os
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.generativeai as genai
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import api_view, renderer_classes


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'  # This scope allows deleting emails
]

def decode_base64(data):
    """Decodes Base64-encoded email body from Gmail API"""
    if not data:
        return "No content available"
    
    try:
        decoded_bytes = base64.urlsafe_b64decode(data.encode("ASCII"))
        return decoded_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error decoding Base64: {e}")
        return "Error decoding email content"

def get_email_body(email_data):
    """Extracts main body text from Gmail API response"""
    payload = email_data.get("payload", {})

    if "body" in payload and "data" in payload["body"]:
        return decode_base64(payload["body"]["data"])

    parts = payload.get("parts", [])
    for part in parts:
        if part["mimeType"] == "text/plain":
            return decode_base64(part["body"]["data"])

    return "No message body found"

def is_inquiry_email(email):
    """Check if an email is an inquiry email based on subject or content."""
    inquiry_keywords = ["inquiry", "question", "help", "support", "request", "info"]
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()

    return any(keyword in subject or keyword in body for keyword in inquiry_keywords)

def is_support_email(email):
    """Check if an email is a support-related email based on subject or content."""
    support_keywords = ["support", "help", "assistance", "technical", "issue", "problem", "troubleshoot", "bug", "error"]
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()

    return any(keyword in subject or keyword in body for keyword in support_keywords)

def is_grievance_email(email):
    """Check if an email is a grievance/complaint email based on subject or content."""
    grievance_keywords = ["complaint", "grievance", "dispute", "unhappy", "dissatisfied", "wrong", "incorrect", "bad", "poor", "terrible"]
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()

    return any(keyword in subject or keyword in body for keyword in grievance_keywords)

def fetch_emails(access_token):
    """Fetch latest emails from Gmail API using the provided access token"""    
    
    try:
        # Create credentials from the access token
        creds = Credentials(token=access_token)        
        service = build("gmail", "v1", credentials=creds)
        
        if not service:
            return [], None  
            
        # Get user profile
        user_profile = service.users().getProfile(userId='me').execute()
        user_email = user_profile.get('emailAddress')
        username = user_email.split('@')[0] if user_email else '' 
        
        # Get user info from Gmail API
        user_info = {
            'email': user_email,
            'name': username,
        }

        print(f"Fetching emails for user: {user_info}")
               
        # Add labelIds=['INBOX'] to only fetch received emails
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=5).execute()
        messages = results.get("messages", [])
        print(f"Found {len(messages)} messages in inbox")

        full_email = []
        for msg in messages:
            try:
                msg_id = msg["id"]
                email_data = service.users().messages().get(userId='me', id=msg_id).execute()

                headers = email_data["payload"]["headers"]
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
                recipient = next((h["value"] for h in headers if h["name"].lower() == "to"), "Unknown Recipient")
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                date = next((h["value"] for h in headers if h["name"].lower() == "date"), "Unknown Date")
                
                # Get read status from labelIds
                label_ids = email_data.get("labelIds", [])
                is_read = "UNREAD" not in label_ids

                body = get_email_body(email_data)
                email_obj = {
                    "id": msg_id,
                    "from": sender,
                    "to": recipient,
                    "subject": subject,
                    "date": date,
                    "body": body,
                    "is_read": is_read,
                    "categories": []
                }

                # Add email categories
                if is_inquiry_email(email_obj):
                    email_obj["categories"].append("inquiry")
                if is_support_email(email_obj):
                    email_obj["categories"].append("support")
                if is_grievance_email(email_obj):
                    email_obj["categories"].append("grievance")

                full_email.append(email_obj)
                print(f"Processed email: {subject}")
            except Exception as e:
                print(f"Error processing message {msg.get('id', 'unknown')}: {str(e)}")
                continue

        print(f"Successfully processed {len(full_email)} emails")
        return full_email, user_info
        
    except Exception as e:
        print(f"Error in fetch_emails: {str(e)}")
        return [], None

def fetch_sent_emails(access_token):
    """Fetch sent emails from Gmail API using the provided access token"""
    try:
        # Create credentials from the access token
        creds = Credentials(token=access_token)
        service = build("gmail", "v1", credentials=creds)
        
        if not service:
            return []
            
        # Get sent emails
        results = service.users().messages().list(
            userId='me',
            labelIds=['SENT'],
            maxResults=5
        ).execute()
        
        messages = results.get("messages", [])
        print(f"Found {len(messages)} sent messages")

        sent_emails = []
        for msg in messages:
            try:
                msg_id = msg["id"]
                email_data = service.users().messages().get(userId='me', id=msg_id).execute()

                headers = email_data["payload"]["headers"]
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
                recipient = next((h["value"] for h in headers if h["name"].lower() == "to"), "Unknown Recipient")
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
                date = next((h["value"] for h in headers if h["name"].lower() == "date"), "Unknown Date")

                body = get_email_body(email_data)
                email_obj = {
                    "id": msg_id,
                    "from": sender,
                    "to": recipient,
                    "subject": subject,
                    "date": date,
                    "body": body
                }

                sent_emails.append(email_obj)
                print(f"Processed sent email: {subject}")
            except Exception as e:
                print(f"Error processing sent message {msg.get('id', 'unknown')}: {str(e)}")
                continue

        print(f"Successfully processed {len(sent_emails)} sent emails")
        return sent_emails
        
    except Exception as e:
        print(f"Error in fetch_sent_emails: {str(e)}")
        return []

def delete_email(message_id, access_token):
    """Delete an email from Gmail using the provided access token"""
    try:
        # Create credentials from the access token
        creds = Credentials(token=access_token)
        service = build("gmail", "v1", credentials=creds)
        
        if not service:
            return False, "Failed to initialize Gmail service"

        # Delete the email
        service.users().messages().trash(userId='me', id=message_id).execute()
        return True, "Email deleted successfully"
        
    except Exception as e:
        print(f"Error deleting email: {str(e)}")
        return False, str(e)
