from uploader_bot.main import setup_routes as uploader_routes
from checker_bot.main import setup_routes as checker_routes
from flask import Flask
import os

server = Flask(__name__)

uploader_routes(server)
checker_routes(server)

@server.route("/")
def index():
    return "Webhook set!", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    server.run(host="0.0.0.0", port=port)
