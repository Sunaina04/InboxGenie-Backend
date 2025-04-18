import os
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .pdf_loader import load_manual
import chromadb

# Persistent DB path
DB_PATH = "./chroma_db"
client = chromadb.PersistentClient(path=DB_PATH)

def store_manual_embeddings(pdf_path):
    """Generates embeddings and stores them persistently using ChromaDB."""
    collection_name = "lg_washing_manual"

    # In Chroma v0.6.0+, this returns just a list of collection names
    existing_collections = client.list_collections()
    if collection_name in existing_collections:
        print(f"Collection '{collection_name}' already exists. Loading existing embeddings...")
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),
            client=client
        )
        return vectorstore

    # Load text
    text_chunks = load_manual(pdf_path)
    if not text_chunks:
        raise ValueError("No text chunks were extracted from the PDF.")

    # Generate embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # Store to Chroma
    vectorstore = Chroma.from_documents(
        text_chunks,
        embeddings,
        client=client,
        collection_name=collection_name
    )

    print(f"Embeddings stored in collection '{collection_name}'.")
    return vectorstore

pdf_path = "ai_email/lg washing machine manual.pdf"
vector_store = store_manual_embeddings(pdf_path)
