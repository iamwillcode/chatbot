import json
import tkinter as tk
from tkinter import scrolledtext, filedialog, ttk, messagebox
from tinydb import TinyDB
from fuzzywuzzy import fuzz
import re

DB_PATH = './data/knowledge_db.json'
SYN_FILE = './synonyms.json'

db = TinyDB(DB_PATH)
entries = db.all()

with open(SYN_FILE, 'r', encoding='utf-8') as f:
    SYNONYMS = json.load(f)

def expand_query_with_synonyms(query):
    words = query.lower().split()
    expanded = set(words)
    for w in words:
        for key, syns in SYNONYMS.items():
            if w == key or w in syns:
                expanded.add(key)
                expanded.update(syns)
    return list(expanded)

def highlight_keywords(text_widget, text, keywords):
    text_widget.configure(state='normal')
    text_widget.insert(tk.END, "\n")
    last_pos = 0
    lower_text = text.lower()
    matches = []
    for kw in keywords:
        start = 0
        while True:
            idx = lower_text.find(kw, start)
            if idx == -1:
                break
            matches.append((idx, idx+len(kw)))
            start = idx + len(kw)

    matches.sort()
    pos = 0
    for start_idx, end_idx in matches:
        if pos < start_idx:
            text_widget.insert(tk.END, text[pos:start_idx])
        text_widget.insert(tk.END, text[start_idx:end_idx], "highlight")
        pos = end_idx
    if pos < len(text):
        text_widget.insert(tk.END, text[pos:])
    text_widget.insert(tk.END, "\n\n")
    text_widget.configure(state='disabled')

def sanitize_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def search_knowledge_base(query, selected_tag=None, selected_file_type=None, threshold=65, max_results=10):
    expanded_words = expand_query_with_synonyms(query)
    results = []
    for item in entries:
        if selected_tag and selected_tag != "All" and selected_tag not in item.get('tags', []):
            continue
        if selected_file_type and selected_file_type != "All" and not item['file'].endswith(selected_file_type):
            continue
        para = item['paragraph'].lower()
        if any(fuzz.partial_ratio(word, para) >= threshold for word in expanded_words):
            score = max(fuzz.partial_ratio(word, para) for word in expanded_words)
            results.append((score, item))
    results.sort(reverse=True, key=lambda x: x[0])
    return results[:max_results]

def send_message():
    user_input = entry.get()
    if not user_input.strip():
        return
    append_chat(f"You: {user_input}\n", "user")

    tag_filter = tag_var.get()
    file_type_filter = file_type_var.get()

    results = search_knowledge_base(user_input, tag_filter, file_type_filter)
    if not results:
        append_chat("Bot: Sorry, I couldn’t find anything relevant.\n\n", "bot")
    else:
        grouped = {}
        for score, item in results:
            grouped.setdefault(item['file'], []).append((score, sanitize_text(item['paragraph'])))

        for file, matches in grouped.items():
            append_chat(f"📄 {file}\n", "file")
            for score, para in matches:
                append_chat(f"🧠 (Score: {score}) ", "bot")
                highlight_keywords(chat_window, para, expand_query_with_synonyms(user_input))

    add_to_history(user_input)
    entry.delete(0, tk.END)

def append_chat(text, tag=None):
    chat_window.configure(state='normal')
    chat_window.insert(tk.END, text, tag)
    chat_window.see(tk.END)
    chat_window.configure(state='disabled')

def export_chat():
    chat_content = chat_window.get("1.0", tk.END)
    save_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(chat_content)
        messagebox.showinfo("Export Successful", f"Chat exported to:\n{save_path}")

history = []
MAX_HISTORY = 20

def add_to_history(query):
    if query not in history:
        history.insert(0, query)
        if len(history) > MAX_HISTORY:
            history.pop()
    update_history_panel()

def update_history_panel():
    history_listbox.delete(0, tk.END)
    for q in history:
        history_listbox.insert(tk.END, q)

def on_history_select(event):
    selection = history_listbox.curselection()
    if selection:
        value = history_listbox.get(selection[0])
        entry.delete(0, tk.END)
        entry.insert(0, value)
        send_message()

def add_faq_buttons(faq_list):
    for faq in faq_list:
        btn = tk.Button(faq_frame, text=faq, width=20, command=lambda q=faq: on_faq_click(q))
        btn.pack(pady=2)

def on_faq_click(question):
    entry.delete(0, tk.END)
    entry.insert(0, question)
    send_message()

window = tk.Tk()
window.title("Support Knowledge Bot - Modernized")
window.geometry("900x650")
window.configure(bg="#f0f2f5")

main_frame = tk.Frame(window, bg="#f0f2f5")
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

chat_frame = tk.Frame(main_frame, bg="white", bd=2, relief=tk.SUNKEN)
chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

chat_window = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Segoe UI", 11), bg="white", fg="#333333")
chat_window.pack(fill=tk.BOTH, expand=True)
chat_window.configure(state='disabled')
chat_window.tag_config("user", foreground="#1a73e8", font=("Segoe UI", 11, "bold"))
chat_window.tag_config("bot", foreground="#202124", font=("Segoe UI", 11))
chat_window.tag_config("file", foreground="#34a853", font=("Segoe UI", 10, "italic"))
chat_window.tag_config("highlight", background="#fff475")

input_frame = tk.Frame(chat_frame, bg="white")
input_frame.pack(fill=tk.X, padx=5, pady=5)

entry = tk.Entry(input_frame, font=("Segoe UI", 13))
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
entry.bind("<Return>", lambda e: send_message())

send_button = tk.Button(input_frame, text="Search", bg="#1a73e8", fg="white", font=("Segoe UI", 11), command=send_message)
send_button.pack(side=tk.LEFT, padx=5)

export_button = tk.Button(input_frame, text="Export Chat", bg="#34a853", fg="white", font=("Segoe UI", 11), command=export_chat)
export_button.pack(side=tk.LEFT)

sidebar = tk.Frame(main_frame, bg="#f0f2f5", width=260)
sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(10,0))

tk.Label(sidebar, text="Filters", font=("Segoe UI", 12, "bold"), bg="#f0f2f5").pack(anchor="w", pady=(5,2), padx=5)

tag_var = tk.StringVar(value="All")
all_tags = set(tag for entry in entries for tag in entry.get('tags', []))
tag_dropdown = ttk.Combobox(sidebar, textvariable=tag_var, values=["All"] + sorted(all_tags), state="readonly", width=25)
tag_dropdown.pack(padx=5, pady=2)

file_type_var = tk.StringVar(value="All")
all_file_types = set(entry['file'].split('.')[-1] for entry in entries)
file_dropdown = ttk.Combobox(sidebar, textvariable=file_type_var, values=["All"] + sorted(all_file_types), state="readonly", width=25)
file_dropdown.pack(padx=5, pady=(0,10))

tk.Label(sidebar, text="Search History", font=("Segoe UI", 12, "bold"), bg="#f0f2f5").pack(anchor="w", pady=(10,2), padx=5)
history_listbox = tk.Listbox(sidebar, height=8, font=("Segoe UI", 10))
history_listbox.pack(padx=5, fill=tk.X)
history_listbox.bind("<<ListboxSelect>>", on_history_select)

tk.Label(sidebar, text="Quick FAQs", font=("Segoe UI", 12, "bold"), bg="#f0f2f5").pack(anchor="w", pady=(10,2), padx=5)
faq_frame = tk.Frame(sidebar, bg="#f0f2f5")
faq_frame.pack(padx=5, fill=tk.X)

example_faqs = [
    "How do I reset my password?",
    "Why is my printer offline?",
    "WiFi keeps disconnecting",
    "How to update firmware?",
    "Refund policy"
]
add_faq_buttons(example_faqs)

window.mainloop()