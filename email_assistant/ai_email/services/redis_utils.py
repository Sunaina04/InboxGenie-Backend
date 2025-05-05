import redis
import json
from django.conf import settings

# Initialize Redis client
redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

PROCESSED_EMAIL_SET_KEY = "processed_emails"

def cache_email_by_category(category, email_obj, expiration_time=3600):
    """
    Store or append the email to Redis cache by category.
    """
    try:
        cache_key = f"emails:{category}"

        existing_data = redis_client.get(cache_key)
        try:
            parsed_data = json.loads(existing_data) if existing_data else []
        except json.JSONDecodeError:
            parsed_data = []

        if isinstance(parsed_data, dict):
            parsed_data = [parsed_data]

        if not isinstance(parsed_data, list):
            parsed_data = []

        parsed_data.append(email_obj)

        redis_client.setex(cache_key, expiration_time, json.dumps(parsed_data))
        print(f"Successfully cached email under category: {category}")
    except Exception as e:
        print(f"Error caching email: {str(e)}")


def fetch_from_redis_cache(cache_key):
    """Fetch data from Redis cache."""
    try:
        cached_data = redis_client.get(cache_key)
        return json.loads(cached_data) if cached_data else None
    except Exception as e:
        print(f"Error fetching data from Redis: {str(e)}")
        return None


# === NEW FUNCTIONS FOR TRACKING PROCESSED EMAILS ===

def is_email_processed(email_id):
    """
    Check if the email ID has already been processed.
    """
    try:
        return redis_client.sismember(PROCESSED_EMAIL_SET_KEY, email_id)
    except Exception as e:
        print(f"Error checking processed email: {str(e)}")
        return False


def mark_email_as_processed(email_id):
    """
    Add the email ID to the set of processed emails.
    """
    try:
        redis_client.sadd(PROCESSED_EMAIL_SET_KEY, email_id)
    except Exception as e:
        print(f"Error marking email as processed: {str(e)}")
