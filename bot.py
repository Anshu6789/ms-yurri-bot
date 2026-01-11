import os
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# --- Web Server to keep it alive ---
app = Flask('')
@app.route('/')
def home(): return "Ms. Yurri Bot is ONLINE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- Config & Storage ---
TOKEN = '8592510849:AAEqXaB2cI_RebRLKhFLqmIrQWPvoMwKl5o'
admin_data = {
    "state": None,
    "channel_id": None,
    "welcome_msg": "Welcome to our Channel!",
    "reminder_post_id": None,
    "reminder_from_chat": None,
    "random_posts": [] # List of (chat_id, message_id)
}

# --- Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_data["state"] = "waiting_for_channel"
    text = (
        "नमस्ते! मैं Ms. Yurri Bot हूँ। 🌸\n\n"
        "अपना चैनल जोड़ने के लिए, पहले मुझे अपने चैनल में **Admin** बनाएँ,\n"
        "फिर वहाँ से कोई भी एक पोस्ट यहाँ **Forward** करें।"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def show_menu(update_or_msg, context):
    text = "चैनल सफलतापूर्वक जुड़ गया है! अब आप सेटिंग्स चुन सकते हैं:"
    keyboard = [
        [InlineKeyboardButton("Custom Welcome Message", callback_data="welcome")],
        [InlineKeyboardButton("Custom Reminder Message", callback_data="reminder")],
        [InlineKeyboardButton("Custom Random Reminder", callback_data="random")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_msg, 'reply_text'):
        await update_or_msg.reply_text(text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update_or_msg.chat_id, text=text, reply_markup=reply_markup)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = admin_data["state"]
    
    # Channel detect karne ka logic (Forwarded post se)
    if state == "waiting_for_channel":
        if update.message.forward_from_chat:
            admin_data["channel_id"] = update.message.forward_from_chat.id
            admin_data["state"] = None
            await update.message.reply_text(f"✅ Channel connected: {update.message.forward_from_chat.title}")
            await show_menu(update.message, context)
        else:
            await update.message.reply_text("कृपया अपने चैनल से कोई पोस्ट Forward करें।")
        return

    if state == "waiting_welcome":
        admin_data["welcome_msg"] = update.message.text
        admin_data["state"] = None
        await update.message.reply_text("✅ Welcome message save ho gaya!")
        await show_menu(update.message, context)
    
    elif state == "waiting_reminder":
        admin_data["reminder_post_id"] = update.message.message_id
        admin_data["reminder_from_chat"] = update.message.chat_id
        admin_data["state"] = None
        await update.message.reply_text("✅ Reminder post set ho gaya!")
        await show_menu(update.message, context)

    elif state == "waiting_random":
        if len(admin_data["random_posts"]) < 5:
            admin_data["random_posts"].append((update.message.chat_id, update.message.message_id))
            await update.message.reply_text(f"Post add ho gaya ({len(admin_data['random_posts'])}/5). Aur bhejein ya /done likhein.")

async def done_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(admin_data["random_posts"]) >= 2:
        admin_data["state"] = None
        await update.message.reply_text("✅ Random reminders set ho gaye hain!")
        await show_menu(update.message, context)
    else:
        await update.message.reply_text("Kam se kam 2 post bhejna zaroori hai.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "welcome":
        admin_data["state"] = "waiting_welcome"
        await query.edit_message_text("Abhi apna Welcome Message bhejein.")
    elif query.data == "reminder":
        admin_data["state"] = "waiting_reminder"
        await query.edit_message_text("Wo post Forward karein jise har 5 ghante me channel pe dikhana hai.")
    elif query.data == "random":
        admin_data["state"] = "waiting_random"
        admin_data["random_posts"] = []
        await query.edit_message_text("2 se 5 post forward karein. Hone ke baad /done likhein.")

# --- Automated Tasks ---

async def auto_reminder(context: ContextTypes.DEFAULT_TYPE):
    if admin_data["channel_id"] and admin_data["reminder_post_id"]:
        await context.bot.copy_message(
            chat_id=admin_data["channel_id"], 
            from_chat_id=admin_data["reminder_from_chat"], 
            message_id=admin_data["reminder_post_id"]
        )

async def random_reminder(context: ContextTypes.DEFAULT_TYPE):
    import random
    if admin_data["channel_id"] and admin_data["random_posts"]:
        chat_id, post_id = random.choice(admin_data["random_posts"])
        msg = await context.bot.copy_message(chat_id=admin_data["channel_id"], from_chat_id=chat_id, message_id=post_id)
        await asyncio.sleep(300) # 5 minutes
        try:
            await context.bot.delete_message(chat_id=admin_data["channel_id"], message_id=msg.message_id)
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
    
    app_bot.run_polling()
