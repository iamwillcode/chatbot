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


Create a Tkinter desktop application named `retail_support_bot_tk.py` for an offline knowledge base chatbot, replicating the functionality of a previous PyQt5 app (artifact ID `e36e43a5-9416-4373-b075-263e17113549`). The app must support `.pdf`, `.docx`, and `.txt` files, use `PyMuPDF` (`fitz`) for PDF image extraction (no `poppler` or external dependencies beyond Python packages), run offline after setup, and be compatible with Python 3.13. Use `tkinter`, `ttk`, `tinydb`, `fuzzywuzzy`, `python-Levenshtein`, `pdfplumber`, `python-docx`, `nltk`, `pillow`, and `PyMuPDF`. Below are the requirements:

### Core Features
1. **Chat Interface**:
   - Use `tk.Tk` with minimum size 800x500, title "Retail Support Bot - Knowledge Base Chatbot".
   - `ttk.Notebook` with 5 tabs: Chat, FAQ Management, Synonym Management, Chat History, Documents.
   - Chat tab:
     - Left sidebar (`tk.Canvas`, width=200, with `ttk.Scrollbar`) for FAQ buttons (`ttk.Button`).
     - Main area (`ttk.Frame`, `grid` layout):
       - Filters: `ttk.Combobox` for tags (NLTK-generated), filetypes (“All”, “pdf”, “docx”, “txt”), `ttk.Checkbutton` for “Regex Search” and “Case Sensitive”, `ttk.Combobox` for regex presets (“Custom”, “Email: \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b”, “Phone: \b\d{3}-\d{3}-\d{4}\b”).
       - Results: `tk.Text` (read-only, `Helvetica 10`, height=10 lines, HTML with `<b>` for keywords, `<i>` for line numbers, scrollbar).
       - Image gallery: `tk.Canvas` (height=100, `ttk.Scrollbar`, horizontal) with 80x80 thumbnails (`ttk.Label` with `ImageTk.PhotoImage`).
       - Chatbox: `ttk.Entry` (width=60, `Helvetica 12`), Send/Clear `ttk.Button`. Enter key triggers search.
   - Responsive `grid` layout to prevent text cutoff.

2. **Search**:
   - Fuzzy search (`fuzzywuzzy`, threshold 70%) with synonym expansion (`synonyms.json`).
   - Regex search with case-sensitive toggle and presets.
   - Filter by tags (`ttk.Combobox`, top 5 NLTK words + filename) and filetype.
   - Display results in `tk.Text` with filename, score, tags, line numbers (regex only), bolded keywords (HTML `<b>`).
   - Show images in gallery, clickable to open zoomable `tk.Toplevel`.

3. **Image Display/Zoom**:
   - Extract images from PDFs (`PyMuPDF`) and `.docx` (`python-docx`) to `images/` (`<uuid>_imgX.png`). No images from `.txt`.
   - Display thumbnails in `tk.Canvas` (`ttk.Label`, 80x80, `ImageTk.PhotoImage`).
   - Zoomable `tk.Toplevel` (600x400) with `tk.Canvas`, `ttk.Scrollbar` (horizontal/vertical), `ttk.Scale` (50–200% zoom), mouse wheel zoom (0.5x–2x), and drag-to-pan.

4. **Theme**:
   - Toggle light (`#f4f4f9` background, `#007bff` buttons, `#ffffff` entries) and dark (`#2d2d2d` background, `#1e90ff` buttons, `#3c3c3c` entries) themes via `ttk.Style` and widget configs.
   - Use `Helvetica` fonts (10pt for `tk.Text`/`ttk.Treeview`, 11pt for `ttk.Label`/`ttk.Button`, 12pt for titles/`ttk.Entry`).
   - Menu bar (`tk.Menu`) with Index Documents, Upload Document, Toggle Theme.

5. **Document Indexing**:
   - Index `.pdf` (sentences >20 chars via `pdfplumber`), `.docx` (paragraphs via `python-docx`), `.txt` (lines) from `docs/` (batch) or `filedialog` (single).
   - Generate tags using NLTK (`word_tokenize`, `stopwords`, top 5 words + filename).
   - Store in `data/knowledge_db.json` with `filename`, `filetype` (“pdf”, “docx”, “txt”), `text`, `tags`, `image_paths`.
   - Show `ttk.Progressbar` for batch indexing.
   - Check duplicates with `messagebox.showwarning`.

6. **FAQ Management**:
   - `ttk.Treeview` (`Question`, `Answer` columns, 300px/400px).
   - Add/edit/delete FAQs (`ttk.Entry` for inputs, `ttk.Button` for add, right-click menu for edit/delete).
   - Store in `data/support_bot_db.json`.

7. **Synonym Management**:
   - `ttk.Treeview` (single column: “key: word1, word2, ...”).
   - Add/edit/delete groups (`ttk.Entry` for comma-separated words, `ttk.Button` for add, right-click menu for edit/delete).
   - Store in `data/synonyms.json`.

8. **Chat History**:
   - `ttk.Treeview` (single column: queries).
   - Filter with `ttk.Entry`, re-run on double-click, export to `chat_transcript.txt`, clear history.

9. **Document Deletion**:
   - `ttk.Treeview` (single column: filenames).
   - Delete with `ttk.Button`, confirm via `messagebox.askyesno`, remove from `knowledge_db.json` and `images/`.

10. **Menu Bar**:
    - `tk.Menu` with actions: Index Documents, Upload Document, Toggle Theme.

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
  ├── retail_support_bot_tk.py # Main app
  ├── chat_transcript.txt      # Chat history
  ├── README.md
  ```
- **Dependencies**:
  ```bash
  pip install tinydb fuzzywuzzy python-Levenshtein pdfplumber python-docx nltk pillow PyMuPDF
  ```
  - Download NLTK data (once, requires internet):
    ```python
    import nltk
    nltk.download('punkt')
    nltk.download('stopwords')
    ```
- **PDF Image Extraction**:
  - Use `PyMuPDF` (`fitz`) for PDF images to `images/` as PNGs. Example:
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
  - Retain non-UI logic (e.g., `extract_from_pdf`, `search`, `generate_tags`) from artifact ID `e36e43a5-9416-4373-b075-263e17113549`, adapting for `.txt` and `PyMuPDF`.
  - Use `pdfplumber` for PDF text, `python-docx` for `.docx` text, `PyMuPDF` for PDF images.
- **UI Implementation**:
  - Use `grid` for responsive layout.
  - `tk.Text` for HTML results (bolded keywords via `<b>`, line numbers via `<i>`).
  - `tk.Canvas` with `ttk.Scrollbar` for FAQ sidebar (width=200) and image gallery (height=100, 80x80 thumbnails).
  - `ttk.Treeview` for FAQs (`Question`, `Answer`), synonyms (`Group`), history (`Query`), documents (`Filename`).
  - `tk.Menu` for Index, Upload, Toggle Theme.
- **Error Handling**:
  - Use `messagebox` for invalid regex, duplicates, and deletion confirmation.
  - Log errors with `logging` (level: INFO).
  - Check `Image.open` for valid images in `display_images`.
- **Image Handling**:
  - Use `ImageTk.PhotoImage` for thumbnails, keep references to prevent garbage collection.
  - Store images in `images/` as `<uuid>_imgX.png`.

### UI/UX Requirements
- Ensure chatbox/buttons always visible (bottom of Chat tab).
- Responsive `grid` layout for resizing and multilingual text.
- Native look-and-feel across Windows, macOS, Linux.
- Smooth scrolling for FAQ sidebar, results, image gallery.
- Use `Helvetica` fonts (10pt for `tk.Text`/`ttk.Treeview`, 11pt for `ttk.Label`/`ttk.Button`, 12pt for titles/`ttk.Entry`).
- Error handling for file processing, regex, and image loading.

### Deliverables
- `retail_support_bot_tk.py`: Main app with all features, artifact ID `e36e43a5-9416-4373-b075-263e17113549`.
- `README.md`: Setup instructions, usage guide, dependency list, directory structure.
- Ensure offline operation after NLTK setup.
- Test for Python 3.13 compatibility, Tkinter (Python standard library).

### Testing
- Verify chat interface: `ttk.Entry` (width=60), buttons visible, Enter key triggers search.
- Test regex search: presets (Email, Phone), case-sensitive toggle, line numbers in `tk.Text`.
- Test image zoom: Click thumbnails, verify `ttk.Scale`, mouse wheel, panning in `tk.Toplevel`.
- Test theme: Toggle via menu, check `ttk.Style` consistency.
- Test indexing/deletion: `ttk.Progressbar` for batch, `messagebox` for duplicates/deletions, verify `.txt` support.
- Test tabs: Navigate `ttk.Notebook`, verify `ttk.Treeview` for FAQs, synonyms, history, documents.
- Test offline: Disconnect internet post-setup, confirm functionality.

### Notes
- Use `PyMuPDF` for PDF image extraction to avoid external dependencies.
- Retain artifact ID `e36e43a5-9416-4373-b075-263e17113549` for continuity.
- Include all features from the original PyQt5 app, with `.txt` support and `PyMuPDF`.
