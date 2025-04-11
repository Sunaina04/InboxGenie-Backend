import google.generativeai as genai
from .embeddings import vector_store
from dotenv import load_dotenv
import os
from tenacity import retry, stop_after_attempt, wait_exponential

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

def generate_manual_response(email_body):
    """Searches ChromaDB for relevant manual content and generates an AI response."""
    if not vector_store:
        return "I apologize, but I'm currently unable to access the manual information. Please try again later."
   
    try:
        docs = vector_store.similarity_search(email_body, k=3)  # Fetch top 3 matching sections
        
      
        context = "\n\n".join([doc.page_content for doc in docs])
       
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
    
# def test_manual_search(query="how to clean the washer filter?"):
#     """Test vector store search without generating a full AI response."""
#     if not vector_store:
#         print("Vector store not available.")
#         return

#     try:
#         docs = vector_store.similarity_search(query, k=3)
#         print(f"\nTop {len(docs)} relevant chunks for query: \"{query}\"")
#         for i, doc in enumerate(docs, start=1):
#             print(f"\n--- Chunk #{i} ---")
#             print(doc.page_content[:500])  # Print first 500 chars for preview
#     except Exception as e:
#         print(f"Error during search test: {e}")
# if __name__ == "__main__":
#     test_manual_search("how to clean the washer filter?")
