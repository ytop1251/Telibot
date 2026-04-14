import json, os, time, asyncio
from telegram import *
from telegram.ext import *

TOKEN = "8615480627:AAHOpdXg33NEMGPgPEV4HYTUOYtYDIsxiP4"
ADMIN_ID = 6363477372
DATA_FILE = "data.json"

# ================= LOAD =================
def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {
            "users": [],
            "sales": 0,
            "demo": [],
            "config": {
                "welcome_text": "Get instant access to premium content.",
                "welcome_img": None,
                "upi": "yourupi@bank",
                "price": 99,
                "qr_img": None,
                "qr_text": "Scan QR and complete payment",
                "channel": None
            }
        }

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load()
config = data["config"]

admin_state = {}
demo_index = {}

# ================= START =================
async def start(update: Update, context):
    user = update.effective_user

    if user.id not in data["users"]:
        data["users"].append(user.id)
        save()

    msg = update.message or update.callback_query.message

    keyboard = [
        [InlineKeyboardButton("🔓 Unlock Premium", callback_data="BUY")],
        [InlineKeyboardButton("👀 View Demo Content", callback_data="DEMO")]
    ]

    text = f"""
🎓 Welcome to Premium Access

{config['welcome_text']}

💰 Price: ₹{config['price']}

👇 Choose an option below:
"""

    if config["welcome_img"]:
        await msg.reply_photo(config["welcome_img"], caption=text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= PAYMENT =================
async def payment(q):
    keyboard = [
        [InlineKeyboardButton("✅ I HAVE PAID", callback_data="PAID")],
        [InlineKeyboardButton("🔙 Back", callback_data="BACK")]
    ]

    text = f"""
💎 Complete Your Payment

💰 Amount: ₹{config['price']}
💳 UPI ID: {config['upi']}

📌 Steps:
1. Send payment to above UPI
2. Take screenshot
3. Click "I HAVE PAID"
4. Send screenshot

⚠️ Payment will be verified manually
"""

    if config["qr_img"]:
        await q.message.edit_media(
            InputMediaPhoto(config["qr_img"], caption=text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await q.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= DEMO =================
async def show_demo(msg, i):
    if not data["demo"]:
        await msg.edit_text("❌ No demo content available yet.")
        return

    total = len(data["demo"])

    keyboard = [
        [
            InlineKeyboardButton("⬅️", callback_data="PREV") if i > 0 else InlineKeyboardButton("•", callback_data="X"),
            InlineKeyboardButton("➡️", callback_data="NEXT") if i < total-1 else InlineKeyboardButton("•", callback_data="X")
        ],
        [InlineKeyboardButton("🏠 Back", callback_data="BACK")]
    ]

    await msg.edit_media(
        InputMediaVideo(data["demo"][i], caption=f"🎬 Demo {i+1} of {total}"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= USER BUTTON =================
async def user_btn(update: Update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "BUY":
        await payment(q)

    elif q.data == "DEMO":
        demo_index[uid] = 0
        await show_demo(q.message, 0)

    elif q.data == "NEXT":
        demo_index[uid] += 1
        await show_demo(q.message, demo_index[uid])

    elif q.data == "PREV":
        demo_index[uid] -= 1
        await show_demo(q.message, demo_index[uid])

    elif q.data == "BACK":
        await q.message.delete()
        await start(update, context)

    elif q.data == "PAID":
        await q.message.reply_text("📸 Please send your payment screenshot for verification.")

# ================= PAYMENT PROOF =================
async def proof(update: Update, context):
    user = update.effective_user

    if user.id == ADMIN_ID:
        return

    if not update.message.photo:
        return

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"💰 New Payment Request\n\n👤 User ID: {user.id}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"A_{user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"R_{user.id}")
            ]
        ])
    )

    await update.message.reply_text("⏳ Screenshot received. Please wait for admin approval.")

# ================= APPROVE / REJECT =================
async def approve(update: Update, context):
    q = update.callback_query
    await q.answer()

    user_id = int(q.data.split("_")[1])

    if q.data.startswith("A_"):

        if not config["channel"]:
            await context.bot.send_message(user_id, "❌ Channel not configured by admin.")
            return

        link = await context.bot.create_chat_invite_link(
            chat_id=config["channel"],
            member_limit=1,
            expire_date=int(time.time()) + 300
        )

        await context.bot.send_message(
            user_id,
            f"🎉 Payment Approved!\n\n🔗 Join your premium content here:\n{link.invite_link}\n\n⚠️ Link valid for 5 minutes."
        )

        data["sales"] += config["price"]
        save()

        await q.edit_message_caption("✅ Approved")

    else:
        await context.bot.send_message(user_id, "❌ Your payment was not approved.")
        await q.edit_message_caption("❌ Rejected")

# ================= ADMIN PANEL =================
async def admin(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="DASH")],
        [InlineKeyboardButton("📝 Update Welcome", callback_data="WELCOME")],
        [InlineKeyboardButton("🧾 Update QR", callback_data="QR")],
        [InlineKeyboardButton("💰 Update UPI", callback_data="UPI")],
        [InlineKeyboardButton("💸 Update Price", callback_data="PRICE")],
        [InlineKeyboardButton("🎬 Upload Demo", callback_data="DEMO_ADMIN")],
        [InlineKeyboardButton("📡 Set Channel", callback_data="CHANNEL")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="BROADCAST")]
    ]

    await update.message.reply_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN BUTTON =================
async def admin_btn(update: Update, context):
    q = update.callback_query
    await q.answer()

    admin_state[q.from_user.id] = q.data

    messages = {
        "WELCOME": "📸 Send welcome image with caption (caption = welcome text).",
        "QR": "📸 Send QR image with caption (caption = payment instructions).",
        "UPI": "💰 Send your new UPI ID.",
        "PRICE": "💸 Send new price (numbers only).",
        "DEMO_ADMIN": "🎬 Send demo video (max 5 allowed).",
        "CHANNEL": "📡 Send your channel ID (example: -100xxxx).",
        "BROADCAST": "📢 Send message to broadcast to all users."
    }

    if q.data == "DASH":
        await q.message.edit_text(f"👥 Total Users: {len(data['users'])}\n💰 Total Earnings: ₹{data['sales']}")
    else:
        await q.message.reply_text(messages[q.data])

# ================= ADMIN TEXT =================
async def admin_text(update: Update, context):
    uid = update.effective_user.id

    if uid != ADMIN_ID or uid not in admin_state:
        return

    state = admin_state[uid]

    if state == "UPI":
        config["upi"] = update.message.text

    elif state == "PRICE":
        config["price"] = int(update.message.text)

    elif state == "CHANNEL":
        config["channel"] = int(update.message.text)

    elif state == "BROADCAST":
        tasks = [context.bot.send_message(u, update.message.text) for u in data["users"]]
        await asyncio.gather(*tasks, return_exceptions=True)

    admin_state.pop(uid)
    save()
    await update.message.reply_text("✅ Updated successfully!")

# ================= ADMIN MEDIA =================
async def admin_media(update: Update, context):
    uid = update.effective_user.id

    if uid != ADMIN_ID or uid not in admin_state:
        return

    state = admin_state[uid]

    if state == "WELCOME":
        config["welcome_img"] = update.message.photo[-1].file_id
        config["welcome_text"] = update.message.caption or config["welcome_text"]

    elif state == "QR":
        config["qr_img"] = update.message.photo[-1].file_id
        config["qr_text"] = update.message.caption or config["qr_text"]

    elif state == "DEMO_ADMIN":
        if len(data["demo"]) >= 5:
            await update.message.reply_text("❌ Maximum 5 demo videos allowed.")
            return
        data["demo"].append(update.message.video.file_id)

    admin_state.pop(uid)
    save()
    await update.message.reply_text("✅ Updated successfully!")

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(approve, pattern="^(A_|R_)"))
app.add_handler(CallbackQueryHandler(admin_btn, pattern="^(DASH|WELCOME|QR|UPI|PRICE|DEMO_ADMIN|CHANNEL|BROADCAST)$"))
app.add_handler(CallbackQueryHandler(user_btn, pattern="^(BUY|DEMO|NEXT|PREV|BACK|PAID)$"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))
app.add_handler(MessageHandler(filters.PHOTO & ~filters.User(user_id=ADMIN_ID), proof))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, admin_media))

print("🚀 BOT RUNNING")
app.run_polling()
