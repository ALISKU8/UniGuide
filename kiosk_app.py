import os
import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
from google import genai
from dotenv import load_dotenv

# ==========================================
# 1. إعدادات الصفحة ودعم اللغة العربية (RTL)
# ==========================================
# التعديل الآمن: تحويل العرض إلى centered وإغلاق القائمة الجانبية تلقائياً في الجوال
st.set_page_config(
    page_title="UniGuide - الخدمة الذاتية", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# كود CSS آمن يخفي الهيدر والفوتر دون المساس بأبعاد الـ React أو الشاشة
st.markdown("""
    <style>
        .stApp {
            direction: rtl;
        }
        p, div, h1, h2, h3, h4, h5, h6, ul, li, span {
            text-align: right !important;
        }
        .stChatInputContainer textarea {
            direction: rtl;
            text-align: right;
        }
        /* إخفاء الشريط العلوي والسفلي بأسلوب غير ضار للحسابات */
        header { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        [data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. تحميل المتغيرات والاتصال بالخدمات[cite: 7]
# ==========================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# استخدام cache لمنع إعادة تحميل قاعدة البيانات مع كل رسالة (لتسريع الأداء)[cite: 7]
@st.cache_resource
def load_database():
    chroma_client = chromadb.PersistentClient(path="chroma_db")
    arabic_embed_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    collection = chroma_client.get_collection(
        name="uj_knowledge_base", 
        embedding_function=arabic_embed_model
    )
    return collection

collection = load_database()

# ==========================================
# 3. القائمة الجانبية (للتوجيه الشخصي وإنهاء الجلسة)[cite: 7]
# ==========================================
with st.sidebar:
    # تم استخدام use_container_width=True لتفادي أخطاء الإصدارات الجديدة[cite: 7]
    st.image("UniGuide_QR_Logo.png", use_container_width=True)
    st.markdown("### 📱 خدمات الطالب الشخصية")
    st.info("لمعرفة خطتك الدراسية أو حساب معدلك التراكمي، امسح الكود واستخدم بوت التليقرام في جوالك.")
    
    st.markdown("---")
    
    # زر هام جداً لإنهاء الجلسة للطالب الحالي وحماية خصوصية الدردشة[cite: 7]
    if st.button("🔄 إنهاء الجلسة (طالب جديد)", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. واجهة الدردشة الرئيسية[cite: 7]
# ==========================================
st.title("🤖 المرشد الأكاديمي الذكي (UniGuide)")
st.write("مرحباً بك في الكلية التطبيقية. تفضل بطرح استفسارك الأكاديمي العام.")

# تهيئة سجل المحادثة في الذاكرة المؤقتة[cite: 7]
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة في المحادثة[cite: 7]
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==========================================
# 5. استقبال الأسئلة ومعالجتها (AI & RAG)[cite: 7]
# ==========================================
if prompt := st.chat_input("اكتب استفسارك هنا (مثال: كيف أتواصل مع شؤون التعليم؟)"):
    # إضافة سؤال الطالب وعرضه[cite: 7]
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # تجهيز وعرض رد المساعد الذكي[cite: 7]
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ جاري البحث في أنظمة الجامعة...")
        
        try:
            # 💡 التعديل الأهم 1: رفع عدد النتائج من 5 إلى 20 لتوحيد محرك البحث مع بوت التليقرام
            results = collection.query(query_texts=[prompt], n_results=20)
            context_text = ""
            if results['documents'] and len(results['documents'][0]) > 0:
                context_text = "\n\n".join(results['documents'][0])
            
            # 💡 التعديل الأهم 2: حقن التعليمات الصارمة والموحدة لتطابق البوت
            augmented_prompt = f"""
            أنت مساعد أكاديمي لطلاب الكلية التطبيقية بجامعة جدة.
            سؤال الطالب: {prompt}
            
            🤖 هوية النظام (حقائق ثابتة لا تبحث عنها في اللوائح):
            - أنت نظام "UniGuide" (المرشد الأكاديمي الذكي) للخدمة الذاتية.
            - انت مخصص للكلية التطبيقية بجامعة جدة
            
            🏢 الهيكل التنظيمي المعتمد للكلية التطبيقية:
            - المرجع الأعلى: رئيس الجامعة، يليه المجلس التنفيذي للكلية التطبيقية.
            - الإدارة العليا للكلية: الرئيس التنفيذي للكلية التطبيقية (وترتبط به مباشرة إدارة "العلاقات والاتصال المؤسسي").
            - المسار الأول (العمليات الأساسية): تحت إدارة "نائب الرئيس التنفيذي"، وتتبعه: (وحدة الخريجين والتوظيف، وحدة الشؤون التعليمية، وحدة البرامج، وحدة الشهادات المهنية).
            - المسار الثاني (الخدمات): تحت إدارة "مساعد الرئيس التنفيذي للخدمات المساندة"، وتتبعه: (وحدة التخطيط، وحدة الشراكات والتسويق، وحدة المالية والقانونية، وحدة التدريب).
            
            🎯 تعليمات التوجيه الذكي للمشكلات:
            - 🚫 التحويل بين الدبلومات: يمنع التحويل بين برامج الدبلوم إطلاقاً.
            - وحدة التدريب التعاوني: لأي أسئلة عن التدريب، وجهه للإيميل: ac.internshipunit@uj.edu.sa
            - وحدة الشؤون التعليمية: لأي أسئلة عن (الجداول، الحرمان، الشؤون الأكاديمية)، وجهه للإيميل: ac.edu@UJ.EDU.SA
            - وحدة الشهادات المهنية: للإيميل: pcert.ap@uj.edu.sa
            - وحدة التواصل: للاستفسارات العامة، وجهه للإيميل: ac.info@uj.edu.sa
            - إذا سأل عن (الخطط الدراسية، مواد التخصص، أو حساب المعدل): اعتذر بلباقة واطلب منه مسح الباركود الموجود في يسار الشاشة لاستخدام بوت التليقرام المخصص للخدمات الشخصية.
            
            📚 المعلومات الرسمية الإضافية (من لوائح الجامعة):
            {context_text}
            
            شروط الإجابة:
            1. ابحث بدقة داخل (المعلومات الرسمية الإضافية / اللوائح) المسترجعة أعلاه للإجابة على أسئلة اللوائح، الحذف والإضافة، والعبء الدراسي.
            2. اعتمد على (تعليمات التوجيه الذكي) أولاً في حال تطابق السؤال معها.
            3. أجب بشكل مباشر، واضح، ومنسق بنقاط إذا لزم الأمر.
            4. إذا كان السؤال عن الأنظمة ولم تجد الإجابة في النصوص نهائياً، أجب بكلمة واحدة فقط: UNKNOWN_QUERY
            """
            
            # 3. إرسال الطلب لنموذج Gemini[cite: 7]
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=augmented_prompt
            )
            
            ai_reply = response.text.strip()
            
            # 💡 التعديل الأهم 3: معالجة الرد في حال لم يجد إجابة في اللوائح
            if "UNKNOWN_QUERY" in ai_reply:
                fallback_message = (
                    "أعتذر منك، بحثت في اللوائح والأنظمة ولم أجد إجابة دقيقة لسؤالك 😔.\n"
                    "يرجى التواصل مع وحدة الشؤون التعليمية عبر البريد الإلكتروني: ac.edu@UJ.EDU.SA"
                )
                message_placeholder.markdown(fallback_message)
                st.session_state.messages.append({"role": "assistant", "content": fallback_message})
            else:
                message_placeholder.markdown(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            
        except Exception as e:
            error_msg = "⚠️ عذراً، يوجد ضغط عالي حالياً على خوادم النظام. يرجى المحاولة بعد قليل."
            message_placeholder.markdown(error_msg)
            print(f"Error: {e}") # طباعة الخطأ في الشاشة السوداء للمطور[cite: 7]