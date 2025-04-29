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
STATS_FILE = "stats.json"


def save_to_db(link_id, file_id):
    db = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            db = json.load(f)
    db[link_id] = file_id
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

    update_stats("uploader")


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


def update_stats(bot_type):
    today = datetime.date.today().isoformat()
    stats = {"uploader": {}, "checker": {}, "channels": {}}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            stats = json.load(f)
    if today not in stats[bot_type]:
        stats[bot_type][today] = 0
    stats[bot_type][today] += 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)


def get_stats():
    if not os.path.exists(STATS_FILE):
        return {"uploader": {}, "checker": {}, "channels": {}}
    with open(STATS_FILE) as f:
        return json.load(f)


def handle_start(message):
    args = message.text.split()
    uid = message.from_user.id

    if len(args) > 1:
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

    if is_admin(uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📂 آپلود ویدیو", "📣 عضویت اجباری", "📊 آمار")
        bot.send_message(message.chat.id, "به پنل خوش آمدید.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "لینک دریافت شده معتبر نیست.")


@bot.message_handler(commands=['start'])
def start_cmd(message):
    handle_start(message)


@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if is_admin(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📂 آپلود ویدیو", "📣 عضویت اجباری", "📊 آمار")
        bot.send_message(message.chat.id, "پنل مدیریت", reply_markup=markup)


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text == "📊 آمار")
def show_statistics(message):
    stats = get_stats()
    today = datetime.date.today()
    def count_days(bot_type, days):
        total = 0
        for i in range(days):
            day = (today - datetime.timedelta(days=i)).isoformat()
            total += stats.get(bot_type, {}).get(day, 0)
        return total

    text = (
        f"آمار کلی:
"
        f"- امروز: آپلودر {count_days('uploader', 1)}, چکر {count_days('checker', 1)}
"
        f"- ۷ روز گذشته: آپلودر {count_days('uploader', 7)}, چکر {count_days('checker', 7)}
"
        f"- ۳۰ روز گذشته: آپلودر {count_days('uploader', 30)}, چکر {count_days('checker', 30)}"
    )
    bot.send_message(message.chat.id, text)


# کد باقی ربات بدون تغییر است...
# لطفاً ادامه‌ی کد اصلی را که فرستادی نگه دار و در اینجا قرار بده
# این بخش فقط قسمت آمار را به کدت اضافه کرده بدون اینکه بخش‌های دیگر را تغییر بدهد



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
