import logging
import sqlite3
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from dotenv import load_dotenv
import pandas as pd
from flask import Flask
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

# ---------------- Config -----------------
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_DISPLAY_NAME = "Contribution Bot"
ADMINS = [1255111776, 7854166119]  # Replace with actual admin user IDs
IST = timezone(timedelta(hours=5, minutes=30))  # India Standard Time

# Conversation states
YEAR, MONTH, CONTRIBUTION_TYPE, FAMILY_NAME, AMOUNT, MORE_FAMILY, SCREENSHOT = range(7)

# ---------------- Database -----------------
class ContributionBot:
    def __init__(self, token: str):
        self.token = token
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, "contributions.db")
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                year INTEGER NOT NULL,
                month TEXT NOT NULL,
                contribution_type TEXT NOT NULL,
                family_member_name TEXT,
                amount REAL NOT NULL,
                screenshot_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def save_contribution(self, user_id: int, username: str, data: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO contributions 
            (user_id, username, year, month, contribution_type, family_member_name, amount, screenshot_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, data['year'], data['month'],
            data['contribution_type'], data.get('family_member_name'),
            data['amount'], data.get('screenshot_path'),
            datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

    def get_all_contributions(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM contributions ORDER BY created_at DESC')
        results = cursor.fetchall()
        conn.close()
        return results

# ---------------- Telegram Handlers -----------------
async def start(update: Update, context) -> int:
    user = update.effective_user
    username = user.first_name
    context.user_data['username'] = username
    await update.message.reply_text(
        f"Hello {username}! 👋\n\n"
        f"Welcome to {BOT_DISPLAY_NAME}! I'll help you record your contributions.\n\n"
        "Let's start by selecting the year:",
        reply_markup=get_year_keyboard()
    )
    return YEAR

def get_year_keyboard():
    years = [2025, 2026, 2027, 2028, 2029, 2030]
    keyboard = [[InlineKeyboardButton(str(y), callback_data=f"year_{y}") for y in years[i:i+2]] for i in range(0, len(years), 2)]
    return InlineKeyboardMarkup(keyboard)

def get_month_keyboard():
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    keyboard = [[InlineKeyboardButton(m, callback_data=f"month_{m}") for m in months[i:i+3]] for i in range(0, len(months), 3)]
    return InlineKeyboardMarkup(keyboard)

def get_contribution_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Self", callback_data="type_self")],
        [InlineKeyboardButton("Family Members", callback_data="type_family")]
    ])

# ---------- Callback Handlers ----------
async def year_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['year'] = int(query.data.split('_')[1])
    await query.message.reply_text("Great! Now please select the month:", reply_markup=get_month_keyboard())
    return MONTH

async def month_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['month'] = query.data.split('_')[1]
    await query.message.reply_text("Perfect! Now please select the contribution type:", reply_markup=get_contribution_type_keyboard())
    return CONTRIBUTION_TYPE

async def contribution_type_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    ctype = query.data.split('_')[1]
    context.user_data['contribution_type'] = ctype

    if ctype == "self":
        await query.message.reply_text("You selected Self contribution. Please enter the amount:")
        return AMOUNT
    else:
        context.user_data['family_members'] = []
        await query.message.reply_text("You selected Family Members contribution. Please enter the first family member's name:")
        return FAMILY_NAME

async def family_name_received(update: Update, context) -> int:
    context.user_data['current_family_name'] = update.message.text.strip()
    await update.message.reply_text("Please enter the amount for this family member:")
    return AMOUNT

async def amount_received(update: Update, context) -> int:
    try:
        amount = float(update.message.text.strip())
        context.user_data['current_amount'] = amount
        if context.user_data['contribution_type'] == 'family':
            await update.message.reply_text("Please upload the screenshot for this family member:")
        else:
            await update.message.reply_text("Please upload the screenshot of your contribution:")
        return SCREENSHOT
    except ValueError:
        await update.message.reply_text("Please enter a valid number for the amount.")
        return AMOUNT

async def screenshot_received(update: Update, context) -> int:
    if not update.message.photo:
        await update.message.reply_text("Please upload a valid photo.")
        return SCREENSHOT

    photo = update.message.photo[-1]
    month = context.user_data['month']
    folder_path = os.path.join("screenshots", month)
    os.makedirs(folder_path, exist_ok=True)

    file = await context.bot.get_file(photo.file_id)
    filename = f"screenshot_{update.effective_user.id}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(folder_path, filename)
    await file.download_to_drive(filepath)

    bot_instance = context.bot_data.get('bot_instance')
    user_id = update.effective_user.id
    username = context.user_data['username']

    if context.user_data['contribution_type'] == 'family':
        context.user_data['family_members'].append({
            'family_member_name': context.user_data['current_family_name'],
            'amount': context.user_data['current_amount'],
            'screenshot_path': filepath
        })
        await update.message.reply_text(f"✅ Screenshot saved for {context.user_data['current_family_name']}.")
        keyboard = [[InlineKeyboardButton("Yes", callback_data="more_yes")],
                    [InlineKeyboardButton("No", callback_data="more_no")]]
        await update.message.reply_text("Do you want to add another family member?", reply_markup=InlineKeyboardMarkup(keyboard))
        return MORE_FAMILY
    else:
        data = {
            'year': context.user_data['year'],
            'month': month,
            'contribution_type': 'self',
            'amount': context.user_data['current_amount'],
            'screenshot_path': filepath
        }
        bot_instance.save_contribution(user_id, username, data)
        await update.message.reply_text(
            f"✅ Contribution recorded!\n\n"
            f"Summary:\n"
            f"Year: {context.user_data['year']}\n"
            f"Month: {month}\n"
            f"Type: Self\n"
            f"Member: Self\n"
            f"Amount: {context.user_data['current_amount']}\n"
            f"Screenshot: Saved ✅\n\n"
            f"Type /start to add another contribution."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def more_family_handler(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    bot_instance = context.bot_data.get('bot_instance')
    user_id = update.effective_user.id
    username = context.user_data['username']
    month = context.user_data['month']

    if query.data == "more_yes":
        await query.message.reply_text("Please enter the next family member's name:")
        return FAMILY_NAME
    else:
        summary_text = "✅ All family contributions recorded successfully!\n\nSummary:\n"
        for member in context.user_data['family_members']:
            data = {
                'year': context.user_data['year'],
                'month': month,
                'contribution_type': 'family',
                'family_member_name': member['family_member_name'],
                'amount': member['amount'],
                'screenshot_path': member['screenshot_path']
            }
            bot_instance.save_contribution(user_id, username, data)
            summary_text += (f"Member: {member['family_member_name']}, "
                             f"Amount: {member['amount']}, Screenshot: Saved ✅\n")
        await query.message.reply_text(summary_text + "\nType /start to add another contribution.")
        context.user_data.clear()
        return ConversationHandler.END

async def cancel(update: Update, context) -> int:
    await update.message.reply_text("Operation cancelled. Type /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END

# ---------------- Export Excel -----------------
async def export_excel(update: Update, context):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ You are not authorized to access this data.")
        return

    bot_instance = context.bot_data.get('bot_instance')
    contributions = bot_instance.get_all_contributions()

    if not contributions:
        await update.message.reply_text("No contributions found.")
        return

    df = pd.DataFrame(contributions, columns=[
        'id', 'user_id', 'username', 'year', 'month', 'contribution_type',
        'family_member_name', 'amount', 'screenshot_path', 'created_at'
    ])

    os.makedirs("exports", exist_ok=True)
    export_path = os.path.join("exports", f"contributions_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.xlsx")
    df.to_excel(export_path, index=False)

    with open(export_path, "rb") as f:
        await update.message.reply_document(f, filename=os.path.basename(export_path),
                                            caption="✅ Contributions exported successfully!")

# ---------------- Flask + Bot -----------------
def run_flask():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "✅ Telegram Contribution Bot is running on Render!"

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    bot_instance = ContributionBot(token)
    application = Application.builder().token(token).build()
    application.bot_data['bot_instance'] = bot_instance

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            YEAR: [CallbackQueryHandler(year_selected, pattern='^year_')],
            MONTH: [CallbackQueryHandler(month_selected, pattern='^month_')],
            CONTRIBUTION_TYPE: [CallbackQueryHandler(contribution_type_selected, pattern='^type_')],
            FAMILY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_name_received)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot_received)],
            MORE_FAMILY: [CallbackQueryHandler(more_family_handler, pattern='^more_')]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('export_excel', export_excel))

    # Run Flask server on a separate thread
    threading.Thread(target=run_flask, daemon=True).start()

    logger.info("Bot started successfully.")
    application.run_polling()

if __name__ == '__main__':
    main()
