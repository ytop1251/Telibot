import json, os, time, asyncio
from telegram import *
from telegram.ext import *

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 6363477372
DB = "db.json"

# ===== LOAD =====
def load():
    try:
        return json.load(open(DB))
    except:
        return {}

def save():
    json.dump(data, open(DB, "w"))

data = load()
state = {}
user_product = {}

# ===== START =====
async def start(update: Update, context):
    uid = update.effective_user.id

    if uid not in data["users"]:
        data["users"].append(uid)
        save()

    kb = [
        [InlineKeyboardButton("💎 Get Premium", callback_data="shop")],
        [InlineKeyboardButton("🎬 Demo", callback_data="demo")]
    ]

    text = data["config"]["welcome_text"]

    if data["config"]["welcome_img"]:
        await update.message.reply_photo(data["config"]["welcome_img"], caption=text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ===== USER =====
async def user_btn(update: Update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "shop":
        kb = [[InlineKeyboardButton(p["name"], callback_data=f"p_{p['id']}")] for p in data["products"]]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
        await q.message.edit_text("Select Product", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("p_"):
        pid = int(q.data.split("_")[1])
        user_product[uid] = pid
        p = next(x for x in data["products"] if x["id"] == pid)

        kb = [
            [InlineKeyboardButton("💰 Buy", callback_data="buy")],
            [InlineKeyboardButton("🔙 Back", callback_data="shop")]
        ]

        await context.bot.send_photo(uid, p["image"], caption=p["desc"], reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "buy":
        p = next(x for x in data["products"] if x["id"] == user_product[uid])

        kb = [[InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid")]]

        await context.bot.send_photo(
            uid,
            p["qr"],
            caption=f"💰 ₹{p['price']}\nUPI: {data['config']['upi']}\n\n{p['steps']}",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif q.data == "paid":
        state[uid] = "payment"
        await q.message.reply_text("📸 Send screenshot")

    elif q.data == "demo":
        for d in data["demo"]:
            await context.bot.send_video(uid, d)

    elif q.data == "home":
        await start(update, context)

# ===== PAYMENT =====
async def proof(update: Update, context):
    uid = update.effective_user.id

    if state.get(uid) != "payment":
        return

    file_id = update.message.photo[-1].file_id

    data["payments"].append({
        "user": uid,
        "product": user_product[uid],
        "file": file_id,
        "status": "pending"
    })
    save()

    kb = [[
        InlineKeyboardButton("✅ Accept", callback_data=f"A_{uid}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"R_{uid}")
    ]]

    await context.bot.send_photo(ADMIN_ID, file_id, caption=f"User {uid}", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("⏳ Waiting approval")
    state.pop(uid)

# ===== APPROVE =====
async def approve(update: Update, context):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])

    if q.data.startswith("A_"):
        link = await context.bot.create_chat_invite_link(
            data["config"]["channel"],
            expire_date=int(time.time()) + 300
        )

        await context.bot.send_message(uid, f"🎉 Approved\n{link.invite_link}")

        data["config"]["earnings"] += 1
        save()

        await q.edit_message_caption("✅ Approved")

    else:
        await context.bot.send_message(uid, "❌ Rejected")
        await q.edit_message_caption("❌ Rejected")

# ===== ADMIN PANEL =====
async def admin(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    pending = len([x for x in data["payments"] if x["status"] == "pending"])

    kb = [
        [InlineKeyboardButton("➕ ADD PRODUCT", callback_data="add")],
        [InlineKeyboardButton("❌ DELETE PRODUCT", callback_data="delete")],
        [InlineKeyboardButton("📋 LIST PRODUCTS", callback_data="list")],
        [InlineKeyboardButton("🎬 SET DEMO", callback_data="demo_set")],
        [InlineKeyboardButton("💰 SET UPI", callback_data="upi")],
        [InlineKeyboardButton("🖼 SET WELCOME IMAGE", callback_data="w_img")],
        [InlineKeyboardButton("✏️ SET WELCOME TEXT", callback_data="w_text")],
        [InlineKeyboardButton("📢 SET CHANNEL", callback_data="channel")],
        [InlineKeyboardButton(f"⏳ PENDING ({pending})", callback_data="pending")],
        [InlineKeyboardButton("📡 BROADCAST", callback_data="broadcast")],
        [InlineKeyboardButton("📊 STATS", callback_data="stats")]
    ]

    text = f"👑 ADMIN PANEL\n\nUsers: {len(data['users'])}\nEarnings: ₹{data['config']['earnings']}"

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ===== ADMIN BUTTON =====
async def admin_btn(update: Update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if uid != ADMIN_ID:
        return

    state[uid] = q.data
    await q.message.reply_text(f"Send data for {q.data}")

# ===== ADMIN TEXT =====
async def admin_text(update: Update, context):
    uid = update.effective_user.id
    text = update.message.text

    if uid != ADMIN_ID or uid not in state:
        return

    if state[uid] == "upi":
        data["config"]["upi"] = text

    elif state[uid] == "w_text":
        data["config"]["welcome_text"] = text

    elif state[uid] == "channel":
        data["config"]["channel"] = int(text)

    elif state[uid] == "broadcast":
        for u in data["users"]:
            try:
                await context.bot.send_message(u, text)
                await asyncio.sleep(0.05)
            except:
                pass

    state.pop(uid)
    save()
    await update.message.reply_text("✅ Updated")

# ===== HANDLERS =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(approve, pattern="^(A_|R_)"))
app.add_handler(CallbackQueryHandler(admin_btn))
app.add_handler(CallbackQueryHandler(user_btn))

app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_text))
app.add_handler(MessageHandler(filters.PHOTO & ~filters.User(ADMIN_ID), proof))

print("🚀 BOT RUNNING")
app.run_polling()
