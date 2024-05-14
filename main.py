import sys
import pytesseract
import spacy
from PIL import Image
import dateutil

    
def extract_info(text, nlp):
    doc = nlp(text)
    merchant = None
    amount = None
    date = None
    currency = 'USD'

    for ent in doc.ents:
        print(ent.label_, ent.text)
        if ent.label_ == 'ORG' and not merchant:
            merchant = ent.text.replace(' ', '_')
        elif ent.label_ == 'MONEY' and not amount:
            try:
                amount = float(ent.text)
            except ValueError:
                pass
        elif ent.label_ == 'TIME' and not date:
            date = dateutil.parser.parse(ent.text)

    return date, merchant, amount, currency

def process_receipts(filenames):
    nlp = spacy.load('en_core_web_sm')

    for filename in filenames:
        image = Image.open(filename)
        text = pytesseract.image_to_string(image)
        print(text)
        
        date, merchant, amount, currency = extract_info(text, nlp)
        print(date, merchant, amount, currency)
        new_filename = f'{date.strftime("%Y-%m-%d")}_{merchant}_{amount}_{currency}.jpg'
        # os.rename(filename, new_filename)
        print(f'{filename}: {new_filename}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Please provide receipt image filenames as arguments')
    else:
        process_receipts(sys.argv[1:])