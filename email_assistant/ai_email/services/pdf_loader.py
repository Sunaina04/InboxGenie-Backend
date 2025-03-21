from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_manual(pdf_path):
  loader = PyMuPDFLoader(pdf_path)
  docs = loader.load()
  
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
  return text_splitter.split_documents(docs)
