import os
import fitz  # هذا هو المستورد الناقص (مكتبة PyMuPDF)
import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
from google import genai
from dotenv import load_dotenv

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(page_title="UniGuide - الخدمة الذاتية", layout="wide")

st.markdown("""
    <style>
        .stApp { direction: rtl; }
        p, div, h1, h2, h3, h4, h5, h6, ul, li, span { text-align: right !important; }
        .stChatInputContainer textarea { direction: rtl; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. تحميل الخدمات
# ==========================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

@st.cache_resource
def load_database():
    # تم تغييرها إلى Client() (In-Memory) لحل مشكلة InternalError على السحابة
    chroma_client = chromadb.Client()
    
    arabic_embed_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    collection = chroma_client.create_collection(
        name="university_regulations",
        embedding_function=arabic_embed_model
    )
    
    # بناء القاعدة ذاتياً من مجلد docs/
    docs_dir = "docs"
    if os.path.exists(docs_dir):
        doc_id_counter = 1
        for filename in os.listdir(docs_dir):
            if filename.endswith(".pdf"):
                file_path = os.path.join(docs_dir, filename)
                doc = fitz.open(file_path)
                full_text = ""
                for page in doc:
                    full_text += page.get_text() + "\n"
                
                chunk_size = 1000
                overlap = 200
                chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size - overlap)]
                
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) > 10:
                        collection.add(
                            documents=[chunk],
                            metadatas=[{"source": filename}],
                            ids=[f"doc_{doc_id_counter}_{i}"]
                        )
                doc_id_counter += 1
    return collection

collection = load_database()

# ==========================================
# 3. واجهة الدردشة
# ==========================================
with st.sidebar:
    st.image("UniGuide_QR_Logo.png", use_container_width=True)
    st.markdown("### 📱 خدمات الطالب الشخصية")
    st.info("لمعرفة خطتك الدراسية أو حساب معدلك التراكمي، استخدم بوت التليقرام.")
    if st.button("🔄 إنهاء الجلسة (طالب جديد)", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

st.title("🤖 المرشد الأكاديمي الذكي (UniGuide)")
st.write("مرحباً بك في الكلية التطبيقية. تفضل بطرح استفسارك.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("اكتب استفسارك هنا..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ جاري البحث في أنظمة الجامعة...")
        
        try:
            results = collection.query(query_texts=[prompt], n_results=20)
            context_text = "\n\n".join(results['documents'][0]) if results['documents'] and len(results['documents'][0]) > 0 else ""
            
            augmented_prompt = f"""
            أنت مساعد أكاديمي لطلاب الكلية التطبيقية بجامعة جدة.
            سؤال الطالب: {prompt}
            
            🏢 الهيكل التنظيمي المعتمد:
            - الرئيس التنفيذي للكلية التطبيقية.
            - المسار الأول: (وحدة الخريجين، الشؤون التعليمية، البرامج، الشهادات المهنية).
            - المسار الثاني: (وحدة التخطيط، الشراكات، المالية والقانونية، التدريب).
            
            🎯 تعليمات التوجيه:
            - التحويل بين الدبلومات: ممنوع.
            - التدريب التعاوني: ac.internshipunit@uj.edu.sa
            - الشؤون التعليمية (جداول، حرمان): ac.edu@UJ.EDU.SA
            - الشهادات المهنية: pcert.ap@uj.edu.sa
            - استفسارات عامة: ac.info@uj.edu.sa
            - إذا سأل عن (الخطط الدراسية، مواد التخصص، حساب المعدل): اعتذر واطلب منه استخدام بوت التليقرام.
            
            📚 اللوائح: {context_text}
            
            شروط الإجابة:
            1. أجب بدقة من اللوائح.
            2. استخدم التوجيهات أعلاه للبريد الإلكتروني.
            3. إذا لم تجد الإجابة، أجب بكلمة واحدة فقط: UNKNOWN_QUERY
            """
            
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash', # تأكد أن هذا هو الموديل الصحيح أو استخدم 'gemini-1.5-flash'
                contents=augmented_prompt
            )
            
            ai_reply = response.text.strip()
            if "UNKNOWN_QUERY" in ai_reply:
                ai_reply = "أعتذر منك، لم أجد إجابة دقيقة في لوائح الكلية. يرجى التواصل مع وحدة الشؤون التعليمية: ac.edu@UJ.EDU.SA"
            
            message_placeholder.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            
        except Exception as e:
            message_placeholder.markdown("⚠️ عذراً، يوجد ضغط عالي حالياً. يرجى المحاولة بعد قليل.")