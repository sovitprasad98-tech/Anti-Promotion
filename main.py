import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from groq import Groq

# ══════════════════════════════════════════════════════════════════
#  CONFIG  —  Set BOT_TOKEN, GROQ_API_KEY as Vercel Env Variables
# ══════════════════════════════════════════════════════════════════
BOT_TOKEN   = os.environ.get("BOT_TOKEN",   "8055567804:AAFXFOr68Xxl6dgGh-dKL_9gMX7xHVIdKx8")
GROQ_KEY    = os.environ.get("GROQ_API_KEY","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")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# ── Owner — all violation reports are forwarded here privately ──
OWNER_ID       = 8589416528          # Your Telegram numeric ID
OWNER_USERNAME = "@SovitX_developer"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_KEY)

# ══════════════════════════════════════════════════════════════════
#  IN-MEMORY WARNING STORE
#  { "chat_id": { "user_id": count } }
#  NOTE: Vercel is stateless — replace with Firebase/Redis for
#        persistence across cold starts.
# ══════════════════════════════════════════════════════════════════
warning_store: dict[str, dict[str, int]] = {}

# ══════════════════════════════════════════════════════════════════
#  COMMUNITY GUIDELINES
# ══════════════════════════════════════════════════════════════════
GUIDELINES = (
    "  ✈️  No promotion\n"
    "  🛒  No buying/selling\n"
    "  🔗  No link sharing\n"
    "  👊  Violence = Ban\n"
    "  🤚  No spam/Fraud\n"
    "  ⛔  Don't Trust Anyone"
)

# ══════════════════════════════════════════════════════════════════
#  GROQ AI — PROMOTION DETECTOR
# ══════════════════════════════════════════════════════════════════
async def is_promotional(text: str) -> bool:
    """
    Returns True if Groq LLaMA 3 judges the message as promotional,
    spam, buying/selling, fraud, or invite-for-money content.
    """
    system_prompt = (
        "You are a strict Telegram group content moderation AI. "
        "Detect if the following message contains ANY of: "
        "promotion of products/services, buying/selling offers, "
        "invite-to-DM for money, deal-making, download link push, "
        "spam, fraud, or earning/payment schemes. "
        "Reply with exactly one word only: YES or NO."
    )
    user_prompt = f'Analyse this message:\n"""\n{text}\n"""'

    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=5,
            temperature=0,
        )
        verdict = response.choices[0].message.content.strip().upper()
        logger.info(f"[GROQ] verdict={verdict!r} | snippet={text[:80]!r}")
        return verdict.startswith("YES")
    except Exception as e:
        logger.error(f"[GROQ] API error: {e}")
        return False   # fail-safe: never punish on API error


# ══════════════════════════════════════════════════════════════════
#  HELPER — check admin status
# ══════════════════════════════════════════════════════════════════
async def user_is_admin(chat_id: int, user_id: int, bot) -> bool:
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════
#  GROUP WARNING MESSAGE  (publicly shown in group — scary tone)
# ══════════════════════════════════════════════════════════════════
def build_group_warning(user, warn_count: int, username_tag: str) -> str:
    # Escalating scary footer — no actual ban/mute happens
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
        f"🚫 *Reason:* Promotional / spam content detected\n"
        f"Your message has been *deleted* as it violated our "
        f"Community Guidelines.\n\n"
        f"📋 *Community Guidelines*\n"
        f"{'─' * 34}\n"
        f"{GUIDELINES}\n"
        f"{'─' * 34}\n\n"
        f"📊 *Your Warning Count:* `{warn_count}`\n\n"
        f"{footer}\n\n"
        f"{'━' * 34}\n"
        f"_Please respect this community and do NOT repeat this._\n"
        f"_🤖 Anti-Promotion Bot · Built by SovitX_"
    )


# ══════════════════════════════════════════════════════════════════
#  OWNER PRIVATE REPORT  (sent to you — includes full message)
# ══════════════════════════════════════════════════════════════════
def build_owner_report(
    user,
    username_tag: str,
    group_name: str,
    group_id: int,
    warn_count: int,
    original_message: str,
) -> str:
    # Truncate very long messages cleanly
    msg_preview = (
        original_message
        if len(original_message) <= 800
        else original_message[:800] + "\n…[truncated]"
    )

    return (
        f"🔔 *Violation Report — Action Taken*\n"
        f"{'━' * 34}\n\n"
        f"🏘️ *Group:*     {group_name}\n"
        f"🆔 *Group ID:* `{group_id}`\n\n"
        f"👤 *Offending User*\n"
        f"┣ 📛 *Name:*      {user.full_name}\n"
        f"┣ 🔖 *Username:*  {username_tag}\n"
        f"┗ 🪪 *User ID:*   `{user.id}`\n\n"
        f"📊 *Total Warnings Given:* `{warn_count}`\n\n"
        f"💬 *Deleted Message (full content):*\n"
        f"{'─' * 34}\n"
        f"{msg_preview}\n"
        f"{'─' * 34}\n\n"
        f"_Message was automatically deleted from the group._"
    )


# ══════════════════════════════════════════════════════════════════
#  HANDLER — group messages
# ══════════════════════════════════════════════════════════════════
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not update.effective_chat:
        return

    chat = update.effective_chat
    user = update.effective_user

    # Groups only
    if chat.type not in ("group", "supergroup"):
        return

    # Skip bots
    if user.is_bot:
        return

    # Admins are ALWAYS fully exempt — no warnings ever
    if await user_is_admin(chat.id, user.id, context.bot):
        return

    # Grab text or caption
    text = (message.text or message.caption or "").strip()
    if not text or len(text) < 5:
        return

    # ── Ask Groq AI ──
    if not await is_promotional(text):
        return   # clean message, nothing to do

    # ════════════════════════════════════════
    #  VIOLATION DETECTED — take action
    # ════════════════════════════════════════

    # 1️⃣  Delete the offending message immediately
    try:
        await message.delete()
        logger.info(f"[BOT] Deleted msg | user={user.id} | chat={chat.id}")
    except Exception as e:
        logger.warning(f"[BOT] Delete failed: {e}")

    # 2️⃣  Update warning count for this user in this chat
    cid = str(chat.id)
    uid = str(user.id)
    warning_store.setdefault(cid, {})
    warning_store[cid][uid] = warning_store[cid].get(uid, 0) + 1
    warn_count = warning_store[cid][uid]

    username_tag = f"@{user.username}" if user.username else "_(no username)_"
    group_name   = chat.title or "Unknown Group"

    # 3️⃣  Send public warning in the group
    group_msg = build_group_warning(user, warn_count, username_tag)
    try:
        await context.bot.send_message(
            chat_id    = chat.id,
            text       = group_msg,
            parse_mode = "Markdown",
        )
    except Exception as e:
        logger.error(f"[BOT] Group warning send failed: {e}")

    # 4️⃣  Send private report to owner with FULL message content
    owner_msg = build_owner_report(
        user             = user,
        username_tag     = username_tag,
        group_name       = group_name,
        group_id         = chat.id,
        warn_count       = warn_count,
        original_message = text,
    )
    try:
        await context.bot.send_message(
            chat_id    = OWNER_ID,
            text       = owner_msg,
            parse_mode = "Markdown",
        )
        logger.info(f"[BOT] Owner report sent | user={user.id}")
    except Exception as e:
        # This fails if owner hasn't /start -ed the bot in private yet.
        # Fix: Open bot in Telegram and send /start once to unlock DMs.
        logger.warning(f"[BOT] Owner DM failed (did you /start the bot?): {e}")


# ══════════════════════════════════════════════════════════════════
#  HANDLER — /start in private chat
# ══════════════════════════════════════════════════════════════════
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user

    intro = (
        f"👋 *Hello, {user.first_name}!*\n\n"
        f"🤖 I'm *Anti-Promotion Bot* — an AI-powered group moderation assistant.\n\n"
        f"{'━' * 34}\n\n"
        f"🛡️ *About Me*\n"
        f"I was created by *SovitX* to automatically detect and remove "
        f"promotional messages, scam offers, spam, and fraud from Telegram groups — "
        f"so admins don't have to watch every single message manually.\n\n"
        f"⚡ *What I Do*\n"
        f"  🔍  Analyse every group message with Groq AI\n"
        f"  🗑️  Instantly delete promotional / spam messages\n"
        f"  ⚠️  Issue escalating public warnings to violators\n"
        f"  📩  Privately notify the group owner of every violation\n"
        f"  ✅  Admins are always fully exempt\n\n"
        f"📋 *Community Guidelines I Enforce*\n"
        f"{'─' * 34}\n"
        f"{GUIDELINES}\n"
        f"{'─' * 34}\n\n"
        f"➕ *Add me to your group & make me Admin* to start protecting your community!\n\n"
        f"_Powered by Groq AI (LLaMA 3-70B) · Built with ❤️ by SovitX_"
    )

    await update.message.reply_text(intro, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════
#  BUILD APPLICATION
# ══════════════════════════════════════════════════════════════════
def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))

    # Plain text messages in groups
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_group_message,
    ))

    # Captions on photos / videos / files
    app.add_handler(MessageHandler(
        filters.CAPTION & ~filters.COMMAND,
        handle_group_message,
    ))

    return app
