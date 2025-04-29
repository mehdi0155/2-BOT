import telebot
from telebot import types
import random
import string
import flask
import os

TOKEN = "7920918778:AAFF4MDkYX4qBpuyXyBgcuCssLa6vjmTN1c"
CHANNEL = "@hottof"
ADMINS = [6378124502, 6387942633, 5459406429, 7189616405]
CHECKER_BOT_USERNAME = "TofLinkBot"  # <<< یوزرنیم ربات چکر اینجا تعریف شده

bot = telebot.TeleBot(TOKEN)
user_data = {}
pending_posts = {}

def is_admin(user_id):
    return user_id in ADMINS

def generate_link_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

@bot.message_handler(commands=['start'])
def start(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("آپلود ویدیو"))
        bot.send_message(message.chat.id, "خوش آمدید.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "دسترسی ندارید.")

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == "آپلود ویدیو")
def ask_video(message):
    msg = bot.send_message(message.chat.id, "ویدیو را ارسال کنید.")
    bot.register_next_step_handler(msg, receive_video)

def receive_video(message):
    if not message.video:
        bot.send_message(message.chat.id, "فقط ویدیو بفرستید.")
        return
    file_id = message.video.file_id
    user_data[message.from_user.id] = {'file_id': file_id}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("ندارم", callback_data="no_cover"))
    bot.send_message(message.chat.id, "کاور را ارسال کنید یا روی 'ندارم' کلیک کنید.", reply_markup=markup)
    bot.register_next_step_handler(message, receive_cover)

@bot.callback_query_handler(func=lambda call: call.data == "no_cover")
def no_cover(call):
    bot.answer_callback_query(call.id)
    data = user_data.get(call.from_user.id)
    if data:
        data['cover'] = None
        msg = bot.send_message(call.message.chat.id, "کپشن و توضیح فایل را بفرستید.")
        bot.register_next_step_handler(msg, receive_caption)

def receive_cover(message):
    if message.photo:
        file_id = message.photo[-1].file_id
        data = user_data.get(message.from_user.id)
        if data:
            data['cover'] = file_id
            msg = bot.send_message(message.chat.id, "کپشن و توضیح فایل را بفرستید.")
            bot.register_next_step_handler(msg, receive_caption)
    else:
        bot.send_message(message.chat.id, "فقط عکس بفرست یا روی 'ندارم' کلیک کن.")

def receive_caption(message):
    data = user_data.get(message.from_user.id)
    if data:
        data['caption'] = message.text
        preview_post(message)

def preview_post(message):
    data = user_data.get(message.from_user.id)
    if data:
        link_id = generate_link_id()
        pending_posts[message.from_user.id] = link_id
        # لینک باید به ربات چکر باشد
        link = f"https://t.me/{CHECKER_BOT_USERNAME}?start={link_id}"
        caption = f"{data['caption']}\n\n@hottof | تُفِ داغ"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("مشاهده فایل", url=link))
        if data['cover']:
            bot.send_photo(message.chat.id, data['cover'], caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)
        confirm_markup = types.InlineKeyboardMarkup()
        confirm_markup.add(
            types.InlineKeyboardButton("ارسال در کانال", callback_data="send_now"),
            types.InlineKeyboardButton("منصرف شدم", callback_data="cancel_post")
        )
        bot.send_message(message.chat.id, "آیا این پست ارسال شود؟", reply_markup=confirm_markup)

@bot.callback_query_handler(func=lambda call: call.data in ["send_now", "cancel_post"])
def process_confirmation(call):
    bot.answer_callback_query(call.id)
    if call.data == "send_now":
        data = user_data.get(call.from_user.id)
        link_id = pending_posts.get(call.from_user.id)
        if data and link_id:
            link = f"https://t.me/{CHECKER_BOT_USERNAME}?start={link_id}"
            caption = f"{data['caption']}\n\n@hottof | تُفِ داغ"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("مشاهده فایل", url=link))
            if data['cover']:
                bot.send_photo(CHANNEL, data['cover'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(CHANNEL, caption, reply_markup=markup)
            bot.send_message(call.message.chat.id, "پست با موفقیت ارسال شد.")
            del user_data[call.from_user.id]
            del pending_posts[call.from_user.id]
    elif call.data == "cancel_post":
        user_data.pop(call.from_user.id, None)
        pending_posts.pop(call.from_user.id, None)
        bot.send_message(call.message.chat.id, "ارسال لغو شد.")

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
