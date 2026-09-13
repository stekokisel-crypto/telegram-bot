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

# Используем официальный клиент Google GenAI с актуальной быстрой моделью
client = genai.Client(api_key=GEMINI_API_KEY)
FAST_MODEL = 'gemini-2.5-flash'

# Веб-сервер для удержания порта на Render
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
        "Привет! Я готов к работе.\n\n"
        "📸 **Фото**: отправь картинку товара\n"
        "🎙 **Голос**: отправь голосовое сообщение\n"
        "🎨 **Генерация**: `/image [описание]`\n"
        "💬 **Текст**: пиши любые вопросы!"
    )

# Команда для генерации изображений: /image <описание>
@dp.message(Command("image"))
async def cmd_generate_image(message: types.Message):
    query = message.text.replace("/image", "").strip()
    if not query:
        await message.answer("Укажи описание, например: `/image кроссовки в студии`")
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

# Обработка фотографий
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo_file_path = None
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        photo_file_path = f"photo_{message.from_user.id}.jpg"
        await message.bot.download_file(file_info.file_path, photo_file_path)

        # Загружаем файл через клиент Google GenAI
        uploaded_file = client.files.upload(file=photo_file_path)
        prompt_text = message.caption if message.caption else "Оцени этот товар, опиши его и помоги найти."

        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=[uploaded_file, prompt_text]
        )
        
        await message.answer(response.text)

    except Exception as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            await message.answer("Сервер перегружен. Повтори отправку фото через пару секунд.")
        else:
            await message.answer(f"Ошибка: {e}")
            
    finally:
        if photo_file_path and os.path.exists(photo_file_path):
            os.remove(photo_file_path)

# Обработка голосовых сообщений (с улучшенным чтением аудио)
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
            contents=[audio_file, "Внимательно прослушай это голосовое сообщение, расшифруй суть и ответь на него четко и по делу."]
        )
        
        await message.answer(response.text)

    except Exception as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            await message.answer("Сервер перегружен. Повтори голосовое.")
        else:
            await message.answer(f"Ошибка обработки голоса: {e}")
            
    finally:
        if voice_file_path and os.path.exists(voice_file_path):
            os.remove(voice_file_path)

# Обработка текстовых сообщений
@dp.message(F.text)
async def chat_with_gemini(message: types.Message):
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=message.text,
        )
        await message.answer(response.text)
    except Exception as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            await message.answer("Сервер перегружен. Повтори запрос.")
        else:
            await message.answer(f"Ошибка: {e}")

async def main():
    asyncio.create_task(web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
            
