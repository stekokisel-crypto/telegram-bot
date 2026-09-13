import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = genai.Client(api_key=GEMINI_API_KEY)
FAST_MODEL = 'gemini-3.6-flash'

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
    await message.answer(
        "Привет! Ассистент готов к работе на максимальной скорости.\n\n"
        "💬 Задавай любые вопросы, ищи товары и информацию\n"
        "📸 Отправляй фото\n"
        "🎙 Отправляй голосовые"
    )

@dp.message(Command("image"))
async def cmd_generate_image(message: types.Message):
    query = message.text.replace("/image", "").strip()
    if not query:
        await message.answer("Укажи описание, например: `/image кроссовки`")
        return
    
    try:
        await message.bot.send_chat_action(message.chat.id, "upload_photo")
        result = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=query,
            config=dict(number_of_images=1, output_mime_type="image/jpeg")
        )
        for generated_image in result.generated_images:
            image_bytes = generated_image.image.image_bytes
            photo_file = types.BufferedInputFile(image_bytes, filename="generated.jpg")
            await message.answer_photo(photo=photo_file, caption=f"🎨 {query}")
            return
    except Exception as e:
        await message.answer(f"Не удалось сгенерировать: {e}")

@dp.message(F.text)
async def chat_with_gemini(message: types.Message):
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Запрос к модели с четкой инструкцией подбирать актуальные данные и ссылки
        prompt = (
            f"Пользователь спрашивает: '{message.text}'. "
            "Дай подробный, полезный ответ. Если применимо (например, поиск товаров или услуг), "
            "укажи ориентиры, где это можно найти, и актуальные ссылки на основные маркетплейсы или сайты."
        )
        
        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=prompt,
        )
        await message.answer(response.text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            await message.answer("⚠️ Слишком много запросов. Подождите 30 секунд.")
        else:
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
        prompt_text = message.caption if message.caption else "Опиши этот товар, оцени его и подскажи, где его можно найти."

        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=[uploaded_file, prompt_text]
        )
        await message.answer(response.text, parse_mode="Markdown")
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

        audio_file = client.files.upload(file=voice_file_path)

        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=[audio_file, "Прослушай голосовое сообщение, пойми суть задачи и дай развернутый ответ."]
        )
        await message.answer(response.text, parse_mode="Markdown")
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
