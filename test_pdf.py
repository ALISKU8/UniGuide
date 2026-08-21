import fitz 

# غير هذا الاسم إلى اسم ملف اللوائح الفعلي الموجود في مجلد docs لديك
PDF_FILE = "docs/دليل اللوائح الدراسية والاختبارات العامه.pdf" 

def test_extraction():
    try:
        doc = fitz.open(PDF_FILE)
        text = ""
        # قراءة أول 3 صفحات فقط للاختبار
        for i in range(min(3, len(doc))):
            text += doc[i].get_text()
        
        print("=== النص المستخرج من ملف اللوائح ===")
        print(text[:1000]) # طباعة أول 1000 حرف
        print("====================================")
        
        if not text.strip():
            print("🚨 تحذير: لم يتم استخراج أي نص! الملف يبدو أنه عبارة عن صور أو محمي.")
    except Exception as e:
        print(f"حدث خطأ: {e}")

if __name__ == "__main__":
    test_extraction()