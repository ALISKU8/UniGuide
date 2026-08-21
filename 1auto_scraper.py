import requests
from bs4 import BeautifulSoup
import json
import time

# ==========================================
# 1. قائمة التخصصات وروابطها (قاعدة بيانات الروابط)
# يمكنك إضافة أي تخصص جديد هنا، والسكريبت سيزوره تلقائياً
# ==========================================
MAJORS_URLS = {
    # تخصصك: رابط الخطة الخاص به
    "علوم حاسب": "https://ac.uj.edu.sa/ar/%D8%A7%D9%84%D8%AE%D8%B7%D8%A9-%D8%A7%D9%84%D8%AF%D8%B1%D8%A7%D8%B3%D9%8A%D8%A9?pc=AS-PRCS-CC",
    
    # يمكنك لاحقاً البحث في موقع الجامعة عن روابط التخصصات الأخرى وإضافتها هنا
    # "إدارة أعمال": "رابط_خطة_إدارة_الأعمال_هنا",
    # "أمن سيبراني": "رابط_خطة_الأمن_السيبراني_هنا"
}

def scrape_all_majors():
    print("⏳ بدأ نظام الأتمتة الشامل في فحص خطط الجامعة لجميع التخصصات...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # هذا القاموس سيجمع كل الخطط لكل التخصصات
    all_study_plans = {}
    
    # حلقة تكرارية تمر على كل تخصص في القائمة
    for major_name, url in MAJORS_URLS.items():
        print(f"🔍 جاري سحب خطة تخصص: {major_name} ...")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            
            if not table:
                print(f"⚠️ تحذير: لم يتم العثور على جدول في صفحة {major_name}")
                continue # يتجاوز هذا التخصص ويكمل الباقي
                
            courses = []
            rows = table.find_all('tr')[1:] # تخطي العناوين
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 5:
                    course_code = cols[0].text.strip()
                    course_name = cols[1].text.strip()
                    credits_text = cols[4].text.strip()
                    credits = int(credits_text) if credits_text.isdigit() else credits_text
                    
                    courses.append({
                        "code": course_code,
                        "name": course_name,
                        "credits": credits
                    })
            
            # حفظ المواد المسحوبة داخل التخصص (سنفترض أنها للمستوى 1 حالياً حتى نطور الكود لاحقاً لقراءة المستويات)
            all_study_plans[major_name] = {"1": courses}
            print(f"✅ تم سحب {len(courses)} مواد بنجاح لـ {major_name}")
            
            # أمر إيقاف بسيط (ثانيتين) بين كل صفحة وصفحة عشان سيرفر الجامعة ما يحظرنا (Anti-ban)
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ فشل الاتصال بصفحة {major_name}. الخطأ: {e}")

    # بعد الانتهاء من كل التخصصات، نقوم بحفظها في الملف
    if all_study_plans:
        with open("study_plans.json", "w", encoding="utf-8") as f:
            json.dump(all_study_plans, f, ensure_ascii=False, indent=4)
        print("\n🎉 اكتملت العملية! تم تحديث ملف study_plans.json بجميع التخصصات.")
    else:
        print("\n⚠️ لم يتم سحب أي بيانات لتحديث الملف.")

if __name__ == "__main__":
    scrape_all_majors()