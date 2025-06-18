import os
import json
import random
import psycopg2
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === Загрузка токена ===
with open("token.txt", "r") as f:
    TOKEN = f.read().strip()

CATS_DIR = "/cats"
INFO_FILE = "info.txt"
DB_CONFIG_FILE = "base.txt"

# === Чтение конфигурации базы данных из JSON-файла ===
def read_db_config(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл {path} не найден.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === Подключение к PostgreSQL ===
conn = None
try:
    db_config = read_db_config(DB_CONFIG_FILE)
    conn = psycopg2.connect(
        host=db_config["host"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"],
        port=db_config["port"]
    )
    conn.autocommit = True
except Exception as e:
    print("Ошибка подключения к БД:", e)

# === Логирование в базу ===
def log_message_to_db(username: str, message: str):
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO bot_logs (username, log) VALUES (%s, %s);",
                    (username, message)
                )
        except Exception as e:
            print("Ошибка записи лога:", e)

# === Кнопки клавиатуры ===
def get_main_buttons():
    keyboard = [
        ["Главное меню ℹ", "Показать кота 🐱"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = "Alex"
    log_message_to_db(username, "/start")
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_buttons()
    )

# === /info ===
async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = "Alex"
    log_message_to_db(username, "/info")
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r", encoding="utf-8") as f:
            info_text = f.read()
        await update.message.reply_text(info_text, reply_markup=get_main_buttons())
    else:
        await update.message.reply_text("Файл с информацией не найден.", reply_markup=get_main_buttons())

# === /cats и кнопка "Показать кота 🐱" ===
async def send_random_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = "Alex"
    log_message_to_db(username, "/cats")

    image_files = [
        f for f in os.listdir(CATS_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if image_files:
        selected = random.choice(image_files)
        with open(os.path.join(CATS_DIR, selected), "rb") as photo:
            await update.message.reply_photo(photo=photo, reply_markup=get_main_buttons())
    else:
        await update.message.reply_text("Картинок не найдено 😿", reply_markup=get_main_buttons())

# === /base — вывод пользователей из bot_users ===
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = "Alex"
    log_message_to_db(username, "/base")

    if not conn:
        await update.message.reply_text("Нет соединения с базой данных.")
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, email, password FROM bot_users;")
            rows = cursor.fetchall()
            if not rows:
                await update.message.reply_text("Нет пользователей в базе.", reply_markup=get_main_buttons())
                return

            lines = []
            for i, (name, email, password) in enumerate(rows, start=1):
                email_part = email if email else "—"
                password_masked = "●●●●●●"
                lines.append(f"{i}. 👤 {name}\n📧 {email_part}\n🔒 {password_masked}")

            message = "\n\n".join(lines)
            await update.message.reply_text(message, reply_markup=get_main_buttons())

    except Exception as e:
        await update.message.reply_text(f"Ошибка при чтении данных: {e}", reply_markup=get_main_buttons())

# === Обработка обычных сообщений ===
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = "Alex"
    user_message = update.message.text
    log_message_to_db(username, user_message)

    if user_message == "Показать кота 🐱":
        await send_random_cat(update, context)

    elif user_message == "Информация о боте ℹ" or user_message == "Главное меню ℹ":
        await show_info(update, context)

    else:
        await update.message.reply_text(f"Вы написали: {user_message}", reply_markup=get_main_buttons())

# === Запуск бота ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", show_info))
    app.add_handler(CommandHandler("cats", send_random_cat))
    app.add_handler(CommandHandler("base", show_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Бот запущен...")
    app.run_polling()
