import os
import asyncio
import random
import pickle
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ChatMemberHandler

# --- Web Server ---
app = Flask('')
@app.route('/')
def home(): return "Ms. Yurri Bot is ONLINE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- Database Logic ---
DATA_FILE = "bot_data.pkl"

def save_data():
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(admin_data, f)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
        except: pass
    return {
        "state": None,
        "channel_id": None,
        "welcome_msg": "Welcome to our Channel!",
        "reminder_post_id": None,
        "reminder_from_chat": None,
        "random_posts": [] 
    }

# --- Config ---
TOKEN = '8592510849:AAGQG7uVkHqKWaWseh10SuEWIKU5wOwNYVk' # Apna token yahan dalein
admin_data = load_data()

# --- Detection Logic Fix ---
def get_forward_chat_id(message):
    # Naye Telegram API ke liye check
    if message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, 'chat'): # Agar channel se hai
            return origin.chat.id, origin.chat.title
    return None, None

# --- Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_data["state"] = "waiting_for_channel"
    save_data()
    await update.message.reply_text("नमस्ते! मैं Ms. Yurri Bot हूँ। 🌸\n\nमैंने अपडेट कर लिया है! अब अपने चैनल का कोई पोस्ट यहाँ **Forward** करें।")

async def show_menu(chat_id, context):
    keyboard = [
        [InlineKeyboardButton("Custom Welcome Message", callback_data="welcome")],
        [InlineKeyboardButton("Custom Reminder Message", callback_data="reminder")],
        [InlineKeyboardButton("Custom Random Reminder", callback_data="random")]
    ]
    await context.bot.send_message(chat_id=chat_id, text="✅ सेटिंग्स चुनें:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return

    # Check for Forwarded Channel Post
    fwd_chat_id, fwd_title = get_forward_chat_id(update.message)
    
    if fwd_chat_id:
        admin_data["channel_id"] = fwd_chat_id
        admin_data["state"] = None
        save_data()
        await update.message.reply_text(f"✅ Channel Connected: {fwd_title}")
        await show_menu(update.effective_chat.id, context)
        return

    # Handle Settings States
    state = admin_data.get("state")
    if state == "waiting_welcome":
        admin_data["welcome_msg"] = update.message.text
        admin_data["state"] = None
        save_data()
        await update.message.reply_text("✅ Welcome Message Save!")
        await show_menu(update.effective_chat.id, context)
    elif state == "waiting_reminder":
        admin_data["reminder_post_id"] = update.message.message_id
        admin_data["reminder_from_chat"] = update.message.chat_id
        admin_data["state"] = None
        save_data()
        await update.message.reply_text("✅ Reminder Post Set!")
        await show_menu(update.effective_chat.id, context)
    elif state == "waiting_random":
        admin_data["random_posts"].append((update.message.chat_id, update.message.message_id))
        save_data()
        await update.message.reply_text(f"✅ Added ({len(admin_data['random_posts'])}/5). Aur bhejein ya /done likhein.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "welcome":
        admin_data["state"] = "waiting_welcome"; await query.edit_message_text("Naya Welcome text bhejein:")
    elif query.data == "reminder":
        admin_data["state"] = "waiting_reminder"; await query.edit_message_text("Wo post forward karein jise har 5 ghante me dikhana hai:")
    elif query.data == "random":
        admin_data["state"] = "waiting_random"; admin_data["random_posts"] = []; await query.edit_message_text("2-5 posts forward karein, phir /done likhein:")

async def done_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_data["state"] = None
    save_data()
    await update.message.reply_text("✅ Random Reminders Active!")
    await show_menu(update.effective_chat.id, context)

# --- Timers (Reminders) ---
async def auto_reminder(context: ContextTypes.DEFAULT_TYPE):
    if admin_data["channel_id"] and admin_data["reminder_post_id"]:
        try:
            await context.bot.copy_message(chat_id=admin_data["channel_id"], from_chat_id=admin_data["reminder_from_chat"], message_id=admin_data["reminder_post_id"])
        except: pass

async def random_reminder(context: ContextTypes.DEFAULT_TYPE):
    if admin_data["channel_id"] and admin_data["random_posts"]:
        c_id, p_id = random.choice(admin_data["random_posts"])
        try:
            m = await context.bot.copy_message(chat_id=admin_data["channel_id"], from_chat_id=c_id, message_id=p_id)
            await asyncio.sleep(300); await context.bot.delete_message(chat_id=admin_data["channel_id"], message_id=m.message_id)
        except: pass

if __name__ == '__main__':
    keep_alive()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("done", done_random))
    app_bot.add_handler(CallbackQueryHandler(button_handler))
    app_bot.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_messages))
    
    job_q = app_bot.job_queue
    job_q.run_repeating(auto_reminder, interval=18000, first=10)
    job_q.run_repeating(random_reminder, interval=18000, first=300)
    
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)
