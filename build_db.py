import os
import chromadb
from chromadb.utils import embedding_functions
import fitz  # مكتبة PyMuPDF القوية لدعم النصوص المعقدة

# 1. إعداد المسارات
DOCS_DIR = "docs"
DB_DIR = "chroma_db"

# 2. تحميل نموذج الذكاء الاصطناعي متعدد اللغات (يدعم العربية بقوة)
print("⏳ جاري تحميل نموذج اللغة العربية (قد يأخذ دقيقة في أول مرة)...")
arabic_embed_model = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# 3. تهيئة قاعدة البيانات
client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_or_create_collection(
    name="uj_knowledge_base", 
    embedding_function=arabic_embed_model
)

# دالة استخراج النص المطورة
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

# التعديل الأهم: تم زيادة حجم القطعة والتداخل للحفاظ على المواد النظامية كاملة
def chunk_text(text, chunk_size=1500, overlap=300):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap 
    return chunks

def main():
    print("🔍 بدأنا في بناء قاعدة المعرفة باللغة العربية...")
    doc_id_counter = 1
    
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".pdf"):
            print(f"📄 جاري معالجة: {filename}")
            file_path = os.path.join(DOCS_DIR, filename)
            
            full_text = extract_text_from_pdf(file_path)
            chunks = chunk_text(full_text)
            
            for i, chunk in enumerate(chunks):
                # فلترة الأجزاء الفارغة لتسريع البحث
                if len(chunk.strip()) > 10: 
                    collection.add(
                        documents=[chunk],
                        metadatas=[{"source": filename}],
                        ids=[f"doc_{doc_id_counter}_{i}"]
                    )
            doc_id_counter += 1
            
    print("\n✅ تم تشفير الملفات بنجاح باللغة العربية! مجلد chroma_db جاهز.")

if __name__ == "__main__":
    main()