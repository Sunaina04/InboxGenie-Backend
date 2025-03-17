import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def fetch_emails():
    """Fetch latest emails from Gmail API"""
    service = authenticate_gmail()
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get("messages", [])

    full_email = []
    for msg in messages:
      msg_id = msg["id"]
      email_data = service.users().messages().get(userId='me', id=msg_id).execute()

      headers = email_data["payload"]["headers"]
      sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

      body = get_email_body(email_data)
      full_email.append({"id": msg_id, "from": sender, "body": body})

    return full_email

