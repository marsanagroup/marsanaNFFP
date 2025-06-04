import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from PIL import Image, ImageFilter
import pytesseract
import os
import datetime
import openpyxl

# بيانات التسعيرة والبونس
DESTINATIONS = {
    "Madinat Zayed": {"price": 792, "bonus": 50},
    "Al Mirfa": {"price": 771, "bonus": 50},
    "Bukrriah": {"price": 890, "bonus": 45},
    "Al Faya": {"price": 770, "bonus": 35},
    "Al Ankah": {"price": 761, "bonus": 45},
    "Wahat Al Sahraa": {"price": 1051, "bonus": 80},
    "Husan": {"price": 943, "bonus": 75},
    "hammem": {"price": 953, "bonus": 75}
}

# بيانات رواتب السائقين
DRIVERS = {
    "MAHENDER SINGH": 2000,
    "Shakawat": 2000
}

BOT_TOKEN = "7900725697:AAEgnCPXnEb1wvT4ixJSUSwb6h-AdHu_6m4"
FILE_NAME = "marsana_daily.xlsx"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل صورة ورقة الترب، ثم أرسل رقم الديزل مباشرة بعد الصورة.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"{user_id}_trip.jpg"
    await file.download_to_drive(file_path)

    image = Image.open(file_path)
    image = image.convert('L')
    image = image.filter(ImageFilter.SHARPEN)

    text = pytesseract.image_to_string(image, lang='eng+ara')
    os.remove(file_path)

    context.user_data['ocr_text'] = text
    await update.message.reply_text("تم استلام الصورة، الآن أرسل لي كم صرفت ديزل؟ (مثال: 10.30)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'ocr_text' not in context.user_data:
        await update.message.reply_text("أرسل صورة ورقة الترب أولاً.")
        return

    diesel_input = update.message.text.strip()
    try:
        diesel = float(diesel_input)
    except ValueError:
        await update.message.reply_text("الرجاء إرسال رقم ديزل صحيح (مثال: 10.30)")
        return

    text = context.user_data['ocr_text']
    lines = text.split("\n")

    shipment = ""
    order = ""
    truck = ""
    driver = ""
    destination = ""

    for line in lines:
        if "Shipment" in line:
            shipment = line.split()[-1]
        if "Delivery note" in line or "note number" in line:
            order = line.split()[-1]
        if "Truck" in line:
            truck = line.split()[-1]
        if "Driver Name" in line:
            driver = " ".join(line.split()[3:])
        if "Madinat Zayed" in line:
            destination = "Madinat Zayed"
        for dest in DESTINATIONS:
            if dest in line:
                destination = dest

    trip_data = DESTINATIONS.get(destination, {"price": 0, "bonus": 0})
    driver_salary = DRIVERS.get(driver.strip(), 0)
    price = trip_data["price"]
    bonus = trip_data["bonus"]
    total = price + bonus - diesel
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    row = [date, driver.strip(), truck, shipment, order, destination, price, bonus, diesel, total]
    save_to_excel(row)

    msg = f"""✅ تم تسجيل الرحلة:
التاريخ: {date}
السائق: {driver}
رقم الشاحنة: {truck}
رقم الشحنة: {shipment}
رقم الطلبية: {order}
الوجهة: {destination}
السعر: {price} درهم
البونس: {bonus} درهم
الديزل: {diesel} درهم
✅ الصافي: {total} درهم"""

    await update.message.reply_text(msg)

def save_to_excel(row):
    if not os.path.exists(FILE_NAME):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["التاريخ", "السائق", "رقم الشاحنة", "رقم الشحنة", "رقم الطلبية", "الوجهة", "السعر", "البونس", "الديزل", "المجموع"])
        wb.save(FILE_NAME)

    wb = openpyxl.load_workbook(FILE_NAME)
    ws = wb.active
    ws.append(row)
    wb.save(FILE_NAME)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

app.run_polling()
