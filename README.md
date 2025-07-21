# Support Knowledge Bot

# Retail Support Demo README

## Overview
The Retail Support Demo is an offline knowledge base application for managing and searching documents (TXT, PDF, DOCX) with support for embedded images. It allows users to add, organize, search, and view documents and associated images in a user-friendly GUI, all without requiring an internet connection.

## Features
- **Document Management**: Add individual documents or scan folders to import TXT, PDF, or DOCX files.
- **Image Support**: Extracts and displays embedded images from PDFs and DOCX files; supports external image association (JPG, JPEG, PNG).
- **Search and Filter**: Search documents by content, name, or tags with case-sensitive and date range options; filter by tags or categories.
- **Organization**: Categorize documents, sort by name, date, or category, and view metadata in tooltips.
- **Image Navigation**: View multiple images with Prev/Next buttons, zoom (mouse wheel), and pan (drag).
- **Accessibility**: Supports keyboard shortcuts, high-contrast mode, and screen reader-compatible widget labels.
- **Database Management**: Export/import the database for backup or migration; handles database corruption on startup.
- **Offline Operation**: Fully functional without internet access.
- **Code Documentation**: The source code (`knowledge_base_app.py`) includes detailed comments explaining each section, function, and key logic block for easier understanding and maintenance.

## Requirements
### Software
- **Python 3.8+**: The app requires Python to run the script.
- **Libraries** (must be installed or bundled):
  - `tkinter`: For the GUI (includes `simpledialog` for category prompts).
  - `tinydb`: For lightweight database storage.
  - `python-docx`: For reading DOCX files.
  - `PyMuPDF` (fitz): For reading PDF files and extracting images.
  - `Pillow` (PIL): For image processing and display.
  - `fuzzywuzzy`: For fuzzy search functionality.
  - `scikit-learn`: For generating document tags via TF-IDF.
- **Optional for Distribution**:
  - Use `PyInstaller` to bundle the app and its dependencies into a standalone executable for offline use.

### Hardware
- **Operating System**: Windows, macOS, or Linux (tested on Windows).
- **Disk Space**: At least 100 MB for the app, documents, and extracted images.
- **Memory**: Minimum 2 GB RAM (more for large documents or databases).

### Installation
1. **Install Python**: Ensure Python 3.8 or higher is installed. Download from [python.org](https://www.python.org/downloads/).
2. **Install Dependencies**: Use pip to install required libraries:
   ```bash
   pip install tinydb python-docx PyMuPDF Pillow fuzzywuzzy scikit-learn


Run the App: Execute the Python script (knowledge_base_app.py):python knowledge_base_app.py


Optional Standalone Executable:
Install PyInstaller: pip install pyinstaller
Create an executable: pyinstaller --onefile knowledge_base_app.py
Distribute the generated executable in the dist folder for offline use.



Folder Structure
The app creates and uses the following folder structure in the same directory as the script:
knowledge_base_app/
├── knowledge_base.json    # TinyDB database storing document metadata, tags, categories, and image references
├── kb_documents/          # Stores imported document files (TXT, PDF, DOCX)
├── images/                # Stores extracted images from documents and manually associated images
└── app.log                # Log file for debugging errors


knowledge_base.json: Contains document metadata (name, content, tags, images, category, creation date, TF-IDF vectors).
kb_documents/: Stores copies of imported documents to ensure offline access.
images/: Stores images extracted from PDFs/DOCX files (e.g., docname_page0_img0.png) and external images (e.g., docname.jpg).
app.log: Logs errors and events for debugging (e.g., file processing errors, database issues).

Note: Ensure write permissions for the app directory to create these files and folders.
How to Use
Starting the App

Run knowledge_base_app.py or the standalone executable.
On startup, the app checks the database integrity. If corrupted, it prompts to clear the database or continue with limited functionality.

Adding Documents

Add Individual Documents:
Go to File > Add KB Document (or press Ctrl+O).
Select one or more TXT, PDF, or DOCX files.
A dialog will prompt for a category for each document; enter a category or leave blank for "Uncategorized".
The app extracts text and up to 5 embedded images per document, storing them in kb_documents and images folders.


Scan Folder:
Go to File > Scan Document Folder.
Select a folder containing TXT, PDF, or DOCX files.
A dialog will prompt for a category for each document; enter a category or leave blank for "Uncategorized".
The app imports non-duplicate files and extracts text/images.



Viewing Documents

Select a document from the listbox on the left to view its content in the text preview area.
Embedded or associated images appear in the canvas below the text.
Use Prev/Next buttons to cycle through multiple images.
Zoom images with the mouse wheel; pan by clicking and dragging.
Hover over a document in the listbox to see a tooltip with metadata (name, tags, category, creation date).

Searching Documents

Enter a query in the search bar (bottom) and press Enter or click Search.
Filters:
Tag Filter: Select a tag from the dropdown to limit results to documents with that tag.
Category Filter: Select a category to filter documents.
Date Range: Enter start/end dates (YYYY-MM-DD) to filter by creation date.
Case Sensitive: Check the box for case-sensitive searches.


Results appear in the listbox; the top result’s content is displayed with highlighted matches.
Click Clear to reset the search and show all documents.

Managing Documents

Delete Documents: Right-click one or more selected documents in the listbox and choose Delete. This removes the document and its images from kb_documents and images.
Associate Image: Go to File > Associate Image, select a document, and choose a JPG, JPEG, or PNG file to link to it.
Sort Documents: Use the sort dropdown to order documents by name, creation date, or category.
View All Documents: Go to File > View All Documents to see a list of all document names.

Customizing Display

Word Wrap: Toggle the Word Wrap checkbox to enable/disable text wrapping in the preview.
Font Size: Use +/- buttons to adjust the text preview font size.
High-Contrast Mode: Go to File > Toggle High Contrast for better visibility.
Image Navigation: Zoom (mouse wheel) and pan (drag) images in the canvas.

Database Management

Export Database: Go to File > Export Database to save knowledge_base.json to a chosen location.
Import Database: Go to File > Import Database to load a previously exported JSON file, replacing the current database.

Accessibility

Use Ctrl+O to add documents and Ctrl+F to focus the search bar.
Widgets (search bar, tag/category filters) have accessible names for screen readers (e.g., NVDA).
Test with screen readers to ensure compatibility, as Tkinter’s support is limited.

Help

Go to File > Help for detailed instructions on using the app.

Troubleshooting

Database Errors: If the app reports a corrupted database, choose to clear it or restore from a backup (exported JSON file).
Missing Documents/Images: Ensure kb_documents and images folders have write permissions.
Performance Issues: For large documents, the app limits image extraction to 5 per file. Use a smaller set of documents if performance is slow.
Errors: Check app.log for detailed error messages. For example, if you see "module tkinter.filedialog has no attribute 'askstring'", ensure you are using the updated code with simpledialog.askstring.
Code Understanding: The source code includes detailed comments for each section, function, and key logic block to aid developers in understanding and maintaining the app.

Notes

Offline Operation: The app requires no internet access. All dependencies must be bundled for standalone use.
Distribution: Use PyInstaller to create a standalone executable for users without Python installed.
Testing: Test with various document types (TXT, PDF, DOCX), large files, and embedded images. Verify search, sorting, and filtering with large databases. Test category prompts to ensure they work correctly.
Storage: Images are stored in images to keep the database lightweight. Consider base64 encoding in TinyDB if disk usage is a concern (requires code modification).
Limitations: Markdown (.md) support is not included to avoid additional dependencies. Add the markdown library if needed.

For issues or feature requests, consult app.log or contact the developer.```

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
Store embedded images as base64 strings in TinyDB instead of files inimg_folder to reduce disk clutter, decoding them for display in show_image.
