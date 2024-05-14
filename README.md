## tl;dr

This is automation tool to organize scanned docs. It get's the merchant, amount paid, date from the scanned docs and receipts and rename files appropriately 

## Dev environment


```shell
brew install virtualenv
virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download es_core_news_sm

```