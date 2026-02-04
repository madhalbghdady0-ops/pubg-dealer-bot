import telebot
import sqlite3
from telebot import types

# --- البيانات الأساسية ---
API_TOKEN = '8246752283:AAHjwR85I18Ac6MgZcJV5zPCX09hsI8XcOY'
bot = telebot.TeleBot(API_TOKEN)

OWNER_ID = 5032066102 
SECONDARY_OWNER = 6373995909 

# --- قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS replies (keyword TEXT PRIMARY KEY, type TEXT, file_id TEXT, text TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS staff (user_id INTEGER PRIMARY KEY, rank INTEGER)''')
    conn.commit()
    return conn

db_conn = init_db()

def get_rank(user_id):
    if user_id in [OWNER_ID, SECONDARY_OWNER]: return 3 
    cursor = db_conn.cursor()
    cursor.execute("SELECT rank FROM staff WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else 0

user_state = {}

# --- 1. رسالة الترحيب ---
@bot.message_handler(commands=['start'])
def welcome(m):
    welcome_text = (
        "البوت خاص بشاتات ببجي ديلر فقط غير مسئولين عن اي شات اخر "
        "و ياريت تنزل اليوزر و تتأكد من اليوزر و الكاش قبل التحويل لأي شخص ♡"
    )
    bot.reply_to(m, welcome_text)

# --- 2. أوامر العرض (الأولوية) ---
@bot.message_handler(func=lambda m: m.text == "الردود")
def list_replies(m):
    if get_rank(m.from_user.id) < 1: return
    cursor = db_conn.cursor()
    cursor.execute("SELECT keyword FROM replies")
    rows = cursor.fetchall()
    if not rows:
        bot.reply_to(m, "⇜ مفيش ردود مضافة حالياً.")
    else:
        text = "⇜ الردود المضافة في البوت:\n\n"
        for row in rows: text += f"• {row[0]}\n"
        bot.reply_to(m, text)

# --- 3. أوامر الإدارة والعقوبات ---
@bot.message_handler(func=lambda m: m.text and (m.text.startswith("رفع ادمن") or m.text.startswith("رفع مدير")))
def promote(m):
    if get_rank(m.from_user.id) < 3: return
    try:
        parts = m.text.split()
        target_id = int(parts[2])
        rank = 2 if "مدير" in m.text else 1
        db_conn.cursor().execute("INSERT OR REPLACE INTO staff VALUES (?, ?)", (target_id, rank))
        db_conn.commit()
        bot.reply_to(m, "⇜ تم الرفع بنجاح ✅")
    except: pass

@bot.message_handler(func=lambda m: m.text in ['تقيد', 'حظر', 'كتم', 'طرد'] and m.reply_to_message)
def punish(m):
    if get_rank(m.from_user.id) < 1: return
    uid = m.reply_to_message.from_user.id
    if m.text in ['حظر', 'طرد']: bot.kick_chat_member(m.chat.id, uid)
    else: bot.restrict_chat_member(m.chat.id, uid, can_send_messages=False)
    bot.reply_to(m, f"⇜ ابشر، تم {m.text} العضو")

@bot.message_handler(func=lambda m: m.text == "رفع قيود" and m.reply_to_message)
def unpunish(m):
    if get_rank(m.from_user.id) < 1: return
    uid = m.reply_to_message.from_user.id
    bot.unban_chat_member(m.chat.id, uid, only_if_banned=True)
    bot.restrict_chat_member(m.chat.id, uid, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)
    bot.reply_to(m, "⇜ تم رفع القيود ✅")

@bot.message_handler(func=lambda m: m.text in ["قفل شات", "فتح شات"])
def chat_control(m):
    if get_rank(m.from_user.id) < 2: return
    can = "فتح" in m.text
    bot.set_chat_permissions(m.chat.id, types.ChatPermissions(can_send_messages=can, can_send_media_messages=can))
    bot.reply_to(m, f"⇜ تم {m.text}")

# --- 4. نظام الردود ---
@bot.message_handler(func=lambda m: m.text == "اضف رد")
def add_reply(m):
    if get_rank(m.from_user.id) < 1: return
    user_state[m.from_user.id] = {'step': 'waiting_keyword'}
    bot.reply_to(m, "⇜ ارسل الكلمة اللي تبيها")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get('step') == 'waiting_keyword')
def step2(m):
    user_state[m.from_user.id] = {'step': 'waiting_response', 'keyword': m.text}
    bot.reply_to(m, "⇜ ارسل جواب الرد (نص، صورة، فيديو...)")

@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'audio', 'animation'], 
                     func=lambda m: user_state.get(m.from_user.id, {}).get('step') == 'waiting_response')
def step3(m):
    state = user_state[m.from_user.id]
    kw = state['keyword']
    res_type = m.content_type
    fid = None
    txt = m.caption if m.caption else m.text
    if res_type == 'photo': fid = m.photo[-1].file_id
    elif res_type == 'video': fid = m.video.file_id
    elif res_type in ['voice', 'audio', 'animation']: fid = getattr(m, res_type).file_id
    
    db_conn.cursor().execute("INSERT OR REPLACE INTO replies VALUES (?, ?, ?, ?)", (kw, res_type, fid, txt))
    db_conn.commit()
    del user_state[m.from_user.id]
    bot.reply_to(m, f"✅ تم حفظ الرد: {kw}")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("مسح رد "))
def del_reply(m):
    if get_rank(m.from_user.id) < 1: return
    kw = m.text.replace("مسح رد ", "").strip()
    cursor = db_conn.cursor()
    cursor.execute("SELECT keyword FROM replies WHERE keyword = ?", (kw,))
    if not cursor.fetchone():
        bot.reply_to(m, "⇜ هذا الرد مو مضاف في قائمة الردود")
    else:
        cursor.execute("DELETE FROM replies WHERE keyword = ?", (kw,))
        db_conn.commit()
        bot.reply_to(m, f"⇜ تم مسح الرد ({kw})")

# --- 5. الرد التلقائي ---
@bot.message_handler(func=lambda m: True)
def auto_reply(m):
    if not m.text: return
    cursor = db_conn.cursor()
    cursor.execute("SELECT type, file_id, text FROM replies WHERE keyword = ?", (m.text.strip(),))
    res = cursor.fetchone()
    if res:
        rtype, fid, rtext = res
        if rtype == 'text': bot.reply_to(m, rtext)
        else: getattr(bot, f"send_{rtype}")(m.chat.id, fid, caption=rtext, reply_to_message_id=m.message_id)

# التعديل الخاص بـ Koyeb للعمل الدائم
print("🚀 بوت ببجي ديلر فخدمتكم")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
  
