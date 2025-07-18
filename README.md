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

Create a PyQt5 desktop application named `retail_support_bot.py` for an offline knowledge base chatbot, replicating the exact functionality of a previous app (artifact ID `e36e43a5-9416-4373-b075-263e17113549`). The app must support `.pdf`, `.docx`, and `.txt` files, use `PyMuPDF` (`fitz`) for PDF image extraction (no `poppler` or other external dependencies beyond Python packages), run offline after setup, and be compatible with Python 3.13. Use `PyQt5`, `tinydb`, `fuzzywuzzy`, `python-Levenshtein`, `pdfplumber`, `python-docx`, `nltk`, `pillow`, and `PyMuPDF` for document processing. Below are the requirements:

### Core Features
1. **Chat Interface**:
   - Use `QMainWindow` with minimum size 800x500, title "Retail Support Bot - Knowledge Base Chatbot".
   - `QTabWidget` with 5 tabs: Chat, FAQ Management, Synonym Management, Chat History, Documents.
   - Chat tab:
     - Left sidebar (`QScrollArea`, width=200) with clickable FAQ buttons (`QPushButton`).
     - Main area (`QVBoxLayout`):
       - Filters (`QHBoxLayout`): `QComboBox` for tags (NLTK-generated), filetypes (“All”, “pdf”, “docx”, “txt”), `QCheckBox` for “Regex Search” and “Case Sensitive”, `QComboBox` for regex presets (“Custom”, “Email: \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b”, “Phone: \b\d{3}-\d{3}-\d{4}\b”).
       - Results (`QTextEdit`, read-only, `Helvetica 10`, height=10 lines, HTML with bolded keywords, line numbers for regex).
       - Image gallery (`QScrollArea`, height=100, 80x80 thumbnails in `QHBoxLayout`).
       - Chatbox (`QHBoxLayout`): `QLineEdit` (600px, `Helvetica 12`), Send/Clear `QPushButton`. Enter key triggers search.
   - Responsive `QVBoxLayout`/`QHBoxLayout` to prevent text cutoff.

2. **Search**:
   - Fuzzy search (`fuzzywuzzy`, threshold 70%) with synonym expansion (`synonyms.json`).
   - Regex search with case-sensitive toggle and presets (via `QComboBox`).
   - Filter by tags (`QComboBox`, top 5 NLTK words + filename) and filetype.
   - Display results in `QTextEdit` with filename, score, tags, line numbers (regex only), bolded keywords.
   - Show associated images in gallery, clickable to open zoomable `QDialog`.

3. **Image Display/Zoom**:
   - Extract images from PDFs (using `PyMuPDF`) and `.docx` (`python-docx`) to `images/` (`<uuid>_imgX.png`). No images from `.txt`.
   - Display thumbnails in `QScrollArea` (`QLabel`, 80x80).
   - Zoomable `QDialog` (600x400) with `QScrollArea`, `QLabel` for image, `QSlider` (50–200% zoom), mouse wheel zoom (0.5x–2x), and drag-to-pan.

4. **Dark Mode**:
   - Toggle via `QToolBar` action using QSS.
   - Light theme: `#f4f4f9` background, `#007bff` buttons, `#ffffff` inputs.
   - Dark theme: `#2d2d2d` background, `#1e90ff` buttons, `#3c3c3c` inputs.
   - `Helvetica` fonts (10pt for `QTextEdit`/`QTreeView`, 11pt for `QWidget`, 12pt for titles/chatbox).

5. **Document Indexing**:
   - Index `.pdf` (sentences >20 chars via `pdfplumber`), `.docx` (paragraphs via `python-docx`), `.txt` (lines) from `docs/` (batch) or `QFileDialog` (single).
   - Generate tags using NLTK (`word_tokenize`, `stopwords`, top 5 words + filename).
   - Store in `data/knowledge_db.json` with `filename`, `filetype` (“pdf”, “docx”, “txt”), `text`, `tags`, `image_paths`.
   - Show `QProgressBar` in status bar for batch indexing.
   - Check for duplicates with `QMessageBox` warning.

6. **FAQ Management**:
   - `QTreeView` with `QStandardItemModel` (`question`, `answer` columns, 300px/400px).
   - Add/edit/delete FAQs (`QLineEdit` for inputs, `QPushButton` for add, context menu for edit/delete).
   - Store in `data/support_bot_db.json`.

7. **Synonym Management**:
   - `QTreeView` with `QStandardItemModel` (single column: “key: word1, word2, ...”).
   - Add/edit/delete groups (`QLineEdit` for comma-separated words, `QPushButton` for add, context menu for edit/delete).
   - Store in `data/synonyms.json`.

8. **Chat History**:
   - `QTreeView` with `QStandardItemModel` (single column: queries).
   - Filter with `QLineEdit`, re-run on double-click, export to `chat_transcript.txt`, clear history.

9. **Document Deletion**:
   - `QTreeView` with `QStandardItemModel` (single column: filenames).
   - Delete with `QPushButton`, confirm via `QMessageBox`, remove from `knowledge_db.json` and `images/`.

10. **Toolbar**:
    - `QToolBar` with actions: Index Documents, Upload Document, Toggle Dark Mode.

### Implementation Details
- **Directory Structure**:
  ```
  retail_support_bot/
  ├── data/
  │   ├── knowledge_db.json    # Indexed paragraphs
  │   ├── support_bot_db.json  # FAQs
  │   ├── synonyms.json        # Synonym groups
  ├── docs/                    # .pdf/.docx/.txt files
  ├── images/                  # Extracted images
  ├── retail_support_bot.py    # Main app
  ├── chat_transcript.txt      # Chat history
  ├── README.md
  ```
- **Dependencies**:
  ```bash
  pip install PyQt5 tinydb fuzzywuzzy python-Levenshtein pdfplumber python-docx nltk pillow PyMuPDF
  ```
  - Download NLTK data (once, requires internet):
    ```python
    import nltk
    nltk.download('punkt')
    nltk.download('stopwords')
    ```
- **PDF Image Extraction**:
  - Use `PyMuPDF` (`fitz`) to extract images from PDFs to `images/` as PNGs. Example:
    ```python
    import fitz
    doc = fitz.open(file_path)
    image_paths = []
    for page in doc:
        for img in page.get_images():
            xref = img[0]
            base_image = doc.extract_image(xref)
            with open(f"images/{doc_id}_img{len(image_paths)}.png", "wb") as f:
                f.write(base_image["image"])
            image_paths.append(f"images/{doc_id}_img{len(image_paths)}.png")
    ```
- **Text File Support**:
  - Read `.txt` files line-by-line, treat each line as a paragraph. Example:
    ```python
    def extract_from_txt(self, file_path: str) -> dict:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return {"text": text, "image_paths": []}
    def extract_txt_paragraphs(self, file_path: Path) -> list:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    ```
  - Update `batch_index` and `upload_document` to handle `.txt` (filetype: “txt”).
  - Update `filetype_combo` to include “txt”.
- **Logic Reuse**:
  - Retain non-UI logic (e.g., `extract_from_pdf`, `search`, `generate_tags`) from artifact ID `e36e43a5-9416-4373-b075-263e17113549`, adapting only for `.txt` support and `PyMuPDF` image extraction.
  - Use `pdfplumber` for PDF text, `python-docx` for `.docx` text, `PyMuPDF` for PDF images.
- **UI Implementation**:
  - Use `QVBoxLayout`/`QHBoxLayout` for responsive UI.
  - `QTextEdit` for HTML-formatted results (bolded keywords, line numbers).
  - `QScrollArea` for FAQ sidebar (width=200) and image gallery (height=100, 80x80 thumbnails).
  - `QTreeView` with `QStandardItemModel` for FAQs (`question`, `answer`), synonyms (`group`), history (`query`), documents (`filename`).
  - `QToolBar` for Index, Upload, Toggle Theme actions.
- **Error Handling**:
  - Use `QMessageBox` for invalid regex, duplicate files, and deletion confirmation.
  - Log errors with `logging` module (level: INFO).
- **Image Handling**:
  - Check `QPixmap.isNull()` in `display_images` to handle invalid images.
  - Store images in `images/` as `<uuid>_imgX.png`.

### UI/UX Requirements
- Ensure chatbox/buttons always visible (bottom of Chat tab).
- Responsive layouts to handle window resizing and multilingual text.
- Native look-and-feel across Windows, macOS, Linux.
- Smooth scrolling for FAQ sidebar, results, image gallery.
- Use `Helvetica` fonts (10pt for `QTextEdit`/`QTreeView`, 11pt for `QWidget`, 12pt for titles/chatbox).
- Error handling for file processing, regex, and image loading.

### Deliverables
- `retail_support_bot.py`: Main app with all features, artifact ID `e36e43a5-9416-4373-b075-263e17113549`.
- `README.md`: Setup instructions, usage guide, dependency list, directory structure.
- Ensure offline operation after NLTK setup.
- Test for Python 3.13 compatibility, PyQt5 GPL license.

### Testing
- Verify chat interface: `QLineEdit` (600px), buttons visible, Enter key triggers search.
- Test regex search: presets (Email, Phone), case-sensitive toggle, line numbers in `QTextEdit`.
- Test image zoom: Click thumbnails, verify `QSlider`, mouse wheel, panning in `QDialog`.
- Test dark mode: Toggle via `QToolBar`, check QSS consistency.
- Test indexing/deletion: `QProgressBar` for batch, `QMessageBox` for duplicates/deletions, verify `.txt` support.
- Test tabs: Navigate `QTabWidget`, verify `QTreeView` for FAQs, synonyms, history, documents.
- Test offline: Disconnect internet post-setup, confirm functionality.

### Notes
- Use `PyMuPDF` for PDF image extraction to avoid external dependencies like `poppler`.
- Retain artifact ID `e36e43a5-9416-4373-b075-263e17113549` for continuity.
- Include all features from the original app, adding only `.txt` support and `PyMuPDF` integration.
- For commercial use, consider PySide2 (LGPL) by replacing `PyQt5` imports.
