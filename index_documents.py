import os
import re
import pdfplumber
from docx import Document
from tinydb import TinyDB
from nltk.corpus import stopwords
from collections import Counter

DOCS_FOLDER = './docs'
DB_PATH = './data/knowledge_db.json'
STOPWORDS = set(stopwords.words('english'))

def generate_tags(text, top_n=5):
    words = re.findall(r'\b\w+\b', text.lower())
    filtered = [word for word in words if word not in STOPWORDS and len(word) > 3]
    common = Counter(filtered).most_common(top_n)
    return [word for word, _ in common]

def extract_docx_text(filepath):
    doc = Document(filepath)
    return [para.text.strip() for para in doc.paragraphs if para.text.strip()]

def extract_pdf_text(filepath):
    text_chunks = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    if line.strip():
                        text_chunks.append(line.strip())
    return text_chunks

def index_documents():
    os.makedirs('./data', exist_ok=True)
    db = TinyDB(DB_PATH)
    db.truncate()

    for filename in os.listdir(DOCS_FOLDER):
        path = os.path.join(DOCS_FOLDER, filename)
        if filename.endswith('.docx'):
            paragraphs = extract_docx_text(path)
        elif filename.endswith('.pdf'):
            paragraphs = extract_pdf_text(path)
        else:
            continue

        for para in paragraphs:
            tags = generate_tags(para) + generate_tags(filename)
            db.insert({
                'file': filename,
                'paragraph': para,
                'tags': list(set(tags))
            })

    print(f"✅ Indexed documents saved to {DB_PATH}")

if __name__ == "__main__":
    import nltk
    nltk.download('stopwords')
    index_documents()