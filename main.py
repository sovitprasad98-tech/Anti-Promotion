import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from groq import Groq

# ══════════════════════════════════════════════
#  CONFIG — set these in Vercel Environment Vars
# ══════════════════════════════════════════════
BOT_TOKEN  = os.environ.get("BOT_TOKEN",  "8055567804:AAFXFOr68Xxl6dgGh-dKL_9gMX7xHVIdKx8")
GROQ_KEY   = os.environ.get("GROQ_API_KEY","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")

# Owner — all violation reports are forwarded here
OWNER_ID = 8589416528   # @SovitX_developer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_KEY)

# In-memory warning store  { "chat_id": { "user_id": count } }
warning_store: dict = {}

GUIDELINES = (
    "  ✈️  No promotion\n"
    "  🛒  No buying/selling\n"
    "  🔗  No link sharing\n"
    "  👊  Violence = Ban\n"
    "  🤚  No spam/Fraud\n"
    "  ⛔  Don't Trust Anyone"
)

# ══════════════════════════════════════════════
#  GROQ AI — detect promotional messages
# ══════════════════════════════════════════════
async def is_promotional(text: str) -> bool:
    system_prompt = (
        "You are a strict Telegram group content moderation AI. "
        "Detect if the following message contains ANY of: "
        "promotion of products/services, buying/selling offers, "
        "invite-to-DM for money, deal-making, download link push, "
        "spam, fraud, or earning/payment schemes. "
        "Reply with exactly one word only: YES or NO."
    )
    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f'Analyse:\n"""\n{text}\n"""'},
            ],
            max_tokens=5,
            temperature=0,
        )
        verdict = response.choices[0].message.content.strip().upper()
        logger.info(f"[GROQ] {verdict!r} | {text[:60]!r}")
        return verdict.startswith("YES")
    except Exception as e:
        logger.error(f"[GROQ] Error: {e}")
        return False


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════
async def user_is_admin(chat_id: int, user_id: int, bot) -> bool:
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except Exception:
        return False


def build_group_warning(user, warn_count: int, username_tag: str) -> str:
    if warn_count == 1:
        footer = (
            "🔴 *This is your FIRST warning.*\n"
            "Any further violation will be reported to admins immediately."
        )
    elif warn_count == 2:
        footer = (
            "🚨 *SECOND WARNING — You are on thin ice!*\n"
            "Your account is now under active observation.\n"
            "One more violation and *permanent removal* will follow."
        )
    else:
        footer = (
            f"☠️ *WARNING #{warn_count} — FINAL NOTICE!*\n"
            "Admin has been personally notified about your activity.\n"
            "Continue and you will be *permanently banned* from this group."
        )

    return (
        f"⚠️ *COMMUNITY VIOLATION DETECTED* ⚠️\n"
        f"{'━' * 34}\n\n"
        f"👤 *Violating User*\n"
        f"┣ 📛 *Name:*      {user.full_name}\n"
        f"┣ 🔖 *Username:*  {username_tag}\n"
        f"┗ 🪪 *User ID:*   `{user.id}`\n\n"
        f"🚫 *Reason:* Promotional/spam content detected\n"
        f"Your message has been *deleted* — it violated our Community Guidelines.\n\n"
        f"📋 *Community Guidelines*\n"
        f"{'─' * 34}\n"
        f"{GUIDELINES}\n"
        f"{'─' * 34}\n\n"
        f"📊 *Your Warning Count:* `{warn_count}`\n\n"
        f"{footer}\n\n"
        f"{'━' * 34}\n"
        f"_Please respect this community. Do NOT repeat this._\n"
        f"_🤖 Anti-Promotion Bot · Built by SovitX_"
    )


def build_owner_report(user, username_tag, group_name, group_id, warn_count, original_message) -> str:
    preview = original_message if len(original_message) <= 800 else original_message[:800] + "\n…[truncated]"
    return (
        f"🔔 *Violation Report*\n"
        f"{'━' * 34}\n\n"
        f"🏘️ *Group:*     {group_name}\n"
        f"🆔 *Group ID:* `{group_id}`\n\n"
        f"👤 *Offending User*\n"
        f"┣ 📛 *Name:*      {user.full_name}\n"
        f"┣ 🔖 *Username:*  {username_tag}\n"
        f"┗ 🪪 *User ID:*   `{user.id}`\n\n"
        f"📊 *Total Warnings:* `{warn_count}`\n\n"
        f"💬 *Deleted Message:*\n"
        f"{'─' * 34}\n"
        f"{preview}\n"
        f"{'─' * 34}\n\n"
        f"_Message was automatically deleted from the group._"
    )


# ══════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not update.effective_chat:
        return

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return
    if user.is_bot:
        return
    if await user_is_admin(chat.id, user.id, context.bot):
        return

    text = (message.text or message.caption or "").strip()
    if not text or len(text) < 5:
        return

    if not await is_promotional(text):
        return

    # Delete message
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"[BOT] Delete failed: {e}")

    # Update warning count
    cid, uid = str(chat.id), str(user.id)
    warning_store.setdefault(cid, {})
    warning_store[cid][uid] = warning_store[cid].get(uid, 0) + 1
    warn_count = warning_store[cid][uid]

    username_tag = f"@{user.username}" if user.username else "_(no username)_"
    group_name   = chat.title or "Unknown Group"

    # Send group warning
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=build_group_warning(user, warn_count, username_tag),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"[BOT] Group warning failed: {e}")

    # Send private report to owner
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=build_owner_report(user, username_tag, group_name, chat.id, warn_count, text),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"[BOT] Owner DM failed (send /start to bot first): {e}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user = update.effective_user
    await update.message.reply_text(
        f"👋 *Hello, {user.first_name}!*\n\n"
        f"🤖 I'm *Anti-Promotion Bot* — an AI-powered group moderation assistant.\n\n"
        f"{'━' * 34}\n\n"
        f"🛡️ *About Me*\n"
        f"I was created by *SovitX* to automatically detect and remove "
        f"promotional messages, scam offers, spam, and fraud from Telegram groups.\n\n"
        f"⚡ *What I Do*\n"
        f"  🔍  Analyse every group message with Groq AI\n"
        f"  🗑️  Instantly delete promotional/spam messages\n"
        f"  ⚠️  Issue escalating public warnings to violators\n"
        f"  📩  Privately notify the group owner of every violation\n"
        f"  ✅  Admins are always fully exempt\n\n"
        f"📋 *Community Guidelines I Enforce*\n"
        f"{'─' * 34}\n"
        f"{GUIDELINES}\n"
        f"{'─' * 34}\n\n"
        f"➕ *Add me to your group & make me Admin* to start!\n\n"
        f"_Powered by Groq AI (LLaMA 3-70B) · Built with ❤️ by SovitX_",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════
#  BUILD APP  (called by api/webhook.py)
# ══════════════════════════════════════════════
def build_app():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))
    application.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_group_message))
    return application


if __name__ == "__main__":
    build_app().run_polling(drop_pending_updates=True)
