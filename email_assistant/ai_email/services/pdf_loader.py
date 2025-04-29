from pdf2image import convert_from_path
import pytesseract
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

def load_manual(pdf_path):
    print(f"Loading manual from: {pdf_path}")

    text = ""

    try:
        # (for normal PDFs)
        print("Attempting direct text extraction using PyMuPDF...")
        with fitz.open(pdf_path) as pdf:
            for i in range(pdf.page_count):
                page = pdf.load_page(i)
                page_text = page.get_text("text")  # Extract text from the page
                if page_text:
                    text += page_text + "\n"

        # Check if text is extracted successfully from normal PDFs
        if text.strip():
            print("Direct text extraction successful using PyMuPDF.")
        else:
            raise ValueError("No text found in the normal PDF. Trying OCR.")

    except Exception as e:
        print(f"Direct extraction failed due to: {str(e)}. Falling back to OCR...")

        # Use OCR for scanned PDFs (or when normal text extraction fails)
        images = convert_from_path(pdf_path)
        for image in images:
            page_text = pytesseract.image_to_string(image)
            text += page_text + "\n"

        if not text.strip():
            raise ValueError("OCR also failed to extract any text.")

        print("OCR extraction successful.")

    # Split the extracted text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.create_documents([text], metadatas=[{"source": pdf_path}])

    print(f"Extracted {len(chunks)} chunks.")
    return chunks
