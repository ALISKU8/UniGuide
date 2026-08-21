import qrcode
from PIL import Image

# 1. إعداد المتغيرات
bot_url = "https://t.me/UJ_UniGuide_bot"
logo_path = "logo.png"  # تأكد إن اسم صورة شعارك مطابق لهذا الاسم

# 2. فتح صورة الشعار وتعديل حجمها
logo = Image.open(logo_path)
# تصغير الشعار عشان ما يغطي الباركود بالكامل (عرض 100 بكسل)
basewidth = 100
wpercent = (basewidth / float(logo.size[0]))
hsize = int((float(logo.size[1]) * float(wpercent)))
logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)

# 3. إنشاء الباركود
qr = qrcode.QRCode(
    version=5, # كبرنا حجم الشبكة شوي عشان تستوعب الشعار بشكل أوضح
    error_correction=qrcode.constants.ERROR_CORRECT_H, # تصحيح أخطاء عالي جداً
    box_size=10,
    border=4,
)
qr.add_data(bot_url)
qr.make(fit=True)

# تحويل الباركود لصورة ملونة (RGB) عشان يقبل دمج الشعار الملون
img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

# 4. حساب نقطة المنتصف ولصق الشعار
pos = ((img.size[0] - logo.size[0]) // 2,
       (img.size[1] - logo.size[1]) // 2)

# لصق الشعار في المنتصف
img.paste(logo, pos)

# حفظ الصورة النهائية
img.save("UniGuide_QR_Logo.png")

print("تم إنشاء الباركود مع الشعار بنجاح! تحصله باسم UniGuide_QR_Logo.png")