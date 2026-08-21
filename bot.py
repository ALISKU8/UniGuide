import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# --- حماية ويندوز من السكون (The Anti-Sleep Hack) ---
try:
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
except Exception as e:
    print(f"Anti-sleep warning: {e}")

import chromadb
from chromadb.utils import embedding_functions
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from google import genai

# ==========================================
# 1. إعدادات البوت والاتصالات
# ==========================================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. نظام قواعد البيانات الدائمة
# ==========================================
STUDENTS_DB_FILE = "students_db.json"
LOGS_DB_FILE = "unanswered_logs.json"

def load_students_db():
    if os.path.exists(STUDENTS_DB_FILE):
        with open(STUDENTS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_students_db(db):
    with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

users_db = load_students_db()

def log_unanswered_question(user_info, question, user_id):
    student_name = user_info['name'] if user_info else f"مجهول (ID: {user_id})"
    major = user_info['major'] if user_info else "غير مسجل"
    level = user_info['level'] if user_info else "غير مسجل"
    
    log_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "student_name": student_name,
        "major": major,
        "level": level,
        "question": question
    }
    
    logs = []
    if os.path.exists(LOGS_DB_FILE):
        with open(LOGS_DB_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
            
    logs.append(log_entry)
    
    with open(LOGS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)

# --- إعدادات ChromaDB ---
print("⏳ جاري الاتصال بقاعدة لوائح الجامعة (ChromaDB)...")
chroma_client = chromadb.PersistentClient(path="chroma_db")
arabic_embed_model = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
collection = chroma_client.get_collection(
    name="uj_knowledge_base", 
    embedding_function=arabic_embed_model
)

try:
    with open("study_plans.json", "r", encoding="utf-8") as f:
        study_plans = json.load(f)
except FileNotFoundError:
    study_plans = {}

# ==========================================
# 3. دالة الاستنتاج والتنظيف الذكي
# ==========================================
async def extract_clean_info(info_type: str, user_text: str) -> str:
    if "المستوى" in info_type:
        logic_rules = """
        - ابحث عن الرقم الصريح في الجملة أولاً. إذا قال الطالب (ثالث ترم، الترم 3، مستوى ثالث)، فالنتيجة فوراً هي الرقم (3).
        - فقط إذا قال (آخر ترم) أو (على وشك التخرج) ولم يذكر رقماً، استنتج الرقم بناءً على الدرجة (الدبلوم = 5، البكالوريوس = 8).
        - أرجع النتيجة كرقم فقط (مثال: 3).
        """
    else:
        logic_rules = """
        - استخرج الكلمة المقصودة فقط كما هي من النص.
        - ممنوع قطعاً تحويل النصوص إلى أرقام، وممنوع الاستنتاج.
        """

    prompt = f"""
    مهمتك هي استخراج '{info_type}' من جملة المستخدم التالية.
    الجملة: "{user_text}"
    تعليمات الاستخراج الصارمة:
    {logic_rules}
    - أرجع النتيجة النهائية المطلوبة فقط، بدون أي شرح، بدون فواصل.
    """
    try:
        response = await gemini_client.aio.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except:
        return user_text 

# ==========================================
# 4. حالات المحادثة (FSM)
# ==========================================
class UserProfile(StatesGroup):
    waiting_for_name = State()    
    waiting_for_college = State() 
    waiting_for_major = State()   
    waiting_for_degree = State()  
    waiting_for_level = State()   

class GPACalculator(StatesGroup):
    waiting_for_current_gpa = State()
    waiting_for_completed_hours = State()
    waiting_for_courses_list = State()

# ==========================================
# 5. مسار التسجيل
# ==========================================
@dp.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext):
    welcome_text = (
        "أهلاً بك في UniGuide، المساعد الأكاديمي لطلاب (جامعة جدة).\n\n"
        "لتقديم إجابات دقيقة تتناسب مع خطتك الدراسية، يرجى إعداد ملفك الأكاديمي.\n\n"
        "🔹 السؤال الأول: ما هو اسمك الأول؟ (الاسم الأول فقط)"
    )
    await message.answer(welcome_text)
    await state.set_state(UserProfile.waiting_for_name)

@dp.message(UserProfile.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    wait_msg = await message.answer("⏳ جاري الحفظ...")
    clean_name = await extract_clean_info("الاسم الأول فقط", message.text)
    await state.update_data(name=clean_name)
    await wait_msg.edit_text(f"حياك الله يا {clean_name}.\n\n🔹 السؤال الثاني: في أي كلية تدرس؟ (مثال: الكلية التطبيقية، كلية الأعمال...)")
    await state.set_state(UserProfile.waiting_for_college)

@dp.message(UserProfile.waiting_for_college)
async def process_college(message: types.Message, state: FSMContext):
    wait_msg = await message.answer("⏳ جاري الحفظ...")
    clean_college = await extract_clean_info("اسم الكلية", message.text)
    await state.update_data(college=clean_college)
    await wait_msg.edit_text("🔹 السؤال الثالث: ما هو تخصصك الدقيق؟ (مثال: إدارة مبيعات، أمن سيبراني...)")
    await state.set_state(UserProfile.waiting_for_major)

@dp.message(UserProfile.waiting_for_major)
async def process_major(message: types.Message, state: FSMContext):
    wait_msg = await message.answer("⏳ جاري الحفظ...")
    clean_major = await extract_clean_info("اسم التخصص الأكاديمي", message.text)
    await state.update_data(major=clean_major)
    await wait_msg.edit_text("🔹 السؤال الرابع: هل تدرس في برنامج 'البكالوريوس' أم 'الدبلوم'؟")
    await state.set_state(UserProfile.waiting_for_degree)

@dp.message(UserProfile.waiting_for_degree)
async def process_degree(message: types.Message, state: FSMContext):
    wait_msg = await message.answer("⏳ جاري الحفظ...")
    clean_degree = await extract_clean_info("الدرجة العلمية", message.text)
    await state.update_data(degree=clean_degree)
    
    level_text = (
        "🔹 السؤال الخامس والأخير: في أي مستوى دراسي أنت الآن؟\n"
        "💡 (تستطيع كتابة الرقم مباشرة، أو وصف حالتك مثل 'هذا آخر ترم لي')."
    )
    await wait_msg.edit_text(level_text)
    await state.set_state(UserProfile.waiting_for_level)

@dp.message(UserProfile.waiting_for_level)
async def process_level(message: types.Message, state: FSMContext):
    wait_msg = await message.answer("⏳ جاري إعداد ملفك...")
    user_data = await state.get_data()
    context_for_inference = f"الطالب يدرس {user_data['degree']}. جملته: {message.text}"
    
    clean_level = await extract_clean_info("المستوى الدراسي كرقم", context_for_inference)
    await state.update_data(level=clean_level)
    
    final_data = await state.get_data()
    user_id = str(message.from_user.id) 
    
    users_db[user_id] = {
        'name': final_data['name'],
        'college': final_data['college'],
        'major': final_data['major'],
        'level': final_data['level'],
        'degree': final_data['degree']
    }
    save_students_db(users_db)
    
    summary_text = (
        f"✅ تم إعداد ملفك بنجاح.\n\n"
        f"📋 بياناتك:\n"
        f"الاسم: {final_data['name']}\n"
        f"الدرجة: {final_data['degree']}\n"
        f"الكلية: {final_data['college']}\n"
        f"التخصص: {final_data['major']} (المستوى {final_data['level']})\n\n"
        f"يمكنك الآن الاستفسار عن اللوائح، أو استخدام القائمة السريعة أدناه:"
    )
    
    main_menu = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 الأنظمة واللوائح", callback_data="menu_faq")],
        [InlineKeyboardButton(text="🗺️ الخطط الدراسية", callback_data="menu_plan")],
        [InlineKeyboardButton(text="🌟 الأندية والتطوع", callback_data="menu_clubs")],
        [InlineKeyboardButton(text="🧮 حاسبة المعدل التراكمي", callback_data="menu_gpa")]
    ])
    await wait_msg.edit_text(summary_text, reply_markup=main_menu)
    await state.clear()

# ==========================================
# 6. القوائم الجانبية
# ==========================================
@dp.callback_query(F.data == "menu_faq")
async def faq_callback(callback: types.CallbackQuery):
    await callback.message.answer("📚 يمكنك كتابة أي استفسار حول اللوائح والأنظمة الجامعية وسأقوم بالرد عليك مباشرة.")
    await callback.answer()

@dp.callback_query(F.data == "menu_plan")
async def plan_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_info = users_db.get(user_id)
    if not user_info:
        await callback.message.answer("عذراً، يرجى إعداد ملفك أولاً عبر أمر /start")
        await callback.answer()
        return

    major = user_info['major']
    level = user_info['level']
    plan = study_plans.get(major, {}).get(str(level))
    
    if plan:
        msg = f"🗺️ **الخطة الدراسية - المستوى {level}**\nتخصص: {major}\n\n"
        for course in plan:
            msg += f"📚 {course['name']} ({course['code']}) - {course['credits']} وحدات\n"
        await callback.message.answer(msg)
    else:
        await callback.message.answer(f"عذراً، خطة {major} للمستوى {level} غير متوفرة حالياً.")
    await callback.answer()

@dp.callback_query(F.data == "menu_clubs")
async def clubs_callback(callback: types.CallbackQuery):
    await callback.message.answer("🌟 **الأندية الطلابية:**\n(قريباً سيتم توفير دليل الأندية).")
    await callback.answer()

# ==========================================
# 7. محرك الذكاء الاصطناعي الأساسي والتوجيه 
# ==========================================
@dp.message(F.text)
async def chat_with_ai(message: types.Message):
    wait_msg = await message.answer("⏳ جاري البحث...")
    
    user_id = str(message.from_user.id)
    user_info = users_db.get(user_id, None)
    
    student_context = ""
    if user_info:
        student_context = f"الاسم: {user_info['name']}, الدرجة: {user_info['degree']}, الكلية: {user_info['college']}, التخصص: {user_info['major']}, المستوى: {user_info['level']}"
    
    try:
        # التعديل الأهم: رفع عدد النتائج المستخرجة إلى 20
        results = collection.query(query_texts=[message.text], n_results=20)
        
        context_text = ""
        if results['documents'] and len(results['documents'][0]) > 0:
            for doc in results['documents'][0]:
                context_text += doc + "\n\n"
                
        augmented_prompt = f"""
        أنت مساعد أكاديمي لطلاب جامعة جدة.
        سؤال الطالب: {message.text}
        
        معلومات الطالب الشخصية:
        {student_context}
        
        🤖 هوية النظام:
        - أنت نظام "UniGuide" (المرشد الأكاديمي الذكي)، مخصص للكلية التطبيقية بجامعة جدة.
        
        الهيكل التنظيمي للكلية التطبيقية:
        - الرئيس التنفيذي للكلية التطبيقية.
        - المسار الأول (العمليات الأساسية): نائب الرئيس (وحدة الخريجين، وحدة الشؤون التعليمية ac.edu@UJ.EDU.SA، وحدة البرامج، وحدة الشهادات المهنية).
        - المسار الثاني (الخدمات): مساعد الرئيس (وحدة التخطيط، وحدة الشراكات، وحدة المالية، وحدة التدريب).
        
        تعليمات الإجابة:
        1. ابحث بدقة داخل (المعلومات الرسمية الإضافية / اللوائح) المسترجعة أدناه للإجابة على أسئلة اللوائح، الحذف والإضافة، والعبء الدراسي.
        2. إذا سألك الطالب عن اسمه أو بياناته، أجب عليه من خلال (معلومات الطالب الشخصية).
        3. إذا كان السؤال عن الأنظمة ولم تجد الإجابة في النصوص نهائياً، أجب بكلمة واحدة فقط: UNKNOWN_QUERY
        
        المعلومات الرسمية الإضافية (لوائح الجامعة):
        {context_text}
        """

        response = await gemini_client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=augmented_prompt
        )
        
        ai_reply = response.text.strip()
        
        if "UNKNOWN_QUERY" in ai_reply:
            log_unanswered_question(user_info, message.text, user_id)
            student_name = user_info['name'] if user_info else "صديقي"
            fallback_message = (
                f"أعتذر منك يا {student_name}، بحثت في اللوائح ولم أجد إجابة دقيقة 😔.\n"
                f"✅ تم تسجيل سؤالك وإرسال تنبيه لفريق التطوير."
            )
            await wait_msg.edit_text(fallback_message)
        else:
            await wait_msg.edit_text(ai_reply)
        
    except Exception as e:
        print(f"System Error: {e}")
        await wait_msg.edit_text("⚠️ حدث ضغط على الخوادم، يرجى المحاولة مرة أخرى بعد قليل 🔄.")

# ==========================================
# وتشغيل البوت
# ==========================================
async def main():
    print("🚀 UniGuide Master Architecture is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())