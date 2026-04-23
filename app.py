from flask import Flask, request, jsonify
import json, asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from main import build_app, BOT_TOKEN
import requests as req

app = Flask(__name__)

async def process_update(update_data):
    application = build_app()
    await application.initialize()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)
    await application.shutdown()

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "bot": "Anti-Promotion Bot", "author": "SovitX"})

@app.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        asyncio.run(process_update(request.get_json(force=True)))
    except Exception as e:
        print(f"Error: {e}")
    return jsonify({"ok": True})

@app.route("/api/webhook", methods=["GET"])
def set_webhook():
    url = f"https://{request.host}/api/webhook"
    r = req.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": url, "allowed_updates": ["message", "callback_query"]},
        timeout=8
    )
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(debug=False)
