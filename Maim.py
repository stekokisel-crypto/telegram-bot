import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from google import genai
from google.genai import types as genai_types

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = 'models/gemini-3.6-flash'

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
    await message.answer("Привет! Бот на связи и готов к работе.")

@dp.message(F.text)
async def chat_with_gemini(message: types.Message):
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=message.text,
            config=genai_types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                system_instruction=(
                    "Ты полезный AI-ассистент. Если пользователь ищет товары, цены или услуги, "
                    "выполняй поиск в интернете и предоставляй актуальные данные со ссылками."
                )
            ),
        )
        
        await message.answer(response.text, disable_web_page_preview=False)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo_file_path = None
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        photo_file_path = f"photo_{message.from_user.id}.jpg"
        await message.bot.download_file(file_info.file_path, photo_file_path)

        uploaded_file = client.files.upload(file=photo_file_path)
        prompt_text = message.caption if message.caption else "Опиши это фото."

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[uploaded_file, prompt_text],
            config=genai_types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        await message.answer(response.text, disable_web_page_preview=False)
    except Exception as e:
        await message.answer(f"Ошибка с фото: {e}")
    finally:
        if photo_file_path and os.path.exists(photo_file_path):
            os.remove(photo_file_path)

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    voice_file_path = None
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        voice = await message.bot.get_file(message.voice.file_id)
        voice_file_path = f"voice_{message.from_user.id}.ogg"
        await message.bot.download_file(voice.file_path, voice_file_path)

        audio_file = client.files.upload(file=voice_file_path, config={"mime_type": "audio/ogg"})

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[audio_file, "Прослушай голосовое сообщение, найди информацию и ответь."],
            config=genai_types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        await message.answer(response.text, disable_web_page_preview=False)
    except Exception as e:
        await message.answer(f"Ошибка с голосом: {e}")
    finally:
        if voice_file_path and os.path.exists(voice_file_path):
            os.remove(voice_file_path)

async def main():
    asyncio.create_task(web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

