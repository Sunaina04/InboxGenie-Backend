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
            return "Sorry, I couldn't find any relevant information in the manual."

        context = "\n\n".join(documents)

        prompt = f"""
        You are a friendly and knowledgeable customer support agent working,
        the official service provider for LG Washing Machines.

        Your job is to help customers by answering their questions using the information provided
        in the LG Washing Machine Manual.

        Respond naturally, like a human would — polite, clear, and conversational.
        Base your answers only on the content provided below.
        If something isn’t directly mentioned, respond in a helpful way using your best judgment,
        without saying that the information is missing.

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
