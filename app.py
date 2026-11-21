"""应用入口：create_app() 供 Flask CLI 与 gunicorn 使用。"""
import os
from flask import Flask, redirect, url_for
from pet_system.config import SECRET_KEY, FLASK_DEBUG
from pet_system.web import child, parent

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE, "pet_system", "web", "static")


def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    app.secret_key = SECRET_KEY
    app.config["DEBUG"] = FLASK_DEBUG
    app.config["JSON_AS_ASCII"] = False
    app.register_blueprint(child.bp)
    app.register_blueprint(parent.bp)

    @app.route("/")
    def index():
        return redirect(url_for("child.home"))

    @app.route("/health")
    def health():
        return "OK"

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=FLASK_DEBUG)
