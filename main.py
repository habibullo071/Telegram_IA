import os
import re
import asyncio
import sqlite3
from io import BytesIO
from gtts import gTTS
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import BufferedInputFile
import google.generativeai as genai

# Token va Kalitlar
BOT_TOKEN = os.getenv("BOT_TOKEN", "8900959568:AAE1XTEYPD0ms516bMpXMClzUTG_dbHppS0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6JJa7sqz4KjUPb4Z_I1rEKwq3x1s-gXFEaWQO58CxP-Kg")
ADMIN_ID = 5233653056

# Gemini API sozlashingiz
genai.configure(api_key=GEMINI_API_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

SYSTEM_INSTRUCTION = (
    "Siz 'Aura AI' nomli aqlli, xushmuomala va vaqtni tejaydigan Telegram yordamchisiz. "
    "Foydalanuvchi qaysi tilda (o'zbek, rus, ingliz, turk) murojaat qilsa, "
    "xuddi shu tilda aniq, ravon va tushunarli javob bering."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

def detect_gtts_lang(text: str) -> str:
    if re.search(r'[а-яА-ЯёЁ]', text):
        return 'ru'
    text_lower = text.lower()
    if re.search(r'[çğıöşüÇĞİÖŞÜ]', text):
        return 'tr'
    english_words = ['the', 'is', 'are', 'you', 'what', 'how', 'this', 'that', 'with', 'have', 'for']
    words = re.findall(r'\b\w+\b', text_lower)
    if any(word in english_words for word in words):
        return 'en'
    return 'tr'

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    first_name = message.from_user.first_name
    
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"Men <b>Aura AI</b> — sizning shaxsiy sun'iy intellekt yordamchingizman. 🤖✨\n\n"
        f"Menga matn yuborishingiz, 📸 <b>rasm</b> tahlil qildirishingiz yoki 🎙 <b>ovozli xabar</b> yuborishingiz mumkin.\n\n"
        f"💡 <i>Suhbat xotirasini tozalash uchun /clear buyrug'ini yuboring.</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("clear"))
async def clear_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
        await message.answer("🧹 Suhbat xotirasi tozalandi!")
    else:
        await message.answer("Suhbat xotirasi bo'sh.")

@dp.message(Command("stat"))
async def stat_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        count = get_users_count()
        await message.answer(f"📊 Foydalanuvchilar: <b>{count}</b> ta", parse_mode="HTML")

# 1. MATN -> MATN
@dp.message(F.text)
async def handle_ai_chat(message: types.Message):
    add_user(message.from_user.id)
    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])

    try:
        response = user_chats[user_id].send_message(message.text)
        await message.answer(response.text)
    except Exception as e:
        print(f"AI Xatoligi: {e}")
        await message.answer("⚠️ Javob tayyorlashda xatolik yuz berdi. API Key yoki ulanishni tekshiring.")

# 2. RASM -> MATN
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    add_user(message.from_user.id)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()

        caption = message.caption or "Ushbu rasmni tahlil qilib ber."

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        response = model.generate_content([caption, image_part])
        await message.answer(response.text)
    except Exception as e:
        print(f"Rasm tahlili xatosi: {e}")
        await message.answer("⚠️ Rasmni tahlil qilishda xatolik yuz berdi.")

# 3. OVOZ -> OVOZ
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    add_user(message.from_user.id)
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    try:
        voice = message.voice
        file_info = await bot.get_file(voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        audio_bytes = downloaded_file.read()

        audio_part = {
            "mime_type": "audio/ogg",
            "data": audio_bytes
        }

        response = model.generate_content([
            "Ushbu ovozli xabarga foydalanuvchi gapirgan tilda qisqa va aniq javob ber.",
            audio_part
        ])

        ai_text = response.text or "Ovozli xabaringiz qabul qilindi."

        try:
            target_lang = detect_gtts_lang(ai_text)
            tts = gTTS(text=ai_text, lang=target_lang)
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            voice_file = BufferedInputFile(fp.read(), filename="response.ogg")
            await message.answer_voice(voice=voice_file, caption=ai_text)
        except Exception as tts_err:
            print(f"gTTS xatosi: {tts_err}")
            await message.answer(ai_text)

    except Exception as e:
        print(f"Ovoz tahlili xatosi: {e}")
        await message.answer("⚠️ Ovozli xabarni qayta ishlashda xatolik yuz berdi.")

async def main():
    print("Aura AI Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())