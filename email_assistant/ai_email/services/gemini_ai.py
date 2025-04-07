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
        You are a customer support assistant for a washing machine company.
        Use the following manual information to provide a professional response.
        use manual information to answer the customer query. Extract company name and product description from manual.  
        use company name as ACC PVT. LTD. 
        
        MANUAL INFORMATION:
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
