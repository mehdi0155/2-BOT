import os
import json
import threading
import time
from flask import Flask, request
import requests

TOKEN = "7920918778:AAFF4MDkYX4qBpuyXyBgcuCssLa6vjmTN1c"
URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_IDS = [5691361407, 5542190852]
UPLOAD_CHANNEL = "@UpTof"
CHECKER_BOT_USERNAME = "TofLinkBot"

app = Flask(__name__)

DB_FILE = "db.json"
SETTINGS_FILE = "settings/settings.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": [], "stats": {}}, f)

if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"required_channels_uploader": [], "required_channels_checker": []}, f)

def read_json():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def write_json(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def read_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def write_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{URL}/sendMessage", data=data)

def delete_message(chat_id, message_id):
    requests.post(f"{URL}/deleteMessage", data={"chat_id": chat_id, "message_id": message_id})

def check_membership(user_id, channels):
    for ch in channels:
        res = requests.get(f"{URL}/getChatMember", params={"chat_id": ch, "user_id": user_id}).json()
        if res.get("result", {}).get("status") in ["left", "kicked"]:
            return False
    return True

def get_user_stats_key():
    t = time.gmtime()
    return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"

def increment_stats(bot_type, user_id):
    db = read_json()
    key = get_user_stats_key()
    if key not in db["stats"]:
        db["stats"][key] = {"uploader": [], "checker": []}
    if user_id not in db["stats"][key][bot_type]:
        db["stats"][key][bot_type].append(user_id)
    write_json(db)

def start_panel(chat_id):
    markup = {
        "inline_keyboard": [
            [{"text": "مدیریت عضویت", "callback_data": "manage_membership"}],
            [{"text": "آمار", "callback_data": "stats"}]
        ]
    }
    send_message(chat_id, "پنل مدیریت", reply_markup=markup)

def send_stats(chat_id):
    db = read_json()
    settings = read_settings()
    now = time.time()
    daily, weekly, monthly = set(), set(), set()
    for key in db["stats"]:
        date_struct = time.strptime(key, "%Y-%m-%d")
        timestamp = time.mktime(date_struct)
        delta = now - timestamp
        if delta <= 86400:
            daily.update(db["stats"][key]["uploader"])
            daily.update(db["stats"][key]["checker"])
        if delta <= 604800:
            weekly.update(db["stats"][key]["uploader"])
            weekly.update(db["stats"][key]["checker"])
        if delta <= 2592000:
            monthly.update(db["stats"][key]["uploader"])
            monthly.update(db["stats"][key]["checker"])

    details = ""
    for ch in settings["required_channels_uploader"] + settings["required_channels_checker"]:
        try:
            res = requests.get(f"{URL}/getChatMembersCount", params={"chat_id": ch}).json()
            count = res.get("result", 0)
            details += f"{ch}: {count} عضو\n"
        except:
            continue

    text = f"آمار کلی:\nروزانه: {len(daily)}\nهفتگی: {len(weekly)}\nماهیانه: {len(monthly)}\n\nآمار جزئی:\n{details}"
    send_message(chat_id, text)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if user_id not in read_json()["users"]:
            db = read_json()
            db["users"].append(user_id)
            write_json(db)

        if text == "/start":
            settings = read_settings()
            if settings["required_channels_uploader"]:
                if not check_membership(user_id, settings["required_channels_uploader"]):
                    btns = [[{"text": "بررسی عضویت", "callback_data": "check_sub"}]]
                    for ch in settings["required_channels_uploader"]:
                        btns.insert(0, [{"text": ch, "url": f"https://t.me/{ch.strip('@')}"}])
                    markup = {"inline_keyboard": btns}
                    send_message(chat_id, "برای استفاده، ابتدا در کانال‌های زیر عضو شوید:", reply_markup=markup)
                    return "ok"
            increment_stats("uploader", user_id)
            send_message(chat_id, "ارسال فایل خود را شروع کنید.")

        if text == "/panel" and user_id in ADMIN_IDS:
            start_panel(chat_id)

    if "callback_query" in update:
        query = update["callback_query"]
        user_id = query["from"]["id"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        data = query["data"]

        if data == "check_sub":
            settings = read_settings()
            if check_membership(user_id, settings["required_channels_uploader"]):
                send_message(chat_id, "عضویت شما تأیید شد. اکنون می‌توانید فایل ارسال کنید.")
            else:
                send_message(chat_id, "عضویت ناقص است. لطفاً در همه کانال‌ها عضو شوید.")

        if data == "manage_membership" and user_id in ADMIN_IDS:
            markup = {
                "inline_keyboard": [
                    [{"text": "افزودن کانال به آپلودر", "callback_data": "add_uploader_channel"}],
                    [{"text": "افزودن کانال به چکر", "callback_data": "add_checker_channel"}],
                    [{"text": "بازگشت", "callback_data": "back_to_panel"}]
                ]
            }
            send_message(chat_id, "مدیریت عضویت:", reply_markup=markup)

        if data == "back_to_panel" and user_id in ADMIN_IDS:
            start_panel(chat_id)

        if data == "stats" and user_id in ADMIN_IDS:
            send_stats(chat_id)

        if data in ["add_uploader_channel", "add_checker_channel"] and user_id in ADMIN_IDS:
            typ = "uploader" if data == "add_uploader_channel" else "checker"
            msg = send_message(chat_id, f"آی‌دی کانال موردنظر برای {typ} را ارسال کنید. اگر ندارید، دکمه زیر را بزنید.", reply_markup={"inline_keyboard": [[{"text": "ندارم", "callback_data": f"no_{typ}"}]]})
            return "ok"

        if data.startswith("no_") and user_id in ADMIN_IDS:
            send_message(chat_id, "هیچ کانالی اضافه نشد.")
            start_panel(chat_id)

    return "ok"

@app.route("/")
def index():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
