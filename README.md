# Support Knowledge Bot

## Overview

This is a Tkinter-based support chatbot that uses TinyDB to load a knowledge base extracted from Word (.docx) and PDF (.pdf) documents. It supports fuzzy keyword matching, synonym expansion, tag and file type filtering, chat history, quick FAQ buttons, and keyword highlighting.

## Setup Instructions

### Requirements

- Python 3.7 or newer
- Install dependencies:

```bash
pip install python-docx pdfplumber tinydb nltk fuzzywuzzy python-Levenshtein
```

- Download NLTK stopwords (run once in Python shell):

```python
import nltk
nltk.download('stopwords')
```

### Prepare your documents

- Put your `.docx` and `.pdf` troubleshooting documents in the `docs/` folder.

### Index your documents

Run the `index_documents.py` script to extract paragraphs, generate tags, and create the TinyDB JSON index:

```bash
python index_documents.py
```

### Run the chatbot

Start the chatbot GUI with:

```bash
python support_bot.py
```

## Files

- `index_documents.py` - Script to index your Word/PDF docs into TinyDB JSON.
- `support_bot.py` - The Tkinter GUI chatbot application.
- `synonyms.json` - JSON file containing synonym groups for better matching.
- `docs/` - Folder for your knowledge base documents.
- `data/` - Folder where the TinyDB JSON index is stored.

## Features

- Fuzzy search with synonym expansion.
- Filter by tags and file types.
- Highlighted matched keywords in responses.
- Search history and quick FAQ buttons.
- Export chat to a text file.

---