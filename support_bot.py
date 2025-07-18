import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tinydb import TinyDB, Query
from fuzzywuzzy import fuzz
from docx import Document
import pdfplumber
import fitz  # PyMuPDF
from collections import Counter
import json
import os
from pathlib import Path
import re
import uuid
import logging
from PIL import Image, ImageTk
import sys
import threading
from queue import Queue
import configparser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('retail_support.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Basic English stopwords list
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", 
    "in", "into", "is", "it", "no", "not", "of", "on", "or", "such", 
    "that", "the", "their", "then", "there", "these", "they", "this", 
    "to", "was", "will", "with", "i", "me", "my", "we", "our", "you", "your"
}

class ImageViewer(tk.Toplevel):
    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title("Image Viewer")
        self.geometry("800x600")
        
        try:
            self.original_image = Image.open(image_path)
            self.current_image = self.original_image.copy()
            self.photo = ImageTk.PhotoImage(self.current_image)
            
            self.canvas = tk.Canvas(self, width=800, height=600)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Zoom controls
            self.zoom_level = 1.0
            self.bind("<MouseWheel>", self.zoom_image)
            self.bind("<Button-4>", lambda e: self.zoom_image(1))  # Linux zoom in
            self.bind("<Button-5>", lambda e: self.zoom_image(-1))  # Linux zoom out
            
            # Pan controls
            self.canvas.bind("<ButtonPress-1>", self.start_pan)
            self.canvas.bind("<B1-Motion>", self.pan_image)
            self.canvas.config(cursor="hand2")
            
        except Exception as e:
            logger.error(f"Failed to open image: {e}")
            messagebox.showerror("Error", f"Could not open image: {e}")
            self.destroy()

    def zoom_image(self, event):
        try:
            # Determine zoom direction
            if isinstance(event, int):
                delta = event
            else:
                delta = event.delta // 120  # Normalize wheel events
            
            zoom_factor = 1.1 if delta > 0 else 0.9
            self.zoom_level *= zoom_factor
            self.zoom_level = max(0.1, min(self.zoom_level, 5.0))  # Limit zoom range
            
            # Calculate new size
            width = int(self.original_image.width * self.zoom_level)
            height = int(self.original_image.height * self.zoom_level)
            
            # Resize image
            self.current_image = self.original_image.resize(
                (width, height), 
                Image.LANCZOS
            )
            self.photo = ImageTk.PhotoImage(self.current_image)
            self.canvas.itemconfig(self.image_id, image=self.photo)
            
            # Update scroll region
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
            
        except Exception as e:
            logger.error(f"Zoom error: {e}")

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def pan_image(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

class RetailSupportBot(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Retail Support Bot")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # Initialize settings
        self.settings = configparser.ConfigParser()
        self.settings.read('settings.ini')
        if not self.settings.has_section('General'):
            self.settings.add_section('General')
            self.settings.set('General', 'theme', 'light')
            self.settings.set('General', 'max_results', '20')
        
        # Initialize databases
        self.init_databases()
        
        # Setup UI
        self.setup_ui()
        self.apply_theme()
        
        # Document processing queue
        self.process_queue = Queue()
        self.processor = threading.Thread(
            target=self.process_documents,
            daemon=True
        )
        self.processor.start()
        
    def init_databases(self):
        try:
            self.db = TinyDB('knowledge_db.json')
            self.paragraphs = self.db.table('paragraphs')
            self.faq_db = TinyDB('faq_db.json')
            self.faqs = self.faq_db.table('faqs')
        except Exception as e:
            logger.error(f"Database init failed: {e}")
            messagebox.showerror("Error", "Failed to initialize databases")
            sys.exit(1)

    def setup_ui(self):
        # Main notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Search tab
        self.setup_search_tab()
        # FAQ tab
        self.setup_faq_tab()
        # Documents tab
        self.setup_documents_tab()
        
        # Menu
        self.setup_menu()

    def setup_search_tab(self):
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Search")
        
        # Search controls
        control_frame = ttk.Frame(search_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Larger query box with Enter key support
        self.query_var = tk.StringVar()
        self.query_entry = ttk.Entry(
            control_frame, 
            textvariable=self.query_var,
            font=('Helvetica', 12),
            width=60
        )
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.query_entry.bind("<Return>", lambda e: self.search())
        
        ttk.Button(control_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear", command=self.clear_results).pack(side=tk.LEFT)
        
        # Results display
        results_frame = ttk.Frame(search_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.results_text = tk.Text(
            results_frame,
            wrap=tk.WORD,
            font=('Helvetica', 11),
            padx=10,
            pady=10
        )
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(results_frame, command=self.results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=scrollbar.set)
        
        # Image thumbnails
        self.thumbnail_frame = ttk.Frame(search_frame, height=120)
        self.thumbnail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.thumbnail_canvas = tk.Canvas(
            self.thumbnail_frame,
            height=120,
            bg='#f0f0f0'
        )
        self.thumbnail_scroll = ttk.Scrollbar(
            self.thumbnail_frame,
            orient=tk.HORIZONTAL,
            command=self.thumbnail_canvas.xview
        )
        self.thumbnail_canvas.config(xscrollcommand=self.thumbnail_scroll.set)
        
        self.thumbnail_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.thumbnail_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.thumbnails_frame = ttk.Frame(self.thumbnail_canvas)
        self.thumbnail_canvas.create_window(
            (0, 0),
            window=self.thumbnails_frame,
            anchor=tk.NW
        )
        
        self.thumbnails_frame.bind(
            "<Configure>",
            lambda e: self.thumbnail_canvas.configure(
                scrollregion=self.thumbnail_canvas.bbox("all")
            )
        )

    def setup_faq_tab(self):
        # FAQ tab implementation
        pass
        
    def setup_documents_tab(self):
        # Documents tab implementation
        pass
        
    def setup_menu(self):
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Upload Document", command=self.upload_document)
        file_menu.add_command(label="Batch Index", command=self.batch_index)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        self.config(menu=menubar)

    def search(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query")
            return
            
        try:
            results = []
            
            # Simple search without NLTK
            for doc in self.paragraphs.all():
                if query.lower() in doc['text'].lower():
                    results.append({
                        'text': doc['text'],
                        'source': doc['filename'],
                        'images': doc.get('image_paths', [])
                    })
            
            self.display_results(results)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            messagebox.showerror("Error", f"Search failed: {e}")

    def display_results(self, results):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        
        if not results:
            self.results_text.insert(tk.END, "No results found")
            return
            
        for result in results[:20]:  # Limit to 20 results
            self.results_text.insert(tk.END, f"From: {result['source']}\n")
            self.results_text.insert(tk.END, f"{result['text']}\n\n")
            self.results_text.insert(tk.END, "-"*80 + "\n\n")
        
        self.results_text.config(state=tk.DISABLED)
        
        # Display thumbnails
        self.show_thumbnails(results[0].get('images', []))

    def show_thumbnails(self, image_paths):
        # Clear existing thumbnails
        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()
        
        if not image_paths:
            return
            
        thumbnail_size = (100, 100)
        
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                img.thumbnail(thumbnail_size)
                photo = ImageTk.PhotoImage(img)
                
                btn = ttk.Button(
                    self.thumbnails_frame,
                    image=photo,
                    command=lambda p=img_path: self.show_image(p)
                )
                btn.image = photo  # Keep reference
                btn.pack(side=tk.LEFT, padx=5, pady=5)
                
            except Exception as e:
                logger.error(f"Failed to load thumbnail {img_path}: {e}")

    def show_image(self, image_path):
        try:
            ImageViewer(self, image_path)
        except Exception as e:
            logger.error(f"Failed to display image {image_path}: {e}")
            messagebox.showerror("Error", f"Could not display image: {e}")

    def upload_document(self):
        filetypes = [
            ("Documents", "*.pdf *.docx *.txt"),
            ("All files", "*.*")
        ]
        
        try:
            filepath = filedialog.askopenfilename(filetypes=filetypes)
            if not filepath:
                return
                
            self.process_queue.put(('process', filepath))
            messagebox.showinfo("Info", "Document added to processing queue")
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            messagebox.showerror("Error", f"Document upload failed: {e}")

    def process_documents(self):
        while True:
            task = self.process_queue.get()
            if task[0] == 'process':
                self._process_document(task[1])
            self.process_queue.task_done()

    def _process_document(self, filepath):
        try:
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.pdf':
                content = self.extract_pdf(filepath)
            elif ext == '.docx':
                content = self.extract_docx(filepath)
            else:
                content = self.extract_text(filepath)
                
            # Generate tags without NLTK
            words = re.findall(r'\w+', content['text'].lower())
            words = [w for w in words if w not in STOPWORDS and len(w) > 2]
            tags = list(set(words[:5]))  # Top 5 unique words
            
            # Store in database
            self.paragraphs.insert({
                'filename': filename,
                'text': content['text'],
                'tags': tags,
                'image_paths': content.get('image_paths', [])
            })
            
            logger.info(f"Processed document: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to process {filepath}: {e}")

    def extract_pdf(self, filepath):
        # PDF extraction implementation
        pass
        
    def extract_docx(self, filepath):
        # DOCX extraction implementation
        pass
        
    def extract_text(self, filepath):
        # Text extraction implementation
        pass

    def clear_results(self):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)
        
        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()

    def toggle_theme(self):
        current_theme = self.settings.get('General', 'theme', fallback='light')
        new_theme = 'dark' if current_theme == 'light' else 'light'
        self.settings.set('General', 'theme', new_theme)
        self.apply_theme()

    def apply_theme(self):
        theme = self.settings.get('General', 'theme', fallback='light')
        
        if theme == 'dark':
            bg = '#2d2d2d'
            fg = '#ffffff'
            entry_bg = '#3c3c3c'
        else:
            bg = '#f4f4f9'
            fg = '#000000'
            entry_bg = '#ffffff'
            
        self.style = ttk.Style()
        self.style.configure('.', background=bg, foreground=fg)
        self.style.configure('TEntry', fieldbackground=entry_bg)
        self.configure(bg=bg)

    def on_closing(self):
        try:
            with open('settings.ini', 'w') as f:
                self.settings.write(f)
            self.db.close()
            self.faq_db.close()
            self.destroy()
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            self.destroy()

if __name__ == "__main__":
    try:
        app = RetailSupportBot()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        messagebox.showerror("Fatal Error", f"The application encountered an error:\n{e}")
        sys.exit(1)
