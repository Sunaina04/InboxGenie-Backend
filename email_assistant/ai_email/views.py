from django.http import JsonResponse
from .utils import fetch_emails

def get_emails(request):
    """Django view to return fetched emails"""
    emails = fetch_emails()
    return JsonResponse({"emails": emails})
