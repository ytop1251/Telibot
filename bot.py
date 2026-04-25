import json, os, time, asyncio
from telegram import *
from telegram.ext import *

TOKEN = os.getenv("TOKEN")
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
user_state = {}

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

    text = f"""🎓 Welcome

{config['welcome_text']}

💰 Price: ₹{config['price']}
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

    text = f"""💎 Payment Details

💰 ₹{config['price']}
💳 UPI: {config['upi']}

{config['qr_text']}
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
        await msg.edit_text("❌ No demo available.")
        return

    total = len(data["demo"])
    item = data["demo"][i]

    keyboard = [
        [
            InlineKeyboardButton("⬅️", callback_data="PREV") if i > 0 else InlineKeyboardButton("•", callback_data="X"),
            InlineKeyboardButton("➡️", callback_data="NEXT") if i < total-1 else InlineKeyboardButton("•", callback_data="X")
        ],
        [InlineKeyboardButton("🏠 Back", callback_data="BACK")]
    ]

    if item["type"] == "photo":
        await msg.edit_media(InputMediaPhoto(item["file_id"], caption=f"Demo {i+1}/{total}"),
                             reply_markup=InlineKeyboardMarkup(keyboard))
    elif item["type"] == "video":
        await msg.edit_media(InputMediaVideo(item["file_id"], caption=f"Demo {i+1}/{total}"),
                             reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.edit_text(item["text"], reply_markup=InlineKeyboardMarkup(keyboard))

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
        await start(update, context)

    elif q.data == "PAID":
        user_state[uid] = "waiting_payment"
        await q.message.reply_text("📸 Send payment screenshot")

# ================= PAYMENT PROOF =================
async def proof(update: Update, context):
    user = update.effective_user

    if user_state.get(user.id) != "waiting_payment":
        return

    if not update.message.photo:
        return

    user_state.pop(user.id)

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"💰 Payment Request\n👤 User: {user.id}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"A_{user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"R_{user.id}")
            ]
        ])
    )

    await update.message.reply_text("⏳ Sent for approval")

# ================= APPROVE =================
async def approve(update: Update, context):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])

    if q.data.startswith("A_"):

        if not config["channel"]:
            await context.bot.send_message(uid, "❌ Channel not set.")
            return

        link = await context.bot.create_chat_invite_link(
            chat_id=config["channel"],
            member_limit=1,
            expire_date=int(time.time()) + 300
        )

        await context.bot.send_message(uid, f"🎉 Approved!\n{link.invite_link}")

        data["sales"] += config["price"]
        save()

        await q.edit_message_caption("✅ Approved")

    else:
        await context.bot.send_message(uid, "❌ Rejected")
        await q.edit_message_caption("❌ Rejected")

# ================= ADMIN PANEL =================
async def admin(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="DASH")],
        [InlineKeyboardButton("📝 Welcome", callback_data="WELCOME")],
        [InlineKeyboardButton("🧾 QR", callback_data="QR")],
        [InlineKeyboardButton("💰 UPI", callback_data="UPI")],
        [InlineKeyboardButton("💸 Price", callback_data="PRICE")],
        [InlineKeyboardButton("🎬 Demo Upload", callback_data="DEMO_ADMIN")],
        [InlineKeyboardButton("📡 Channel", callback_data="CHANNEL")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="BROADCAST")]
    ]

    await update.message.reply_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN BUTTON =================
async def admin_btn(update: Update, context):
    q = update.callback_query
    await q.answer()

    admin_state[q.from_user.id] = q.data

    msgs = {
        "WELCOME": "Send welcome image + caption",
        "QR": "Send QR image + caption",
        "UPI": "Send UPI",
        "PRICE": "Send price",
        "DEMO_ADMIN": "Send demo (photo/video/text)",
        "CHANNEL": "Send channel ID",
        "BROADCAST": "Send broadcast message"
    }

    if q.data == "DASH":
        await q.message.edit_text(f"Users: {len(data['users'])}\nSales: ₹{data['sales']}")
    else:
        await q.message.reply_text(msgs[q.data])

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
        for u in data["users"]:
            try:
                await context.bot.send_message(u, update.message.text)
                await asyncio.sleep(0.05)
            except:
                pass

    admin_state.pop(uid)
    save()
    await update.message.reply_text("✅ Done")

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
        if update.message.photo:
            data["demo"].append({"type": "photo", "file_id": update.message.photo[-1].file_id})
        elif update.message.video:
            data["demo"].append({"type": "video", "file_id": update.message.video.file_id})
        else:
            data["demo"].append({"type": "text", "text": update.message.text})

    admin_state.pop(uid)
    save()
    await update.message.reply_text("✅ Updated")

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(approve, pattern="^(A_|R_)"))
app.add_handler(CallbackQueryHandler(admin_btn))
app.add_handler(CallbackQueryHandler(user_btn))

app.add_handler(MessageHandler(filters.User(ADMIN_ID), admin_text))
app.add_handler(MessageHandler(filters.User(ADMIN_ID) & (filters.PHOTO | filters.VIDEO), admin_media))
app.add_handler(MessageHandler(filters.PHOTO & ~filters.User(ADMIN_ID), proof))

print("🚀 Bot Running...")
app.run_polling()
