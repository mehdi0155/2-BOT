import flask
import telebot, json, os, random, string, threading, time
from telebot import types

TOKEN = "7920918778:AAFF4MDkYX4qBpuyXyBgcuCssLa6vjmTN1c"
CHANNEL = "@hottof"
ADMINS = [6387942633, 5459406429, 7189616405]  # آیدی عددی ادمین‌ها
CHECKER_BOT_USERNAME = "TofLinkBot"

bot = telebot.TeleBot(TOKEN)
user_data, pending_posts = {}, {}
DB_FILE = "db.json"
SETTINGS_FILE = "settings.json"

def save_to_db(link_id, file_id):
    db = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            db = json.load(f)
    db[link_id] = file_id
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def generate_link_id():
    while True:
        link_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if not os.path.exists(DB_FILE): return link_id
        with open(DB_FILE) as f: db = json.load(f)
        if link_id not in db: return link_id

def is_admin(uid): return uid in ADMINS

def load_settings():
    if not os.path.exists(SETTINGS_FILE): return {"uploader_channels": [], "checker_channels": []}
    with open(SETTINGS_FILE) as f: return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)

@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    uid = message.from_user.id

    if len(args) > 1:
        # اگر لینک بود (start با آرگومان)
        link_id = args[1]
        if os.path.exists(DB_FILE):
            with open(DB_FILE) as f:
                db = json.load(f)
            file_id = db.get(link_id)
            if file_id:
                warning = bot.send_message(message.chat.id, "توجه: این محتوا تا ۱۵ ثانیه دیگر پاک می‌شود.")
                sent = bot.send_video(message.chat.id, file_id)
                threading.Thread(target=delete_after, args=(message.chat.id, sent.message_id, warning.message_id)).start()
        return

    # اگر بدون آرگومان بود و ادمین بود، پنل را نشان بده
    if is_admin(uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📂 آپلود ویدیو", "📣 عضویت اجباری")
        bot.send_message(message.chat.id, "به پنل خوش آمدید.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "لینک دریافت شده معتبر نیست.")

@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📂 آپلود ویدیو", "📣 عضویت اجباری")
        bot.send_message(message.chat.id, "پنل مدیریت", reply_markup=markup)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📂 آپلود ویدیو")
def ask_video(message):
    msg = bot.send_message(message.chat.id, "لطفاً ویدیو را ارسال کنید.")
    bot.register_next_step_handler(msg, receive_video)

def receive_video(message):
    if not message.video:
        bot.send_message(message.chat.id, "فقط ویدیو ارسال کنید.")
        return
    user_data[message.from_user.id] = {'file_id': message.video.file_id}
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
        msg = bot.send_message(call.message.chat.id, "کپشن را وارد کنید.")
        bot.register_next_step_handler(msg, receive_caption)

def receive_cover(message):
    if message.photo:
        data = user_data.get(message.from_user.id)
        if data:
            data['cover'] = message.photo[-1].file_id
            msg = bot.send_message(message.chat.id, "کپشن را وارد کنید.")
            bot.register_next_step_handler(msg, receive_caption)
    else:
        bot.send_message(message.chat.id, "فقط عکس ارسال کنید یا روی 'ندارم' بزنید.")

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
        save_to_db(link_id, data['file_id'])
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
        bot.send_message(message.chat.id, "آیا پست ارسال شود؟", reply_markup=confirm_markup)

@bot.callback_query_handler(func=lambda call: call.data in ["send_now", "cancel_post"])
def handle_send(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    data = user_data.get(uid)
    link_id = pending_posts.get(uid)
    if call.data == "send_now" and data and link_id:
        link = f"https://t.me/{CHECKER_BOT_USERNAME}?start={link_id}"
        caption = f"{data['caption']}\n\n@hottof | تُفِ داغ"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("مشاهده فایل", url=link))
        if data.get('cover'):
            bot.send_photo(CHANNEL, data['cover'], caption=caption, reply_markup=markup)
        else:
            bot.send_message(CHANNEL, caption, reply_markup=markup)
        bot.send_message(call.message.chat.id, "ارسال شد.")
    else:
        bot.send_message(call.message.chat.id, "لغو شد.")
    user_data.pop(uid, None)
    pending_posts.pop(uid, None)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📣 عضویت اجباری")
def manage_subscription(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("ربات آپلودر", callback_data="choose_uploader"),
        types.InlineKeyboardButton("ربات چکر", callback_data="choose_checker")
    )
    bot.send_message(message.chat.id, "کدام ربات؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["choose_uploader", "choose_checker"])
def show_channels(call):
    bot.answer_callback_query(call.id)
    settings = load_settings()
    target = "uploader_channels" if call.data == "choose_uploader" else "checker_channels"
    channels = settings[target]
    text = "\n".join(channels) if channels else "❌ هیچ کانالی تنظیم نشده."
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("➕ افزودن کانال", callback_data=f"add_{target}"),
        types.InlineKeyboardButton("➖ حذف کانال", callback_data=f"remove_{target}")
    )
    bot.send_message(call.message.chat.id, f"کانال‌های فعلی:\n{text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def ask_add_channel(call):
    bot.answer_callback_query(call.id)
    target = call.data.replace("add_", "")
    msg = bot.send_message(call.message.chat.id, "آیدی کانال را با @ ارسال کنید:")
    bot.register_next_step_handler(msg, lambda m: add_channel(m, target))

def add_channel(message, target):
    if not message.text.startswith("@"): return bot.send_message(message.chat.id, "فرمت اشتباه است.")
    settings = load_settings()
    if message.text not in settings[target]:
        settings[target].append(message.text)
        save_settings(settings)
        bot.send_message(message.chat.id, "کانال افزوده شد.")
    else:
        bot.send_message(message.chat.id, "این کانال قبلاً اضافه شده است.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_"))
def ask_remove_channel(call):
    bot.answer_callback_query(call.id)
    target = call.data.replace("remove_", "")
    settings = load_settings()
    channels = settings[target]
    if not channels:
        bot.send_message(call.message.chat.id, "هیچ کانالی برای حذف وجود ندارد.")
        return
    markup = types.InlineKeyboardMarkup()
    for ch in channels:
        markup.add(types.InlineKeyboardButton(ch, callback_data=f"rm_{target}_{ch}"))
    bot.send_message(call.message.chat.id, "یکی را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rm_"))
def remove_channel(call):
    bot.answer_callback_query(call.id)
    parts = call.data.split("_")
    target = "_".join(parts[1:-1])
    channel = parts[-1]
    settings = load_settings()
    if channel in settings[target]:
        settings[target].remove(channel)
        save_settings(settings)
        bot.send_message(call.message.chat.id, "کانال حذف شد.")
    else:
        bot.send_message(call.message.chat.id, "کانال پیدا نشد.")

def delete_after(chat_id, msg_id, warn_id):
    time.sleep(15)
    try:
        bot.delete_message(chat_id, msg_id)
        bot.delete_message(chat_id, warn_id)
    except: pass

def setup_routes(server):
    @server.route('/uploader/' + TOKEN, methods=['POST'])
    def handle_uploader():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "OK", 200
