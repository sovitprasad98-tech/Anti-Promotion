"""
api/webhook.py
──────────────
Vercel serverless entry-point.

Flow:
  Telegram → POST /api/webhook
    → parse JSON update
    → forward to python-telegram-bot Application
    → handlers in main.py do the work

How to set the webhook (run once):
  https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<your-project>.vercel.app/api/webhook
"""

import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler

from telegram import Update
from main import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Build the PTB application once (module-level
#  so Vercel can reuse it across warm invocations)
# ──────────────────────────────────────────────
_application = build_application()


def _process(update_data: dict):
    """Run a single Telegram update through PTB synchronously."""
    async def _inner():
        await _application.initialize()
        update = Update.de_json(update_data, _application.bot)
        await _application.process_update(update)

    asyncio.run(_inner())


# ──────────────────────────────────────────────
#  Vercel Python serverless handler
#  (must be a class named 'handler' inheriting
#   BaseHTTPRequestHandler)
# ──────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        logger.info(format % args)

    # Telegram only sends POST requests
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode("utf-8"))

            logger.info(f"[WEBHOOK] Received update: {json.dumps(update_data)[:200]}")

            _process(update_data)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            logger.error(f"[WEBHOOK] Error processing update: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

    # Health-check endpoint (useful to confirm deployment)
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            b'{"status":"ok","bot":"Anti-Promotion Bot","author":"SovitX"}'
        )
