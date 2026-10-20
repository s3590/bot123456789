import os
# 🌟 الإصلاح الجذري: تحميل متغيرات البيئة من ملف .env (يمنع انهيار السيرفر في بيئات التطوير والـ VPS)
from dotenv import load_dotenv
load_dotenv()

# ================= المتغيرات الأساسية =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# ================= حماية الفشل السريع (Fail Fast) =================
if not BOT_TOKEN:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'BOT_TOKEN' في متغيرات البيئة!")

if not DATABASE_URL:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'DATABASE_URL' في متغيرات البيئة!")

# 🌟 تصحيح بادئة asyncpg إذا كانت postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ================= دالة مساعدة لجلب الأرقام بأمان =================
def get_env_int(key: str, default: int = 0) -> int:
    val = os.getenv(key)
    if val and val.strip().lstrip('-').isdigit():
        return int(val.strip())
    return default

# ================= معرفات الإدارة والوكيل (تأكيد الصلاحيات) =================
ADMIN_ID = get_env_int("ADMIN_ID", 0)
NETWORK_OWNER_ID = get_env_int("NETWORK_OWNER_ID", 0)
AGENT_ID = ADMIN_ID # 🌟 تثبيت معرف الوكيل ليطابق استدعاءات ملف main.py والأمان السري

if ADMIN_ID == 0:
    print("⚠️ تحذير أمني: لم يتم تحديد 'ADMIN_ID' في السيرفر! لن تتمكن من استلام إشعارات الوكيل والأخطاء.")

# ================= المفاتيح السرية للنظام (تأمين صارم ومحمي) =================
import base64
import hashlib

_env_enc_key = os.getenv("ENCRYPTION_KEY")
if not _env_enc_key:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'ENCRYPTION_KEY' في متغيرات البيئة!")

# 🌟 اشتقاق مفتاح Fernet آمن وقياسي (32-bytes Base64) مهما كان النص المدخل لمنع الانهيار
try:
    _raw_key = _env_enc_key.strip().encode()
    # إذا كان المفتاح مشفراً بصيغة base64 وصالحاً نقبله، وإلا نشتق منه مفتاحاً نظامياً
    if len(base64.urlsafe_b64decode(_raw_key + b'=' * (-len(_raw_key) % 4))) == 32:
        ENCRYPTION_KEY = _raw_key + b'=' * (-len(_raw_key) % 4)
    else:
        ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(_raw_key).digest())
except Exception:
    ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(_env_enc_key.strip().encode()).digest())

API_SECRET_KEY = os.getenv("API_SECRET_KEY")
if not API_SECRET_KEY:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'API_SECRET_KEY' في متغيرات البيئة!")
API_SECRET_KEY = API_SECRET_KEY.strip()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'JWT_SECRET' في متغيرات البيئة!")
JWT_SECRET = JWT_SECRET.strip()

# ================= وضع الاختبار (Sandbox Mode) =================
# إذا كان True، يمكنك تجربة النظام بدون خصم حقيقي من شركة الاتصالات
TEST_MODE = os.getenv("TEST_MODE", "False").lower() in ("true", "1", "t", "yes")

# ================= إعدادات الواتساب (مركزية وخالية من الأخطاء) =================
WA_API_URL = os.getenv("WA_API_URL", "https://whatsapp-api-fhhi.onrender.com").strip()
WA_INSTANCE = os.getenv("WA_INSTANCE", "alshehappro").strip()
# إذا لم يوجد رقم يعيد None حقيقية وليست نصاً
_raw_gm_wa = os.getenv("GM_WA_NUMBER", "").strip()
GM_WA_NUMBER = _raw_gm_wa if _raw_gm_wa and _raw_gm_wa.lower() != "none" else None

# 🌟 الإصلاح الأمني: منع كتابة مفتاح الواتساب داخل الكود
WA_API_KEY = os.getenv("WA_API_KEY")
if not WA_API_KEY:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'WA_API_KEY' في متغيرات البيئة!")
WA_API_KEY = WA_API_KEY.strip()

# ================= الرمز السري للعمليات الخطيرة (النووية) =================
# 🌟 الإصلاح الأمني: منع كتابة رمز الفورمات داخل الكود
SYSTEM_VAULT_PIN = os.getenv("SYSTEM_VAULT_PIN")
if not SYSTEM_VAULT_PIN:
    raise ValueError("❌ خطأ حرج: لم يتم العثور على 'SYSTEM_VAULT_PIN' في متغيرات البيئة!")
SYSTEM_VAULT_PIN = SYSTEM_VAULT_PIN.strip()

# ================= إعدادات الخزنة السحابية (النسخ الاحتياطي) =================
BACKUP_EMAIL_SENDER = os.getenv("BACKUP_EMAIL_SENDER", "").strip()
BACKUP_EMAIL_PASSWORD = os.getenv("BACKUP_EMAIL_PASSWORD", "").strip()
BACKUP_EMAIL_RECEIVER = os.getenv("BACKUP_EMAIL_RECEIVER", "").strip()

# ================= إعدادات إشعارات الويب (VAPID Keys) =================
# هذه المفاتيح أساسية الآن لإرسال إشعارات صاروخية لمتصفحات الويب (PWA)
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").strip()
VAPID_ADMIN_EMAIL = os.getenv("VAPID_ADMIN_EMAIL", "mailto:admin@alshehab.com").strip()

# تحذير ذكي في سجلات السيرفر إذا كانت المفاتيح مفقودة (بدون إيقاف السيرفر)
if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
    print("⚠️ تحذير: مفاتيح VAPID (العام أو الخاص) مفقودة من متغيرات البيئة! إشعارات الويب (PWA) لن تعمل بشكل صحيح.")

# ================= حسابات الوصول الخاص (المدقق والتجربة) =================
# يتم جلب كلمات المرور من بيئة الاستضافة، مع وضع قيم افتراضية في حال نسيان إضافتها
AUDITOR_PASSWORD = os.getenv("AUDITOR_PASSWORD", "audit2026").strip()
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo").strip()
