import os
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

# === Чтение конфигурации базы данных из base.txt ===
def read_db_config(path: str):
    config = {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл {path} не найден.")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                key, value = line.strip().split(":", 1)
                config[key.strip()] = value.strip()
    return config

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
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id SERIAL NOT NULL,
                username TEXT,
                log TEXT,
                dtime TIMESTAMP DEFAULT NOW()
            );
        """)
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
        ["Показать кота 🐱", "Информация о боте ℹ"]
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

# === Обработка сообщений ===
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = "Alex"
    user_message = update.message.text
    log_message_to_db(username, user_message)

    if user_message == "Показать кота 🐱":
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

    elif user_message == "Информация о боте ℹ":
        if os.path.exists(INFO_FILE):
            with open(INFO_FILE, "r", encoding="utf-8") as f:
                info_text = f.read()
            await update.message.reply_text(info_text, reply_markup=get_main_buttons())
        else:
            await update.message.reply_text("Файл с информацией не найден.", reply_markup=get_main_buttons())

    else:
        await update.message.reply_text(f"Вы написали: {user_message}", reply_markup=get_main_buttons())

# === Запуск ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", show_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Бот запущен...")
    app.run_polling()
