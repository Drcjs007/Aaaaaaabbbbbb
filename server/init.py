from flask import Flask

def create_server():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "Bot is running"

    @app.route("/keep_alive")
    def keep_alive():
        return "Keeping the worker alive."

    return app
