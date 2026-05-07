import os
import asyncio
import gspread
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials

# Логирование
logging.basicConfig(level=logging.INFO)

# Конфигурация из переменных окружения
API_TOKEN = "8643907201:AAFsUqu288MfVlDwk_WoS2TP60wwzCmD5ug"
# Название твоей гугл-таблицы
SHEET_NAME = os.getenv('SHEET_NAME', 'Финансы') 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- РАБОТА С GOOGLE TABLES ---
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Файл service_account.json должен быть в папке проекта
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def add_to_sheet(user_id, user_name, amount, category, t_type):
    sheet = get_sheet()
    date_now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    # Добавляем строку в таблицу: Дата, ID, Имя, Тип, Категория, Сумма
    sheet.append_row([date_now, user_id, user_name, t_type, category, amount])

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Теперь я пишу всё в Google Таблицу 📊")

@dp.message()
async def process_finance(message: types.Message):
    text = message.text.lower().strip()
    parts = text.split()
    
    amount = None
    for part in parts:
        try:
            amount = float(part.replace(',', '.'))
            parts.remove(part)
            break
        except ValueError:
            continue

    if amount is None: return

    category = " ".join(parts) if parts else "разное"
    t_type = "доход" if any(word in category for word in ["зарплат", "доход", "пришло"]) else "расход"

    try:
        # Записываем в облако
        add_to_sheet(message.from_user.id, message.from_user.full_name, amount, category, t_type)
        icon = "💰" if t_type == "доход" else "✅"
        await message.answer(f"{icon} В таблицу добавлено: {amount:,.0f} ₸ ({category})")
    except Exception as e:
        logging.error(f"Ошибка Google: {e}")
        await message.answer("Ошибка при записи в таблицу. Проверь настройки доступа.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
