#!/usr/bin/env python3

import argparse
import os
from typing import Optional
import logging

from PIL import Image
import pytesseract
import PyPDF2
from pdf2image import convert_from_path

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from langchain.chat_models import init_chat_model

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Pydantic
class ScannedDocumentMetadata(BaseModel):
    """Classified scanned document"""
    type: str = Field(description="type of the document: contract, application, receipt, mail, bill")
    merchant: Optional[str] = Field(description="For receipts and bills include the merchant name")
    place: Optional[str] = Field(description="Place where this document was created, if presented")
    date: Optional[str] = Field(description="Date in format YYYY-MM-DD when this document was created", optional=True)
    total: Optional[float] = Field(description="Total amount of the receipt", optional=True)
    sumary: str = Field(description="short summary of the document")
    short_description: str = Field(description="short 3 wordsdescription of the document")
    currency: Optional[str] = Field(description="Currency code (USD, EUR, RUB, etc.) that was used in the document", optional=True)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from the first three pages of a PDF, using OCR if necessary."""
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = min(3, len(reader.pages))
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                print(page_num, page_text)
                if page_text:
                    text += page_text
                else:
                    # Use pdf2image to convert page to image
                    images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
                    for image in images:
                        ocr_text = pytesseract.image_to_string(image, lang='eng')
                        text += ocr_text
    except Exception as e:
        logger.error(f"Could not extract text from PDF {pdf_path}: {e}")
    return text

def main():
    parser_arg = argparse.ArgumentParser(
        description="Classify documents using Tesseract OCR + LangChain (structured output)."
    )
    parser_arg.add_argument("documents", nargs="+", help="List of document paths to process")
    args = parser_arg.parse_args()

    llm = init_chat_model("gpt-4o-mini", model_provider="openai")

    for document_path in args.documents:
        if not os.path.isfile(document_path):
            logger.info(f"File not found: {document_path}")
            continue

        text_extracted = ""
        if document_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            try:
                text_extracted = pytesseract.image_to_string(Image.open(document_path), lang='eng')
                logger.info(f"OCR result for {document_path}:{text_extracted}")
            except Exception as e:
                logger.error(f"Could not perform OCR on {document_path}: {e}")
                continue
        elif document_path.lower().endswith('.pdf'):
            text_extracted = extract_text_from_pdf(document_path)
            logger.info(f"PDF text extraction result for {document_path}:{text_extracted}")

        try:
            model_with_structured_output = llm.with_structured_output(ScannedDocumentMetadata)
            classification_result = model_with_structured_output.invoke(f"Classify the following scanned document text\n<text>{text_extracted}</text>")
            logger.info(f"{classification_result}")

            _, file_extension = os.path.splitext(document_path)
            if classification_result.type == "receipt":
                new_filename = f"{classification_result.date}_{classification_result.type}_{classification_result.merchant}_{classification_result.place}_{classification_result.total}{classification_result.currency}{file_extension}"
            else:
                new_filename = f"{classification_result.date}_{classification_result.type}_{classification_result.short_description}{file_extension}"

            if new_filename:
                directory = os.path.dirname(document_path)
                new_path = os.path.join(directory, new_filename)
                
                if os.path.exists(new_path):
                    logger.info(f"Warning: {new_path} already exists. Skipping rename.")
                else:
                    os.rename(document_path, new_path)
                    logger.info(f"Renamed '{document_path}' to '{new_path}'")
            else:
                logger.info("No 'new_document_name' found. Skipping rename.")

        except Exception as e:
            logger.error(f"Classification failed for {document_path}: {e}")
            logger.exception(e)


if __name__ == "__main__":
    main()
