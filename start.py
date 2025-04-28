from uploader_bot.main import server as uploader_server
from checker_bot.main import server as checker_server
import threading

def run_uploader-bot():
    uploader_server.run(host="0.0.0.0", port=5000)

def run_checker():
    checker_server.run(host="0.0.0.0", port=5001)

if __name__ == "__main__":
    threading.Thread(target=run_uploader).start()
    threading.Thread(target=run_checker).start()
