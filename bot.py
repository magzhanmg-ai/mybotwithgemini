
import os
import asyncio
import gspread
import logging
import google.generativeai as genai
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials

# Логи
logging.basicConfig(level=logging.INFO)

# Ключи
BOT_TOKEN = "8643907201:AAFsUqu288MfVlDwk_WoS2TP60wwzCmD5ug"
GEMINI_KEY = "AIzaSyC9wh_8AJyWVfztPQ_m1VhzoUBT0BgPPGU"
SHEET_NAME = "Финансы"

# Настройка Gemini (старый, проверенный способ)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def parse_message_with_ai(text):
    prompt = f"""
    Ты финансовый помощник. Извлеки данные из текста: "{text}"
    Верни ТОЛЬКО в формате: сумма,категория,тип
    Тип: доход или расход. Сумма: число. Категория: одно слово.
    Если нет суммы, верни: error
    Пример: кофе 500 -> 500,Еда,расход
    """
    try:
        # В этой библиотеке вызов идет проще
        response = model.generate_content(prompt)
        res = response.text.strip().lower()
        if res.count(',') != 2:
            return "error"
        return res
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "error"

def add_to_sheet(ai_result, user_name):
    amount, category, t_type = ai_result.split(',')
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    date_now = datetime.now().strftime('%d.%m.%Y')
    sheet.append_row([date_now, user_name, t_type.capitalize(), category.capitalize(), amount])

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот обновлен! Напиши расход, например: 'обед 2500'")

@dp.message()
async def handle(message: types.Message):
    res = await parse_message_with_ai(message.text)
    if res == "error":
        await message.answer("Не понял сумму. Напиши четче.")
        return
    try:
        add_to_sheet(res, message.from_user.first_name)
        amount, cat, t = res.split(',')
        await message.answer(f"✅ Записано: {amount} ₸ ({cat})")
    except Exception as e:
        logging.error(f"Sheet Error: {e}")
        await message.answer("Ошибка таблицы. Проверь доступ!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
