from celery import shared_task
from .embeddings import store_manual_embeddings
from ai_email.models import Manual

@shared_task
def generate_manual_embeddings_task(manual_id, user_id):
    try:
        # Fetch the manual object by its ID
        manual = Manual.objects.get(id=manual_id)
        
        # Update the status to 'processing'
        manual.embedding_status = 'processing'
        manual.save()

        # Get the file path from the manual
        pdf_path = manual.file.path

        # Call the embedding function with the file path and user_id, manual_id
        store_manual_embeddings(pdf_path, user_id, manual_id)

        # Update the status to 'success' after processing
        manual.embedding_status = 'success'
        manual.save()

        return {"status": "success", "manual_id": manual_id}

    except Exception as e:
        # In case of failure, mark the status as 'failed'
        if 'manual' in locals():
            manual.embedding_status = 'failed'
            manual.save()
        
        return {"status": "error", "error": str(e), "manual_id": manual_id}
