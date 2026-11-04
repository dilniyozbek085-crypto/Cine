import sqlite3
import telebot
from telebot import types

# Bot tokeningizni bu yerga yozasiz
TOKEN = "9256819212:AAH4OuaZQl0mtuhwt39XQ8AX-62CHUMmvY8"
ADMIN_ID = 8657503976  # O'z Telegram ID raqamingizni yozing

bot = telebot.TeleBot(TOKEN)

# --- BAZA BILAN ISHLASH ---
def db_connect():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    return conn

def setup_database():
    conn = db_connect()
    cursor = conn.cursor()
    # Kinolar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT,
            caption TEXT
        )
    """)
    # Majburiy obuna kanallari jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_username TEXT PRIMARY KEY,
            channel_title TEXT
        )
    """)
    conn.commit()
    conn.close()

setup_database()

# --- OBUNANI TEKSHIRISH FUNKSIYASI ---
def check_subscriptions(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_username, channel_title FROM channels")
    channels = cursor.fetchall()
    conn.close()

    not_subscribed = []
    for username, title in channels:
        try:
            member = bot.get_chat_member(username, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append((username, title))
        except Exception:
            # Agar bot kanalga admin bo'lmasa yoki xatolik bo'lsa
            not_subscribed.append((username, title))
    return not_subscribed

# --- /START BUYRUG'I ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    not_sub = check_subscriptions(user_id)

    if not_sub:
        markup = types.InlineKeyboardMarkup()
        for username, title in not_sub:
            # Username dan @ belgisini olib tashlablink yasaymiz
            clean_username = username.replace('@', '')
            markup.add(types.InlineKeyboardButton(text=f"📢 {title}", url=f"https://t.me/{clean_username}"))
        
        markup.add(types.InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
        bot.send_message(
            message.chat.id,
            "⚠️ **Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:**\n\n"
            "Obuna bo'lgach, **'✅ Obunani tekshirish'** tugmasini bosing.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        # Admin bo'lsa maxsus panel chiqadi
        if user_id == ADMIN_ID:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("🎬 Kino qo'shish"), types.KeyboardButton("🗑 Kino o'chirish"))
            markup.add(types.KeyboardButton("📢 Kanal qo'shish"), types.KeyboardButton("📋 Kanallar ro'yxati"))
            bot.send_message(message.chat.id, "Salom Admin! Kerakli bo'limni tanlang:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Xush kelibsiz! Kino kodini yuboring (masalan: `1`, `15`):", parse_mode="Markdown")

# --- OBUNANI TEKSHIRISH TUGMASI ---
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    not_sub = check_subscriptions(user_id)

    if not_sub:
        bot.answer_callback_query(call.id, "❌ Hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "Rahmat! Obuna tasdiqlandi ✅")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Endi kino kodini yuborishingiz mumkin!")

# --- ADMIN PANEL: KINO QO'SHISH ---
@bot.message_handler(func=lambda message: message.text == "🎬 Kino qo'shish" and message.from_user.id == ADMIN_ID)
def add_movie_step1(message):
    msg = bot.send_message(message.chat.id, "Kino uchun maxsus **kod** yuboring (masalan: `101`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_movie_code)

def process_movie_code(message):
    code = message.text.strip()
    msg = bot.send_message(message.chat.id, "Endi o'sha **kinoni (videoni)** yuboring:")
    bot.register_next_step_handler(msg, process_movie_video, code)

def process_movie_video(message, code):
    if not message.video:
        bot.send_message(message.chat.id, "❌ Iltimos, faqat video yuboring! Qaytadan urinib ko'ring.")
        return
    file_id = message.video.file_id
    caption = message.caption if message.caption else ""

    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, caption) VALUES (?, ?, ?)", (code, file_id, caption))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Kino muvaffaqiyatli saqlandi! Kodi: `{code}`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")
    finally:
        conn.close()

# --- ADMIN PANEL: KANAL QO'SHISH ---
@bot.message_handler(func=lambda message: message.text == "📢 Kanal qo'shish" and message.from_user.id == ADMIN_ID)
def add_channel_step(message):
    msg = bot.send_message(message.chat.id, "Kanal username'sini yuboring (masalan: `@favorit_kinos`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_channel_username)

def process_channel_username(message):
    username = message.text.strip()
    msg = bot.send_message(message.chat.id, "Kanalning nomini yuboring (masalan: `Favorit Kinos`):")
    bot.register_next_step_handler(msg, process_channel_title, username)

def process_channel_title(message, username):
    title = message.text.strip()
    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO channels (channel_username, channel_title) VALUES (?, ?)", (username, title))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Kanal muvaffaqiyatli qo'shildi: {title} ({username})")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xatolik: {e}")
    finally:
        conn.close()

# --- ADMIN PANEL: KANALLAR RO'YXATI ---
@bot.message_handler(func=lambda message: message.text == "📋 Kanallar ro'yxati" and message.from_user.id == ADMIN_ID)
def list_channels(message):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_username, channel_title FROM channels")
    channels = cursor.fetchall()
    conn.close()

    if not channels:
        bot.send_message(message.chat.id, "Hozircha majburiy obuna uchun kanallar qo'shilmagan.")
        return

    text = "📋 **Majburiy obuna kanallari:**\n\n"
    for username, title in channels:
        text += f"• {title} ({username})\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# --- KINOLARNI QIDIRISH (ODDIY FOYDALANUCHILAR UCHUN) ---
@bot.message_handler(func=lambda message: True)
def get_movie(message):
    user_id = message.from_user.id
    
    # Har safar xabar yozganda ham majburiy obunani tekshiramiz
    not_sub = check_subscriptions(user_id)
    if not_sub:
        markup = types.InlineKeyboardMarkup()
        for username, title in not_sub:
            clean_username = username.replace('@', '')
            markup.add(types.InlineKeyboardButton(text=f"📢 {title}", url=f"https://t.me/{clean_username}"))
        markup.add(types.InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
        bot.send_message(
            message.chat.id,
            "⚠️ Botdan foydalanish uchun avval kanallarga obuna bo'ling!",
            reply_markup=markup
        )
        return

    code = message.text.strip()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
    movie = cursor.fetchone()
    conn.close()

    if movie:
        file_id, caption = movie
        bot.send_video(message.chat.id, file_id, caption=caption)
    else:
        bot.send_message(message.chat.id, "❌ Bunday kodli kino topilmad. Iltimos, to'g'ri kod yuboring.")

# Botni ishga tushirish
print("Bot ishga tushdi...")
bot.infinity_polling()
