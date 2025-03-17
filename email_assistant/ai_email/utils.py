from google.oauth2 import service_account
from googleapiclient.discovery import build

def fetch_emails():
  credentials = service_account.Credentials.from_service_account_file("credentials.json")
  service = build('gmail', 'v1', credentials=credentials)
  results = service.users().messages().list(userId='me', maxResults=10).execute()
  return results.get('messages', [])