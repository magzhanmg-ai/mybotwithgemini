import os
import asyncio
import gspread
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
from google import genai  # Новая библиотека

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Ключи и настройки
BOT_TOKEN = "8643907201:AAFsUqu288MfVlDwk_WoS2TP60wwzCmD5ug"
GEMINI_KEY = "AIzaSyC9wh_8AJyWVfztPQ_m1VhzoUBT0BgPPGU"
SHEET_NAME = os.getenv('SHEET_NAME', 'Финансы')

# Инициализация нового клиента Gemini
client_gemini = genai.Client(api_key=GEMINI_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ ИИ (Обновленная) ---
async def parse_message_with_ai(text):
    prompt = f"""
    Проанализируй текст: "{text}"
    Верни ответ строго в формате: сумма,категория,тип
    Тип: доход или расход.
    Сумма: только число.
    Категория: одно слово (например: Еда, Транспорт, Зарплата).
    Если суммы нет, верни: error
    """
    try:
        # Используем модель gemini-1.5.0-flash (она самая новая и стабильная)
        response = client_gemini.models.generate_content(
            model="gemini-1.5.0-flash", 
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Ошибка Gemini: {e}")
        return "error"

# --- РАБОТА С ТАБЛИЦЕЙ ---
def add_to_sheet(data_string, user_name):
    amount, category, t_type = data_string.split(',')
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    gc = gspread.authorize(creds)
    sheet = gc.open(SHEET_NAME).sheet1
    
    date_now = datetime.now().strftime('%d.%m.%Y')
    sheet.append_row([date_now, user_name, t_type, category, amount])

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("ИИ-помощник готов! Пиши расходы, например: 'такси 1200' или 'обед 3500'.")

@dp.message()
async def handle_message(message: types.Message):
    result = await parse_message_with_ai(message.text)
    
    if "error" in result or "," not in result:
        await message.answer("Не удалось распознать сумму. Попробуй написать проще.")
        return

    try:
        add_to_sheet(result, message.from_user.first_name)
        amount, category, t_type = result.split(',')
        icon = "💰" if "доход" in t_type else "✅"
        await message.answer(f"{icon} Записано!\n💰 Сумма: {amount} ₸\n📂 Категория: {category}")
    except Exception as e:
        logging.error(f"Ошибка записи: {e}")
        await message.answer("Бот работает, но не может достучаться до таблицы. Проверь доступ для email бота!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
