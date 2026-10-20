import os
import re
from io import BytesIO
from datetime import datetime
from decimal import Decimal

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

import arabic_reshaper
from bidi.algorithm import get_display

# محاولة استيراد qrcode لتوليد رمز التحقق بالفاتورة بأمان
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

# إعداد الخطوط ومسارات الصور
FONT_PATHS = [
    "Amiri-Regular.ttf",
    "static/fonts/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf",
    "Arial.ttf"
]
LOGO_PATH = "static/logo.png"

FONT_NAME = 'Helvetica'
for path in FONT_PATHS:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('ArabicFont', path))
            FONT_NAME = 'ArabicFont'
            break
        except Exception as e:
            print(f"Error loading font {path}: {e}")

# ================= دالة التفقيط المالي بالريال العربي =================
def tafqeet_arabic(number):
    """تحويل الأرقام إلى نصوص مالية عربية رسمية لمنع التلاعب"""
    try:
        val = int(Decimal(str(number)))
    except:
        return ""
    if val == 0:
        return "صفر ريال لا غير"

    ones = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة",
            "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"]
    tens = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
    hundreds = ["", "مائة", "مئتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]

    def convert_below_thousand(n):
        res = []
        c = n // 100
        r = n % 100
        if c > 0:
            res.append(hundreds[c])
        if r > 0:
            if r < 20:
                res.append(ones[r])
            else:
                unit = r % 10
                ten = r // 10
                if unit > 0:
                    res.append(f"{ones[unit]} و{tens[ten]}")
                else:
                    res.append(tens[ten])
        return " و".join(res)

    thousands = val // 1000
    rem = val % 1000
    res_str = []
    if thousands > 0:
        if thousands == 1:
            res_str.append("ألف")
        elif thousands == 2:
            res_str.append("ألفان")
        elif 3 <= thousands <= 10:
            res_str.append(f"{ones[thousands]} آلاف")
        else:
            res_str.append(f"{convert_below_thousand(thousands)} ألف")
    
    if rem > 0:
        res_str.append(convert_below_thousand(rem))

    return "فقط " + " و".join(res_str) + " ريال يمني لا غير"

# ================= دوال الدعم والحماية =================
def safe_amount(val, as_float=False):
    """حماية المبالغ وتنسيقها مع الحفاظ التام على الكسور العشرية"""
    if val is None or str(val).strip() == '' or str(val).strip().lower() == 'none':
        return 0.0 if as_float else "0"
    try:
        d = Decimal(str(val))
        if as_float:
            return float(d)
        if d == d.to_integral():
            return f"{int(d):,}"
        return f"{d:,.2f}"
    except Exception:
        return 0.0 if as_float else "0"

def strip_emojis(text):
    """إزالة الرموز التعبيرية التي تسبب انهيار مكتبة ReportLab"""
    if not text:
        return ""
    # إزالة نطاقات الإيموجي الشائعة
    pattern = re.compile("[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff]", flags=re.UNICODE)
    cleaned = pattern.sub('', str(text))
    return cleaned.replace("▪️", "-").replace("🌹", "").strip()

def fix_arabic(text):
    """ضبط النصوص العربية والاتصال الصحيح"""
    if text is None:
        return ""
    clean = strip_emojis(text)
    try:
        reshaped = arabic_reshaper.reshape(str(clean))
        return get_display(reshaped)
    except Exception:
        return str(clean)

def draw_logo(c, x, y, w, h):
    """رسم الشعار بأمان دون تعليق السيرفر إذا كان الملف مفقوداً"""
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, x, y, width=w, height=h, mask='auto')
        except Exception:
            pass

def draw_qr_code(c, data: str, x, y, size=60):
    """توليد ورسم باركود QR مباشر على الفاتورة"""
    if HAS_QR and data:
        try:
            qr = qrcode.QRCode(box_size=3, border=1)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            c.drawImage(ImageReader(img_buffer), x, y, width=size, height=size)
        except Exception:
            pass

# ================= 1. فاتورة العمليات الفردية (A5) =================
def generate_receipt(receipt_id: int, client_name: str, amount, receipt_type: str, details: str) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5

    # الإطار الخارجي والترويسة
    c.setStrokeColor(colors.HexColor("#1F4E78"))
    c.setLineWidth(1.5)
    c.roundRect(15, 15, width - 30, height - 30, 8)

    c.setFillColor(colors.HexColor("#1F4E78"))
    c.roundRect(15, height - 80, width - 30, 65, 8, fill=1)
    
    draw_logo(c, width - 75, height - 75, 50, 50)
    
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME, 18)
    c.drawCentredString(width / 2, height - 42, fix_arabic("فاتورة سند رسمية"))
    c.setFont(FONT_NAME, 13)
    c.drawCentredString(width / 2, height - 63, fix_arabic("الشهاب Pro - منصة الخدمات المحاسبية"))

    # بيانات الفاتورة
    c.setFillColor(colors.black)
    c.setFont(FONT_NAME, 13)
    
    start_y = height - 115
    line_spacing = 30
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.drawRightString(width - 35, start_y, fix_arabic(f"رقم السند: {receipt_id}"))
    c.drawRightString(width - 35, start_y - line_spacing, fix_arabic(f"التاريخ: {now_str}"))
    c.drawRightString(width - 35, start_y - (line_spacing * 2), fix_arabic(f"العميل: {client_name}"))
    c.drawRightString(width - 35, start_y - (line_spacing * 3), fix_arabic(f"نوع العملية: {receipt_type}"))
    
    # مربع المبلغ المالي المميز
    c.setFillColor(colors.HexColor("#F8F9FA"))
    c.setStrokeColor(colors.HexColor("#1F4E78"))
    c.setLineWidth(1)
    c.roundRect(25, start_y - (line_spacing * 4) - 25, width - 50, 40, 5, fill=1)

    c.setFont(FONT_NAME, 16)
    c.setFillColor(colors.HexColor("#900C3F"))
    amount_str = safe_amount(amount)
    c.drawRightString(width - 40, start_y - (line_spacing * 4) - 13, fix_arabic(f"المبلغ: {amount_str} ريال"))

    # التفقيط المالي التلقائي
    c.setFont(FONT_NAME, 11)
    c.setFillColor(colors.HexColor("#2C3E50"))
    tafqeet_text = tafqeet_arabic(safe_amount(amount, as_float=True))
    c.drawRightString(width - 40, start_y - (line_spacing * 4) - 27, fix_arabic(tafqeet_text))

    # التفاصيل
    safe_details = str(details) if details else "بدون تفاصيل إضافية"
    safe_details = re.sub(r'[\{\}\[\]"\'_]', ' ', safe_details).strip()
    
    c.setFillColor(colors.black)
    c.setFont(FONT_NAME, 12)
    y_det = start_y - (line_spacing * 5) - 20
    c.drawRightString(width - 35, y_det, fix_arabic("التفاصيل:"))
    y_det -= 20

    if "+" in safe_details:
        parts = safe_details.split("+")
        for part in parts[:4]:
            c.drawRightString(width - 50, y_det, fix_arabic(f"- {part.strip()}"))
            y_det -= 18
    else:
        words = safe_details.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) < 42:
                current_line += word + " "
            else:
                lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        for line in lines[:3]:
            c.drawRightString(width - 50, y_det, fix_arabic(f"- {line.strip()}"))
            y_det -= 18

    # رسم QR Code للتحقق
    qr_data = f"Receipt:{receipt_id}|Client:{client_name}|Amount:{amount_str}|Date:{now_str}"
    draw_qr_code(c, qr_data, 35, 75, size=55)

    # التذييل
    c.setStrokeColor(colors.lightgrey)
    c.line(30, 70, width - 30, 70)
    
    c.setFont(FONT_NAME, 10)
    c.setFillColor(colors.dimgrey)
    c.drawCentredString(width / 2 + 25, 50, fix_arabic("مستند إلكتروني رسمي معتمد آلياً عبر نظام الشهاب Pro"))
    c.drawCentredString(width / 2 + 25, 32, fix_arabic("شكراً لتعاملكم معنا"))

    c.save()
    buffer.seek(0)
    return buffer

# ================= 2. كشف الحساب المبسط للعميل (A5) =================
def generate_client_statement(client_name: str, debt, inventory_items: list, last_payment: str) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5

    c.setStrokeColor(colors.HexColor("#1F4E78"))
    c.setLineWidth(1.5)
    c.roundRect(15, 15, width - 30, height - 30, 8)

    c.setFillColor(colors.HexColor("#1F4E78"))
    c.roundRect(15, height - 70, width - 30, 55, 8, fill=1)
    draw_logo(c, width - 65, height - 63, 42, 42)
    
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME, 16)
    c.drawCentredString(width / 2, height - 42, fix_arabic("الشهاب Pro - كشف رصيد عميل"))
    
    c.setFillColor(colors.black)
    c.setFont(FONT_NAME, 12)
    c.drawRightString(width - 35, height - 95, fix_arabic(f"اسم العميل: {client_name}"))
    c.drawRightString(width - 35, height - 118, fix_arabic(f"تاريخ الكشف: {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
    
    # مربع الرصيد المطلوب
    c.setFillColor(colors.HexColor("#FFF5F5"))
    c.setStrokeColor(colors.HexColor("#900C3F"))
    c.roundRect(25, height - 170, width - 50, 42, 5, fill=1)

    c.setFont(FONT_NAME, 14)
    c.setFillColor(colors.HexColor("#900C3F"))
    debt_val = safe_amount(debt)
    c.drawRightString(width - 35, height - 150, fix_arabic(f"إجمالي الرصيد المطلوب سداده: {debt_val} ريال"))
    
    c.setFillColor(colors.black)
    c.setFont(FONT_NAME, 11)
    c.drawRightString(width - 35, height - 190, fix_arabic(f"آخر عملية سداد: {last_payment if last_payment else 'لا يوجد'}"))

    c.setStrokeColor(colors.lightgrey)
    c.line(30, height - 205, width - 30, height - 205)

    c.setFont(FONT_NAME, 12)
    c.drawRightString(width - 35, height - 225, fix_arabic("مخزون الكروت المسجل بمحل العميل حالياً:"))
    
    y_pos = height - 250
    c.setFont(FONT_NAME, 11)
    
    if inventory_items:
        for i, item in enumerate(inventory_items[:7]):
            qty = safe_amount(item.get('quantity', 0))
            card = item.get('card_type', 'غير محدد')
            c.drawRightString(width - 50, y_pos, fix_arabic(f"- عدد {qty} كرت من فئة ({card})"))
            y_pos -= 22
        if len(inventory_items) > 7:
            c.drawRightString(width - 50, y_pos, fix_arabic("- ... وفئات إضافية مسجلة بالنظام"))
    else:
        c.drawRightString(width - 50, y_pos, fix_arabic("لا يوجد كروت مسجلة في عهدتكم حالياً."))

    c.setFont(FONT_NAME, 10)
    c.setFillColor(colors.dimgrey)
    c.drawCentredString(width / 2, 35, fix_arabic("شكراً لتعاملكم مع الشهاب Pro"))

    c.save()
    buffer.seek(0)
    return buffer

# ================= 3. كشف الحساب التفصيلي (A4) مع دعم الصفحات =================
def generate_detailed_statement(client_name: str, debt, transactions: list, start_date: str, end_date: str) -> BytesIO:
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    def draw_page_framework(canvas_obj, is_first_page=True):
        canvas_obj.setStrokeColor(colors.HexColor("#1F4E78"))
        canvas_obj.setLineWidth(1.5)
        canvas_obj.rect(15, 15, width - 30, height - 30)
        
        # الهيدر
        canvas_obj.setFillColor(colors.HexColor("#1F4E78"))
        header_h = 75 if is_first_page else 45
        canvas_obj.rect(15, height - 15 - header_h, width - 30, header_h, fill=1)
        draw_logo(canvas_obj, width - 75, height - 15 - header_h + 10, header_h - 20, header_h - 20)
        
        canvas_obj.setFillColor(colors.white)
        if is_first_page:
            canvas_obj.setFont(FONT_NAME, 20)
            canvas_obj.drawCentredString(width / 2.0, height - 50, fix_arabic("كشف حساب عميل تفصيلي"))
            canvas_obj.setFont(FONT_NAME, 12)
            canvas_obj.drawCentredString(width / 2.0, height - 75, fix_arabic(f"الفترة: من {start_date} إلى {end_date}"))
        else:
            canvas_obj.setFont(FONT_NAME, 13)
            canvas_obj.drawCentredString(width / 2.0, height - 45, fix_arabic(f"كشف حساب: {client_name} (تابع)"))

    def draw_table_header(canvas_obj, y_pos):
        canvas_obj.setFillColor(colors.HexColor("#EAECEE"))
        canvas_obj.rect(25, y_pos, width - 50, 26, fill=1)
        canvas_obj.setFillColor(colors.black)
        canvas_obj.setFont(FONT_NAME, 11)
        # توزيع الأعمدة بشكل هندسي يمنع التداخل
        canvas_obj.drawRightString(width - 35, y_pos + 8, fix_arabic("التاريخ"))
        canvas_obj.drawRightString(width - 130, y_pos + 8, fix_arabic("نوع العملية"))
        canvas_obj.drawRightString(width - 240, y_pos + 8, fix_arabic("المبلغ (ريال)"))
        canvas_obj.drawRightString(width - 330, y_pos + 8, fix_arabic("البيان / التفاصيل"))
        return y_pos - 24

    # الصفحة الأولى
    draw_page_framework(p, is_first_page=True)

    p.setFillColor(colors.black)
    p.setFont(FONT_NAME, 14)
    p.drawRightString(width - 35, height - 120, fix_arabic(f"العميل: {client_name}"))
    p.setFillColor(colors.HexColor("#900C3F"))
    p.drawRightString(width - 35, height - 145, fix_arabic(f"إجمالي الرصيد القائم: {safe_amount(debt)} ريال"))
    
    y_pos = height - 180
    y_pos = draw_table_header(p, y_pos)

    p.setFont(FONT_NAME, 10)
    if not transactions:
        p.setFillColor(colors.dimgrey)
        p.drawCentredString(width / 2.0, y_pos - 30, fix_arabic("لا توجد حركات مسجلة خلال الفترة المحددة."))
    else:
        for trans in reversed(transactions):
            if y_pos < 60:
                p.showPage()
                draw_page_framework(p, is_first_page=False)
                y_pos = height - 85
                y_pos = draw_table_header(p, y_pos)
                p.setFont(FONT_NAME, 10)

            date_val = trans.get('date', '')
            date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)[:10]
            trans_type = str(trans.get('type', '')).replace('_', ' ')
            amount = safe_amount(trans.get('amount', 0))
            
            raw_details = str(trans.get('details', '') or 'بدون تفاصيل')
            details = (raw_details[:45] + '...') if len(raw_details) > 45 else raw_details

            p.setFillColor(colors.black)
            p.drawRightString(width - 35, y_pos + 5, fix_arabic(date_str))
            p.drawRightString(width - 130, y_pos + 5, fix_arabic(trans_type))
            p.drawRightString(width - 240, y_pos + 5, fix_arabic(amount))
            p.drawRightString(width - 330, y_pos + 5, fix_arabic(details))

            p.setStrokeColor(colors.HexColor("#E5E7EB"))
            p.setLineWidth(0.5)
            p.line(25, y_pos, width - 25, y_pos)
            y_pos -= 24

    p.setFont(FONT_NAME, 9)
    p.setFillColor(colors.dimgrey)
    p.drawCentredString(width / 2.0, 25, fix_arabic("نظام الشهاب Pro للتدقيق والمحاسبة الذكية"))

    p.save()
    buffer.seek(0)
    return buffer

# ================= 4. التقرير اليومي (A4) - مع الحماية السرية التامة للوكيل =================
def generate_daily_report(date_str: str, wholesale, retail, collected, expenses, damaged, 
                          network_cash=0, telecom_cash=0, total_drawer_cash=0, is_agent_copy=False) -> BytesIO:
    """
    ملاحظة أمان:
    - إذا كان is_agent_copy=False: تصدر نسخة رسمية للمدير العام تركز حصرياً على حركة الكروت دون ذكر التسديدات إطلاقاً.
    - إذا كان is_agent_copy=True: تصدر نسخة خاصة بالوكيل تتضمن كاش التسديدات والدرج الكامل.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setStrokeColor(colors.HexColor("#1F4E78"))
    p.setLineWidth(1.5)
    p.rect(15, 15, width - 30, height - 30)

    p.setFillColor(colors.HexColor("#1F4E78"))
    p.rect(15, height - 90, width - 30, 75, fill=1)
    draw_logo(p, width - 85, height - 80, 55, 55)
    
    p.setFillColor(colors.white)
    p.setFont(FONT_NAME, 20)
    report_title = "التقرير المالي اليومي للوكالة" if is_agent_copy else "تقرير مبيعات وحركة الكروت اليومي"
    p.drawCentredString(width / 2.0, height - 50, fix_arabic(report_title))
    p.setFont(FONT_NAME, 12)
    p.drawCentredString(width / 2.0, height - 73, fix_arabic(f"تاريخ التقرير: {date_str}"))

    p.setFillColor(colors.black)
    p.setFont(FONT_NAME, 14)
    
    y = height - 130
    spacing = 38

    p.drawRightString(width - 45, y, fix_arabic(f"مبيعات الجملة للبقالات (آجل): {safe_amount(wholesale)} ريال"))
    y -= spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مبيعات التجزئة (كاش مباشر): {safe_amount(retail)} ريال"))
    y -= spacing
    p.drawRightString(width - 45, y, fix_arabic(f"المبالغ المحصلة من ديون البقالات: {safe_amount(collected)} ريال"))
    y -= spacing
    p.drawRightString(width - 45, y, fix_arabic(f"المصروفات والتسديدات التشغيلية: {safe_amount(expenses)} ريال"))
    y -= spacing
    p.drawRightString(width - 45, y, fix_arabic(f"الكروت التالفة المسجلة اليوم: {safe_amount(damaged)} ريال"))
    
    y -= 45
    p.setStrokeColor(colors.lightgrey)
    p.line(40, y + 15, width - 40, y + 15)

    if is_agent_copy:
        # تقرير الوكيل السري
        p.setFillColor(colors.HexColor("#006400"))
        p.setFont(FONT_NAME, 16)
        p.drawRightString(width - 45, y, fix_arabic(f"إجمالي النقدية الشاملة بالدرج: {safe_amount(total_drawer_cash)} ريال"))
        y -= 25
        p.setFont(FONT_NAME, 12)
        p.setFillColor(colors.dimgrey)
        p.drawRightString(width - 45, y, fix_arabic(f"- كاش الشبكة المتبقي: {safe_amount(network_cash)} ريال"))
        y -= 20
        p.drawRightString(width - 45, y, fix_arabic(f"- كاش بوابة التسديدات: {safe_amount(telecom_cash)} ريال"))
    else:
        # تقرير المدير العام (محمي وخالٍ تماماً من التسديدات)
        p.setFillColor(colors.HexColor("#1F4E78"))
        p.setFont(FONT_NAME, 16)
        cards_net_cash = safe_amount(collected, as_float=True) + safe_amount(retail, as_float=True) - safe_amount(expenses, as_float=True)
        p.drawRightString(width - 45, y, fix_arabic(f"صافي النقدية الموردة من الكروت: {safe_amount(cards_net_cash)} ريال"))

    p.setFont(FONT_NAME, 9)
    p.setFillColor(colors.dimgrey)
    p.drawCentredString(width / 2.0, 25, fix_arabic("تم الإصدار آلياً عبر نظام الشهاب Pro"))

    p.save()
    buffer.seek(0)
    return buffer

# ================= 5. تقرير المركز المالي الشامل (A4) =================
def generate_comprehensive_report(total_profit, market_debt, inventory_value, available_cash, net_to_gm) -> BytesIO:
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setStrokeColor(colors.HexColor("#1F4E78"))
    p.setLineWidth(1.5)
    p.rect(15, 15, width - 30, height - 30)

    p.setFillColor(colors.HexColor("#1F4E78"))
    p.rect(15, height - 90, width - 30, 75, fill=1)
    draw_logo(p, width - 85, height - 80, 55, 55)
    
    p.setFillColor(colors.white)
    p.setFont(FONT_NAME, 20)
    p.drawCentredString(width / 2.0, height - 50, fix_arabic("تقرير المركز المالي الشامل (الكروت)"))
    p.setFont(FONT_NAME, 12)
    p.drawCentredString(width / 2.0, height - 73, fix_arabic(f"تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %H:%M')}"))

    p.setFillColor(colors.black)
    p.setFont(FONT_NAME, 14)
    
    y = height - 140
    p.drawRightString(width - 45, y, fix_arabic(f"إجمالي أرباح الوكيل المعتمدة: {safe_amount(total_profit)} ريال"))
    y -= 40
    p.drawRightString(width - 45, y, fix_arabic(f"إجمالي مديونيات السوق (البقالات): {safe_amount(market_debt)} ريال"))
    y -= 40
    p.drawRightString(width - 45, y, fix_arabic(f"إجمالي القيمة التقديرية للمخزون: {safe_amount(inventory_value)} ريال"))
    y -= 40
    p.drawRightString(width - 45, y, fix_arabic(f"السيولة النقدية المتوفرة لدى الوكيل: {safe_amount(available_cash)} ريال"))
    
    y -= 60
    p.setFillColor(colors.HexColor("#900C3F"))
    p.setFont(FONT_NAME, 16)
    p.drawRightString(width - 45, y, fix_arabic(f"الصافي المستحق للإدارة العامة: {safe_amount(net_to_gm)} ريال"))

    p.setFont(FONT_NAME, 9)
    p.setFillColor(colors.dimgrey)
    p.drawCentredString(width / 2.0, 25, fix_arabic("منظومة الشهاب Pro للرقابة المالية"))

    p.save()
    buffer.seek(0)
    return buffer

# ================= 6. التقرير المالي المخصص التفصيلي (A4) =================
def generate_custom_report_pdf(start_date: str, end_date: str, summary_data: dict) -> BytesIO:
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setStrokeColor(colors.HexColor("#1F4E78"))
    p.setLineWidth(1.5)
    p.rect(15, 15, width - 30, height - 30)

    p.setFillColor(colors.HexColor("#1F4E78"))
    p.rect(15, height - 90, width - 30, 75, fill=1)
    draw_logo(p, width - 85, height - 80, 55, 55)
    
    p.setFillColor(colors.white)
    p.setFont(FONT_NAME, 20)
    p.drawCentredString(width / 2.0, height - 50, fix_arabic("التقرير المالي الدوري المخصص"))
    p.setFont(FONT_NAME, 12)
    p.drawCentredString(width / 2.0, height - 73, fix_arabic(f"الفترة: من {start_date} إلى {end_date}"))

    p.setFont(FONT_NAME, 13)
    y = height - 125
    line_spacing = 22

    # قسم حركة الكروت
    p.setFillColor(colors.HexColor("#1F4E78"))
    p.drawString(width - 220, y, fix_arabic("[ حركة الكروت والمبيعات ]"))
    p.setFillColor(colors.black)
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"كروت مستلمة من الإدارة: {safe_amount(summary_data.get('received_from_gm', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مبيعات جملة للبقالات (آجل): {safe_amount(summary_data.get('wholesale_debt', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مبيعات جملة (نقدية): {safe_amount(summary_data.get('wholesale_cash', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مبيعات تجزئة مباشرة (كاش): {safe_amount(summary_data.get('retail_cash', 0))} ريال"))
    
    y -= (line_spacing + 8)

    # قسم حركة الأموال
    p.setFillColor(colors.HexColor("#1F4E78"))
    p.drawString(width - 220, y, fix_arabic("[ حركة الأموال والتحصيلات ]"))
    p.setFillColor(colors.black)
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"إجمالي تحصيلات الديون: {safe_amount(summary_data.get('collected', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مبالغ محولة للإدارة العامة: {safe_amount(summary_data.get('paid_to_gm', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"المصروفات التشغيلية: {safe_amount(summary_data.get('expenses', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"عمولات الوكيل المستحقة: {safe_amount(summary_data.get('agent_commission', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"سحوبات أرباح شخصية: {safe_amount(summary_data.get('profit_withdrawal', 0))} ريال"))

    y -= (line_spacing + 8)

    # قسم المرتجعات والتوالف
    p.setFillColor(colors.HexColor("#1F4E78"))
    p.drawString(width - 220, y, fix_arabic("[ المرتجعات والتوالف ]"))
    p.setFillColor(colors.black)
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مرتجعات من البقالات: {safe_amount(summary_data.get('returns_client', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"مرتجعات مسلّمة للإدارة: {safe_amount(summary_data.get('returns_gm', 0))} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"كروت تالفة مسجلة: {safe_amount(summary_data.get('damaged', 0))} ريال"))

    y -= 35
    p.setFillColor(colors.HexColor("#006400"))
    p.setFont(FONT_NAME, 15)
    net_cash = summary_data.get('net_cash', 0)
    p.drawRightString(width - 45, y, fix_arabic(f"صافي التدفق النقدي للفترة: {safe_amount(net_cash)} ريال"))

    p.setFont(FONT_NAME, 9)
    p.setFillColor(colors.dimgrey)
    p.drawCentredString(width / 2.0, 25, fix_arabic("نظام الشهاب Pro للمحاسبة الذكية"))

    p.save()
    buffer.seek(0)
    return buffer

# ================= 7. التقرير السري لمالية التسديدات (A4) - خاص بالوكيل فقط =================
def generate_telecom_secret_pdf(start_date: str, end_date: str, total_sales, total_profit, total_collected, total_recharged, current_balance) -> BytesIO:
    """تقرير مالي فائق السرية لا يشارك مع الإدارة ويخص نشاط الوكيل المستقل"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setStrokeColor(colors.HexColor("#4A154B"))
    p.setLineWidth(1.5)
    p.rect(15, 15, width - 30, height - 30)

    p.setFillColor(colors.HexColor("#4A154B"))
    p.rect(15, height - 90, width - 30, 75, fill=1)
    draw_logo(p, width - 85, height - 80, 55, 55)
    
    p.setFillColor(colors.white)
    p.setFont(FONT_NAME, 20)
    p.drawCentredString(width / 2.0, height - 50, fix_arabic("تقرير مالية التسديدات والشحن الفوري"))
    p.setFont(FONT_NAME, 12)
    p.drawCentredString(width / 2.0, height - 73, fix_arabic(f"خاص بالوكيل | الفترة: من {start_date} إلى {end_date}"))

    p.setFillColor(colors.black)
    p.setFont(FONT_NAME, 14)
    
    y = height - 140
    line_spacing = 40

    p.drawRightString(width - 45, y, fix_arabic(f"إجمالي مبيعات الباقات والشحن: {safe_amount(total_sales)} ريال"))
    y -= line_spacing
    p.setFillColor(colors.HexColor("#006400"))
    p.drawRightString(width - 45, y, fix_arabic(f"الأرباح الصافية المحققة للوكيل: {safe_amount(total_profit)} ريال"))
    p.setFillColor(colors.black)
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"تحصيلات ديون الرصيد من العملاء: {safe_amount(total_collected)} ريال"))
    y -= line_spacing
    p.drawRightString(width - 45, y, fix_arabic(f"تغذية رصيد البوابة (من الصندوق): {safe_amount(total_recharged)} ريال"))
    
    y -= 50
    p.setFillColor(colors.HexColor("#1A5276"))
    p.setFont(FONT_NAME, 16)
    p.drawRightString(width - 45, y, fix_arabic(f"الرصيد المتبقي ببوابة التسديدات: {safe_amount(current_balance)} ريال"))

    p.setFont(FONT_NAME, 9)
    p.setFillColor(colors.dimgrey)
    p.drawCentredString(width / 2.0, 25, fix_arabic("سري للغاية - بيانات استثمارية خاصة بحساب الوكيل المستقل"))

    p.save()
    buffer.seek(0)
    return buffer
