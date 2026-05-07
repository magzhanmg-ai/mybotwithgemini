import os
import asyncio
import gspread
import logging
import google.generativeai as genai
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Ключи и настройки
BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
SHEET_NAME = os.getenv('SHEET_NAME', 'Финансы')

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ ИИ ---
async def parse_message_with_ai(text):
    prompt = f"""
    Проанализируй текст расхода/дохода: "{text}"
    Верни ответ строго в формате: сумма,категория,тип
    Тип может быть только: доход или расход.
    Сумма — только число.
    Категория — одно слово с большой буквы.
    Если в тексте нет суммы, верни: error
    Пример: кофе 500 -> 500,Еда,расход
    """
    response = model.generate_content(prompt)
    result = response.text.strip()
    return result

# --- РАБОТА С ТАБЛИЦЕЙ ---
def add_to_sheet(data_string, user_name):
    # Разделяем ответ от ИИ
    amount, category, t_type = data_string.split(',')
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    
    date_now = datetime.now().strftime('%d.%m.%Y')
    sheet.append_row([date_now, user_name, t_type, category, amount])

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я твой финансовый ИИ-помощник. Пиши что угодно, например: 'купил продукты на 5000' или 'зарплата 400к'")

@dp.message()
async def handle_message(message: types.Message):
    ai_data = await parse_message_with_ai(message.text)
    
    if ai_data == "error":
        await message.answer("Не смог понять сумму. Попробуй написать понятнее.")
        return

    try:
        add_to_sheet(ai_data, message.from_user.first_name)
        # Красивый ответ пользователю
        amount, category, t_type = ai_data.split(',')
        icon = "💰" if t_type == "доход" else "✅"
        await message.answer(f"{icon} Записано в таблицу!\nСумма: {amount} ₸\nКатегория: {category}")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Ошибка доступа к таблице. Проверь Drive API и доступ для почты бота.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
