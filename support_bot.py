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

# Initialize database and folders
db = TinyDB("knowledge_base.json")
kb_folder = "kb_documents"
img_folder = "images"
os.makedirs(kb_folder, exist_ok=True)
os.makedirs(img_folder, exist_ok=True)

# Helper functions
def extract_text(file_path):
    ext = file_path.lower()
    if ext.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext.endswith(".docx"):
        doc = DocxDocument(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    elif ext.endswith(".pdf"):
        doc = fitz.open(file_path)
        return "\n".join([page.get_text() for page in doc])
    return ""

def generate_tags(text, top_n=5):
    vectorizer = TfidfVectorizer(stop_words="english", max_features=50)
    try:
        X = vectorizer.fit_transform([text])
        scores = X.toarray()[0]
        words = vectorizer.get_feature_names_out()
        top_indices = scores.argsort()[::-1][:top_n]
        return [words[i] for i in top_indices if scores[i] > 0]
    except:
        return []

def highlight_text(text_widget, keyword):
    text_widget.tag_remove("highlight", "1.0", tk.END)
    if keyword:
        idx = "1.0"
        while True:
            idx = text_widget.search(keyword, idx, nocase=1, stopindex=tk.END)
            if not idx:
                break
            lastidx = f"{idx}+{len(keyword)}c"
            text_widget.tag_add("highlight", idx, lastidx)
            idx = lastidx
        text_widget.tag_config("highlight", background="yellow")

def is_duplicate(file_name):
    return any(doc["name"] == file_name for doc in db.all())

# GUI
class KnowledgeBaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retail Support Demo")
        self.root.configure(bg="red")
        self.root.geometry("1000x600")

        self.main_frame = ttk.Frame(root, padding=5)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.setup_menu()
        self.setup_layout()
        self.load_documents()

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add KB Document", command=self.add_document)
        file_menu.add_command(label="Scan Document Folder", command=self.scan_folder)
        file_menu.add_command(label="View All Documents", command=self.show_all_documents)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

    def setup_layout(self):
        self.left_frame = ttk.Frame(self.main_frame, width=250)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.doc_listbox = tk.Listbox(self.left_frame)
        self.doc_listbox.pack(fill=tk.BOTH, expand=True)
        self.doc_listbox.bind("<<ListboxSelect>>", self.display_selected_document)

        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.text_preview = ScrolledText(self.right_frame, wrap=tk.WORD)
        self.text_preview.pack(fill=tk.BOTH, expand=True)

        self.image_label = ttk.Label(self.right_frame)
        self.image_label.pack()

        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(side=tk.BOTTOM, pady=5)

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.bottom_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, ipady=6)
        self.search_entry.bind("<Return>", lambda e: self.search_documents())

        self.search_button = ttk.Button(self.bottom_frame, text="Search", command=self.search_documents)
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(self.bottom_frame, text="Clear", command=self.clear_search)
        self.clear_button.pack(side=tk.LEFT, padx=5)

    def add_document(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Documents", "*.txt *.pdf *.docx")])
        for path in file_paths:
            name = os.path.basename(path)
            if is_duplicate(name):
                continue
            text = extract_text(path)
            tags = generate_tags(text)
            db.insert({"name": name, "content": text, "tags": tags})
            dest = os.path.join(kb_folder, name)
            if not os.path.exists(dest):
                with open(dest, "wb") as f_out, open(path, "rb") as f_in:
                    f_out.write(f_in.read())
        self.load_documents()

    def scan_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        for file in os.listdir(folder):
            if file.lower().endswith((".txt", ".pdf", ".docx")):
                full_path = os.path.join(folder, file)
                if not is_duplicate(file):
                    text = extract_text(full_path)
                    tags = generate_tags(text)
                    db.insert({"name": file, "content": text, "tags": tags})
                    dest = os.path.join(kb_folder, file)
                    if not os.path.exists(dest):
                        with open(dest, "wb") as f_out, open(full_path, "rb") as f_in:
                            f_out.write(f_in.read())
        self.load_documents()

    def load_documents(self):
        self.doc_listbox.delete(0, tk.END)
        for doc in db.all():
            self.doc_listbox.insert(tk.END, doc["name"])

    def display_selected_document(self, event=None):
        selection = self.doc_listbox.curselection()
        if not selection:
            return
        name = self.doc_listbox.get(selection[0])
        doc = next((d for d in db.all() if d["name"] == name), None)
        if doc:
            self.text_preview.delete("1.0", tk.END)
            self.text_preview.insert(tk.END, doc["content"])
            self.image_label.config(image="")
            self.show_image(name)

    def show_image(self, doc_name):
        base = os.path.splitext(doc_name)[0]
        for ext in [".jpg", ".jpeg", ".png"]:
            img_path = os.path.join(img_folder, base + ext)
            if os.path.exists(img_path):
                img = Image.open(img_path)
                img.thumbnail((400, 300))
                self.tk_img = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.tk_img)
                break

    def search_documents(self):
        query = self.search_var.get().strip()
        if not query:
            return
        results = []
        for doc in db.all():
            score = max(
                fuzz.partial_ratio(query.lower(), doc["name"].lower()),
                fuzz.partial_ratio(query.lower(), doc["content"].lower()),
                max((fuzz.partial_ratio(query.lower(), tag.lower()) for tag in doc.get("tags", [])), default=0)
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
            highlight_text(self.text_preview, query)
            self.show_image(top_doc["name"])

    def clear_search(self):
        self.search_var.set("")
        self.text_preview.delete("1.0", tk.END)
        self.image_label.config(image="")
        self.load_documents()

    def show_all_documents(self):
        all_docs = db.all()
        if not all_docs:
            messagebox.showinfo("Documents", "No documents in the database.")
            return
        doc_names = "\n".join(doc["name"] for doc in all_docs)
        messagebox.showinfo("All Documents", doc_names)

if __name__ == "__main__":
    root = tk.Tk()
    app = KnowledgeBaseApp(root)
    root.mainloop()
