# 🤖 Anti-Promotion Bot — SovitX
> AI-powered Telegram group moderation bot using Groq (LLaMA 3)

---

## 📁 File Structure
```
├── api/
│   └── webhook.py      ← Vercel serverless entry-point
├── main.py             ← Bot logic, AI detection, handlers
├── requirements.txt    ← Python dependencies
├── vercel.json         ← Vercel deployment config
└── README.md
```

---

## 🚀 Deployment Steps

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Anti-Promotion Bot v1"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2 — Deploy on Vercel
1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repo
3. Framework Preset: **Other**
4. Add these **Environment Variables** in Vercel dashboard:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | Your Telegram bot token |
| `GROQ_API_KEY` | Your Groq API key |
| `WEBHOOK_URL` | `https://YOUR-PROJECT.vercel.app/api/webhook` |

5. Click **Deploy**

### Step 3 — Register Webhook with Telegram
After Vercel gives you a URL, open this in your browser (replace values):
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR-PROJECT>.vercel.app/api/webhook
```
You should see:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### Step 4 — Add Bot to Your Group
1. Add `@Anti_Promotion_SovitX_bot` to your Telegram group
2. **Make it an Admin** with these permissions:
   - ✅ Delete Messages
   - ✅ Restrict Members
3. Done! Bot will now auto-monitor all messages.

---

## ⚙️ How It Works
1. User sends a message in the group
2. Bot checks if user is an admin (admins are exempt)
3. Message is sent to **Groq AI (LLaMA 3-70B)** for analysis
4. If AI detects promotional content:
   - 🗑️ Message is deleted instantly
   - ⚠️ Warning is sent with user details + guidelines
   - After **3 warnings** → user is auto-muted 🔇

---

## 📋 Community Guidelines Enforced
- ✈️ No promotion  
- 🛒 No buying/selling  
- 🔗 No link sharing  
- 👊 Violence = Ban  
- 🤚 No spam/Fraud  
- ⛔ Don't Trust Anyone  

---

_Built with ❤️ by SovitX · Powered by Groq AI_
