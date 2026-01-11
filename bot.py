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
DATA_FILE = "user_data.pkl"

def save_data():
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(all_users, f)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
        except: pass
    return {}

# --- Config ---
TOKEN = '8592510849:AAFcVxoLN9dFn_SlywEnOuxciPqv8MilpFc' 
all_users = load_data()

def get_user_data(user_id):
    if str(user_id) not in all_users:
        all_users[str(user_id)] = {
            "channel_id": None,
            "channel_name": None,
            "multiple_channels": [], # List for multiple channels
            "state": None,
            "welcome_msg": "Welcome to our Channel!",
            "reminder_post_id": None,
            "reminder_from_chat": None,
            "random_posts": []
        }
    return all_users[str(user_id)]

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = get_user_data(user_id)
    text = f"Hello {update.effective_user.first_name}! How can I help you today? ✨"
    
    keyboard = []
    if ud["channel_id"]:
        keyboard.append([InlineKeyboardButton(f"📺 My Channel: {ud['channel_name']}", callback_data="my_channel")])
    
    keyboard.append([InlineKeyboardButton("➕ Add/Change Channel", callback_data="add_btn")])
    keyboard.append([InlineKeyboardButton("🌐 Multi-Channel Random Reminder", callback_data="multi_remind")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user_id = update.effective_user.id
    ud = get_user_data(user_id)
    state = ud.get("state")

    # Adding Main or Multi-Channel
    if state == "waiting_for_channel" or state == "waiting_for_multi":
        if update.message.forward_origin and hasattr(update.message.forward_origin, 'chat'):
            f_id = update.message.forward_origin.chat.id
            f_title = update.message.forward_origin.chat.title
            
            if state == "waiting_for_multi":
                if f_id not in ud["multiple_channels"]:
                    ud["multiple_channels"].append(f_id)
                    await update.message.reply_text(f"✅ Added to Multi-Channel list: {f_title}")
                else:
                    await update.message.reply_text("⚠️ This channel is already in the list.")
            else:
                ud["channel_id"] = f_id
                ud["channel_name"] = f_title
                await update.message.reply_text(f"✅ Main Channel Set: {f_title}")
            
            ud["state"] = None
            save_data()
            await start(update, context) # Show main menu again
        return

    # Sticky States for Settings
    if state == "waiting_welcome":
        ud["welcome_msg"] = update.message.text
        ud["state"] = None
        save_data(); await update.message.reply_text("✅ Welcome Message Saved!")
    elif state == "waiting_reminder":
        ud["reminder_post_id"] = update.message.message_id
        ud["reminder_from_chat"] = update.message.chat_id
        ud["state"] = None
        save_data(); await update.message.reply_text("✅ Reminder Post Saved!")
    elif state == "waiting_random":
        ud["random_posts"].append((update.message.chat_id, update.message.message_id))
        save_data(); await update.message.reply_text(f"✅ Added ({len(ud['random_posts'])}/5). /done likhein.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ud = get_user_data(query.from_user.id)
    await query.answer()

    if query.data == "add_btn":
        ud["state"] = "waiting_for_channel"
        await query.edit_message_text("Now forward a post from the channel you want as **Main**.")
    
    elif query.data == "multi_remind":
        text = f"🌐 **Multi-Channel Random Reminder**\n\nIsme wo posts send honge jo aapne Random Reminder me set kiye hain.\n\nConnected Channels: {len(ud['multiple_channels'])}\n\nNaya channel list me jodne ke liye `/add_multi` command dein."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "welcome":
        ud["state"] = "waiting_welcome"; await query.edit_message_text("Send the Welcome Text:")
    elif query.data == "reminder":
        ud["state"] = "waiting_reminder"; await query.edit_message_text("Forward the Hourly Reminder post:")
    elif query.data == "random":
        ud["state"] = "waiting_random"; ud["random_posts"] = []; await query.edit_message_text("Forward 2-5 posts for Random Reminders:")
    elif query.data == "back_start":
        await start(query, context)

    save_data()

async def add_multi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = get_user_data(update.effective_user.id)
    ud["state"] = "waiting_for_multi"
    await update.message.reply_text("Okay! Forward a post from the **additional channel** you want to add to the Multi-Channel list.")

# --- Automation Timer (Multi-Channel Logic) ---
async def global_job_timer(context: ContextTypes.DEFAULT_TYPE):
    for uid, ud in all_users.items():
        if ud["random_posts"]:
            c_id, p_id = random.choice(ud["random_posts"])
            
            # Send to Main Channel
            if ud["channel_id"]:
                try:
                    m = await context.bot.copy_message(ud["channel_id"], c_id, p_id)
                    await asyncio.sleep(600); await context.bot.delete_message(ud["channel_id"], m.message_id)
                except: pass
            
            # Send to Multiple Channels (Saved List)
            for m_chat_id in ud["multiple_channels"]:
                try:
                    m_multi = await context.bot.copy_message(m_chat_id, c_id, p_id)
                    # Auto delete from multi channels too after 10 mins
                    context.job_queue.run_once(lambda c: context.bot.delete_message(m_chat_id, m_multi.message_id), when=600)
                except: pass

if __name__ == '__main__':
    keep_alive()
    app_bot = ApplicationBuilder().token(TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("add_multi", add_multi_cmd))
    app_bot.add_handler(CommandHandler("add_channel", lambda u,c: u.message.reply_text("Use buttons to add channel!")))
    app_bot.add_handler(CommandHandler("done", lambda u,c: u.message.reply_text("✅ All set!")))
    app_bot.add_handler(CallbackQueryHandler(button_handler))
    app_bot.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    app_bot.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_messages))
    
    app_bot.job_queue.run_repeating(global_job_timer, interval=3600, first=10)
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)
