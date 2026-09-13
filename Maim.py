import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация официального клиента Google GenAI
client = genai.Client(api_key=GEMINI_API_KEY)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Бот успешно переключен на Google Gemini и готов к работе. Напиши мне что-нибудь!")

@dp.message()
async def chat_with_gemini(message: types.Message):
    try:
        # Отправляем текстовое сообщение модели gemini-2.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
        )
        await message.answer(response.text)
    except Exception as e:
        await message.answer(f"Произошла ошибка при обращении к Gemini: {e}")

async def main():
    # Очищаем зависшие вебхуки перед запуском поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
