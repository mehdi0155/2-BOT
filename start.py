from flask import Flask
import threading
import time

from uploader_bot.main import setup_routes as uploader_routes, bot as uploader_bot
from checker_bot.main import setup_routes as checker_routes, bot as checker_bot, TOKEN as CHECKER_TOKEN

server = Flask(__name__)

uploader_routes(server)
checker_routes(server)

# تنظیم webhook برای هر دو ربات
uploader_bot.remove_webhook()
checker_bot.remove_webhook()

uploader_bot.set_webhook(url="https://two-bot-hcxp.onrender.com/uploader/" + uploader_bot.token)
checker_bot.set_webhook(url="https://two-bot-hcxp.onrender.com/checker/" + CHECKER_TOKEN)

# جلوگیری از خواب رفتن Render
def keep_alive():
    while True:
        time.sleep(15 * 60)
        print("Keeping alive...")

if __name__ == "__main__":
    threading.Thread(target=keep_alive).start()
    server.run(host="0.0.0.0", port=10000)
