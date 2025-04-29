from flask import Flask
import threading
import time

from uploader_bot.main import setup_routes as uploader_routes
from checker_bot.main import setup_routes as checker_routes

server = Flask(__name__)

uploader_routes(server)
checker_routes(server)

# جلوگیری از خواب رفتن Render
def keep_alive():
    while True:
        time.sleep(15 * 60)  # هر ۱۵ دقیقه
        print("Keeping alive...")

if __name__ == "__main__":
    threading.Thread(target=keep_alive).start()
    server.run(host="0.0.0.0", port=10000)
