import telebot
from telebot import types
import random
import string
import os
import json

TOKEN = "7920918778:AAFF4MDkYX4qBpuyXyBgcuCssLa6vjmTN1c"
CHANNEL = "@hottof"
ADMINS = [6387942633, 5459406429]
CHECKER_BOT_USERNAME = "TofLinkBot"

bot = telebot.TeleBot(TOKEN)
user_data = {}
pending_posts = {}

DB_FILE = "db.json"

def save_to_db(link_id, file_unique_id):
    db = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    db[link_id] = file_unique_id
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def is_admin(user_id):
    return user_id in ADMINS

def generate_link_id():
    while True:
        link_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if not os.path.exists(DB_FILE):
            return link_id
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        if link_id not in db:
            return link_id

@bot.message_handler(commands=['start'])
def start(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("آپلود ویدیو"))
        bot.send_message(message.chat.id, "خوش آمدید.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "دسترسی ندارید.")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "آپلود ویدیو")
def ask_video(message):
    msg = bot.send_message(message.chat.id, "ویدیو را ارسال کنید.")
    bot.register_next_step_handler(msg, receive_video)

def receive_video(message):
    if not message.video:
        bot.send_message(message.chat.id, "فقط ویدیو بفرستید.")
        return
    user_data[message.from_user.id] = {
        'file_unique_id': message.video.file_unique_id
    }
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
        save_to_db(link_id, data['file_unique_id'])

        link = f"https://t.me/{CHECKER_BOT_USERNAME}?start={link_id}"
        caption = f"{data['caption']}\n\n@hottof | تُفِ داغ"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("مشاهده فایل", url=link))

        if data.get('cover'):
            bot.send_photo(message.chat.id, data['cover'], caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)

        confirm_markup = types.InlineKeyboardMarkup()
        confirm_markup.add(
            types.InlineKeyboardButton("ارسال در کانال", callback_data="send_now"),
            types.InlineKeyboardButton("لغو ارسال", callback_data="cancel_post")
        )
        bot.send_message(message.chat.id, "آیا این پست ارسال شود؟", reply_markup=confirm_markup)

@bot.callback_query_handler(func=lambda call: call.data in ["send_now", "cancel_post"])
def process_confirmation(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id

    if call.data == "send_now":
        data = user_data.get(user_id)
        link_id = pending_posts.get(user_id)
        if data and link_id:
            link = f"https://t.me/{CHECKER_BOT_USERNAME}?start={link_id}"
            caption = f"{data['caption']}\n\n@hottof | تُفِ داغ"

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("مشاهده فایل", url=link))

            if data.get('cover'):
                bot.send_photo(CHANNEL, data['cover'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(CHANNEL, caption, reply_markup=markup)

            bot.send_message(call.message.chat.id, "پست با موفقیت ارسال شد.")
            user_data.pop(user_id, None)
            pending_posts.pop(user_id, None)

    elif call.data == "cancel_post":
        user_data.pop(user_id, None)
        pending_posts.pop(user_id, None)
        bot.send_message(call.message.chat.id, "ارسال لغو شد.")

def setup_routes(server):
    import flask
    @server.route('/uploader/' + TOKEN, methods=['POST'])
    def get_uploader_message():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "!", 200
