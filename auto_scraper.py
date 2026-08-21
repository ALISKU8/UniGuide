import schedule
import time
import json
import requests
from bs4 import BeautifulSoup

def fetch_and_update_plans():
    print("⏳ بدأ نظام الأتمتة في فحص خطط الجامعة...")
    
    # 1. كود الدخول للموقع وسحب البيانات (سنبنيه لاحقاً بناءً على روابط جامعتك)
    # url = "رابط صفحة تخصصات الجامعة"
    # html_content = requests.get(url).text
    
    # 2. قراءة الملف القديم
    try:
        with open("study_plans.json", "r", encoding="utf-8") as f:
            old_plans = json.load(f)
    except FileNotFoundError:
        old_plans = {}

    # 3. محاكاة السحب والمقارنة
    new_plans = {} # هنا نضع البيانات المسحوبة حديثاً
    
    if old_plans != new_plans:
        print("🚨 تم رصد تحديثات في الخطط الدراسية! جاري تحديث قاعدة البيانات...")
        with open("study_plans.json", "w", encoding="utf-8") as f:
            json.dump(new_plans, f, ensure_ascii=False, indent=4)
        # هنا ممكن نخلي البوت يرسل لك رسالة على تيليجرام يقولك: تم تحديث الخطط!
    else:
        print("✅ الخطط مطابقة تماماً. لا توجد تغييرات جديدة.")

# جدولة المهمة لتشتغل كل 4 أسابيع
schedule.every(4).weeks.do(fetch_and_update_plans)

print("🚀 نظام المراقبة الآلي يعمل في الخلفية...")

# حلقة لتبقي السكريبت شغال دائماً في سيرفرك
while True:
    schedule.run_pending()
    time.sleep(3600) # ينام ساعة ثم يتأكد من الوقت المجدول