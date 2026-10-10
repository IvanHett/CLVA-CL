"""API layer: serves the web chat interface and the JSON endpoints.

Run with:  python -m src.api
"""
from dataclasses import asdict

from flask import Flask, jsonify, request, send_from_directory

from . import config
from .chatbot import Chatbot
from .storage import InteractionLogger

MAX_QUERY_LENGTH = 500


def create_app(chatbot: Chatbot | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(config.WEB_DIR), static_url_path="/static")
    bot = chatbot or Chatbot(logger=InteractionLogger())

    @app.get("/")
    def index():
        return send_from_directory(config.WEB_DIR, "index.html")

    @app.post("/ask")
    def ask():
        body = request.get_json(silent=True) or {}
        query = body.get("query")
        mode = body.get("mode", config.DEFAULT_MODE)
        if not isinstance(query, str) or not query.strip():
            return jsonify(error="Request body must include a non-empty 'query' string."), 400
        if len(query) > MAX_QUERY_LENGTH:
            return jsonify(error=f"'query' must be at most {MAX_QUERY_LENGTH} characters."), 400
        if mode not in config.MODES:
            return jsonify(error=f"'mode' must be one of {list(config.MODES)}."), 400
        return jsonify(bot.ask(query.strip(), mode).to_dict())

    @app.get("/modules")
    def modules():
        return jsonify([asdict(m) for m in bot.dataset.modules])

    @app.get("/admin/unanswered")
    def unanswered():
        return jsonify(bot.logger.unanswered() if bot.logger else [])

    @app.get("/health")
    def health():
        return jsonify(status="ok", intents=len(bot.dataset.answers), modules=len(bot.dataset.modules))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
