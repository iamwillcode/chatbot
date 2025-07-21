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

#Prompt to make app

Prompt:



Below is a concise list of recommended changes to improve your offline knowledge base app, focusing on enabling the display of images embedded in documents (PDFs and DOCX files) and enhancing overall functionality, while keeping the app offline and dependency-free for end users. These recommendations incorporate the suggestions for handling embedded images and additional improvements for usability, performance, and robustness.

Extract Embedded Images from Documents
Modify the extract_text function to extract images from PDFs (using PyMuPDF) and DOCX files (using python-docx), saving them to the img_folder with unique names (e.g., docname_pageX_imgY.png).
Return both text and a list of image filenames from extract_text.
Store Image References in Database
Update add_document and scan_folder to store the list of extracted image filenames in the TinyDB database alongside document metadata (name, content, tags).
Ensure database entries include an "images" field for embedded images.
Display Embedded Images in GUI
Modify the show_image method to prioritize displaying embedded images stored in the database’s "images" field.
Fallback to existing logic for external images (e.g., docname.jpg in img_folder) if no embedded images exist.
Optionally, add "Prev" and "Next" buttons to cycle through multiple embedded images, with a status bar indicating the current image (e.g., "Image 1 of 3").
Clean Up Images on Document Deletion
Update the delete_document method to remove associated embedded images from img_folder when a document is deleted, in addition to external images.
Improve User Interface
Change the red background (self.root.configure(bg="red")) to a neutral color (e.g., #f0f0f0) or use a ttk theme (e.g., clam) for a modern look.
Make the app resizable with proportional frame resizing using self.root.resizable(True, True) and pack_propagate(False).
Add a status bar to display messages (e.g., "Added docname with 2 images") using ttk.Label with a StringVar.
Add a right-click context menu to the document listbox for deleting documents.
Enhance Search Functionality
Add a tag filter dropdown (ttk.Combobox) to search by specific tags, populated with unique tags from the database.
Cache TF-IDF vectors in TinyDB to improve tag generation and search performance (store as pickled objects).
Support Additional File Types
Add support for .md files using the markdown library (if bundled) to extract text, updating extract_text and file dialogs.
Improve Image Handling
Allow manual association of external images with documents via a new "Associate Image" menu option.
Use a tk.Canvas for image display to enable zooming/panning for large images.
Enhance Performance and Robustness
Add try-except blocks in add_document and scan_folder to handle file operation errors and show user-friendly messages via messagebox.showerror.
Process large documents in a separate thread using threading to keep the GUI responsive.
Use TinyDB’s table feature (e.g., db.table("documents")) to optimize database queries.
Add Accessibility Features
Implement keyboard shortcuts (e.g., Ctrl+O for adding documents, Ctrl+F for search focus).
Add a high-contrast theme toggle in the menu for accessibility.
Provide User Guidance
Add a "Help" menu with a messagebox.showinfo displaying basic instructions (e.g., how to add documents, search, or delete).
Optimize Storage (Optional)
Store embedded images as base64 strings in TinyDB instead of files in
