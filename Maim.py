import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from groq import Groq

# Получаем токены из переменных окружения Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я ваш ИИ-бот на базе Groq. Напишите мне что-нибудь.")

@dp.message()
async def chat_with_groq(message: types.Message):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": message.text}
            ],
            model="llama3-8b-8192-versatile",
        )
        answer = chat_completion.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
