from http.server import BaseHTTPRequestHandler
import json, os, asyncio, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from main import build_app, BOT_TOKEN
import requests as req


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length      = int(self.headers["Content-Length"])
            body        = self.rfile.read(length)
            update_data = json.loads(body.decode("utf-8"))
            asyncio.run(process_update(update_data))
        except Exception as e:
            print(f"Error: {e}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self):
        # Visit /api/webhook in browser to auto-set the webhook
        host        = self.headers.get("Host", "")
        webhook_url = f"https://{host}/api/webhook"
        r = req.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["message", "callback_query"]},
            timeout=8,
        )
        result = r.json()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())


async def process_update(update_data):
    application = build_app()
    await application.initialize()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)
    await application.shutdown()
