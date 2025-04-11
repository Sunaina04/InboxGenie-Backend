import chromadb
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .pdf_loader import load_manual
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_embeddings_with_retry(embeddings, text):
    """Generate embeddings with retry logic for handling timeouts"""
    try:
        return embeddings.embed_query(text)
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        raise

def store_manual_embeddings(pdf_path):
    """Generates embeddings for the washing machine manual and stores them in ChromaDB."""
    text_chunks = load_manual(pdf_path)
    
    if not text_chunks:
        raise ValueError("No text chunks were extracted from the PDF.")

    # Initialize ChromaDB client
    chroma_client = chromadb.Client()

    # Create a new collection
    collection_name = "lg_washing_manual"
    new_collection = chroma_client.create_collection(name=collection_name)

    print(f"Collection '{collection_name}' created successfully.")

    # List all collections to verify
    collections = chroma_client.list_collections()
    print("Current collections:", collections)

    # Generate embeddings with timeout handling
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        request_timeout=30  # Set timeout to 30 seconds
    )

    # Debug: Check if embeddings are generated with retry
    try:
        sample_embedding = generate_embeddings_with_retry(embeddings, "Test query")
        if not sample_embedding:
            raise ValueError("Embeddings generation failed.")
    except Exception as e:
        print(f"Failed to generate sample embedding after retries: {str(e)}")
        raise

    # Store vectors in ChromaDB
    vectorstore = Chroma.from_documents(
        text_chunks, embeddings, client=chroma_client, collection_name="lg_washing_manual"
    )

    # return chroma_client, collection_name, vectorstore
    return vectorstore

pdf_path = "ai_email/lg washing machine manual.pdf"
vector_store = store_manual_embeddings(pdf_path) 

