#!/bin/sh
pip install flask spacy nltk rapidfuzz click --quiet
python3 -m spacy download en_core_web_sm --quiet
python3 -m steeltrap.server
