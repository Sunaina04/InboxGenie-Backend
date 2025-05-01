import os
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .pdf_loader import load_manual
import chromadb

# Persistent DB path
DB_PATH = "./chroma_db"
client = chromadb.PersistentClient(path=DB_PATH)

def load_vector_store(collection_name):
    existing_collections = client.list_collections()

    if collection_name not in existing_collections:
        raise ValueError(f"Collection {collection_name} does not exist.")

    collection = client.get_collection(collection_name)
    return collection

def store_manual_embeddings(pdf_path, user_id, manual_id):
    """Generates embeddings and stores them persistently using ChromaDB."""
    collection_name = f"user_{user_id}_manual_{manual_id}"

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
def delete_manual_embeddings(user_id, manual_id):
    """Deletes the ChromaDB collection for the given manual."""
    collection_name = f"user_{user_id}_manual_{manual_id}"
    
    try:
        existing_collections = client.list_collections()
        if collection_name in existing_collections:
            client.delete_collection(name=collection_name)
            print(f"Deleted embeddings collection: {collection_name}")
            return True
        else:
            print(f"Collection '{collection_name}' does not exist.")
            return False
    except Exception as e:
        print(f"Failed to delete collection '{collection_name}': {str(e)}")
        raise

# pdf_path = "ai_email/lg washing machine manual.pdf"
# vector_store = store_manual_embeddings(pdf_path)
