import chromadb
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .pdf_loader import load_manual

def store_manual_embeddings(pdf_path):
    """Generates embeddings for the washing machine manual and stores them in ChromaDB."""
    text_chunks = load_manual(pdf_path)
    
    if not text_chunks:
        raise ValueError("No text chunks were extracted from the PDF.")

    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(path="./chroma_db")

    # Generate embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # Debug: Check if embeddings are generated
    sample_embedding = embeddings.embed_query("Test query")
    if not sample_embedding:
        raise ValueError("Embeddings generation failed.")

    # Store vectors in ChromaDB
    vectorstore = Chroma.from_documents(
        text_chunks, embeddings, client=chroma_client, collection_name="washing_manual"
    )

    return vectorstore


pdf_path = "ai_email/manual.pdf"

vector_store = store_manual_embeddings(pdf_path)

