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
        "Привет! Ассистент с поиском в реальном времени и ссылками готов к работе.\n\n"
        "🔗 Напиши что найти (например: *«купи керамогранит в Днепре»*)\n"
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
async def chat_with_search(message: types.Message):
    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Запрос с поиском Google для реального времени и ссылок
        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=message.text,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
            )
        )
        
        reply_text = response.text if response.text else "Информация не найдена."
        
        # Автоматический сбор и добавление ссылок из результатов поиска
        links_section = ""
        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            if metadata.grounding_chunks:
                sources = []
                for chunk in metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        title = chunk.web.title or "Ссылка на сайт"
                        url = chunk.web.uri
                        sources.append(f"• [{title}]({url})")
                if sources:
                    links_section = "\n\n🔗 **Найденные ссылки:**\n" + "\n".join(sources[:5])

        await message.answer(reply_text + links_section, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            await message.answer("⚠️ Превышен лимит бесплатных запросов к поиску Google. Пожалуйста, подождите 1-2 минуты и повторите попытку.")
        else:
            await message.answer(f"Ошибка запроса: {e}")

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
        prompt_text = message.caption if message.caption else "Найди информацию об этом товаре в интернете, дай описание и ссылки."

        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=[uploaded_file, prompt_text],
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
            )
        )
        
        reply_text = response.text if response.text else "Информация не найдена."
        links_section = ""
        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            if metadata.grounding_chunks:
                sources = []
                for chunk in metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        title = chunk.web.title or "Ссылка"
                        url = chunk.web.uri
                        sources.append(f"• [{title}]({url})")
                if sources:
                    links_section = "\n\n🔗 **Ссылки:**\n" + "\n".join(sources[:5])

        await message.answer(reply_text + links_section, parse_mode="Markdown", disable_web_page_preview=True)
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
            contents=[audio_file, "Прослушай голосовое сообщение, выполни поиск в интернете и предоставь ответ с ссылками."],
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(genai_types.GoogleSearch())],
            )
        )
        
        reply_text = response.text if response.text else "Информация не найдена."
        links_section = ""
        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            if metadata.grounding_chunks:
                sources = []
                for chunk in metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        title = chunk.web.title or "Ссылка"
                        url = chunk.web.uri
                        sources.append(f"• [{title}]({url})")
                if sources:
                    links_section = "\n\n🔗 **Ссылки:**\n" + "\n".join(sources[:5])

        await message.answer(reply_text + links_section, parse_Mode="Markdown", disable_web_page_preview=True)
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
                                           
