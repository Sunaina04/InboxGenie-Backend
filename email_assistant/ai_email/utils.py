import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly"
]

def authenticate_gmail():
    """Authenticate and return Gmail API service"""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=8080, access_type="offline", prompt="consent")
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

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

def fetch_emails():
    """Fetch latest emails from Gmail API"""
    
    
    service = authenticate_gmail()
           
    # Add labelIds=['INBOX'] to only fetch received emails
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=5).execute()
        messages = results.get("messages", [])
        print(f"Found {len(messages)} messages in inbox")
    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        return []

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
    return full_email

def fetch_sent_emails():
    """Fetch latest sent emails from Gmail API"""
    service = authenticate_gmail()
    
    results = service.users().messages().list(userId='me', labelIds=['SENT'], maxResults=10).execute()
    messages = results.get("messages", [])

    sent_emails = []
    for msg in messages:
        msg_id = msg["id"]
        email_data = service.users().messages().get(userId='me', id=msg_id).execute()

        headers = email_data["payload"]["headers"]
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
        recipient = next((h["value"] for h in headers if h["name"].lower() == "to"), "Unknown Recipient")
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        date = next((h["value"] for h in headers if h["name"].lower() == "date"), "Unknown Date")

        body = get_email_body(email_data)
        sent_emails.append({
            "id": msg_id,
            "from": sender,
            "to": recipient,
            "subject": subject,
            "date": date,
            "body": body,
        })

    return sent_emails
