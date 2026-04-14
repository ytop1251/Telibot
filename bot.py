import json, os, time, random, asyncio
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
                "welcome_text": "🔥 Premium Content Access",
                "welcome_img": None,
                "upi": "upi@bank",
                "price": 99,
                "qr_img": None,
                "qr_text": "💎 Complete your payment below",
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

# ================= CODE =================
def gen_code():
    return str(random.randint(100000, 999999))

# ================= START =================
async def start(update: Update, context):
    user = update.effective_user

    if user.id not in data["users"]:
        data["users"].append(user.id)
        save()

    msg = update.message or update.callback_query.message

    kb = [
        [InlineKeyboardButton("🔓 Unlock Premium", callback_data="BUY")],
        [InlineKeyboardButton("👀 View Demo Content", callback_data="DEMO")]
    ]

    txt = f"""
🎓 *Welcome to Premium Access*

{config['welcome_text']}

💰 *Price:* ₹{config['price']}

👇 Choose an option below:
"""

    if config["welcome_img"]:
        await msg.reply_photo(config["welcome_img"], caption=txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await msg.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ================= PAYMENT =================
async def payment(q, context):
    code = gen_code()
    context.user_data["code"] = code

    kb = [
        [InlineKeyboardButton("✅ I HAVE PAID", callback_data="PAID")],
        [InlineKeyboardButton("🔙 Back", callback_data="BACK")]
    ]

    txt = f"""
💎 *Complete Your Payment*

💰 *Amount:* ₹{config['price']}
💳 *UPI ID:* `{config['upi']}`

🆔 *Your Code:* `{code}`

📌 *Steps:*
1. Pay using UPI
2. Add code in note
3. Send screenshot

⚠️ Without code → not approved
"""

    if config["qr_img"]:
        await q.message.edit_media(InputMediaPhoto(config["qr_img"], caption=txt, parse_mode="Markdown"),
                                   reply_markup=InlineKeyboardMarkup(kb))
    else:
        await q.message.edit_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ================= DEMO =================
async def show_demo(msg, i):
    if not data["demo"]:
        await msg.edit_text("❌ No demo available")
        return

    total = len(data["demo"])

    kb = [
        [
            InlineKeyboardButton("⬅️", callback_data="PREV") if i > 0 else InlineKeyboardButton("•", callback_data="X"),
            InlineKeyboardButton("➡️", callback_data="NEXT") if i < total-1 else InlineKeyboardButton("•", callback_data="X")
        ],
        [InlineKeyboardButton("🏠 Back", callback_data="BACK")]
    ]

    await msg.edit_media(
        InputMediaVideo(data["demo"][i], caption=f"🎬 Demo {i+1}/{total}"),
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= USER BUTTON =================
async def user_btn(update: Update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "BUY":
        await payment(q, context)

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
        await q.message.reply_text("📸 Send screenshot with code visible")

# ================= PROOF =================
async def proof(update: Update, context):
    if update.effective_user.id == ADMIN_ID:
        return

    code = context.user_data.get("code", "")
    caption = update.message.caption or ""

    if code not in caption:
        await update.message.reply_text("❌ Code missing! Please send correct screenshot.")
        return

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"💰 Payment Request\n👤 {update.effective_user.id}\nCode: {code}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"A_{update.effective_user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"R_{update.effective_user.id}")
            ]
        ])
    )

    await update.message.reply_text("⏳ Waiting for admin approval")

# ================= APPROVE =================
async def approve(update: Update, context):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])

    if q.data.startswith("A_"):

        if not config["channel"]:
            await context.bot.send_message(uid, "❌ Channel not set")
            return

        link = await context.bot.create_chat_invite_link(
            config["channel"], member_limit=1, expire_date=int(time.time())+300
        )

        await context.bot.send_message(uid, f"🎉 Approved!\n🔗 {link.invite_link}")
        data["sales"] += config["price"]
        save()

        await q.edit_message_caption("✅ Approved")

    else:
        await context.bot.send_message(uid, "❌ Payment rejected")
        await q.edit_message_caption("❌ Rejected")

# ================= ADMIN =================
async def admin(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="DASH")],
        [InlineKeyboardButton("📝 Update Welcome", callback_data="WELCOME")],
        [InlineKeyboardButton("🧾 Update QR", callback_data="QR")],
        [InlineKeyboardButton("💰 Update UPI", callback_data="UPI")],
        [InlineKeyboardButton("💸 Update Price", callback_data="PRICE")],
        [InlineKeyboardButton("🎬 Upload Demo", callback_data="DEMO_ADMIN")],
        [InlineKeyboardButton("📡 Set Channel", callback_data="CHANNEL")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="BROADCAST")]
    ]

    await update.message.reply_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

# ================= ADMIN BUTTON =================
async def admin_btn(update: Update, context):
    q = update.callback_query
    await q.answer()

    admin_state[q.from_user.id] = q.data

    msgs = {
        "WELCOME": "📸 Send welcome image + caption",
        "QR": "📸 Send QR image + caption",
        "UPI": "💰 Send your UPI ID",
        "PRICE": "💸 Send new price",
        "DEMO_ADMIN": "🎬 Send demo video (max 5)",
        "CHANNEL": "📡 Send channel ID (-100xxxx)",
        "BROADCAST": "📢 Send message to broadcast"
    }

    if q.data == "DASH":
        await q.message.edit_text(f"👥 Users: {len(data['users'])}\n💰 Sales: ₹{data['sales']}")
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
        tasks = [context.bot.send_message(u, update.message.text) for u in data["users"]]
        await asyncio.gather(*tasks, return_exceptions=True)

    admin_state.pop(uid)
    save()
    await update.message.reply_text("✅ Successfully updated!")

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
            await update.message.reply_text("❌ Max 5 demos allowed")
            return
        data["demo"].append(update.message.video.file_id)

    admin_state.pop(uid)
    save()
    await update.message.reply_text("✅ Successfully updated!")

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(user_btn))
app.add_handler(CallbackQueryHandler(admin_btn))
app.add_handler(CallbackQueryHandler(approve, pattern="^(A_|R_)"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))
app.add_handler(MessageHandler(filters.PHOTO, proof))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, admin_media))

print("🚀 BOT RUNNING")
app.run_polling()
