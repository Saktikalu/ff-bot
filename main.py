import telebot
import sqlite3
import os
from flask import Flask
from threading import Thread

# 1. वेब सर्वर सेटअप (रेंडर को फेल होने से बचाने के लिए)
app = Flask('')

@app.route('/')
def home():
    return "Free Fire Bot is Alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. आपका टेलीग्राम बॉट टोकन
API_TOKEN = "8678880550:AAGOQEJ_xQMgfOAlK1Yg9_vjD6wsc88N0D8"
bot = telebot.TeleBot(API_TOKEN)

# 3. आपकी टेलीग्राम Numeric ID
ADMIN_ID = 7694125647
MAX_PLAYERS = 48  # टूर्नामेंट के लिए अधिकतम खिलाड़ी

# डेटाबेस सेटअप
def init_db():
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            ff_uid TEXT,
            ff_name TEXT,
            match_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

# /start कमांड
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🏆 *Welcome to Free Fire Tournament Bot!*\n\n"
        "📜 *Commands List:*\n"
        "🔹 /register - टूर्नामेंट में भाग लें\n"
        "🔹 /unregister - अपना रजिस्ट्रेशन रद्द करें\n\n"
        "📌 *नोट:* केवल टॉप 48 खिलाड़ियों को ही स्लॉट मिलेगा।"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# रजिस्ट्रेशन की शुरुआत
@bot.message_handler(commands=['register'])
def start_registration(message):
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM players")
    count = cursor.fetchone()
    conn.close()

    if count[0] >= MAX_PLAYERS:
        bot.reply_to(message, f"❌ *ماف करें!* इस टूर्नामेंट के सभी {MAX_PLAYERS} स्लॉट फुल हो चुके हैं।", parse_mode='Markdown')
        return

    msg = bot.reply_to(message, "📝 कृपया अपना **Free Fire UID** टाइप करके भेजें:")
    bot.register_next_step_handler(msg, process_uid)

def process_uid(message):
    ff_uid = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    
    msg = bot.reply_to(message, "🎮 अब अपना **Free Fire In-Game Name (IGN)** भेजें:")
    bot.register_next_step_handler(msg, lambda m: ask_match_type(m, ff_uid, user_id, username))

def ask_match_type(message, ff_uid, user_id, username):
    ff_name = message.text
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Solo', 'Duo', 'Squad')
    
    msg = bot.reply_to(message, "⚔️ आप किस मोड में खेलना चाहते हैं? नीचे दिए गए बटन से चुनें:", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: save_player(m, ff_uid, ff_name, user_id, username))

def save_player(message, ff_uid, ff_name, user_id, username):
    match_type = message.text
    if match_type not in ['Solo', 'Duo', 'Squad']:
        bot.reply_to(message, "❌ गलत विकल्प। कृपया /register कमांड फिर से चलाएं।")
        return

    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?)", (user_id, username, ff_uid, ff_name, match_type))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM players")
        current_count = cursor.fetchone()
        
        success_msg = (
            f"✅ *रजिस्ट्रेशन सफल रहा!*\n\n"
            f"👤 *Name:* {ff_name}\n"
            f"🆔 *UID:* {ff_uid}\n"
            f"⚔️ *Mode:* {match_type}\n"
            f"🎟️ *Your Slot Number:* #{current_count[0]}\n\n"
            f"मैच शुरू होने से पहले रूम आईडी आपको यहाँ भेज दी जाएगी।"
        )
        bot.reply_to(message, success_msg, parse_mode='Markdown', reply_markup=telebot.types.ReplyKeyboardRemove())
    except sqlite3.IntegrityError:
        bot.reply_to(message, "❌ आप पहले से ही इस टूर्नामेंट में रजिस्टर्ड हैं।", reply_markup=telebot.types.ReplyKeyboardRemove())
    finally:
        conn.close()

# नाम हटाने की कमांड
@bot.message_handler(commands=['unregister'])
def remove_player(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("DELETE FROM players WHERE user_id=?", (user_id,))
        conn.commit()
        bot.reply_to(message, "⚠️ *आपका रजिस्ट्रेशन रद्द कर दिया गया है!*", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ आप इस टूर्नामेंट में रजिस्टर्ड नहीं हैं।")
    conn.close()

# ----------------- एडमिन फीचर -----------------

@bot.message_handler(commands=['sendroom'])
def ask_room_details(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.reply_to(message, "📢 सभी खिलाड़ियों को भेजने के लिए रूम विवरण टाइप करें:\n\n*(उदाहरण: Room ID: 12345, Pass: 555)*")
        bot.register_next_step_handler(msg, broadcast_room)
    else:
        bot.reply_to(message, "❌ यह कमांड केवल एडमिन के लिए है।")

def broadcast_room(message):
    room_details = message.text
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM players")
    all_players = cursor.fetchall()
    conn.close()
    
    success_count = 0
    for player in all_players:
        try:
            bot.send_message(player[0], f"🎮 *FREE FIRE ROOM DETAILS:*\n\n{room_details}", parse_mode='Markdown')
            success_count += 1
        except Exception:
            pass
            
    bot.reply_to(message, f"✅ रूम डिटेल्स सफलतापूर्वक {success_count} खिलाड़ियों को भेज दी गई है!")

@bot.message_handler(commands=['players'])
def view_players(message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('tournament.db')
        cursor = conn.cursor()
        cursor.execute("SELECT ff_name, ff_uid, match_type, username FROM players")
        rows = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM players")
        total_count = cursor.fetchone()
        conn.close()
        
        if not rows:
            bot.reply_to(message, "📭 अभी तक किसी भी खिलाड़ी ने रजिस्ट्रेशन नहीं किया है।")
            return
            
        response = f"🏆 *Registered Players ({total_count[0]}/{MAX_PLAYERS}):*\n\n"
        for index, row in enumerate(rows, start=1):
            response += f"{index}. *{row[0]}* ({row[2]}) | UID: {row[1]} | TG: @{row[3]}\n"
            
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ यह कमांड केवल एडमिन के लिए है।")

if __name__ == '__main__':
    init_db()
    keep_alive()
    print("Advanced Tournament Bot with Web Server is running...")
    bot.infinity_polling()
    
