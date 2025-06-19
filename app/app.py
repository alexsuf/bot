import os
import json
import random
import psycopg2
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
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

# === Карта действий для кнопок по умолчанию ===
default_menu_map = {
    "Стартовая страница": "/start",
    "Меню ℹ": "/menu"
}

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

# === Получение Telegram username ===
def extract_username(update: Update) -> str:
    user = update.message.from_user
    return user.username or f"{user.first_name} {user.last_name or ''}".strip() or "Неизвестный"

# === Логирование в базу ===
def log_message_to_db(username: str, message: str):
    if conn and message:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO bot_logs (username, log) VALUES (%s, %s);",
                    (username, message)
                )
        except Exception as e:
            print("Ошибка записи лога:", e)

# === Статическая клавиатура по умолчанию ===
def get_main_buttons():
    keyboard = [[name for name in default_menu_map.keys()]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === Динамическое меню из bot_menu ===
def get_dynamic_menu(user_telegram_name: str | None):
    if not conn:
        return get_main_buttons()
    try:
        with conn.cursor() as cursor:
            if user_telegram_name == 'alexeyzadonsky':
                cursor.execute("SELECT menu_name FROM bot_menu WHERE menu_item = 'alexeyzadonsky' ORDER BY menu_id;")
            else:
                cursor.execute("SELECT menu_name FROM bot_menu WHERE menu_item = 'base' ORDER BY menu_id;")
            rows = cursor.fetchall()
            keyboard = [[name] for (name,) in rows] if rows else [[name for name in default_menu_map.keys()]]
            return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        print("Ошибка чтения меню:", e)
        return get_main_buttons()

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = extract_username(update)
    log_message_to_db(username, "/start")
    await show_info(update, context)

# === /info ===
async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = extract_username(update)
    log_message_to_db(username, "/info")
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r", encoding="utf-8") as f:
            info_text = f.read()
        await update.message.reply_text(info_text, reply_markup=get_main_buttons())
    else:
        await update.message.reply_text("Файл с информацией не найден.", reply_markup=get_main_buttons())

# === /cats ===
async def send_random_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = extract_username(update)
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

# === /users ===
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = extract_username(update)
    log_message_to_db(username, "/users")
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

# === /menu ===
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = extract_username(update)
    log_message_to_db(username, "/menu")
    telegram_username = update.message.from_user.username
    await update.message.reply_text("Выберите пункт меню:", reply_markup=get_dynamic_menu(telegram_username))

# === /logs ===
async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = extract_username(update)
    log_message_to_db(username, "/logs")
    if not conn:
        await update.message.reply_text("Нет соединения с базой данных.")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username, log, dtime FROM bot_logs ORDER BY id DESC LIMIT 20;")
            rows = cursor.fetchall()
            if not rows:
                await update.message.reply_text("Логов пока нет.")
                return
            log_lines = [f"<b>{u}</b> [{d.strftime('%Y-%m-%d %H:%M')}]: {l}" for u, l, d in rows]
            await update.message.reply_text("\n\n".join(log_lines), parse_mode=ParseMode.HTML, reply_markup=get_main_buttons())
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении логов: {e}")

# === Обработка текстовых сообщений ===
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    username = extract_username(update)
    user_message = update.message.text
    telegram_username = user.username
    log_message_to_db(username, user_message)

    try:
        menu_map = default_menu_map.copy()

        if conn:
            with conn.cursor() as cursor:
                if telegram_username == 'alexeyzadonsky':
                    cursor.execute("SELECT menu_name, menu_action FROM bot_menu WHERE menu_item = 'alexeyzadonsky';")
                else:
                    cursor.execute("SELECT menu_name, menu_action FROM bot_menu WHERE menu_item = 'base';")
                rows = cursor.fetchall()
                menu_map.update({name: action for name, action in rows})

        action = menu_map.get(user_message)
        if action:
            if action == "/info":
                await show_info(update, context)
            elif action == "/cats":
                await send_random_cat(update, context)
            elif action == "/users":
                await show_users(update, context)
            elif action == "/logs":
                await show_logs(update, context)
            elif action == "/menu":
                await show_menu(update, context)
            elif action == "/start":
                await start(update, context)
            return

    except Exception as e:
        print("Ошибка поиска действия по кнопке:", e)

    # Если не совпало с кнопками
    msg = f"<b>{username}</b> написал: {user_message}"
    await update.message.reply_text(msg, reply_markup=get_main_buttons(), parse_mode=ParseMode.HTML)

# === Запуск бота ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", show_info))
    app.add_handler(CommandHandler("cats", send_random_cat))
    app.add_handler(CommandHandler("users", show_users))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("logs", show_logs))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Бот запущен...")
    app.run_polling()

