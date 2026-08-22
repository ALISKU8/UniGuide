import os
import time
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from google import genai
from google.genai import types
from dotenv import load_dotenv
import fitz  # مكتبة PyMuPDF القوية لدعم النصوص المعقدة

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 1. إعداد المسارات
DOCS_DIR = "docs"
DB_DIR = "chroma_db"


# 💡 دالة تحويل النصوص لأرقام (embeddings) عبر خدمة Gemini
# بدل تحميل نموذج ثقيل على الجهاز (PyTorch)، نرسل النص لخوادم جوجل ونستقبل الأرقام جاهزة
class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, task_type: str = "RETRIEVAL_DOCUMENT"):
        self.client = genai.Client(api_key=api_key)
        self.task_type = task_type

    def __call__(self, input: Documents) -> Embeddings:
        result = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=input,
            config=types.EmbedContentConfig(
                task_type=self.task_type,
                output_dimensionality=768,
            ),
        )
        return [e.values for e in result.embeddings]


# 2. تهيئة دالة التضمين الجديدة (بدل نموذج SentenceTransformer المحلي)
print("⏳ جاري الاتصال بخدمة Gemini للتضمين (embeddings)...")
gemini_embed_fn = GeminiEmbeddingFunction(
    api_key=GEMINI_API_KEY, task_type="RETRIEVAL_DOCUMENT"
)

# 3. تهيئة قاعدة البيانات
client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_or_create_collection(
    name="uj_knowledge_base",
    embedding_function=gemini_embed_fn
)


# دالة استخراج النص المطورة
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text


# تم زيادة حجم القطعة والتداخل للحفاظ على المواد النظامية كاملة
def chunk_text(text, chunk_size=1500, overlap=300):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def main():
    print("🔍 بدأنا في بناء قاعدة المعرفة باللغة العربية (عبر Gemini)...")
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
                    # محاولات إعادة عند حدوث خطأ مؤقت من الشبكة أو حد الطلبات
                    for attempt in range(3):
                        try:
                            collection.add(
                                documents=[chunk],
                                metadatas=[{"source": filename}],
                                ids=[f"doc_{doc_id_counter}_{i}"]
                            )
                            break
                        except Exception as e:
                            print(f"   ⚠️ محاولة {attempt + 1} فشلت: {e}")
                            time.sleep(2)
            doc_id_counter += 1

    print("\n✅ تم تشفير الملفات بنجاح باللغة العربية عبر Gemini! مجلد chroma_db جاهز.")


if __name__ == "__main__":
    main()
