import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tinydb import TinyDB, Query
from docx import Document as DocxDocument
import fitz  # PyMuPDF
from PIL import Image, ImageTk
from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
import threading
from datetime import datetime
import pickle
import logging

# Setup logging
logging.basicConfig(filename="app.log", level=logging.INFO)

# Initialize database and folders
db = TinyDB("knowledge_base.json")
doc_table = db.table("documents")
kb_folder = "kb_documents"
img_folder = "images"
os.makedirs(kb_folder, exist_ok=True)
os.makedirs(img_folder, exist_ok=True)

# Helper functions
def extract_text(file_path, max_images=5):
    ext = file_path.lower()
    images = []
    text = ""
    try:
        if ext.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif ext.endswith(".docx"):
            doc = DocxDocument(file_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            img_count = 0
            for rel in doc.part.rels.values():
                if "image" in rel.reltype and img_count < max_images:
                    img_data = rel.target_part.blob
                    img_name = f"{os.path.splitext(os.path.basename(file_path))[0]}_img{img_count}.png"
                    img_path = os.path.join(img_folder, img_name)
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    images.append(img_name)
                    img_count += 1
        elif ext.endswith(".pdf"):
            doc = fitz.open(file_path)
            text = "\n".join([page.get_text() for page in doc])
            img_count = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                for img_index, img in enumerate(page.get_images(full=True)):
                    if img_count >= max_images:
                        break
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    img_data = base_image["image"]
                    img_name = f"{os.path.splitext(os.path.basename(file_path))[0]}_page{page_num}_img{img_index}.png"
                    img_path = os.path.join(img_folder, img_name)
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    images.append(img_name)
                    img_count += 1
    except Exception as e:
        logging.error(f"Error extracting {file_path}: {str(e)}")
    return text, images

def generate_tags(text, top_n=5):
    vectorizer = TfidfVectorizer(stop_words="english", max_features=50)
    try:
        X = vectorizer.fit_transform([text])
        scores = X.toarray()[0]
        words = vectorizer.get_feature_names_out()
        top_indices = scores.argsort()[::-1][:top_n]
        tags = [words[i] for i in top_indices if scores[i] > 0]
        return tags, pickle.dumps((X, vectorizer))
    except:
        return [], None

def highlight_text(text_widget, keyword, case_sensitive=False):
    text_widget.tag_remove("highlight", "1.0", tk.END)
    if keyword:
        idx = "1.0"
        while True:
            idx = text_widget.search(keyword, idx, nocase=not case_sensitive, stopindex=tk.END)
            if not idx:
                break
            lastidx = f"{idx}+{len(keyword)}c"
            text_widget.tag_add("highlight", idx, lastidx)
            idx = lastidx
        text_widget.tag_config("highlight", background="yellow")

def is_duplicate(file_name):
    return any(doc["name"] == file_name for doc in doc_table.all())

# GUI
class KnowledgeBaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retail Support Demo")
        self.root.configure(bg="#f0f0f0")
        self.root.geometry("1000x600")
        self.root.resizable(True, True)
        self.root.style = ttk.Style()
        self.root.style.theme_use("clam")
        
        self.current_image_index = 0
        self.current_images = []
        self.status_var = tk.StringVar(value="Ready")
        self.font_size = 12
        self.zoom_level = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.tooltip = None
        self.word_wrap_var = tk.BooleanVar(value=True)
        self.case_sensitive_var = tk.BooleanVar(value=False)
        self.sort_var = tk.StringVar(value="Name")
        
        try:
            doc_table.all()
        except Exception as e:
            if messagebox.askyesno("Error", "Database corrupted. Clear and start fresh?"):
                doc_table.truncate()
                self.status_var.set("Database cleared")
            else:
                self.status_var.set("Database error; some features may not work")
            logging.error(f"Database error on startup: {str(e)}")
        
        self.setup_menu()
        self.setup_layout()
        self.setup_context_menu()
        self.load_documents()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add KB Document", command=self.add_document, accelerator="Ctrl+O")
        file_menu.add_command(label="Scan Document Folder", command=self.scan_folder)
        file_menu.add_command(label="Associate Image", command=self.associate_image)
        file_menu.add_command(label="Export Database", command=self.export_database)
        file_menu.add_command(label="Import Database", command=self.import_database)
        file_menu.add_command(label="View All Documents", command=self.show_all_documents)
        file_menu.add_command(label="Toggle High Contrast", command=self.toggle_high_contrast)
        menubar.add_cascade(label="File", menu=file_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
        self.root.bind("<Control-o>", lambda e: self.add_document())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus())

    def setup_layout(self):
        self.main_frame = ttk.Frame(self.root, padding=5)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.pack_propagate(False)

        self.left_frame = ttk.Frame(self.main_frame, width=250)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)

        self.doc_listbox = tk.Listbox(self.left_frame, selectmode=tk.MULTIPLE)
        self.doc_listbox.pack(fill=tk.BOTH, expand=True)
        self.doc_listbox.bind("<<ListboxSelect>>", self.display_selected_document)
        self.doc_listbox.bind("<Motion>", self.show_tooltip)
        self.doc_listbox.bind("<Leave>", self.hide_tooltip)

        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_frame.pack_propagate(False)

        self.text_preview = ScrolledText(self.right_frame, wrap=tk.WORD, font=("TkDefaultFont", self.font_size))
        self.text_preview.pack(fill=tk.BOTH, expand=True)

        self.image_frame = ttk.Frame(self.right_frame)
        self.image_frame.pack()
        self.image_canvas = tk.Canvas(self.image_frame, width=400, height=300)
        self.image_canvas.pack()
        self.image_canvas.bind("<MouseWheel>", self.zoom_image)
        self.image_canvas.bind("<ButtonPress-1>", self.start_pan)
        self.image_canvas.bind("<B1-Motion>", self.pan_image)
        self.prev_button = ttk.Button(self.image_frame, text="Prev", command=self.show_prev_image, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT)
        self.next_button = ttk.Button(self.image_frame, text="Next", command=self.show_next_image, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT)

        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(side=tk.BOTTOM, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.bottom_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, ipady=6)
        self.search_entry.accessible_name = "Search documents"
        self.search_entry.bind("<Return>", lambda e: self.search_documents())

        self.tag_filter = ttk.Combobox(self.bottom_frame, values=["All"], width=20)
        self.tag_filter.pack(side=tk.LEFT, padx=5)
        self.tag_filter.set("All")
        self.tag_filter.accessible_name = "Filter by tag"

        self.category_filter = ttk.Combobox(self.bottom_frame, values=["All"], width=20)
        self.category_filter.pack(side=tk.LEFT, padx=5)
        self.category_filter.set("All")
        self.category_filter.accessible_name = "Filter by category"

        self.sort_combobox = ttk.Combobox(self.bottom_frame, textvariable=self.sort_var, values=["Name", "Date", "Category"], width=10)
        self.sort_combobox.pack(side=tk.LEFT, padx=5)
        self.sort_combobox.bind("<<ComboboxSelected>>", lambda e: self.load_documents())

        self.word_wrap_check = ttk.Checkbutton(self.bottom_frame, text="Word Wrap", variable=self.word_wrap_var, command=self.toggle_word_wrap)
        self.word_wrap_check.pack(side=tk.LEFT, padx=5)

        self.case_sensitive_check = ttk.Checkbutton(self.bottom_frame, text="Case Sensitive", variable=self.case_sensitive_var)
        self.case_sensitive_check.pack(side=tk.LEFT, padx=5)

        ttk.Button(self.bottom_frame, text="+", command=self.increase_font_size).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.bottom_frame, text="-", command=self.decrease_font_size).pack(side=tk.LEFT, padx=2)

        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        ttk.Label(self.bottom_frame, text="Start Date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.bottom_frame, textvariable=self.start_date_var, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.bottom_frame, text="End Date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.bottom_frame, textvariable=self.end_date_var, width=12).pack(side=tk.LEFT, padx=5)

        self.search_button = ttk.Button(self.bottom_frame, text="Search", command=self.search_documents)
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(self.bottom_frame, text="Clear", command=self.clear_search)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Delete", command=self.delete_document)
        self.doc_listbox.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def add_document(self):
        def process_files():
            try:
                for path in file_paths:
                    name = os.path.basename(path)
                    if is_duplicate(name):
                        self.status_var.set(f"Skipped duplicate: {name}")
                        continue
                    text, images = extract_text(path)
                    tags, vector = generate_tags(text)
                    category = filedialog.askstring("Category", f"Enter category for {name}:", parent=self.root) or "Uncategorized"
                    doc_table.insert({"name": name, "content": text, "tags": tags, "images": images, "created": str(datetime.now()), "category": category, "vector": vector})
                    dest = os.path.join(kb_folder, name)
                    if not os.path.exists(dest):
                        with open(dest, "wb") as f_out, open(path, "rb") as f_in:
                            f_out.write(f_in.read())
                    self.status_var.set(f"Added {name} with {len(images)} images")
                self.root.after(0, self.load_documents)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to add document: {str(e)}"))
                logging.error(f"Add document error: {str(e)}")
        
        file_paths = filedialog.askopenfilenames(filetypes=[("Documents", "*.txt *.pdf *.docx")])
        if file_paths:
            threading.Thread(target=process_files, daemon=True).start()

    def scan_folder(self):
        def process_folder():
            try:
                for file in os.listdir(folder):
                    if file.lower().endswith((".txt", ".pdf", ".docx")):
                        full_path = os.path.join(folder, file)
                        if not is_duplicate(file):
                            text, images = extract_text(full_path)
                            tags, vector = generate_tags(text)
                            category = filedialog.askstring("Category", f"Enter category for {file}:", parent=self.root) or "Uncategorized"
                            doc_table.insert({"name": file, "content": text, "tags": tags, "images": images, "created": str(datetime.now()), "category": category, "vector": vector})
                            dest = os.path.join(kb_folder, file)
                            if not os.path.exists(dest):
                                with open(dest, "wb") as f_out, open(full_path, "rb") as f_in:
                                    f_out.write(f_in.read())
                self.root.after(0, self.load_documents)
                self.root.after(0, lambda: self.status_var.set("Folder scan completed"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to scan folder: {str(e)}"))
                logging.error(f"Scan folder error: {str(e)}")
        
        folder = filedialog.askdirectory()
        if folder:
            threading.Thread(target=process_folder, daemon=True).start()

    def load_documents(self):
        self.doc_listbox.delete(0, tk.END)
        docs = doc_table.all()
        sort_key = self.sort_var.get()
        if sort_key == "Date":
            docs.sort(key=lambda x: x.get("created", ""), reverse=True)
        elif sort_key == "Category":
            docs.sort(key=lambda x: x.get("category", "Uncategorized"))
        else:
            docs.sort(key=lambda x: x["name"])
        for doc in docs:
            self.doc_listbox.insert(tk.END, doc["name"])
        tags = ["All"] + sorted(set(tag for doc in doc_table.all() for tag in doc.get("tags", [])))
        categories = ["All"] + sorted(set(doc.get("category", "Uncategorized") for doc in doc_table.all()))
        self.tag_filter.config(values=tags)
        self.category_filter.config(values=categories)

    def display_selected_document(self, event=None):
        selection = self.doc_listbox.curselection()
        if not selection:
            return
        name = self.doc_listbox.get(selection[0])
        doc = next((d for d in doc_table.all() if d["name"] == name), None)
        if doc:
            self.text_preview.delete("1.0", tk.END)
            self.text_preview.insert(tk.END, doc["content"])
            self.show_image(name)
            self.status_var.set(f"Tags: {', '.join(doc['tags'])}, Category: {doc.get('category', 'Uncategorized')}, Size: {os.path.getsize(os.path.join(kb_folder, name))} bytes")

    def show_image(self, doc_name):
        self.image_canvas.delete("all")
        self.current_images = []
        self.current_image_index = 0
        doc = next((d for d in doc_table.all() if d["name"] == doc_name), None)
        if doc and doc.get("images"):
            self.current_images = doc["images"]
        else:
            base = os.path.splitext(doc_name)[0]
            for ext in [".jpg", ".jpeg", ".png"]:
                img_path = os.path.join(img_folder, base + ext)
                if os.path.exists(img_path):
                    self.current_images = [base + ext]
                    break
        self.update_image()

    def update_image(self):
        self.image_canvas.delete("all")
        if self.current_images and 0 <= self.current_image_index < len(self.current_images):
            img_path = os.path.join(img_folder, self.current_images[self.current_image_index])
            if os.path.exists(img_path):
                img = Image.open(img_path)
                width, height = img.size
                new_size = int(width * self.zoom_level), int(height * self.zoom_level)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                self.tk_img = ImageTk.PhotoImage(img)
                self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
                self.image_canvas.image = self.tk_img
                self.status_var.set(f"Image {self.current_image_index + 1} of {len(self.current_images)}, Zoom: {self.zoom_level:.1f}x")
            self.prev_button.config(state=tk.NORMAL if self.current_image_index > 0 else tk.DISABLED)
            self.next_button.config(state=tk.NORMAL if self.current_image_index < len(self.current_images) - 1 else tk.DISABLED)
        else:
            self.image_canvas.delete("all")
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            self.status_var.set("No images available")

    def zoom_image(self, event):
        scale = 1.1 if event.delta > 0 else 0.9
        self.zoom_level *= scale
        self.zoom_level = max(0.5, min(self.zoom_level, 3.0))
        self.update_image()

    def start_pan(self, event):
        self.image_canvas.scan_mark(event.x, event.y)
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def pan_image(self, event):
        self.image_canvas.scan_dragto(event.x, event.y, gain=1)
        self.status_var.set("Panning image")

    def show_prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.zoom_level = 1.0  # Reset zoom when switching images
            self.update_image()

    def show_next_image(self):
        if self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.zoom_level = 1.0  # Reset zoom when switching images
            self.update_image()

    def associate_image(self):
        selection = self.doc_listbox.curselection()
        if not selection:
            self.status_var.set("No document selected")
            return
        name = self.doc_listbox.get(selection[0])
        img_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if img_path:
            try:
                dest = os.path.join(img_folder, os.path.splitext(name)[0] + os.path.splitext(img_path)[1])
                with open(dest, "wb") as f_out, open(img_path, "rb") as f_in:
                    f_out.write(f_in.read())
                self.show_image(name)
                self.status_var.set(f"Associated image with {name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to associate image: {str(e)}")
                logging.error(f"Associate image error: {str(e)}")

    def search_documents(self):
        query = self.search_var.get().strip()
        tag_filter = self.tag_filter.get()
        category_filter = self.category_filter.get()
        case_sensitive = self.case_sensitive_var.get()
        start_date = self.start_date_var.get().strip()
        end_date = self.end_date_var.get().strip()
        if not query:
            return
        results = []
        for doc in doc_table.all():
            if tag_filter != "All" and tag_filter not in doc.get("tags", []):
                continue
            if category_filter != "All" and doc.get("category", "Uncategorized") != category_filter:
                continue
            if start_date:
                try:
                    if datetime.strptime(doc["created"], "%Y-%m-%d %H:%M:%S.%f") < datetime.strptime(start_date, "%Y-%m-%d"):
                        continue
                except ValueError:
                    self.status_var.set("Invalid start date format")
                    return
            if end_date:
                try:
                    if datetime.strptime(doc["created"], "%Y-%m-%d %H:%M:%S.%f") > datetime.strptime(end_date, "%Y-%m-%d"):
                        continue
                except ValueError:
                    self.status_var.set("Invalid end date format")
                    return
            name = doc["name"] if case_sensitive else doc["name"].lower()
            content = doc["content"] if case_sensitive else doc["content"].lower()
            query_cmp = query if case_sensitive else query.lower()
            score = max(
                fuzz.partial_ratio(query_cmp, name),
                fuzz.partial_ratio(query_cmp, content),
                max((fuzz.partial_ratio(query_cmp, tag if case_sensitive else tag.lower()) for tag in doc.get("tags", [])), default=0)
            )
            if score > 50:
                results.append((score, doc))
        results.sort(key=lambda x: x[0], reverse=True)
        self.doc_listbox.delete(0, tk.END)
        for _, doc in results:
            self.doc_listbox.insert(tk.END, doc["name"])
        if results:
            top_doc = results[0][1]
            self.text_preview.delete("1.0", tk.END)
            self.text_preview.insert(tk.END, top_doc["content"])
            highlight_text(self.text_preview, query, case_sensitive)
            self.show_image(top_doc["name"])
        else:
            self.status_var.set("No results found")

    def clear_search(self):
        self.search_var.set("")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.text_preview.delete("1.0", tk.END)
        self.image_canvas.delete("all")
        self.tag_filter.set("All")
        self.category_filter.set("All")
        self.load_documents()
        self.status_var.set("Search cleared")

    def delete_document(self):
        selections = self.doc_listbox.curselection()
        for index in selections[::-1]:
            name = self.doc_listbox.get(index)
            doc = next((d for d in doc_table.all() if d["name"] == name), None)
            if doc:
                try:
                    doc_table.remove(Query().name == name)
                    os.remove(os.path.join(kb_folder, name))
                    for img_name in doc.get("images", []):
                        img_path = os.path.join(img_folder, img_name)
                        if os.path.exists(img_path):
                            os.remove(img_path)
                    base = os.path.splitext(name)[0]
                    for ext in [".jpg", ".jpeg", ".png"]:
                        img_path = os.path.join(img_folder, base + ext)
                        if os.path.exists(img_path):
                            os.remove(img_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete {name}: {str(e)}")
                    logging.error(f"Delete document error: {str(e)}")
        self.load_documents()
        self.status_var.set(f"Deleted {len(selections)} documents")

    def export_database(self):
        try:
            export_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
            if export_path:
                with open(export_path, "w") as f:
                    f.write(doc_table.storage.read())
                self.status_var.set(f"Database exported to {export_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export database: {str(e)}")
            logging.error(f"Export database error: {str(e)}")

    def import_database(self):
        try:
            import_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
            if import_path:
                doc_table.storage.write(open(import_path, "r").read())
                self.load_documents()
                self.status_var.set(f"Database imported from {import_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import database: {str(e)}")
            logging.error(f"Import database error: {str(e)}")

    def show_all_documents(self):
        all_docs = doc_table.all()
        if not all_docs:
            messagebox.showinfo("Documents", "No documents in the database.")
            return
        doc_names = "\n".join(doc["name"] for doc in all_docs)
        messagebox.showinfo("All Documents", doc_names)

    def toggle_high_contrast(self):
        if self.root.style.theme_use() == "clam":
            self.root.style.theme_use("alt")
            self.status_var.set("High-contrast mode enabled")
        else:
            self.root.style.theme_use("clam")
            self.status_var.set("High-contrast mode disabled")

    def toggle_word_wrap(self):
        wrap = tk.WORD if self.word_wrap_var.get() else tk.NONE
        self.text_preview.config(wrap=wrap)
        self.status_var.set(f"Word wrap {'enabled' if wrap == tk.WORD else 'disabled'}")

    def increase_font_size(self):
        self.font_size += 2
        self.text_preview.config(font=("TkDefaultFont", self.font_size))
        self.status_var.set(f"Font size: {self.font_size}")

    def decrease_font_size(self):
        if self.font_size > 8:
            self.font_size -= 2
            self.text_preview.config(font=("TkDefaultFont", self.font_size))
            self.status_var.set(f"Font size: {self.font_size}")

    def show_tooltip(self, event):
        index = self.doc_listbox.nearest(event.y)
        if index >= 0:
            name = self.doc_listbox.get(index)
            doc = next((d for d in doc_table.all() if d["name"] == name), None)
            if doc:
                tooltip_text = f"Name: {doc['name']}\nTags: {', '.join(doc['tags'])}\nCategory: {doc.get('category', 'Uncategorized')}\nCreated: {doc['created']}"
                if self.tooltip:
                    self.tooltip.destroy()
                self.tooltip = tk.Toplevel(self.root)
                self.tooltip.wm_overrideredirect(True)
                self.tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
                label = tk.Label(self.tooltip, text=tooltip_text, background="yellow", relief=tk.SOLID, borderwidth=1)
                label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def show_help(self):
        help_text = (
            "Retail Support Demo\n\n"
            "- Add documents: File > Add KB Document (Ctrl+O)\n"
            "- Scan folder: File > Scan Document Folder\n"
            "- Associate image: File > Associate Image\n"
            "- Export/Import database: File > Export/Import Database\n"
            "- Search: Enter query in search bar (Ctrl+F), use tag/category filters\n"
            "- Filter by date: Enter dates in YYYY-MM-DD format\n"
            "- Sort documents: Use sort dropdown (Name, Date, Category)\n"
            "- Delete documents: Right-click on document in list\n"
            "- Navigate images: Use Prev/Next buttons, zoom with mouse wheel, pan with drag\n"
            "- Adjust text: Toggle word wrap, change font size with +/- buttons"
        )
        messagebox.showinfo("Help", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = KnowledgeBaseApp(root)
    root.mainloop()
