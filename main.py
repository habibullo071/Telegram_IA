import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from google import genai
from google.genai import types as genai_types

# Token va API kalitlar (Railway / Environment Variables orqali yoki to'g'ridan-to'g'ri o'qiydi)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8900959568:AAE1XTEYPD0ms516bMpXMClzUTG_dbHppS0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6Ksdnf6-IWKCgZIrcmKW68LrRflWddIXeY49_F2Nr5knw")
ADMIN_ID = 5233653056

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

user_chats = {}
DB_PATH = "aura_ai_users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

init_db()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    first_name = message.from_user.first_name
    
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"Men <b>Aura AI</b> — sizning shaxsiy sun'iy intellekt yordamchingizman. 🤖✨\n\n"
        f"Menga istalgan savolingizni yuborishingiz, kod tahlil qildirishingiz yoki matnlar tayyorlatishingiz mumkin.\n\n"
        f"💡 <i>Suhbat xotirasini tozalash uchun /clear buyrug'ini yuboring.</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("clear"))
async def clear_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
        await message.answer("🧹 Suhbat xotirasi tozalandi! Yangi mavzuda savol berishingiz mumkin.")
    else:
        await message.answer("Suhbat xotirasi allaqachon bo'sh.")

@dp.message(Command("stat"))
async def stat_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        count = get_users_count()
        await message.answer(f"📊 <b>Bot statistikasi:</b>\n\nJami foydalanuvchilar: <b>{count}</b> ta", parse_mode="HTML")

@dp.message(F.text)
async def handle_ai_chat(message: types.Message):
    add_user(message.from_user.id)
    user_id = message.from_user.id
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    if user_id not in user_chats:
        user_chats[user_id] = ai_client.chats.create(
            model="gemini-3.6-flash",
            config=genai_types.GenerateContentConfig(
                system_instruction=(
                    "Siz 'Aura AI' nomli aqlli, xushmuomala va vaqtni tejaydigan Telegram yordamchisiz. "
                    "Foydalanuvchiga har doim aniq, ravon va tushunarli o'zbek tilida javob bering."
                )
            )
        )

    chat = user_chats[user_id]

    try:
        response = chat.send_message(message.text)
        await message.answer(response.text)
    except Exception as e:
        print(f"AI Xatoligi: {e}")
        await message.answer("⚠️ Javob tayyorlashda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

async def main():
    print("Aura AI Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())