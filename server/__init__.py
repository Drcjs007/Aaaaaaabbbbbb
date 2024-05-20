from flask import Flask
from .routes import register_routes

def create_server():
    app = Flask(__name__)
    register_routes(app)
    return app

app = create_server()  # This ensures that app is available as an attribute
