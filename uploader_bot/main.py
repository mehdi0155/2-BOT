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
SETTINGS_FILE = "settings.json"

# --- Database Functions ---
def save_to_db(link_id, file_unique_id):
    db = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    db[link_id] = file_unique_id
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"checker_required_channels": [], "uploader_required_channels": []}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def is_admin(user_id):
    return user_id in ADMINS

def generate_link_id():
    while True:
        link_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if link_id not in load_db():
            return link_id

def is_user_member(user_id):
    channels = load_settings().get("uploader_required_channels", [])
    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

# --- Message Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("آپلود ویدیو", "مدیریت عضویت")
        bot.send_message(message.chat.id, "خوش آمدید.", reply_markup=markup)
    else:
        args = message.text.split()
        if len(args) > 1:
            link_id = args[1]
            if is_user_member(message.from_user.id):
                send_video_to_user(message.chat.id, link_id)
            else:
                send_uploader_subscription_prompt(message.chat.id, link_id)
        else:
            bot.send_message(message.chat.id, "لینک معتبر نیست یا عضویت ندارید.")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "آپلود ویدیو")
def ask_video(message):
    msg = bot.send_message(message.chat.id, "ویدیو را ارسال کنید.")
    bot.register_next_step_handler(msg, receive_video)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "مدیریت عضویت")
def manage_membership(message):
    settings = load_settings()
    txt = f"کانال‌های فعلی عضویت:
آپلودر: {settings.get('uploader_required_channels', [])}
چکر: {settings.get('checker_required_channels', [])}"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("تنظیم عضویت آپلودر", "تنظیم عضویت چکر", "بازگشت")
    bot.send_message(message.chat.id, txt, reply_markup=markup)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "تنظیم عضویت آپلودر")
def set_uploader_channels(message):
    msg = bot.send_message(message.chat.id, "آیدی کانال‌ها برای آپلودر را با فاصله بفرست:")
    bot.register_next_step_handler(msg, save_uploader_channels)

def save_uploader_channels(message):
    ids = message.text.split()
    settings = load_settings()
    settings['uploader_required_channels'] = ids
    save_settings(settings)
    bot.send_message(message.chat.id, "ذخیره شد.")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "تنظیم عضویت چکر")
def set_checker_channels(message):
    msg = bot.send_message(message.chat.id, "آیدی کانال‌ها برای چکر را با فاصله بفرست:")
    bot.register_next_step_handler(msg, save_checker_channels)

def save_checker_channels(message):
    ids = message.text.split()
    settings = load_settings()
    settings['checker_required_channels'] = ids
    save_settings(settings)
    bot.send_message(message.chat.id, "ذخیره شد.")

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "بازگشت")
def back_to_panel(message):
    start(message)

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

def receive_cover(message):
    if message.photo:
        file_id = message.photo[-1].file_id
        user_data[message.from_user.id]['cover'] = file_id
        msg = bot.send_message(message.chat.id, "کپشن فایل را بفرست:")
        bot.register_next_step_handler(msg, receive_caption)
    else:
        bot.send_message(message.chat.id, "فقط عکس بفرست یا روی 'ندارم' کلیک کن.")

@bot.callback_query_handler(func=lambda call: call.data == "no_cover")
def no_cover(call):
    bot.answer_callback_query(call.id)
    user_data[call.from_user.id]['cover'] = None
    msg = bot.send_message(call.message.chat.id, "کپشن فایل را بفرست:")
    bot.register_next_step_handler(msg, receive_caption)

def receive_caption(message):
    data = user_data.get(message.from_user.id)
    if data:
        data['caption'] = message.text
        preview_post(message)

def preview_post(message):
    data = user_data.get(message.from_user.id)
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
    else:
        user_data.pop(user_id, None)
        pending_posts.pop(user_id, None)
        bot.send_message(call.message.chat.id, "ارسال لغو شد.")

# --- Sending Video to User with Timer ---
def send_video_to_user(chat_id, link_id):
    db = load_db()
    file_unique_id = db.get(link_id)
    if not file_unique_id:
        return bot.send_message(chat_id, "فایل یافت نشد.")

    msg1 = bot.send_message(chat_id, "این ویدیو تا ۱۵ ثانیه دیگر پاک می‌شود.")
    msg2 = bot.send_video(chat_id, file_unique_id, caption="@hottof | تُفِ داغ")

    def delete_messages():
        time.sleep(15)
        try:
            bot.delete_message(chat_id, msg1.message_id)
            bot.delete_message(chat_id, msg2.message_id)
        except:
            pass

    threading.Thread(target=delete_messages).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("checkupload_"))
def check_uploader_subscription(call):
    link_id = call.data.split("_", 1)[1]
    if is_user_member(call.from_user.id):
        send_video_to_user(call.message.chat.id, link_id)
    else:
        send_uploader_subscription_prompt(call.message.chat.id, link_id)

def send_uploader_subscription_prompt(chat_id, link_id):
    channels = load_settings().get("uploader_required_channels", [])
    markup = types.InlineKeyboardMarkup()
    for ch in channels:
        markup.add(types.InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch[1:]}"))
    markup.add(types.InlineKeyboardButton("بررسی عضویت", callback_data=f"checkupload_{link_id}"))
    bot.send_message(chat_id, "برای دریافت فایل باید عضو کانال‌ها شوید:", reply_markup=markup)

# --- Webhook Setup ---
def setup_routes(server):
    @server.route('/uploader/' + TOKEN, methods=['POST'])
    def get_uploader_message():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "!", 200
