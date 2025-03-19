import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SCOPES = ["https://mail.google.com/"]

def authenticate_gmail():
    """Authenticate and return Gmail API service"""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        creds = flow.run_local_server(port=8080,access_type="offline", prompt="consent")
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

