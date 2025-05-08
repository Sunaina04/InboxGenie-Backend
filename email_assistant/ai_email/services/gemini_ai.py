import google.generativeai as genai
from .embeddings import load_vector_store
from dotenv import load_dotenv
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from django.contrib.auth.models import User
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_response_with_retry(model, prompt):
    """Generate response with retry logic for handling timeouts"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        raise


def generate_manual_response(email_body, email, collection_name=None):
    """Searches ChromaDB for relevant manual content and generates an AI response."""

    if not collection_name:
        try:
            user = User.objects.get(email=email)
            collection_name = f"user_{user.id}_manual_embeddings"
        except User.DoesNotExist:
            return "User not found. Please check your email."

    # Load vector store using the dynamically generated or passed collection name
    vector_store = load_vector_store(collection_name)
    if not vector_store:
        return "I apologize, but I'm currently unable to access the manual information. Please try again later."

    try:
        embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        query_embedding = embedding_model.embed_query(email_body)

        # Query with the embedding, not raw text
        results = vector_store.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=["documents"]
        )

        documents = results.get('documents', [[]])[0]  # fallback to empty list if missing

        if not documents:
            return "Sorry, I couldn't find any relevant information."

        context = "\n\n".join(documents)

        prompt = f"""
        You are a friendly and knowledgeable customer support agent for LG Washing Machines.

        Your job is to help customers by answering their questions using the content below from the LG Washing Machine Manual.

        Respond clearly, confidently, and naturally — like a helpful human agent. 
        You must not mention whether information is or isn’t present in the manual. 
        Never say things like "the manual doesn’t mention", "not detailed", "not found", or "based on the manual".
        Instead, always provide a helpful, complete, and polite response using what you know from the context and your general understanding.
        At the end add contact information.
        --- LG Washing Machine Manual Content ---
        {context}

        CUSTOMER QUERY:
        {email_body}
        """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response_text = generate_response_with_retry(model, prompt)
        return response_text

    except Exception as e:
        print(f"Error in generate_manual_response: {str(e)}")
        return "I apologize, but I'm having trouble generating a response at the moment. Please try again later."

def classify_with_gemini(subject, body):
    """Classifies email as inquiry, support, or grievance using Gemini."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are an email classifier. Categorize the following email into one of these categories:
    - inquiry
    - support
    - grievance

    Return only the category name (e.g., 'inquiry').

    Subject: {subject}
    Body: {body}
    """

    try:
        response = model.generate_content(prompt)
        category = response.text.strip().lower()

        if category not in ["inquiry", "support", "grievance"]:
            return "unknown"

        return category
    except Exception as e:
        print(f"Error in classify_with_gemini: {str(e)}")
        return "error"
