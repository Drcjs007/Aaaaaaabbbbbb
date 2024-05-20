def register_routes(app):
    @app.route("/")
    def index():
        return "Bot is running"

    @app.route("/keep_alive")
    def keep_alive():
        return "Keeping the worker alive."
