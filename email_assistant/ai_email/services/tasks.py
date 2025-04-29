from celery import shared_task
from .embeddings import store_manual_embeddings

@shared_task
def generate_manual_embeddings_task(pdf_path, user_id):
    print("user in task", user_id)
    
    try:
        store_manual_embeddings(pdf_path, user_id)
        return {"status": "success", "path": pdf_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}
