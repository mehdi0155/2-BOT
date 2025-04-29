import telebot
from telebot import types
import random
import string
import os
import json
import threading
import time

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


@bot.message_handler(commands=['start', 'panel'])
def start(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("آپلود ویدیو", "مدیریت عضویت")
        bot.send_message(message.chat.id, "به پنل مدیریت خوش آمدید.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "برای دریافت فایل، لینک را از کانال انتخاب کنید.")


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "آپلود ویدیو")
def ask_video(message):
    msg = bot.send_message(message.chat.id, "ویدیو را ارسال کنید.")
    bot.register_next_step_handler(msg, receive_video)


def receive_video(message):
    if not message.video:
        bot.send_message(message.chat.id, "فقط ویدیو بفرستید.")
        return
    user_data[message.from_user.id] = {'file_unique_id': message.video.file_unique_id}
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
                msg = bot.send_photo(CHANNEL, data['cover'], caption=caption, reply_markup=markup)
            else:
                msg = bot.send_message(CHANNEL, caption, reply_markup=markup)

            bot.send_message(call.message.chat.id, "پست با موفقیت ارسال شد.")
            user_data.pop(user_id, None)
            pending_posts.pop(user_id, None)

    elif call.data == "cancel_post":
        user_data.pop(user_id, None)
        pending_posts.pop(user_id, None)
        bot.send_message(call.message.chat.id, "ارسال لغو شد.")


@bot.message_handler(commands=['start'])
def handle_user_start(message):
    args = message.text.split()
    if len(args) > 1:
        link_id = args[1]
        file_unique_id = load_file_id(link_id)
        if file_unique_id:
            msg = bot.send_message(message.chat.id, "این ویدیو تا ۱۵ ثانیه دیگر حذف خواهد شد.")
            vid_msg = bot.send_video(message.chat.id, file_unique_id, caption="@hottof | تُفِ داغ")

            threading.Thread(target=delete_after_delay, args=(message.chat.id, vid_msg.message_id, msg.message_id)).start()


def load_file_id(link_id):
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "r") as f:
        db = json.load(f)
    return db.get(link_id)


def delete_after_delay(chat_id, video_msg_id, warn_msg_id):
    time.sleep(15)
    try:
        bot.delete_message(chat_id, video_msg_id)
        bot.delete_message(chat_id, warn_msg_id)
    except:
        pass


def setup_routes(server):
    @server.route('/uploader/' + TOKEN, methods=['POST'])
    def get_uploader_message():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "!", 200

SETTINGS_FILE = "settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"checker_required_channels": [], "uploader_required_channels": []}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "مدیریت عضویت")
def manage_membership(message):
    settings = load_settings()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("افزودن کانال به چکر", "حذف کانال از چکر")
    markup.add("افزودن کانال به آپلودر", "حذف کانال از آپلودر")
    markup.add("دیدن لیست عضویت‌ها", "بازگشت")
    bot.send_message(message.chat.id, "مدیریت عضویت را انتخاب کنید:", reply_markup=markup)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "افزودن کانال به چکر")
def add_checker_channel(message):
    msg = bot.send_message(message.chat.id, "آیدی کانال (مثلاً @mychannel) را بفرست:")
    bot.register_next_step_handler(msg, process_add_checker)

def process_add_checker(message):
    settings = load_settings()
    ch = message.text.strip()
    if ch.startswith("@"):
        if ch not in settings["checker_required_channels"]:
            settings["checker_required_channels"].append(ch)
            save_settings(settings)
            bot.send_message(message.chat.id, "کانال با موفقیت به چکر اضافه شد.")
        else:
            bot.send_message(message.chat.id, "این کانال قبلاً اضافه شده.")
    else:
        bot.send_message(message.chat.id, "آیدی باید با @ شروع شود.")
    manage_membership(message)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "افزودن کانال به آپلودر")
def add_uploader_channel(message):
    msg = bot.send_message(message.chat.id, "آیدی کانال (مثلاً @mychannel) را بفرست:")
    bot.register_next_step_handler(msg, process_add_uploader)

def process_add_uploader(message):
    settings = load_settings()
    ch = message.text.strip()
    if ch.startswith("@"):
        if ch not in settings["uploader_required_channels"]:
            settings["uploader_required_channels"].append(ch)
            save_settings(settings)
            bot.send_message(message.chat.id, "کانال با موفقیت به آپلودر اضافه شد.")
        else:
            bot.send_message(message.chat.id, "این کانال قبلاً اضافه شده.")
    else:
        bot.send_message(message.chat.id, "آیدی باید با @ شروع شود.")
    manage_membership(message)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "حذف کانال از چکر")
def remove_checker_channel(message):
    settings = load_settings()
    if not settings["checker_required_channels"]:
        bot.send_message(message.chat.id, "هیچ کانالی وجود ندارد.")
        return manage_membership(message)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for ch in settings["checker_required_channels"]:
        markup.add(ch)
    markup.add("بازگشت")
    msg = bot.send_message(message.chat.id, "یکی از کانال‌ها را برای حذف انتخاب کن:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_remove_checker)

def process_remove_checker(message):
    settings = load_settings()
    ch = message.text.strip()
    if ch in settings["checker_required_channels"]:
        settings["checker_required_channels"].remove(ch)
        save_settings(settings)
        bot.send_message(message.chat.id, "کانال حذف شد.")
    else:
        bot.send_message(message.chat.id, "کانال پیدا نشد.")
    manage_membership(message)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "حذف کانال از آپلودر")
def remove_uploader_channel(message):
    settings = load_settings()
    if not settings["uploader_required_channels"]:
        bot.send_message(message.chat.id, "هیچ کانالی وجود ندارد.")
        return manage_membership(message)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for ch in settings["uploader_required_channels"]:
        markup.add(ch)
    markup.add("بازگشت")
    msg = bot.send_message(message.chat.id, "یکی از کانال‌ها را برای حذف انتخاب کن:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_remove_uploader)

def process_remove_uploader(message):
    settings = load_settings()
    ch = message.text.strip()
    if ch in settings["uploader_required_channels"]:
        settings["uploader_required_channels"].remove(ch)
        save_settings(settings)
        bot.send_message(message.chat.id, "کانال حذف شد.")
    else:
        bot.send_message(message.chat.id, "کانال پیدا نشد.")
    manage_membership(message)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "دیدن لیست عضویت‌ها")
def show_membership_lists(message):
    settings = load_settings()
    checker = "\n".join(settings["checker_required_channels"]) or "هیچی"
    uploader = "\n".join(settings["uploader_required_channels"]) or "هیچی"
    bot.send_message(message.chat.id, f"چکر:\n{checker}\n\nآپلودر:\n{uploader}")
    manage_membership(message)
