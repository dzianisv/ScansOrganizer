#!/usr/bin/env python3

import argparse
import os
from typing import Optional

from PIL import Image
import pytesseract

# LangChain imports
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


# 1) Define a Pydantic schema to describe the structured output we expect.
#    We now include fields for renaming the file, a date, type, and some short summary info.
class DocumentClassification(BaseModel):
    new_document_name: str = Field(
        ...,
        description="A new filename for the document, including an extension (e.g., 'my_contract.pdf' or 'receipt_2023.png')"
    )
    document_date: Optional[str] = Field(
        None,
        description="The date of the document (e.g. '2023-10-05' or '5 October 2023')."
    )
    document_type: str = Field(
        ...,
        description="Type of the document (e.g. 'contract', 'receipt', 'application', etc.)."
    )
    short_document_info: str = Field(
        ...,
        description="Short summary of the document. For a receipt, could be merchant name, total. For a contract, the title or agreement summary."
    )


# 2) Create an instance of the parser
parser = PydanticOutputParser(pydantic_object=DocumentClassification)


# 3) Create the system message prompt
system_template = """\
You are a helpful assistant that classifies text documents. 
You will output JSON that follows the provided schema exactly, without any extra keys.

Schema:
{schema}
"""

# 4) Create the user (human) prompt
human_template = """\
Classify the following text. Provide:
- A new filename for the document (include an extension).
- The date of the document, if known.
- The document type (contract, receipt, application, etc.).
- A short summary of the document:
    - If it's a receipt, include merchant name, total, or other relevant info.
    - If it's a contract, include a short agreement summary or contract title.
    - If it's an application, provide any short summary that's relevant.

Text:
```
{document_text}
```
"""

# 5) Build the complete prompt template
system_message_prompt = SystemMessagePromptTemplate.from_template(
    system_template
)
human_message_prompt = HumanMessagePromptTemplate.from_template(
    human_template
)
chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])


def classify_document(text: str, llm) -> DocumentClassification:
    """
    Send the extracted text to the LLM for classification using a structured output parser.
    """
    # Format the prompt with the schema instructions & the document text
    messages = chat_prompt.format_messages(
        schema=parser.get_format_instructions(), 
        document_text=text
    )

    # 1) Get raw response from the LLM
    response = llm(messages)
    
    # 2) Parse the response into our Pydantic model
    parsed_result: DocumentClassification = parser.parse(response.content)
    return parsed_result


def main():
    parser_arg = argparse.ArgumentParser(
        description="Classify documents using Tesseract OCR + LangChain"
    )
    parser_arg.add_argument("images", nargs="+", help="List of image paths to process")
    args = parser_arg.parse_args()

    # Replace with your chosen model & pass your API key if needed
    # For example:
    # llm = ChatOpenAI(openai_api_key="YOUR_API_KEY", temperature=0)
    llm = ChatOpenAI(temperature=0)

    for image_path in args.images:
        if not os.path.isfile(image_path):
            print(f"File not found: {image_path}")
            continue
        
        # 1) OCR - Extract text from the image
        try:
            # curl -o /opt/homebrew/share/tessdata/rus.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata
            text_extracted = pytesseract.image_to_string(Image.open(image_path), lang='rus')
            print(f"\n--- OCR Result for {image_path} ---\n{text_extracted}\n")
        except Exception as e:
            print(f"Could not perform OCR on {image_path}: {e}")
            continue
        
        # 2) Classification via LLM - parse structured output
        try:
            classification_result = classify_document(text_extracted, llm=llm)
            print(f"--- Classification for {image_path} ---")
            print(classification_result.json(indent=2))

            # 3) Rename the file based on 'new_document_name'
            #    This is optional. If you don't want to rename the file, skip this part.
            directory = os.path.dirname(image_path)
            new_path = os.path.join(directory, classification_result.new_document_name)
            
            # Avoid overwriting an existing file inadvertently
            if os.path.exists(new_path):
                print(f"** Warning: {new_path} already exists. Skipping rename.")
            else:
                os.rename(image_path, new_path)
                print(f"Renamed '{image_path}' to '{new_path}'")

        except Exception as e:
            print(f"Classification failed for {image_path}: {e}")


if __name__ == "__main__":
    main()

