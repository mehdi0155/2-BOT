import telebot
import os
import json
import flask

TOKEN = "7679592392:AAFK0BHxrvxH_I23UGveiVGzc_-M10lPUOA"
REQUIRED_CHANNELS = ["@hottof"]

bot = telebot.TeleBot(TOKEN)

DB_FILE = "db.json"  # مسیر اشتراکی دیتابیس فایل‌ها

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def is_member(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                return False
        except:
            return False
    return True

@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    if len(args) > 1:
        link_id = args[1]
        if is_member(message.from_user.id):
            send_file(message, link_id)
        else:
            send_subscription_prompt(message, link_id)
    else:
        bot.send_message(message.chat.id, "به ربات خوش آمدید.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_subscription(call):
    link_id = call.data.split("_", 1)[1]
    if is_member(call.from_user.id):
        send_file(call.message, link_id)
    else:
        send_subscription_prompt(call.message, link_id)

def send_subscription_prompt(message, link_id):
    markup = telebot.types.InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(telebot.types.InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch[1:]}"))
    markup.add(telebot.types.InlineKeyboardButton("بررسی عضویت", callback_data=f"check_{link_id}"))
    bot.send_message(message.chat.id, "برای دریافت فایل باید عضو کانال شوید.", reply_markup=markup)

def send_file(message, link_id):
    db = load_db()
    file_unique_id = db.get(link_id)
    if not file_unique_id:
        bot.send_message(message.chat.id, "متأسفم، این فایل در دسترس نیست یا حذف شده.")
        return
    # ارسال با unique_id
    bot.send_video(message.chat.id, file_unique_id, caption="@hottof | تُفِ داغ")

def setup_routes(server):
    @server.route('/checker/' + TOKEN, methods=['POST'])
    def get_checker_message():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "!", 200
