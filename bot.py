

import os
import asyncio
import gspread
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
from google import genai

# Настройка логирования, чтобы видеть ошибки в Railway
logging.basicConfig(level=logging.INFO)

# Берем настройки из переменных Railway
BOT_TOKEN = "8643907201:AAFsUqu288MfVlDwk_WoS2TP60wwzCmD5ug"
GEMINI_KEY = "AIzaSyC9wh_8AJyWVfztPQ_m1VhzoUBT0BgPPGU"
SHEET_NAME = os.getenv('SHEET_NAME', 'Финансы')

# Инициализация ИИ
client_gemini = genai.Client(api_key=GEMINI_KEY)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ ИИ ---
async def parse_message_with_ai(text):
    # Инструкция, которая заставляет ИИ отвечать только данными
    sys_instr = (
        "Ты — финансовый парсер. Твоя задача вычленять данные из текста. "
        "Отвечай СТРОГО в формате: сумма,категория,тип. "
        "Тип: только 'доход' или 'расход'. "
        "Сумма: только число (целое или через точку). "
        "Категория: Одно слово (Еда, Транспорт, Жилье, Досуг и т.д.). "
        "Если в сообщении нет суммы, ответь: error"
    )
    
    try:
        response = client_gemini.models.generate_content(
            model="gemini-1.5-flash",
            contents=text,
            config={"system_instruction": sys_instr}
        )
        
        res = response.text.strip().lower()
        # Проверка: ответ должен содержать две запятые (сумма,категория,тип)
        if res.count(',') != 2:
            return "error"
        return res
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "error"

# --- ЗАПИСЬ В ТАБЛИЦУ ---
def add_to_sheet(ai_result, user_name):
    # Разбиваем строку "500,еда,расход" на части
    amount, category, t_type = ai_result.split(',')
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Файл ключа должен лежать в той же папке на GitHub
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    
    date_now = datetime.now().strftime('%d.%m.%Y')
    # Записываем: Дата, Имя, Тип, Категория, Сумма
    sheet.append_row([date_now, user_name, t_type.capitalize(), category.capitalize(), amount])

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Салам, {message.from_user.first_name}! 👋\n"
        "Я записываю твои деньги в таблицу. Просто пиши текстом:\n"
        "— 'кофе 500'\n"
        "— 'пришла зп 350000'\n"
        "— 'заправился на 15к'"
    )

@dp.message()
async def handle_any_text(message: types.Message):
    # 1. Отправляем текст в ИИ
    parse_res = await parse_message_with_ai(message.text)
    
    if parse_res == "error":
        await message.answer("Не понял сумму. Попробуй написать точнее (например: 'ужин 4500').")
        return

    # 2. Пишем в таблицу
    try:
        add_to_sheet(parse_res, message.from_user.first_name)
        # 3. Отвечаем пользователю
        amount, category, t_type = parse_res.split(',')
        icon = "💰" if "доход" in t_type else "✅"
        await message.answer(f"{icon} В таблицу записано:\n— {amount} ₸ ({category})")
    except Exception as e:
        logging.error(f"Sheet Error: {e}")
        await message.answer("Бот понял данные, но не смог записать в таблицу. Проверь доступ!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
