"""
api/webhook.py — Vercel serverless entry point (Flask-based)
"""
import sys
import os

# Allow importing main.py from the parent (root) directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update
from main import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Build PTB application once at module level
_ptb_app = build_application()


async def _process_update(data: dict):
    await _ptb_app.initialize()
    update = Update.de_json(data, _ptb_app.bot)
    await _ptb_app.process_update(update)


@app.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"[WEBHOOK] Update received: {str(data)[:150]}")
        asyncio.run(_process_update(data))
        return "OK", 200
    except Exception as e:
        logger.error(f"[WEBHOOK] Error: {e}")
        return "Error", 500


@app.route("/", methods=["GET"])
@app.route("/api/webhook", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "Anti-Promotion Bot", "author": "SovitX"})
