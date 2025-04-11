from pdf2image import convert_from_path
import pytesseract
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

def load_manual(pdf_path):
    print(f"Loading manual from: {pdf_path} using OCR")
    # Convert PDF pages to images
    images = convert_from_path(pdf_path)
    
    text = ""
    for i, image in enumerate(images):
        page_text = pytesseract.image_to_string(image)
        # print(f"OCR extracted from page {i+1}: {page_text[:100]}...")
        text += page_text + "\n"

    if not text.strip():
        raise ValueError("OCR failed to extract any text.")

    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.create_documents([text], metadatas=[{"source": pdf_path}])
    # print(f"Extracted {len(chunks)} chunks from OCR.")
    return chunks
