import os
import asyncio
import gspread
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
from google import genai

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- ВОТ ЭТИ СТРОКИ БЫЛИ ПРОПУЩЕНЫ ---
# Бот берет данные из переменных Railway
BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
SHEET_NAME = os.getenv('SHEET_NAME', 'Финансы')

# Инициализация ИИ
client_gemini = genai.Client(api_key=GEMINI_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ ИИ ---
async def parse_message_with_ai(text):
    sys_instr = (
        "Ты — финансовый помощник. Твоя задача — извлекать данные из текста. "
        "Отвечай СТРОГО в формате: сумма,категория,тип. "
        "Тип: только 'доход' или 'расход'. "
        "Сумма: только число (целое или через точку). "
        "Категория: Одно слово с большой буквы. "
        "Если суммы нет, ответь словом 'error'."
    )
    
    try:
        # Исправленный путь к модели для новой библиотеки
        response = client_gemini.models.generate_content(
            model="gemini-1.5-flash", 
            contents=text,
            config={"system_instruction": sys_instr}
        )
        
        res = response.text.strip().lower()
        if res.count(',') != 2:
            return "error"
        return res
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "error"

# --- ЗАПИСЬ В ТАБЛИЦУ ---
def add_to_sheet(ai_result, user_name):
    amount, category, t_type = ai_result.split(',')
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    
    date_now = datetime.now().strftime('%d.%m.%Y')
    sheet.append_row([date_now, user_name, t_type.capitalize(), category.capitalize(), amount])

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Салам, {message.from_user.first_name}! 👋\n"
        "Я ИИ-помощник для бюджета. Просто пиши:\n"
        "— 'бензин 15000'\n"
        "— 'зарплата 400к'"
    )

@dp.message()
async def handle_any_text(message: types.Message):
    parse_res = await parse_message_with_ai(message.text)
    
    if parse_res == "error":
        await message.answer("Не понял сумму. Попробуй написать понятнее.")
        return

    try:
        add_to_sheet(parse_res, message.from_user.first_name)
        amount, category, t_type = parse_res.split(',')
        icon = "💰" if "доход" in t_type else "✅"
        await message.answer(f"{icon} Записано!\n— {amount} ₸ ({category})")
    except Exception as e:
        logging.error(f"Sheet Error: {e}")
        await message.answer("Ошибка записи в таблицу. Проверь доступ для email бота!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
