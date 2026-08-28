import os
import asyncio
import sqlite3
from gtts import gTTS
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile
from google import genai
from google.genai import types as genai_types

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

SYSTEM_INSTRUCTION = (
    "Siz 'Aura AI' nomli aqlli, xushmuomala va vaqtni tejaydigan Telegram yordamchisiz. "
    "Foydalanuvchiga har doim aniq, ravon va tushunarli o'zbek tilida javob bering."
)

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    first_name = message.from_user.first_name
    
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"Men <b>Aura AI</b> — sizning shaxsiy sun'iy intellekt yordamchingizman. 🤖✨\n\n"
        f"Menga matn yuborishingiz, 📸 <b>rasm</b> tahlil qildirishingiz yoki 🎙 <b>ovozli xabar</b> yuborishingiz mumkin. Ovozli xabaringizga men ham ovozda javob qaytaraman!\n\n"
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

# Matnli xabarlar uchun
@dp.message(F.text)
async def handle_ai_chat(message: types.Message):
    add_user(message.from_user.id)
    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    if user_id not in user_chats:
        user_chats[user_id] = ai_client.chats.create(
            model="gemini-3.6-flash",
            config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )

    try:
        response = user_chats[user_id].send_message(message.text)
        await message.answer(response.text)
    except Exception as e:
        print(f"AI Xatoligi: {e}")
        await message.answer("⚠️ Javob tayyorlashda xatolik yuz berdi.")

# Rasm fayllarini tahlil qilish
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    add_user(message.from_user.id)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()

        caption = message.caption or "Ushbu rasmni batafsil tahlil qilib ber va rasmda nimalar borligini ayt."

        response = ai_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                caption
            ],
            config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )
        await message.answer(response.text)
    except Exception as e:
        print(f"Rasm tahlili xatosi: {e}")
        await message.answer("⚠️ Rasmni tahlil qilishda xatolik yuz berdi.")

# Ovozli xabarlarni tushunish va OVOZDA javob qaytarish
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    add_user(message.from_user.id)
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

    try:
        voice = message.voice
        file_info = await bot.get_file(voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        audio_bytes = downloaded_file.read()

        response = ai_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                genai_types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
                "Ushbu ovozli xabarga o'zbek tilida qisqa va tushunarli javob ber."
            ],
            config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )

        ai_text = response.text

        # Matnni ovozga aylantirish (gTTS)
        tts = gTTS(text=ai_text, lang='uz')
        audio_path = f"voice_resp_{message.from_user.id}.mp3"
        tts.save(audio_path)

        # Ovozli xabar qilib yuborish
        voice_file = FSInputFile(audio_path)
        await message.answer_voice(voice=voice_file, caption=ai_text)

        # Faylni tozalash
        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        print(f"Ovoz tahlili xatosi: {e}")
        await message.answer("⚠️ Ovozli xabarni qayta ishlashda xatolik yuz berdi.")

async def main():
    print("Aura AI Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())