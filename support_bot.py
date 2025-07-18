import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tinydb import TinyDB, Query, where
from fuzzywuzzy import fuzz
from docx import Document
import pdfplumber
import fitz  # PyMuPDF
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
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
import time
from queue import Queue
import configparser

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CONFIG = {
    'general': {
        'theme': 'light',
        'max_results': '10',
        'results_per_page': '5'
    },
    'paths': {
        'docs_dir': 'docs',
        'data_dir': 'data',
        'images_dir': 'images'
    }
}

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading...")
        self.geometry("300x150")
        self.resizable(False, False)
        
        # Center the splash screen
        window_width = self.winfo_reqwidth()
        window_height = self.winfo_reqheight()
        position_right = int(self.winfo_screenwidth()/2 - window_width/2)
        position_down = int(self.winfo_screenheight()/2 - window_height/2)
        self.geometry(f"+{position_right}+{position_down}")
        
        self.label = ttk.Label(self, text="Retail Support Bot\nInitializing...", 
                             font=("Helvetica", 12), justify="center")
        self.label.pack(expand=True, padx=20, pady=20)
        
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=(0, 20))
        self.progress.start()

class SettingsManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = Path('config.ini')
        self.load_settings()
        
    def load_settings(self):
        if not self.config_path.exists():
            self.create_default_config()
        self.config.read(self.config_path)
        
    def create_default_config(self):
        self.config.read_dict(DEFAULT_CONFIG)
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
            
    def get_setting(self, section, key, default=None):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
            
    def set_setting(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

class DocumentProcessor(threading.Thread):
    def __init__(self, queue, db_path, images_dir):
        super().__init__()
        self.queue = queue
        self.db_path = db_path
        self.images_dir = images_dir
        self.daemon = True
        
    def run(self):
        while True:
            task = self.queue.get()
            if task is None:  # Sentinel value to stop the thread
                break
                
            file_path, callback = task
            try:
                doc_id = str(uuid.uuid4())
                filename = Path(file_path).name
                
                if file_path.lower().endswith('.pdf'):
                    extracted_data = self.extract_from_pdf(file_path, doc_id)
                    paragraphs = self.extract_pdf_paragraphs(file_path)
                    filetype = 'pdf'
                elif file_path.lower().endswith('.docx'):
                    extracted_data = self.extract_from_docx(file_path, doc_id)
                    paragraphs = self.extract_docx_paragraphs(file_path)
                    filetype = 'docx'
                else:
                    extracted_data = self.extract_from_txt(file_path)
                    paragraphs = self.extract_txt_paragraphs(file_path)
                    filetype = 'txt'
                
                db = TinyDB(self.db_path)
                paragraphs_table = db.table('paragraphs')
                
                for para in paragraphs:
                    tags = self.generate_tags(para, filename)
                    paragraphs_table.insert({
                        'filename': filename,
                        'filetype': filetype,
                        'text': para,
                        'tags': tags,
                        'image_paths': extracted_data['image_paths']
                    })
                
                callback(True, filename)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                callback(False, filename)
            finally:
                self.queue.task_done()
    
    def extract_from_pdf(self, file_path: str, doc_id: str) -> dict:
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            doc = fitz.open(file_path)
            image_paths = []
            for page_num in range(len(doc)):
                for img in doc[page_num].get_images():
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image:
                        image_path = self.images_dir / f"{doc_id}_img{len(image_paths)}.png"
                        with open(image_path, "wb") as f:
                            f.write(base_image["image"])
                        image_paths.append(str(image_path))
            doc.close()
            return {"text": text, "image_paths": image_paths}
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {"text": "", "image_paths": []}

    def extract_pdf_paragraphs(self, file_path: Path) -> list:
        try:
            with pdfplumber.open(file_path) as pdf:
                paragraphs = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        paras = text.split('\n\n')
                        for para in paras:
                            if para.strip():
                                sentences = sent_tokenize(para.strip())
                                for sentence in sentences:
                                    if len(sentence) > 20:
                                        paragraphs.append(sentence.strip())
                return paragraphs
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            return []

    def extract_from_docx(self, file_path: str, doc_id: str) -> dict:
        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            image_paths = []
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    image_bytes = rel.target_part.blob
                    image_ext = rel.target_ref.split('.')[-1]
                    image_path = self.images_dir / f"{doc_id}_img{len(image_paths)}.{image_ext}"
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    image_paths.append(str(image_path))
            return {"text": text, "image_paths": image_paths}
        except Exception as e:
            logger.error(f"Error processing DOCX: {str(e)}")
            return {"text": "", "image_paths": []}

    def extract_docx_paragraphs(self, file_path: Path) -> list:
        try:
            doc = Document(file_path)
            return [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {str(e)}")
            return []

    def extract_from_txt(self, file_path: str) -> dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return {"text": text, "image_paths": []}
        except Exception as e:
            logger.error(f"Error processing TXT: {str(e)}")
            return {"text": "", "image_paths": []}

    def extract_txt_paragraphs(self, file_path: Path) -> list:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error processing TXT {file_path}: {str(e)}")
            return []

    def generate_tags(self, text: str, filename: str) -> list:
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalpha() and word not in stop_words]
        filename_tags = re.findall(r'\w+', filename.lower())
        word_counts = Counter(words)
        tags = [word for word, _ in word_counts.most_common(5)] + filename_tags
        return list(set(tags))

class ImageZoomDialog(tk.Toplevel):
    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title("Image Preview")
        self.geometry("600x400")
        try:
            self.image = Image.open(image_path)
            self.original_image = self.image.copy()
        except Exception as e:
            logger.error(f"Failed to open image {image_path}: {str(e)}")
            messagebox.showerror("Error", f"Failed to open image: {str(e)}")
            self.destroy()
            return
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.last_pos = None

        self.canvas = tk.Canvas(self, highlightthickness=0, cursor="hand2")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.h_scroll = ttk.Scrollbar(self, orient="horizontal",
                                     command=self.canvas.xview)
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.v_scroll = ttk.Scrollbar(self, orient="vertical",
                                     command=self.canvas.yview)
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=self.h_scroll.set,
                             yscrollcommand=self.v_scroll.set)

        zoom_frame = ttk.Frame(self)
        zoom_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(zoom_frame, text="Zoom:").pack(side="left")
        self.zoom_scale = ttk.Scale(zoom_frame, from_=25, to=200, value=100,
                                   orient="horizontal", command=self.update_zoom)
        self.zoom_scale.pack(side="left", fill="x", expand=True)
        
        reset_btn = ttk.Button(zoom_frame, text="Reset", command=self.reset_view)
        reset_btn.pack(side="right", padx=5)

        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan_image)
        self.canvas.bind("<MouseWheel>", self.zoom_wheel)
        self.canvas.bind("<Button-4>", self.zoom_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.zoom_wheel)  # Linux scroll down

        self.photo = None
        self.image_id = None
        self.update_image()

    def reset_view(self):
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_scale.set(100)
        self.update_image()

    def update_image(self):
        try:
            if not hasattr(self, 'image') or not self.image:
                return
                
            width, height = self.image.size
            new_size = (int(width * self.scale), int(height * self.scale))
            resized = self.image.resize(new_size, Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(resized)
            
            if self.image_id is not None:
                self.canvas.delete(self.image_id)
                
            self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
            self.canvas.configure(scrollregion=(0, 0, new_size[0], new_size[1]))
            
            # Maintain view position
            if new_size[0] > 0 and new_size[1] > 0:
                self.canvas.xview_moveto(self.offset_x / new_size[0])
                self.canvas.yview_moveto(self.offset_y / new_size[1])
        except Exception as e:
            logger.error(f"Error updating image: {str(e)}")

    def update_zoom(self, value):
        try:
            self.scale = float(value) / 100.0
            self.update_image()
        except Exception as e:
            logger.error(f"Error in zoom update: {str(e)}")

    def start_pan(self, event):
        self.last_pos = (event.x, event.y)

    def pan_image(self, event):
        if self.last_pos:
            dx = event.x - self.last_pos[0]
            dy = event.y - self.last_pos[1]
            self.offset_x -= dx
            self.offset_y -= dy
            self.last_pos = (event.x, event.y)
            self.update_image()

    def zoom_wheel(self, event):
        try:
            # Handle different event types for different platforms
            if hasattr(event, 'delta'):
                delta = event.delta
            else:  # Linux
                delta = 120 if event.num == 4 else -120
                
            factor = 1.1 if delta > 0 else 0.909
            new_scale = max(0.25, min(self.scale * factor, 2.0))
            self.zoom_scale.set(new_scale * 100)
            self.update_image()
        except Exception as e:
            logger.error(f"Error in wheel zoom: {str(e)}")

class RetailSupportBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Show splash screen
        self.splash = SplashScreen(self)
        self.update()
        
        # Initialize settings
        self.settings = SettingsManager()
        
        # Initialize in background thread
        self.init_thread = threading.Thread(target=self.initialize_app)
        self.init_thread.start()
        
        # Check initialization status periodically
        self.check_initialization()
        
    def check_initialization(self):
        if self.init_thread.is_alive():
            self.after(100, self.check_initialization)
        else:
            self.splash.destroy()
            self.deiconify()
            
    def initialize_app(self):
        # Load NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
        
        # Load settings
        theme = self.settings.get_setting('general', 'theme', 'light')
        self.is_dark_mode = theme == 'dark'
        self.max_results = int(self.settings.get_setting('general', 'max_results', 10))
        self.results_per_page = int(self.settings.get_setting('general', 'results_per_page', 5))
        
        # Setup paths
        self.DOCS_DIR = Path(self.settings.get_setting('paths', 'docs_dir', 'docs'))
        self.DATA_DIR = Path(self.settings.get_setting('paths', 'data_dir', 'data'))
        self.IMAGES_DIR = Path(self.settings.get_setting('paths', 'images_dir', 'images'))
        
        # Create directories if they don't exist
        self.DATA_DIR.mkdir(exist_ok=True)
        self.IMAGES_DIR.mkdir(exist_ok=True)
        
        # Initialize databases
        self.DB_PATH = self.DATA_DIR / "knowledge_db.json"
        self.FAQ_DB_PATH = self.DATA_DIR / "support_bot_db.json"
        self.SYNONYMS_PATH = self.DATA_DIR / "synonyms.json"
        
        self.db = TinyDB(self.DB_PATH)
        self.paragraphs_table = self.db.table('paragraphs')
        self.faq_db = TinyDB(self.FAQ_DB_PATH)
        self.faq_table = self.faq_db.table('faqs')
        
        # Load synonyms
        try:
            with open(self.SYNONYMS_PATH, 'r') as f:
                self.synonyms = json.load(f)
        except FileNotFoundError:
            self.synonyms = {}
            with open(self.SYNONYMS_PATH, 'w') as f:
                json.dump(self.synonyms, f, indent=4)
        
        # Initialize document processing queue
        self.process_queue = Queue()
        self.processor = DocumentProcessor(self.process_queue, self.DB_PATH, self.IMAGES_DIR)
        self.processor.start()
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        self.title("Retail Support Bot - Knowledge Base Chatbot")
        self.geometry("1000x700")
        self.minsize(800, 500)
        
        # Setup menu
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Index Documents", command=self.batch_index)
        file_menu.add_command(label="Upload Document", command=self.upload_document)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="Actions", menu=file_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
        
        # Setup notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        
        # Setup tabs
        self.setup_search_tab()
        self.setup_faq_tab()
        self.setup_synonym_tab()
        self.setup_history_tab()
        self.setup_documents_tab()
        
        # Apply theme
        self.apply_theme()
        
        # Initialize pagination
        self.current_page = 1
        self.total_pages = 1
        self.search_results = []
        
    def show_settings(self):
        settings_dialog = tk.Toplevel(self)
        settings_dialog.title("Settings")
        settings_dialog.geometry("400x300")
        
        ttk.Label(settings_dialog, text="Max Results:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        max_results_var = tk.StringVar(value=str(self.max_results))
        ttk.Entry(settings_dialog, textvariable=max_results_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(settings_dialog, text="Results Per Page:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        results_per_page_var = tk.StringVar(value=str(self.results_per_page))
        ttk.Entry(settings_dialog, textvariable=results_per_page_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        def save_settings():
            try:
                self.max_results = int(max_results_var.get())
                self.results_per_page = int(results_per_page_var.get())
                
                self.settings.set_setting('general', 'max_results', self.max_results)
                self.settings.set_setting('general', 'results_per_page', self.results_per_page)
                
                messagebox.showinfo("Success", "Settings saved successfully")
                settings_dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
        
        ttk.Button(settings_dialog, text="Save", command=save_settings).grid(row=2, column=0, columnspan=2, pady=10)
    
    def show_about(self):
        about_text = """Retail Support Bot
Version 1.0
A knowledge base chatbot for retail support
"""
        messagebox.showinfo("About", about_text)
    
    def apply_theme(self):
        if self.is_dark_mode:
            bg, fg, btn_bg, btn_fg = "#2d2d2d", "#ffffff", "#1e90ff", "#ffffff"
            entry_bg = "#3c3c3c"
        else:
            bg, fg, btn_bg, btn_fg = "#f4f4f9", "#000000", "#007bff", "#ffffff"
            entry_bg = "#ffffff"
        
        self.style = ttk.Style()
        self.style.configure("TNotebook", background=bg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg,
                            font=("Helvetica", 11))
        self.style.configure("TButton", background=btn_bg, foreground=btn_fg,
                            font=("Helvetica", 11))
        self.style.configure("TEntry", fieldbackground=entry_bg, foreground=fg,
                            font=("Helvetica", 10))
        self.style.configure("TCombobox", fieldbackground=entry_bg, foreground=fg,
                            font=("Helvetica", 10))
        self.style.configure("Treeview", background=entry_bg, foreground=fg,
                            fieldbackground=entry_bg, font=("Helvetica", 10))
        self.configure(bg=bg)
        
        for child in self.winfo_children():
            if isinstance(child, ttk.Notebook):
                child.configure(style="TNotebook")
            elif isinstance(child, tk.Frame):
                child.configure(bg=bg)
        
        self.update_tab_fonts()
        logger.info("Theme applied")

    def update_tab_fonts(self):
        if not hasattr(self, 'notebook'):
            logger.warning("Notebook not initialized in update_tab_fonts")
            return
        for tab_id in self.notebook.tabs():
            frame = self.notebook.nametowidget(tab_id)
            for widget in frame.winfo_children():
                if isinstance(widget, tk.Text):
                    widget.configure(font=("Helvetica", 10),
                                    bg="#ffffff" if not self.is_dark_mode else "#3c3c3c",
                                    fg="#000000" if not self.is_dark_mode else "#ffffff")
                elif isinstance(widget, tk.Entry):
                    widget.configure(font=("Helvetica", 12),
                                    bg="#ffffff" if not self.is_dark_mode else "#3c3c3c",
                                    fg="#000000" if not self.is_dark_mode else "#ffffff")
                elif isinstance(widget, tk.Label) and \
                     widget.cget("text") in ["Quick FAQ", "Chat History",
                                            "Indexed Documents"]:
                    widget.configure(font=("Helvetica", 12, "bold"))

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.settings.set_setting('general', 'theme', 'dark' if self.is_dark_mode else 'light')
        self.apply_theme()

    def get_all_tags(self):
        tags = set()
        for doc in self.paragraphs_table.all():
            tags.update(doc['tags'])
        return sorted(list(tags))

    def get_indexed_documents(self):
        return sorted(set(doc['filename'] for doc in self.paragraphs_table.all()))

    def setup_search_tab(self):
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Chat")
        logger.info("Search tab initialized")

        faq_frame = ttk.Frame(search_frame)
        faq_frame.grid(row=0, column=0, sticky="ns", padx=5, pady=5)
        faq_canvas = tk.Canvas(faq_frame, width=200, highlightthickness=0)
        faq_scroll = ttk.Scrollbar(faq_frame, orient="vertical",
                                  command=faq_canvas.yview)
        faq_scroll.pack(side="right", fill="y")
        faq_inner = ttk.Frame(faq_canvas)
        faq_canvas.create_window((0, 0), window=faq_inner, anchor="nw")
        faq_canvas.configure(yscrollcommand=faq_scroll.set)
        faq_canvas.pack(side="left", fill="y")
        ttk.Label(faq_inner, text="Quick FAQ", font=("Helvetica", 12, "bold")).\
            pack(anchor="w", padx=5, pady=5)
        self.faq_buttons = []
        self.faq_inner = faq_inner
        self.faq_canvas = faq_canvas
        self.load_faq_buttons()
        faq_inner.bind("<Configure>", lambda e: faq_canvas.configure(
            scrollregion=faq_canvas.bbox("all")))

        main_frame = ttk.Frame(search_frame)
        main_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        search_frame.columnconfigure(1, weight=1)
        search_frame.rowconfigure(0, weight=1)

        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(filter_frame, text="Filter by Tag:").pack(side="left")
        self.tag_var = tk.StringVar()
        self.tag_combo = ttk.Combobox(filter_frame, textvariable=self.tag_var,
                                     values=self.get_all_tags())
        self.tag_combo.pack(side="left", padx=5)
        ttk.Label(filter_frame, text="File Type:").pack(side="left")
        self.filetype_var = tk.StringVar(value="All")
        self.filetype_combo = ttk.Combobox(filter_frame,
                                          textvariable=self.filetype_var,
                                          values=["All", "pdf", "docx", "txt"])
        self.filetype_combo.pack(side="left", padx=5)
        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(filter_frame, text="Regex Search",
                        variable=self.regex_var).pack(side="left", padx=5)
        self.case_var = tk.BooleanVar()
        ttk.Checkbutton(filter_frame, text="Case Sensitive",
                        variable=self.case_var).pack(side="left", padx=5)
        self.preset_var = tk.StringVar(value="Custom")
        self.preset_combo = ttk.Combobox(filter_frame, textvariable=self.preset_var,
                                        values=["Custom", "Email", "Phone"])
        self.preset_combo.pack(side="left", padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.set_regex_preset)

        self.results_text = tk.Text(main_frame, height=10, font=("Helvetica", 10),
                                   wrap="word")
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.results_text.configure(state="disabled")
        results_scroll = ttk.Scrollbar(main_frame, orient="vertical",
                                      command=self.results_text.yview)
        results_scroll.pack(side="right", fill="y")
        self.results_text.configure(yscrollcommand=results_scroll.set)

        image_frame = ttk.Frame(main_frame)
        image_frame.pack(fill="x", padx=5, pady=5)
        self.image_canvas = tk.Canvas(image_frame, height=100, highlightthickness=0)
        self.image_scroll = ttk.Scrollbar(image_frame, orient="horizontal",
                                         command=self.image_canvas.xview)
        self.image_scroll.pack(side="bottom", fill="x")
        self.image_inner = ttk.Frame(self.image_canvas)
        self.image_canvas.create_window((0, 0), window=self.image_inner, anchor="nw")
        self.image_canvas.configure(xscrollcommand=self.image_scroll.set)
        self.image_canvas.pack(side="top", fill="x")
        self.image_inner.bind("<Configure>", lambda e: self.image_canvas.configure(
            scrollregion=self.image_canvas.bbox("all")))
        self.image_labels = []

        chat_frame = ttk.Frame(main_frame)
        chat_frame.pack(fill="x", padx=5, pady=5)
        self.query_entry = ttk.Entry(chat_frame, width=60, font=("Helvetica", 12))
        self.query_entry.pack(side="left", padx=5)
        self.query_entry.bind("<Return>", lambda e: self.search())
        ttk.Button(chat_frame, text="Send", command=self.search).pack(side="left",
                                                                    padx=5)
        ttk.Button(chat_frame, text="Clear", command=self.clear_chat).\
            pack(side="left", padx=5)
        
        # Pagination controls
        pagination_frame = ttk.Frame(main_frame)
        pagination_frame.pack(fill="x", padx=5, pady=5)
        
        self.prev_btn = ttk.Button(pagination_frame, text="Previous", 
                                 command=self.prev_page, state="disabled")
        self.prev_btn.pack(side="left", padx=5)
        
        self.page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
        self.page_label.pack(side="left", padx=5)
        
        self.next_btn = ttk.Button(pagination_frame, text="Next", 
                                 command=self.next_page, state="disabled")
        self.next_btn.pack(side="left", padx=5)

    def setup_faq_tab(self):
        faq_frame = ttk.Frame(self.notebook)
        self.notebook.add(faq_frame, text="FAQ Management")
        logger.info("FAQ tab initialized")

        input_frame = ttk.Frame(faq_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(input_frame, text="Question:").pack(side="left")
        self.faq_question_entry = ttk.Entry(input_frame, width=50)
        self.faq_question_entry.pack(side="left", padx=5)
        input_frame = ttk.Frame(faq_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(input_frame, text="Answer:").pack(side="left")
        self.faq_answer_entry = ttk.Entry(input_frame, width=50)
        self.faq_answer_entry.pack(side="left", padx=5)
        ttk.Button(faq_frame, text="Add FAQ", command=self.add_faq).pack(padx=5,
                                                                       pady=5)

        self.faq_tree = ttk.Treeview(faq_frame, columns=("Question", "Answer"),
                                    show="headings")
        self.faq_tree.heading("Question", text="Question")
        self.faq_tree.heading("Answer", text="Answer")
        self.faq_tree.column("Question", width=300)
        self.faq_tree.column("Answer", width=400)
        self.faq_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.faq_tree.bind("<Button-3>", self.show_faq_context_menu)
        self.faq_tree.bind("<<TreeviewSelect>>", self.load_faq)
        self.load_faq_list()

    def setup_synonym_tab(self):
        synonym_frame = ttk.Frame(self.notebook)
        self.notebook.add(synonym_frame, text="Synonym Management")
        logger.info("Synonym tab initialized")

        input_frame = ttk.Frame(synonym_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(input_frame, text="Synonym Group (comma-separated):").\
            pack(side="left")
        self.synonym_entry = ttk.Entry(input_frame, width=50)
        self.synonym_entry.pack(side="left", padx=5)
        ttk.Button(synonym_frame, text="Add/Edit Synonym Group",
                   command=self.add_synonym).pack(padx=5, pady=5)

        self.synonym_tree = ttk.Treeview(synonym_frame, columns=("Group",),
                                        show="headings")
        self.synonym_tree.heading("Group", text="Group")
        self.synonym_tree.column("Group", width=400)
        self.synonym_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.synonym_tree.bind("<Button-3>", self.show_synonym_context_menu)
        self.synonym_tree.bind("<<TreeviewSelect>>", self.load_synonym)
        self.load_synonym_list()

    def setup_history_tab(self):
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="Chat History")
        logger.info("History tab initialized")

        ttk.Label(history_frame, text="Chat History",
                  font=("Helvetica", 12, "bold")).pack(anchor="w", padx=5, pady=5)
        self.history_filter = ttk.Entry(history_frame, width=50)
        self.history_filter.pack(padx=5, pady=5)
        self.history_filter.bind("<KeyRelease>", self.filter_history)
        self.history_tree = ttk.Treeview(history_frame, columns=("Query",),
                                        show="headings")
        self.history_tree.heading("Query", text="Query")
        self.history_tree.column("Query", width=600)
        self.history_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.history_tree.bind("<Double-1>", self.load_history_query)
        ttk.Button(history_frame, text="Export Chat", command=self.export_chat).\
            pack(padx=5, pady=5)
        ttk.Button(history_frame, text="Clear History", command=self.clear_history).\
            pack(padx=5, pady=5)
        self.load_history_list()

    def setup_documents_tab(self):
        documents_frame = ttk.Frame(self.notebook)
        self.notebook.add(documents_frame, text="Documents")
        logger.info("Documents tab initialized")

        ttk.Label(documents_frame, text="Indexed Documents",
                  font=("Helvetica", 12, "bold")).pack(anchor="w", padx=5, pady=5)
        self.documents_tree = ttk.Treeview(documents_frame, columns=("Filename",),
                                          show="headings")
        self.documents_tree.heading("Filename", text="Filename")
        self.documents_tree.column("Filename", width=600)
        self.documents_tree.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(documents_frame, text="Delete Selected Document",
                   command=self.delete_document).pack(padx=5, pady=5)
        self.load_documents_list()

    def load_faq_buttons(self):
        for widget in self.faq_buttons:
            widget.destroy()
        self.faq_buttons = []
        for faq in self.faq_table.all():
            if not isinstance(faq, dict) or 'question' not in faq:
                logger.warning(f"Invalid FAQ entry: {faq}")
                continue
            btn = ttk.Button(self.faq_inner, text=faq['question'],
                             command=lambda q=faq['question']: self.search_faq(q))
            btn.pack(anchor="w", padx=5, pady=2)
            self.faq_buttons.append(btn)
        self.faq_canvas.configure(scrollregion=self.faq_canvas.bbox("all"))

    def load_faq_list(self):
        for item in self.faq_tree.get_children():
            self.faq_tree.delete(item)
        for faq in self.faq_table.all():
            if not isinstance(faq, dict) or 'id' not in faq or \
               'question' not in faq or 'answer' not in faq:
                logger.warning(f"Invalid FAQ entry: {faq}")
                continue
            self.faq_tree.insert("", "end", iid=faq['id'],
                                values=(faq['question'], faq['answer']))

    def load_synonym_list(self):
        for item in self.synonym_tree.get_children():
            self.synonym_tree.delete(item)
        for key, words in self.synonyms.items():
            self.synonym_tree.insert("", "end", iid=key,
                                    values=(f"{key}: {', '.join(words)}",))

    def load_history_list(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for i, query in enumerate(self.chat_history):
            self.history_tree.insert("", "end", iid=str(i), values=(query,))

    def load_documents_list(self):
        for item in self.documents_tree.get_children():
            self.documents_tree.delete(item)
        for filename in self.get_indexed_documents():
            self.documents_tree.insert("", "end", values=(filename,))

    def filter_history(self, event):
        filter_text = self.history_filter.get().lower()
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for i, query in enumerate(self.chat_history):
            if filter_text in query.lower() or not filter_text:
                self.history_tree.insert("", "end", iid=str(i), values=(query,))

    def display_images(self, image_paths):
        for label in self.image_labels:
            label.destroy()
        self.image_labels = []
        self.image_refs = []
        for path in image_paths:
            try:
                img = Image.open(path)
                img.thumbnail((80, 80), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                label = ttk.Label(self.image_inner, image=photo)
                label.image = photo
                self.image_refs.append(photo)
                label.bind("<Button-1>", lambda e, p=path: self.open_image(p))
                label.pack(side="left", padx=5)
                self.image_labels.append(label)
            except Exception as e:
                logger.error(f"Error loading image {path}: {str(e)}")
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))

    def open_image(self, path):
        ImageZoomDialog(self, path)

    def set_regex_preset(self, event):
        preset = self.preset_var.get()
        if preset == "Email":
            self.query_entry.delete(0, tk.END)
            self.query_entry.insert(0, r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        elif preset == "Phone":
            self.query_entry.delete(0, tk.END)
            self.query_entry.insert(0, r"\b\d{3}-\d{3}-\d{4}\b")
        else:
            self.query_entry.delete(0, tk.END)

    def search(self):
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a question")
            return

        self.chat_history.append(query)
        self.load_history_list()
        self.notebook.select(0)

        # Process query and get results
        self.search_results = self.get_search_results(query)
        self.total_pages = (len(self.search_results) + self.results_per_page - 1) // self.results_per_page
        self.current_page = 1
        self.display_page()
    
    def get_search_results(self, query):
        expanded_query = set(query.lower().split())
        for word in query.lower().split():
            for group in self.synonyms.values():
                if word in group:
                    expanded_query.update(group)
        expanded_query = list(expanded_query)

        results = []
        if self.regex_var.get():
            try:
                flags = 0 if self.case_var.get() else re.IGNORECASE
                pattern = re.compile(query, flags)
                for doc in self.paragraphs_table.all():
                    if self.filetype_var.get() != "All" and \
                       doc['filetype'] != self.filetype_var.get():
                        continue
                    if self.tag_var.get() and self.tag_var.get() not in doc['tags']:
                        continue
                    lines = doc['text'].split('\n')
                    for i, line in enumerate(lines, 1):
                        if pattern.search(line):
                            results.append({
                                'filename': doc['filename'],
                                'matched_text': line,
                                'line_number': i,
                                'tags': doc['tags'],
                                'score': 100,
                                'image_paths': doc['image_paths']
                            })
            except re.error:
                messagebox.showerror("Error", "Invalid regex pattern")
                return []
        else:
            for doc in self.paragraphs_table.all():
                if self.filetype_var.get() != "All" and \
                   doc['filetype'] != self.filetype_var.get():
                    continue
                if self.tag_var.get() and self.tag_var.get() not in doc['tags']:
                    continue
                score = max(fuzz.partial_ratio(word.lower(), doc['text'].lower())
                          for word in expanded_query)
                if score > 70:
                    results.append({
                        'filename': doc['filename'],
                        'matched_text': doc['text'],
                        'line_number': None,
                        'tags': doc['tags'],
                        'score': score,
                        'image_paths': doc['image_paths']
                    })

        return sorted(results, key=lambda x: x['score'], reverse=True)[:self.max_results]
    
    def display_page(self):
        start_idx = (self.current_page - 1) * self.results_per_page
        end_idx = start_idx + self.results_per_page
        page_results = self.search_results[start_idx:end_idx]
        
        # Group results by filename
        grouped_results = {}
        image_paths = set()
        for result in page_results:
            filename = result['filename']
            if filename not in grouped_results:
                grouped_results[filename] = []
            grouped_results[filename].append((result['matched_text'], result['score'],
                                           result['tags'], result['line_number']))
            image_paths.update(result['image_paths'])
        
        # Display results
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        
        text_content = ""
        for filename, paras in grouped_results.items():
            text_content += f"📄 {filename}\n"
            for text, score, tags, line_number in paras:
                text_content += f"Score: {score}% | Tags: {', '.join(tags)}"
                if line_number:
                    text_content += f" | Line: {line_number}"
                text_content += f"\n{text}\n\n"
        
        self.results_text.insert("1.0", text_content)
        self.results_text.configure(state="disabled")
        self.display_images(image_paths)
        
        # Update pagination controls
        self.update_pagination_controls()
    
    def update_pagination_controls(self):
        self.page_label.config(text=f"Page {self.current_page} of {self.total_pages}")
        self.prev_btn.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_btn.config(state="normal" if self.current_page < self.total_pages else "disabled")
    
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_page()
    
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_page()
    
    def search_faq(self, question: str):
        self.query_entry.delete(0, tk.END)
        self.query_entry.insert(0, question)
        self.search()

    def load_faq(self, event):
        selection = self.faq_tree.selection()
        if selection:
            faq_id = selection[0]
            faq = self.faq_table.get(Query().id == faq_id)
            if faq:
                self.faq_question_entry.delete(0, tk.END)
                self.faq_question_entry.insert(0, faq['question'])
                self.faq_answer_entry.delete(0, tk.END)
                self.faq_answer_entry.insert(0, faq['answer'])
                self.selected_faq_id = faq_id

    def show_faq_context_menu(self, event):
        selection = self.faq_tree.selection()
        if selection:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Edit", command=self.edit_faq)
            menu.add_command(label="Delete", command=self.delete_faq)
            menu.post(event.x_root, event.y_root)

    def show_synonym_context_menu(self, event):
        selection = self.synonym_tree.selection()
        if selection:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Edit", command=self.add_synonym)
            menu.add_command(label="Delete", command=self.delete_synonym)
            menu.post(event.x_root, event.y_root)

    def load_synonym(self, event):
        selection = self.synonym_tree.selection()
        if selection:
            key = selection[0]
            self.synonym_entry.delete(0, tk.END)
            self.synonym_entry.insert(0, ','.join(self.synonyms[key]))

    def load_history_query(self, event):
        selection = self.history_tree.selection()
        if selection:
            query_index = int(selection[0])
            self.query_entry.delete(0, tk.END)
            self.query_entry.insert(0, self.chat_history[query_index])
            self.search()

    def clear_chat(self):
        self.query_entry.delete(0, tk.END)
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.configure(state="disabled")
        self.display_images([])

    def clear_history(self):
        self.chat_history = []
        self.load_history_list()
        messagebox.showinfo("Success", "Chat history cleared")

    def upload_document(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF/DOCX/TXT files", "*.pdf *.docx *.txt")])
        if not file_path:
            return
            
        filename = Path(file_path).name
        if filename in self.get_indexed_documents():
            messagebox.showwarning("Warning",
                                f"Document '{filename}' is already indexed")
            return
            
        def callback(success, filename):
            if success:
                self.tag_combo.configure(values=self.get_all_tags())
                self.tag_var.set("")
                self.load_documents_list()
                messagebox.showinfo("Success", f"Document '{filename}' indexed successfully")
            else:
                messagebox.showerror("Error", f"Failed to index document '{filename}'")
        
        # Add to processing queue
        self.process_queue.put((file_path, callback))
        messagebox.showinfo("Processing", f"Document '{filename}' is being processed in the background")

    def batch_index(self):
        self.DOCS_DIR.mkdir(exist_ok=True)
        doc_files = list(self.DOCS_DIR.glob("*.pdf")) + \
                    list(self.DOCS_DIR.glob("*.docx")) + \
                    list(self.DOCS_DIR.glob("*.txt"))
        indexed_files = self.get_indexed_documents()
        new_files = [f for f in doc_files if f.name not in indexed_files]
        
        if not new_files:
            messagebox.showwarning("Warning", "No new .pdf, .docx, or .txt files "
                                "found in docs/ folder")
            return
            
        progress = ttk.Progressbar(self, maximum=len(new_files))
        progress.pack(fill="x", padx=10, pady=5)
        self.update_idletasks()
        
        def callback(success, filename):
            progress["value"] += 1
            if progress["value"] == len(new_files):
                progress.destroy()
                messagebox.showinfo("Success", f"Indexed {len(new_files)} new documents")
        
        for file_path in new_files:
            self.process_queue.put((file_path, callback))
        
        messagebox.showinfo("Processing", f"{len(new_files)} documents are being processed in the background")

    def add_faq(self):
        question = self.faq_question_entry.get().strip()
        answer = self.faq_answer_entry.get().strip()
        if not question or not answer:
            messagebox.showwarning("Warning", "Please enter both question and answer")
            return
        faq_id = str(uuid.uuid4())
        self.faq_table.insert({
            "id": faq_id,
            "question": question,
            "answer": answer
        })
        self.load_faq_buttons()
        self.load_faq_list()
        self.faq_question_entry.delete(0, tk.END)
        self.faq_answer_entry.delete(0, tk.END)
        messagebox.showinfo("Success", "FAQ added successfully")

    def edit_faq(self):
        if not hasattr(self, 'selected_faq_id'):
            messagebox.showwarning("Warning", "No FAQ selected")
            return
        question = self.faq_question_entry.get().strip()
        answer = self.faq_answer_entry.get().strip()
        if not question or not answer:
            messagebox.showwarning("Warning", "Please enter both question and answer")
            return
        self.faq_table.update({
            "question": question,
            "answer": answer
        }, Query().id == self.selected_faq_id)
        self.load_faq_buttons()
        self.load_faq_list()
        self.faq_question_entry.delete(0, tk.END)
        self.faq_answer_entry.delete(0, tk.END)
        delattr(self, 'selected_faq_id')
        messagebox.showinfo("Success", "FAQ updated successfully")

    def delete_faq(self):
        if not hasattr(self, 'selected_faq_id'):
            messagebox.showwarning("Warning", "No FAQ selected")
            return
        if messagebox.askyesno("Confirm", "Delete this FAQ?"):
            self.faq_table.remove(Query().id == self.selected_faq_id)
            self.load_faq_buttons()
            self.load_faq_list()
            self.faq_question_entry.delete(0, tk.END)
            self.faq_answer_entry.delete(0, tk.END)
            delattr(self, 'selected_faq_id')
            messagebox.showinfo("Success", "FAQ deleted successfully")

    def add_synonym(self):
        synonyms = self.synonym_entry.get().strip()
        if not synonyms:
            messagebox.showwarning("Warning", "Please enter synonyms")
            return
        words = [w.strip().lower() for w in synonyms.split(',') if w.strip()]
        if len(words) < 2:
            messagebox.showwarning("Warning", "Enter at least two synonyms")
            return
        key = words[0]
        self.synonyms[key] = words
        with open(self.SYNONYMS_PATH, 'w') as f:
            json.dump(self.synonyms, f, indent=4)
        self.load_synonym_list()
        self.synonym_entry.delete(0, tk.END)
        messagebox.showinfo("Success", "Synonym group added/updated")

    def delete_synonym(self):
        selection = self.synonym_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No synonym group selected")
            return
        if messagebox.askyesno("Confirm", "Delete this synonym group?"):
            key = selection[0]
            del self.synonyms[key]
            with open(self.SYNONYMS_PATH, 'w') as f:
                json.dump(self.synonyms, f, indent=4)
            self.load_synonym_list()
            self.synonym_entry.delete(0, tk.END)
            messagebox.showinfo("Success", "Synonym group deleted")

    def export_chat(self):
        with open("chat_transcript.txt", "w", encoding="utf-8") as f:
            for query in self.chat_history:
                f.write(f"{query}\n")
        messagebox.showinfo("Success", "Chat history exported to chat_transcript.txt")

    def delete_document(self):
        selection = self.documents_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No document selected")
            return
        filename = self.documents_tree.item(selection[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Delete document '{filename}'?"):
            docs = self.paragraphs_table.all()
            image_paths = set()
            for doc in docs:
                if doc['filename'] == filename:
                    image_paths.update(doc['image_paths'])
            for path in image_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        logger.error(f"Error deleting image {path}: {str(e)}")
            self.paragraphs_table.remove(Query().filename == filename)
            self.tag_combo.configure(values=self.get_all_tags())
            self.tag_var.set("")
            self.load_documents_list()
            messagebox.showinfo("Success", f"Document '{filename}' deleted")

if __name__ == "__main__":
    try:
        app = RetailSupportBotApp()
        app.withdraw()  # Hide main window until initialization is complete
        app.mainloop()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        messagebox.showerror("Fatal Error", f"The application encountered an error and needs to close:\n{str(e)}")
        sys.exit(1)
