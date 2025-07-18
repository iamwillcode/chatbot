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

Explanation for Your Manager
What is this app?
It’s a lightweight, offline chatbot designed to assist support agents by quickly searching through troubleshooting documents (Word, PDF) to find relevant solutions.

How does it work?

It indexes all your existing knowledge base documents into a searchable database.

When you type in a question or issue, the bot uses fuzzy keyword matching to find the most relevant information.

It highlights keywords in the results and allows filtering by topics or file type for faster lookup.

The interface is user-friendly with search history and quick FAQ buttons for common issues.

Why offline?

No dependency on internet connectivity or cloud services, so it’s secure and works anywhere, even without network access.

All data stays on the local machine, ensuring confidentiality.

Can it be updated?

Yes! Adding new troubleshooting documents is as simple as placing them in a folder and running a script that updates the searchable database.

This keeps the knowledge base current without complex retraining or AI model updates.

Benefits for the team:

Speeds up response times by providing immediate access to relevant troubleshooting steps.

Reduces repetitive manual searching across multiple documents.

Easy to maintain and expand with new documents.

No costly AI infrastructure or ongoing cloud fees.
