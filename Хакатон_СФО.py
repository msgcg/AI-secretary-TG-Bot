import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.input_file import InputFile
from dotenv import load_dotenv

from stt import STT
from aiogram.types import ContentType
from PyPDF2 import PdfReader
from docx import Document

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)  # Объект бота
dp = Dispatcher(bot)  # Диспетчер для бота


stt = STT()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
)


# Хэндлер на команду /start , /help
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    await message.reply(
        "Привет! Это Ваш персональтный ИИ секретарь от MMC.co!"
        "Отправьте мне запись встречи в аудио, docx, pdf формате или сообщением, и я классифицирую материал, выделяя главное!"
    )


# Хэндлер на команду /test
@dp.message_handler(commands="test")
async def cmd_test(message: types.Message):
    """
    Обработчик команды /test
    """
    await message.answer("Test")


# Функция ИИ суммаризации
async def ai_answer(text: str, message: types.Message):
    # 1. Обработка основного текста
    try:
        await message.answer("ИИ начинает обработку, пожалуйста, подождите или наберите чаек...")
        from g4f.client import Client
        client = Client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "Businessman", "content": "Select the main things from the text, summarize and structure this things. Be sure to highlight the characters of the dialogues. Use only Russian. Text:" + text}],
        )
        await message.answer(response.choices[0].message.content)
    except:
        await message.answer("Произошла ошибка при обработке основного текста.")

    # 2. Распределение задач на основании текста
    try:
        await message.answer("Сейчас я попытаюсь распределить задачи на основании текста...")
        from g4f.client import Client
        client = Client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "SheduleTask_maker", "content": "Create shedule of the tasks by the text. Use only Russian. Text:" + text}],
        )
        await message.answer(response.choices[0].message.content)
    except:
        await message.answer("Произошла ошибка при создании расписания задач.")

    # 3. Создание таблицы протоколов
    try:
        await message.answer("Создаю таблицу протоколов...")
        from g4f.client import Client
        client = Client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "SheduleTask_maker", "content": "Create a formatted little protocol table based on the text. Use only Russian. Text:" + text}],
        )
        await message.answer(response.choices[0].message.content)
    except:
        await message.answer("Произошла ошибка при создании таблицы протоколов.")


# Хэндлер на получение текста
@dp.message_handler(content_types=[types.ContentType.TEXT])
async def cmd_text(message: types.Message):
    """
    Обработчик на получение текста
    """
    await message.reply("Текст получен, обрабатываю")
    await ai_answer(message.text, message)







# Функция для извлечения текста из PDF
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as file:
        pdf = PdfReader(file)
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text
# Функция для извлечения текста из Word документов
def extract_text_from_word(file_path):
    text = ""
    doc = Document(file_path)
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

# Хэндлер на получение голосового, аудио сообщения и различных типов документов
@dp.message_handler(content_types=[
    ContentType.VOICE,
    ContentType.AUDIO,
    ContentType.DOCUMENT
])
async def message_handler(message: types.Message):
    """
    Обработчик на получение голосового, аудио сообщения и различных типов документов.
    """
    if message.content_type == ContentType.VOICE:
        file_id = message.voice.file_id
    elif message.content_type == ContentType.AUDIO:
        file_id = message.audio.file_id
    elif message.content_type == ContentType.DOCUMENT:
        file_id = message.document.file_id
        file_name = message.document.file_name
    else:
        await message.reply("❌Формат документа не поддерживается")
        return

    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_on_disk = Path("", f"{file_id}.tmp")
    await bot.download_file(file_path, destination=file_on_disk)
    await message.reply("Данные получены, обрабатываю")

    if message.content_type in [ContentType.VOICE, ContentType.AUDIO]:
        text = stt.audio_to_text(file_on_disk)
        if not text:
            text = "❌Не удалось распознать аудио"
            await message.answer(text)
        else:
            await message.answer("🎙️Распознанный текст:\n\n" + text)
            await ai_answer(text, message)
    elif message.content_type == ContentType.DOCUMENT:
        # Определите тип документа и извлеките текст
        if file_name.endswith('.txt'):
            with open(file_on_disk, 'r', encoding='utf-8') as file:
                text = file.read()
        elif file_name.endswith('.pdf'):
            text = extract_text_from_pdf(file_on_disk)
        elif file_name.endswith('.docx'):
            text = extract_text_from_word(file_on_disk)
        else:
            text = "❌Формат файла не поддерживается"
        
        if text:
            await message.answer("✒️Содержимое документа:\n\n" + text)
            await ai_answer(text, message)

    os.remove(file_on_disk)



if __name__ == "__main__":
    # Запуск бота
    print("БОТ ЗАПУЩЕН УСПЕШНО")
    try:
        executor.start_polling(dp, skip_updates=True)
    except (KeyboardInterrupt, SystemExit):
        pass
