import google.generativeai as genai
from .embeddings import vector_store
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_manual_response(email_body):
    """Searches ChromaDB for relevant manual content and generates an AI response."""
   
    docs = vector_store.similarity_search(email_body, k=3)  # Fetch top 3 matching sections
    
    # Combine relevant manual sections
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Create a structured prompt
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
    response = model.generate_content(prompt)

    return response.text
