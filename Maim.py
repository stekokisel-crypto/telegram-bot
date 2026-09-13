import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.foutils import safe_text
from groq import Groq

# Получаем токены из переменных окружения Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я твой расширенный AI-ассистент на базе Groq. Я умею отвечать на тексты и голосовые сообщения. Напиши или скажи мне что-нибудь!")

# Обработка голосовых сообщений
@dp.message(lambda message: message.voice is not None)
async def handle_voice(message: types.Message):
    try:
        await message.answer("🎧 Распознаю голосовое сообщение...")
        
        # Скачиваем голосовой файл из Telegram
        voice = message.voice
        file = await bot.get_file(voice.file_id)
        file_path = file.file_path
        
        # Загружаем байты файла
        voice_bytes = await bot.download_file(file_path)
        
        # Отправляем в Groq Whisper для расшифровки в текст
        transcription = client.audio.transcriptions.create(
            file=("voice.ogg", voice_bytes.read()),
            model="whisper-large-v3",
            language="ru"
        )
        
        user_text = transcription.text
        await message.answer(f"🗣 Распознано: *{user_text}*", parse_mode="Markdown")
        
        # Передаем распознанный текст модели для генерации ответа
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — профессиональный, экспертный и глубокий AI-ассистент. Отвечай максимально развернуто, структурировано, детально и качественно на любые вопросы."},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=1500,
            temperature=0.7
        )
        answer = chat_completion.choices[0].message.content
        await message.answer(answer)
        
    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке голоса: {e}")

# Обработка обычных текстовых сообщений
@dp.message()
async def chat_with_groq(message: types.Message):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — профессиональный, экспертный и глубокий AI-ассистент. Отвечай максимально развернуто, структурировано, детально и качественно на любые вопросы."},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=1500,
            temperature=0.7
        )
        answer = chat_completion.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
