import telebot
import sqlite3
import os
from flask import Flask
from threading import Thread

# 1. वेब सर्वर सेटअप (रेंडर के लिए)
app = Flask('')

@app.route('/')
def home():
    return "Free Fire UTR Bot is Alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. बॉट और एडमिन सेटअप
API_TOKEN = "8678880550:AAGOQEJ_xQMgfOAlK1Yg9_vjD6wsc88N0D8"
bot = telebot.TeleBot(API_TOKEN)

ADMIN_ID = 7694125647
MAX_PLAYERS = 48  # टूर्नामेंट के लिए अधिकतम खिलाड़ी

# अपने QR कोड इमेज की डायरेक्ट लिंक यहाँ डालें (Optional)
# यदि आपके पास लिंक नहीं है, तो बॉट सिर्फ टेक्स्ट निर्देश दिखाएगा।
QR_CODE_URL = "https://your-image-link-here.com"

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
            match_type TEXT,
            utr_id TEXT,
            status TEXT
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
        "🔹 /register - टूर्नामेंट के लिए रजिस्ट्रेशन प्रक्रिया शुरू करें\n"
        "🔹 /unregister - अपना रजिस्ट्रेशन रद्द करें\n\n"
        "📌 *नोट:* केवल अप्रूव्ड खिलाड़ियों को ही स्लॉट नंबर और रूम आईडी मिलेगी।"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# रजिस्ट्रेशन की शुरुआत
@bot.message_handler(commands=['register'])
def start_registration(message):
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM players WHERE status='Approved'")
    count = cursor.fetchone()[0]
    conn.close()

    if count >= MAX_PLAYERS:
        bot.reply_to(message, f"❌ *माफ करें!* इस टूर्नामेंट के सभी {MAX_PLAYERS} स्लॉट फुल हो चुके हैं।", parse_mode='Markdown')
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
    
    msg = bot.reply_to(message, "⚔️ अपना गेम मोड चुनें:", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: ask_payment(m, ff_uid, ff_name, user_id, username))

# खिलाड़ी से UTR विवरण मांगना
def ask_payment(message, ff_uid, ff_name, user_id, username):
    match_type = message.text
    if match_type not in ['Solo', 'Duo', 'Squad']:
        bot.reply_to(message, "❌ गलत विकल्प। कृपया /register फिर से करें।")
        return

    payment_text = (
        "💳 *रजिस्ट्रेशन प्रक्रिया (Verification Step):*\n\n"
        "1. ऊपर दिए गए निर्देशों/QR कोड के अनुसार प्रक्रिया पूरी करें।\n"
        "2. सफलतापूर्वक पूरा होने के बाद मिली **UTR ID / Transaction Number** को नीचे टाइप करके भेजें।\n\n"
        "⚠️ *ध्यान दें:* गलत UTR भेजने पर आपका रजिस्ट्रेशन रिजेक्ट कर दिया जाएगा।"
    )
    
    # यदि इमेज उपलब्ध है तो इमेज भेजें, अन्यथा सिर्फ टेक्स्ट
    try:
        msg = bot.send_photo(message.chat.id, QR_CODE_URL, caption=payment_text, parse_mode='Markdown', reply_markup=telebot.types.ReplyKeyboardRemove())
    except Exception:
        msg = bot.send_message(message.chat.id, payment_text, parse_mode='Markdown', reply_markup=telebot.types.ReplyKeyboardRemove())
        
    bot.register_next_step_handler(msg, lambda m: send_to_admin(m, ff_uid, ff_name, match_type, user_id, username))

# एडमिन को पेंडिंग रिक्वेस्ट भेजना
def send_to_admin(message, ff_uid, ff_name, match_type, user_id, username):
    utr_id = message.text
    
    # डेटाबेस में पेंडिंग स्टेटस के साथ सेव करना
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, 'Pending')", (user_id, username, ff_uid, ff_name, match_type, utr_id))
        conn.commit()
        
        bot.reply_to(message, "⏳ *आपका अनुरोध एडमिन को भेज दिया गया है!*\n\nसमीक्षा (Verification) पूरी होते ही आपको यहाँ स्लॉट नंबर मिल जाएगा।")
        
        # एडमिन के लिए इनलाइन बटन बनाना
        markup = telebot.types.InlineKeyboardMarkup()
        btn_approve = telebot.types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_id}")
        btn_reject = telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
        markup.add(btn_approve, btn_reject)
        
        admin_msg = (
            f"📢 *नया रजिस्ट्रेशन अनुरोध (Pending):*\n\n"
            f"👤 *Name:* {ff_name}\n"
            f"🆔 *UID:* {ff_uid}\n"
            f"⚔️ *Mode:* {match_type}\n"
            f"🧾 *UTR/Details:* `{utr_id}`\n"
            f"📱 *TG:* @{username}\n"
        )
        bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown', reply_markup=markup)
        
    except sqlite3.IntegrityError:
        bot.reply_to(message, "❌ आप पहले से ही रजिस्टर्ड हैं या आपका अनुरोध पेंडिंग है।")
    finally:
        conn.close()

# एडमिन के बटन क्लिक को हैंडल करना (Callback Query)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_admin_action(call):
    action, player_id = call.data.split('_')
    player_id = int(player_id)
    
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    
    if action == 'app':
        # स्टेटस अपडेट करना
        cursor.execute("UPDATE players SET status='Approved' WHERE user_id=?", (player_id,))
        conn.commit()
        
        # स्लॉट नंबर पता करना
        cursor.execute("SELECT COUNT(*) FROM players WHERE status='Approved'")
        slot_num = cursor.fetchone()[0]
        
        # खिलाड़ी को मैसेज भेजना
        try:
            bot.send_message(player_id, f"🎉 *बधाई हो! आपका रजिस्ट्रेशन अप्रूव हो गया है।*\n\n🎟️ *Your Slot Number:* #{slot_num}\n\nमैच शुरू होने से पहले रूम आईडी आपको यहीं मिल जाएगी।")
            bot.edit_message_text(f"{call.message.text}\n\n🟢 *Status: Approved (Slot #{slot_num})*", call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            bot.answer_callback_query(call.id, "खिलाड़ी को मैसेज नहीं भेजा जा सका!")
            
    elif action == 'rej':
        # डेटाबेस से हटाना
        cursor.execute("DELETE FROM players WHERE user_id=?", (player_id,))
        conn.commit()
        
        try:
            bot.send_message(player_id, "❌ *माफ करें!* आपका रजिस्ट्रेशन अनुरोध एडमिन द्वारा रिजेक्ट कर दिया गया है। कृपया सही विवरण के साथ दोबारा प्रयास करें।")
            bot.edit_message_text(f"{call.message.text}\n\n🔴 *Status: Rejected*", call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
            
    conn.close()
    bot.answer_callback_query(call.id, "Action Completed!")

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

# एडमिन रूम सेंडिंग फीचर (केवल अप्रूव्ड खिलाड़ियों को)
@bot.message_handler(commands=['sendroom'])
def ask_room_details(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.reply_to(message, "📢 सभी अप्रूव्ड खिलाड़ियों को भेजने के लिए रूम विवरण टाइप करें:\n\n*(उदाहरण: Room ID: 12345, Pass: 555)*")
        bot.register_next_step_handler(msg, broadcast_room)
    else:
        bot.reply_to(message, "❌ यह कमांड केवल एडमिन के लिए है।")

def broadcast_room(message):
    room_details = message.text
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM players WHERE status='Approved'")
    all_players = cursor.fetchall()
    conn.close()
    
    success_count = 0
    for player in all_players:
        try:
            bot.send_message(player[0], f"🎮 *FREE FIRE ROOM DETAILS:*\n\n{room_details}", parse_mode='Markdown')
            success_count += 1
        except Exception:
            pass
            
    bot.reply_to(message, f"✅ रूम डिटेल्स सफलतापूर्वक {success_count} अप्रूव्ड खिलाड़ियों को भेज दी गई है!")

@bot.message_handler(commands=['players'])
def view_players(message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('tournament.db')
        cursor = conn.cursor()
        cursor.execute("SELECT ff_name, ff_uid, match_type, utr_id FROM players WHERE status='Approved'")
        rows = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM players WHERE status='Approved'")
        total_count = cursor.fetchone()[0]
        conn.close()
        
        if not rows:
            bot.reply_to(message, "📭 अभी तक कोई भी अप्रूव्ड खिलाड़ी नहीं है।")
            return
            
        response = f"🏆 *Approved Players ({total_count}/{MAX_PLAYERS}):*\n\n"
        for index, row in enumerate(rows, start=1):
            response += f"{index}. *{row[0]}* ({row[2]}) | UID: {row[1]} | UTR: {row[3]}\n"

    
