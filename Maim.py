import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = genai.Client(api_key=GEMINI_API_KEY)

# Простейший веб-сервер, чтобы Render не ругался на порты
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Бот успешно работает на Gemini 3.6 Flash.")

@dp.message()
async def chat_with_gemini(message: types.Message):
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=message.text,
        )
        await message.answer(response.text)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def main():
    # Запускаем фальшивый веб-сервер для порта Render
    asyncio.create_task(web_server())
    
    # Сбрасываем старые зависшие подключения Telegram
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
