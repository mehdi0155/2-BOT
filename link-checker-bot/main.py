import telebot
from telebot import types
import os
import threading
import time
import flask

TOKEN = "7679592392:AAFK0BHxrvxH_I23UGveiVGzc_-M10lPUOA"
ADMIN_BOT_USERNAME = "UpTofBot"
REQUIRED_CHANNELS = ["@hottof"]

bot = telebot.TeleBot(TOKEN)

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
            send_temp_link(message, link_id)
        else:
            markup = types.InlineKeyboardMarkup()
            for ch in REQUIRED_CHANNELS:
                markup.add(types.InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch[1:]}"))
            markup.add(types.InlineKeyboardButton("بررسی عضویت", callback_data=f"check_{link_id}"))
            bot.send_message(message.chat.id, "برای دریافت فایل باید عضو کانال شوید.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_membership(call):
    link_id = call.data.split("_", 1)[1]
    if is_member(call.from_user.id):
        send_temp_link(call.message, link_id)
    else:
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("بررسی عضویت", callback_data=f"check_{link_id}"))
        bot.edit_message_text("هنوز عضو نشده‌اید. لطفاً عضو شوید و دوباره بررسی کنید.", call.message.chat.id, call.message.message_id, reply_markup=markup)

def send_temp_link(message, link_id):
    msg = bot.send_message(message.chat.id, f"دریافت فایل:\nhttps://t.me/{ADMIN_BOT_USERNAME}?start={link_id}")
    threading.Thread(target=delete_after, args=(msg.chat.id, msg.message_id)).start()

def delete_after(chat_id, message_id):
    time.sleep(15)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

server = flask.Flask(__name__)

@server.route('/' + TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))])
    return "!", 200

@server.route("/")
def webhook():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        bot.remove_webhook()
        bot.set_webhook(url=url + "/" + TOKEN)
    return "Webhook set!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
