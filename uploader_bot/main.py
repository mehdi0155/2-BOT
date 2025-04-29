import flask
import telebot, json, os, random, string, threading, time, datetime
from telebot import types

TOKEN = "7920918778:AAFF4MDkYX4qBpuyXyBgcuCssLa6vjmTN1c"
CHANNEL = "@hottof"
ADMINS = [6387942633, 5459406429, 7189616405]
CHECKER_BOT_USERNAME = "TofLinkBot"

bot = telebot.TeleBot(TOKEN)
user_data, pending_posts = {}, {}
DB_FILE = "db.json"
SETTINGS_FILE = "settings.json"
UPLOADER_STATS = "uploader_stats.json"
CHECKER_STATS = "checker_stats.json"


def save_to_db(link_id, file_id):
    db = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            db = json.load(f)
    db[link_id] = file_id
    with open(DB_FILE, "w") as f:
        json.dump(db, f)


def get_non_member_channels(user_id):
    settings = load_settings()
    non_members = []
    for ch in settings.get("uploader_channels", []):
        try:
            member = bot.get_chat_member(ch["id"], user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                non_members.append(ch)
        except:
            non_members.append(ch)
    return non_members


def generate_link_id():
    while True:
        link_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        if not os.path.exists(DB_FILE):
            return link_id
        with open(DB_FILE) as f:
            db = json.load(f)
        if link_id not in db:
            return link_id


def is_admin(uid):
    return uid in ADMINS


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"uploader_channels": [], "checker_channels": []}
    with open(SETTINGS_FILE) as f:
        return json.load(f)


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def log_stats(file, user_id, channels):
    stats = {}
    if os.path.exists(file):
        with open(file) as f:
            stats = json.load(f)
    today = datetime.date.today().isoformat()
    if today not in stats:
        stats[today] = {"users": [], "channels": {}}
    if user_id not in stats[today]["users"]:
        stats[today]["users"].append(user_id)
    for ch in channels:
        stats[today]["channels"].setdefault(ch, 0)
        stats[today]["channels"][ch] += 1
    with open(file, "w") as f:
        json.dump(stats, f)
@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def recheck_subscription(call):
    non_members = get_non_member_channels(call.from_user.id)
    if non_members:
        markup = types.InlineKeyboardMarkup()
        for ch in non_members:
            username = ch["id"][1:] if ch["id"].startswith("@") else ch["id"]
            name = ch.get("name", username)
            markup.add(types.InlineKeyboardButton(f"عضویت در {name}", url=f"https://t.me/{username}"))
        markup.add(types.InlineKeyboardButton("بررسی عضویت", callback_data=call.data))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "هنوز عضو نشدی! لطفاً ابتدا عضو شو:", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "عضویت تأیید شد. دوباره لینک را بزن.")

@bot.message_handler(commands=['start'])
def handle_start(message):
    args = message.text.split()
    uid = message.from_user.id

    if len(args) > 1:
        link_id = args[1]
        non_members = get_non_member_channels(uid)
        if non_members:
            markup = types.InlineKeyboardMarkup()
            for ch in non_members:
                username = ch["id"][1:] if ch["id"].startswith("@") else ch["id"]
                name = ch.get("name", username)
                markup.add(types.InlineKeyboardButton(f"عضویت در {name}", url=f"https://t.me/{username}"))
            markup.add(types.InlineKeyboardButton("بررسی عضویت", callback_data=f"check_{link_id}"))
            bot.send_message(message.chat.id, "برای دریافت فایل، ابتدا در کانال(های) زیر عضو شو:", reply_markup=markup)
            return

        with open(DB_FILE) as f:
            db = json.load(f)
        file_id = db.get(link_id)
        if file_id:
            warning = bot.send_message(message.chat.id, "توجه: این محتوا تا ۱۵ ثانیه دیگر پاک می‌شود.")
            sent = bot.send_video(message.chat.id, file_id)
            threading.Thread(target=delete_after, args=(message.chat.id, sent.message_id, warning.message_id)).start()
        return

    if is_admin(uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📂 آپلود ویدیو", "📣 عضویت اجباری", "📊 آمار")
        bot.send_message(message.chat.id, "به پنل خوش آمدید.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "لینک دریافت شده معتبر نیست.")

@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📂 آپلود ویدیو", "📣 عضویت اجباری", "📊 آمار")
        bot.send_message(message.chat.id, "پنل مدیریت", reply_markup=markup)


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📂 آپلود ویدیو")
def ask_video(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("برگشت")
    msg = bot.send_message(message.chat.id, "لطفاً ویدیو را ارسال کنید.", reply_markup=markup)
    bot.register_next_step_handler(msg, receive_video)


def receive_video(message):
    if not message.video:
        bot.send_message(message.chat.id, "فقط ویدیو ارسال کنید.")
        return
    user_data[message.from_user.id] = {'file_id': message.video.file_id}
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("ندارم", callback_data="no_cover"))
    bot.send_message(message.chat.id, "کاور را ارسال کنید یا روی 'ندارم' بزنید.", reply_markup=markup)
    bot.register_next_step_handler(message, receive_cover)


@bot.callback_query_handler(func=lambda call: call.data == "no_cover")
def handle_no_cover(call):
    data = user_data.get(call.from_user.id)
    if data:
        bot.delete_message(call.message.chat.id, call.message.message_id)
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
        bot.send_message(message.chat.id, "فقط عکس ارسال کنید یا گزینه 'ندارم' را بزنید.")


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
        caption = f"{data['caption']}\n\n[مشاهده]({link})\n\n@hottof | تُفِ داغ"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("ارسال در کانال", "لغو ارسال")
        if data.get('cover'):
            bot.send_photo(message.chat.id, data['cover'], caption=caption, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, caption, parse_mode="Markdown")
        bot.send_message(message.chat.id, "آیا پست ارسال شود؟", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in ["ارسال در کانال", "لغو ارسال"])
def handle_send(message):
    uid = message.from_user.id
    data = user_data.get(uid)
    link_id = pending_posts.get(uid)
    if message.text == "ارسال در کانال" and data and link_id:
        link = f"https://t.me/{CHECKER_BOT_USERNAME}?start={link_id}"
        caption = f"{data['caption']}\n\n@hottof | تُفِ داغ"
        if data.get('cover'):
            bot.send_photo(CHANNEL, data['cover'], caption=caption)
        else:
            bot.send_message(CHANNEL, caption)
        bot.send_message(message.chat.id, "ارسال شد.")
    elif message.text == "لغو ارسال":
        bot.send_message(message.chat.id, "ارسال لغو شد. بازگشت به پنل اصلی.")
        admin_panel(message)
    user_data.pop(uid, None)
    pending_posts.pop(uid, None)


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📣 عضویت اجباری")
def manage_subscription(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ربات آپلودر", "ربات چکر")
    markup.add("برگشت")
    bot.send_message(message.chat.id, "کدام ربات؟", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in ["ربات آپلودر", "ربات چکر"])
def show_channels(message):
    target = "uploader_channels" if message.text == "ربات آپلودر" else "checker_channels"
    settings = load_settings()
    channels = settings[target]
    text = "\n".join(channels) if channels else "❌ هیچ کانالی تنظیم نشده."
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ افزودن کانال", "➖ حذف کانال")
    markup.add("برگشت")
    bot.send_message(message.chat.id, f"کانال‌های فعلی:\n{text}", reply_markup=markup)
    user_data[message.from_user.id] = {'target': target}


@bot.message_handler(func=lambda m: m.text == "➕ افزودن کانال")
def ask_add_channel(message):
    target = user_data.get(message.from_user.id, {}).get('target')
    if not target:
        return bot.send_message(message.chat.id, "ابتدا ربات را انتخاب کنید.")
    msg = bot.send_message(message.chat.id, "آیدی کانال را با @ ارسال کنید:")
    bot.register_next_step_handler(msg, lambda m: add_channel(m, target))


def add_channel(message, target):
    if not message.text.startswith("@"):
        return bot.send_message(message.chat.id, "فرمت اشتباه است.")
    settings = load_settings()
    channel_id = message.text
    for ch in settings[target]:
        if ch["id"] == channel_id:
            return bot.send_message(message.chat.id, "این کانال قبلاً اضافه شده است.")
    msg = bot.send_message(message.chat.id, "نام نمایشی برای این کانال را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: save_named_channel(m, target, channel_id))

def save_named_channel(message, target, channel_id):
    channel_name = message.text
    settings = load_settings()
    for ch in settings[target]:
        if ch["id"] == channel_id:
            return bot.send_message(message.chat.id, "این کانال قبلاً اضافه شده است.")
    settings[target].append({"id": channel_id, "name": channel_name})
    save_settings(settings)
    bot.send_message(message.chat.id, "کانال با موفقیت افزوده شد.")


@bot.message_handler(func=lambda m: m.text == "➖ حذف کانال")
def ask_remove_channel(message):
    target = user_data.get(message.from_user.id, {}).get('target')
    if not target:
        return bot.send_message(message.chat.id, "ابتدا ربات را انتخاب کنید.")
    settings = load_settings()
    channels = settings[target]
    if not channels:
        return bot.send_message(message.chat.id, "هیچ کانالی برای حذف وجود ندارد.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for ch in channels:
        markup.add(ch)
    markup.add("برگشت")
    bot.send_message(message.chat.id, "یکی را انتخاب کنید:", reply_markup=markup)
    user_data[message.from_user.id]['remove_mode'] = True


@bot.message_handler(func=lambda m: m.text == "برگشت")
def go_back(message):
    admin_panel(message)


@bot.message_handler(func=lambda m: user_data.get(m.from_user.id, {}).get('remove_mode'))
def remove_channel(message):
    target = user_data[message.from_user.id]['target']
    settings = load_settings()
    if message.text in settings[target]:
        settings[target].remove(message.text)
        save_settings(settings)
        bot.send_message(message.chat.id, "کانال حذف شد.")
    else:
        bot.send_message(message.chat.id, "کانال پیدا نشد.")
    user_data[message.from_user.id].pop('remove_mode', None)


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📊 آمار")
def show_stats(message):
    text = "📊 آمار کلی:\n"
    now = datetime.date.today()
    days = {
        "روز": now.isoformat(),
        "هفته": [(now - datetime.timedelta(days=i)).isoformat() for i in range(7)],
        "ماه": [(now - datetime.timedelta(days=i)).isoformat() for i in range(30)],
    }

    def count_users(file, period_days):
        total = 0
        if os.path.exists(file):
            with open(file) as f:
                data = json.load(f)
            for day in period_days:
                total += len(data.get(day, {}).get("users", []))
        return total

    for label, period in days.items():
        text += f"\n⬜️ آپلودر ({label}): {count_users(UPLOADER_STATS, period)} نفر"
        text += f"\n⬜️ چکر ({label}): {count_users(CHECKER_STATS, period)} نفر\n"

    settings = load_settings()
    def channel_counts(file, period_days, channels):
        results = {}
        if os.path.exists(file):
            with open(file) as f:
                data = json.load(f)
            for day in period_days:
                day_data = data.get(day, {}).get("channels", {})
                for ch in channels:
                    results[ch] = results.get(ch, 0) + day_data.get(ch, 0)
        return results

    text += "\n📍 آمار عضویت در کانال‌ها (۳۰ روز گذشته):\n"
    for kind, label in [("uploader_channels", "آپلودر"), ("checker_channels", "چکر")]:
        chs = settings.get(kind, [])
        ch_stats = channel_counts(UPLOADER_STATS if kind == "uploader_channels" else CHECKER_STATS, days["ماه"], chs)
        if ch_stats:
            text += f"\n• {label}:\n"
            for ch, count in ch_stats.items():
                text += f"   {ch}: {count} عضو\n"

    bot.send_message(message.chat.id, text)


def delete_after(chat_id, msg_id, warn_id):
    time.sleep(15)
    try:
        bot.delete_message(chat_id, msg_id)
        bot.delete_message(chat_id, warn_id)
    except:
        pass


def setup_routes(server):
    @server.route('/uploader/' + TOKEN, methods=['POST'])
    def handle_uploader():
        bot.process_new_updates([
            telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))
        ])
        return "OK", 200
