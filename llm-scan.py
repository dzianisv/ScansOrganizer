#!/usr/bin/env python3

import argparse
import os
from typing import Optional
import logging

from PIL import Image
import pytesseract

# LangChain imports
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Pydantic
class ScannedDocumentMetadata(BaseModel):
    """Classified scanned document"""
    file_name: str = Field(description="A document file name without extension. Includes the date if preseneted in the document text, type of document, short summary of document and place.")
    type: str = Field(description="type of the document: contract, application, receipt, mail, bill")
    merchant: Optional[str] = Field(description="For receipts and bills include the merchant name")
    place: Optional[str] = Field(description="Place where this document was created, if presented")
    date: Optional[datetime] = Field(description="Date and time when this document was created")
    total: Optional[float] = Field(description="Total amount of the receipt")
    sumary: str = Field(description="short summary of the document")

def main():
    parser_arg = argparse.ArgumentParser(
        description="Classify documents using Tesseract OCR + LangChain (structured output)."
    )
    parser_arg.add_argument("images", nargs="+", help="List of image paths to process")
    args = parser_arg.parse_args()

    # Instantiate your LLM (OpenAI GPT, for example). 
    # Adjust the model name if needed, e.g. "gpt-3.5-turbo" or "gpt-4".
    # Make sure your environment variable OPENAI_API_KEY is set if needed.
    llm = ChatOpenAI(
        temperature=0,
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        model_name="gpt-4o"
    )


    for image_path in args.images:
        if not os.path.isfile(image_path):
            logger.info(f"File not found: {image_path}")
            continue

        try:
            # Example: using Russian (lang='rus'), change to 'eng' or other if needed
            text_extracted = pytesseract.image_to_string(Image.open(image_path), lang='rus')
            logger.info(f"OCR result for {image_path}:{text_extracted}")
        except Exception as e:
            logger.error(f"Could not perform OCR on {image_path}: {e}")
            continue

        try:
            # it doesn't work for some reason https://genai.stackexchange.com/questions/2188/llm-with-structured-output-notimplementederror
            model_with_structured_output = llm.with_structured_output(ScannedDocumentMetadata)
            classification_result = model_with_structured_output.invoke(f"Classify the following scanned document text\n<text>{text_extracted}</text>")
            print(classification_result)

            logger.info(f"{classification_result}")

            # 3) Rename the file based on 'new_document_name' (optional)
            new_filename = classification_result.get("new_document_name")
            if new_filename:
                directory = os.path.dirname(image_path)
                new_path = os.path.join(directory, new_filename)
                
                if os.path.exists(new_path):
                    logger.info(f"Warning: {new_path} already exists. Skipping rename.")
                else:
                    os.rename(image_path, new_path)
                    logger.info(f"Renamed '{image_path}' to '{new_path}'")
            else:
                logger.info("No 'new_document_name' found. Skipping rename.")

        except Exception as e:
            logger.error(f"Classification failed for {image_path}: {e}")
            logger.exception(e)


if __name__ == "__main__":
    main()
