import telebot, json, os, flask, time, threading

TOKEN = "7679592392:AAFK0BHxrvxH_I23UGveiVGzc_-M10lPUOA"
bot = telebot.TeleBot(TOKEN)

DB_FILE = "db.json"
SETTINGS_FILE = "settings.json"

def load_db():
    return json.load(open(DB_FILE)) if os.path.exists(DB_FILE) else {}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {"checker_channels": []}

def get_non_member_channels(user_id):
    settings = load_settings()
    non_members = []
    for ch in settings.get("checker_channels", []):
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                non_members.append(ch)
        except:
            non_members.append(ch)
    return non_members

@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    if len(args) > 1:
        link_id = args[1]
        non_members = get_non_member_channels(message.from_user.id)
        if not non_members:
            send_download_link(message.chat.id, link_id)
        else:
            send_sub_prompt(message.chat.id, link_id, non_members)
    else:
        bot.send_message(message.chat.id, "لینک نامعتبر است.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_again(call):
    link_id = call.data.split("_", 1)[1]
    non_members = get_non_member_channels(call.from_user.id)
    if not non_members:
        send_download_link(call.message.chat.id, link_id)
    else:
        send_sub_prompt(call.message.chat.id, link_id, non_members)

def send_download_link(chat_id, link_id):
    warn = bot.send_message(chat_id, "توجه: این پیام تا ۱۵ ثانیه دیگر حذف می‌شود.")
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("مشاهده فایل", url=f"https://t.me/UpTofBot?start={link_id}"))
    msg = bot.send_message(chat_id, "روی دکمه زیر بزن تا فایل را بگیری:", reply_markup=markup)
    threading.Thread(target=delete_after, args=(chat_id, msg.message_id, warn.message_id)).start()

def send_sub_prompt(chat_id, link_id, channels):
    markup = telebot.types.InlineKeyboardMarkup()
    for ch in channels:
        markup.add(telebot.types.InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch[1:]}"))
    markup.add(telebot.types.InlineKeyboardButton("بررسی عضویت", callback_data=f"check_{link_id}"))
    bot.send_message(chat_id, "برای دریافت فایل، ابتدا در کانال(های) زیر عضو شو:", reply_markup=markup)

def delete_after(chat_id, msg_id, warn_id):
    time.sleep(15)
    try:
        bot.delete_message(chat_id, msg_id)
        bot.delete_message(chat_id, warn_id)
    except: pass

def setup_routes(server):
    @server.route('/checker/' + TOKEN, methods=['POST'])
    def handle_checker():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "OK", 200
