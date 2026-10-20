import asyncio
import logging
import os
import traceback
import html
import time
from logging.handlers import RotatingFileHandler

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# 🌟 ضبط توقيت السيرفر الأساسي على توقيت اليمن ومكة المكرمة
os.environ['TZ'] = 'Asia/Aden'
try:
    time.tzset()
except AttributeError:
    pass

# =====================================================================
# 🌟 تحميل ملفات النظام الأساسية تلقائياً (بأعلى معايير الاستقرار)
# =====================================================================
async def download_initial_assets():
    os.makedirs("static", exist_ok=True)
    file_path = "static/localforage.min.js"
    font_path = "Amiri-Regular.ttf"

    # مسح الملفات المعطوبة إذا كان حجمها غير منطقي
    if os.path.exists(file_path) and os.path.getsize(file_path) < 15000:
        try: os.remove(file_path)
        except: pass
    if os.path.exists(font_path) and os.path.getsize(font_path) < 40000:
        try: os.remove(font_path)
        except: pass

    timeout = aiohttp.ClientTimeout(total=25)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        # 1. تحميل مكتبة الأوفلاين
        if not os.path.exists(file_path):
            try:
                print("⏳ جاري تحميل مكتبة الأوفلاين (localforage)...")
                url = "https://cdnjs.cloudflare.com/ajax/libs/localforage/1.10.0/localforage.min.js"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(file_path + ".tmp", 'wb') as f:
                            f.write(content)
                        os.replace(file_path + ".tmp", file_path)
                        print("✅ تم تحميل مكتبة الأوفلاين بنجاح!")
            except Exception as e:
                print(f"⚠️ تعذر تحميل مكتبة الأوفلاين: {e}")

        # 2. تحميل الخط العربي من CDN موثوق
        if not os.path.exists(font_path):
            try:
                print("⏳ جاري تحميل الخط العربي للفواتير...")
                # رابط بديل سريع جداً ومستقر عبر jsdelivr
                font_url = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf"
                async with session.get(font_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(font_path + ".tmp", 'wb') as f:
                            f.write(content)
                        os.replace(font_path + ".tmp", font_path)
                        print("✅ تم تحميل الخط العربي بنجاح!")
                    else:
                        print(f"❌ تعذر تحميل الخط، كود الاستجابة: {resp.status}")
            except Exception as e:
                print(f"⚠️ فشل تحميل الخط العربي: {e}")

# =====================================================================
# 🌟 استيراد إعدادات النظام والموجهات
# =====================================================================
from config import BOT_TOKEN, ADMIN_ID
# إذا كان لديك AGENT_ID في config استخدمه للأخطاء السرية، وإلا سنستخدم ADMIN_ID
try:
    from config import AGENT_ID
    OWNER_NOTIFICATION_ID = AGENT_ID
except ImportError:
    OWNER_NOTIFICATION_ID = ADMIN_ID

import database
import core_accounting
from scheduler import start_scheduler
try:
    from scheduler import stop_scheduler
except ImportError:
    stop_scheduler = lambda: None

import client_panel
import unified_main
import tickets
import ai_chat_panel
from web_api import setup_web_api

# إعداد السجلات (Logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler("system_logs.log", maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# مجموعة لحفظ مراجع المهمات الخلفية ومنع بايثون من قتلها
background_tasks = set()

# ================= صائد الأخطاء البرمجية العام (محمي لسرية الوكيل) =================
@dp.error()
async def global_error_handler(event: ErrorEvent):
    error_details = traceback.format_exc()
    truncated_details = error_details[-2500:] if len(error_details) > 2500 else error_details
    
    safe_details = html.escape(truncated_details)
    safe_error_msg = html.escape(str(event.exception)[:500])
    
    error_msg = (
        "🚨 <b>تنبيه أمان: حدث خطأ غير متوقع في النظام!</b>\n\n"
        f"<b>نوع الخطأ:</b> {type(event.exception).__name__}\n"
        f"<b>الرسالة:</b> {safe_error_msg}\n\n"
        f"<b>التفاصيل التقنية:</b>\n<code>{safe_details}</code>"
    )
    try:
        # يُرسل حصرياً لمعرف الوكيل/المالك وليس لأي حساب آخر لحماية الأسرار
        await bot.send_message(OWNER_NOTIFICATION_ID, error_msg)
    except Exception as e:
        logging.error(f"فشل إرسال تقرير الخطأ: {e}")

# ================= دالة التشغيل الأساسية =================
async def main():
    print("🚀 جاري إقلاع منصة الشهاب Pro المتطورة...")
    
    # 0. تحميل الملفات والأصول الأساسية
    await download_initial_assets()
    
    # 1. تهيئة قاعدة البيانات السريعة
    await database.init_db()
    
    # 🌟 الحماية المحاسبية: تشغيل مهمة تنظيف الذاكرة ومفاتيح العمليات بمرجع قوي
    cleanup_task = asyncio.create_task(core_accounting.cleanup_idempotency_keys(database.pool))
    background_tasks.add(cleanup_task)
    cleanup_task.add_done_callback(background_tasks.discard)
    
    # 2. تفعيل جلسات الذكاء الاصطناعي والموجهات
    await ai_chat_panel.init_ai_session()
    
    dp.include_router(client_panel.router)
    dp.include_router(unified_main.router)
    dp.include_router(tickets.router)
    dp.include_router(ai_chat_panel.router) # الذكاء الاصطناعي في النهاية

    # حذف أي رسائل قديمة معلقة أثناء توقف البوت
    await bot.delete_webhook(drop_pending_updates=True)

    # 3. إعداد وتكوين سيرفر الويب السريع (aiohttp)
    app = setup_web_api(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f"🌐 تم تشغيل واجهة الويب والـ API على المنفذ: {port}")

    # 4. تشغيل الخدمات المتزامنة
    try:
        await site.start()
        
        # تشغيل المجدول الليلي (النسخ الاحتياطي والتدقيق التلقائي)
        start_scheduler(bot)
        print("⏰ تم تشغيل المجدول الآلي للتدقيق والنسخ الاحتياطي.")
        
        # إشعار تشغيل ناجح للوكيل
        try:
            await bot.send_message(
                OWNER_NOTIFICATION_ID,
                "✅ <b>تم إقلاع نظام الشهاب Pro بنجاح!</b> 🚀\n"
                "• محرك العمليات المحاسبية: نشط وقيد المراقبة.\n"
                "• سيرفر الويب والبوت: يعملان بأقصى سرعة."
            )
        except Exception:
            pass
        
        print("🤖 بوت الشهاب Pro يستقبل الرسائل الآن بكفاءة 100%...")
        await dp.start_polling(bot)

    finally:
        # إغلاق منظم وتدريجي يمنع تدمير البيانات (Graceful Shutdown)
        print("🛑 جاري إيقاف النظام وتنظيف الموارد...")
        
        # إيقاف المجدول أولاً لمنع طلبات جديدة
        try:
            stop_scheduler()
            print("⏰ تم إيقاف المجدول بنجاح.")
        except Exception:
            pass
            
        # إلغاء المهمات الخلفية
        for task in background_tasks:
            task.cancel()

        # إيقاف سيرفر الويب
        await runner.cleanup()
        print("🌐 تم إيقاف سيرفر الويب.")
        
        # إغلاق جلسة الذكاء الاصطناعي
        try:
            await ai_chat_panel.close_ai_session()
            print("🧠 تم إغلاق جلسات الذكاء الاصطناعي.")
        except Exception:
            pass
            
        # إغلاق جلسة البوت
        await bot.session.close()
        print("🤖 تم إغلاق جلسة التيليجرام.")
            
        # إغلاق مجمع اتصالات قاعدة البيانات بأمان
        await database.close_db()
        print("🗄️ تم إغلاق قاعدة البيانات وتأمين العمليات.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 تم إيقاف النظام بأمر المستخدم.")
