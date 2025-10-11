import logging
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
YEAR, MONTH, CONTRIBUTION_TYPE, FAMILY_NAME, AMOUNT, MORE_FAMILY, SCREENSHOT = range(7)

# Bot display name
BOT_DISPLAY_NAME = "Contribution Bot"

# Admin user IDs for export
ADMIN_USER_IDS = [1255111776,7854166119]  # Replace with your Telegram user ID

# ---------------- Database ----------------
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
        logger.info("Database initialized successfully")

    def save_contribution(self, user_id: int, username: str, data: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO contributions 
            (user_id, username, year, month, contribution_type, family_member_name, amount, screenshot_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, data['year'], data['month'],
            data['contribution_type'], data.get('family_member_name'),
            data['amount'], data.get('screenshot_path')
        ))
        conn.commit()
        conn.close()
        logger.info(f"Contribution saved for user {username}")

    def export_to_excel(self, output_file="contributions_export.xlsx"):
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM contributions ORDER BY created_at DESC", conn)
        conn.close()
        df.to_excel(output_file, index=False)
        return output_file


# ---------------- Telegram Handlers ----------------

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
    keyboard = []
    for i in range(0, len(years), 2):
        row = []
        for j in range(2):
            if i + j < len(years):
                year = years[i + j]
                row.append(InlineKeyboardButton(str(year), callback_data=f"year_{year}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def get_month_keyboard():
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    keyboard = []
    for i in range(0, len(months), 3):
        row = []
        for j in range(3):
            if i + j < len(months):
                month = months[i + j]
                row.append(InlineKeyboardButton(month, callback_data=f"month_{month}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def get_contribution_type_keyboard():
    keyboard = [
        [InlineKeyboardButton("Self", callback_data="type_self")],
        [InlineKeyboardButton("Family Members", callback_data="type_family")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------- Callback Handlers ----------

async def year_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    year = int(query.data.split('_')[1])
    context.user_data['year'] = year
    await query.message.reply_text(
        f"Great! You selected {year}. Now please select the month:",
        reply_markup=get_month_keyboard()
    )
    return MONTH


async def month_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    month = query.data.split('_')[1]
    context.user_data['month'] = month
    await query.message.reply_text(
        f"Perfect! You selected {month}. Now please select the contribution type:",
        reply_markup=get_contribution_type_keyboard()
    )
    return CONTRIBUTION_TYPE


async def contribution_type_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    contribution_type = query.data.split('_')[1]
    context.user_data['contribution_type'] = contribution_type

    if contribution_type == "self":
        await query.message.reply_text("You selected Self contribution. Please enter the amount:")
        return AMOUNT
    else:
        context.user_data['family_members'] = []
        await query.message.reply_text("You selected Family Members contribution. Please enter the first family member's name:")
        return FAMILY_NAME


async def family_name_received(update: Update, context) -> int:
    family_name = update.message.text.strip()
    context.user_data['current_family_name'] = family_name
    await update.message.reply_text(f"Thanks! You entered {family_name}. Now please enter the amount for this family member:")
    return AMOUNT


async def amount_received(update: Update, context) -> int:
    try:
        amount = float(update.message.text.strip())
        context.user_data['current_amount'] = amount

        if context.user_data.get('contribution_type') == 'family':
            await update.message.reply_text(
                f"Amount {amount} recorded for {context.user_data['current_family_name']}. Please upload the screenshot for this family member:"
            )
            return SCREENSHOT
        else:
            await update.message.reply_text("Amount recorded. Please upload the screenshot of your contribution:")
            return SCREENSHOT

    except ValueError:
        await update.message.reply_text("Please enter a valid amount (numbers only):")
        return AMOUNT


async def screenshot_received(update: Update, context) -> int:
    if update.message.photo:
        photo = update.message.photo[-1]
        month = context.user_data['month']
        folder_path = os.path.join("screenshots", month)
        os.makedirs(folder_path, exist_ok=True)

        file = await context.bot.get_file(photo.file_id)
        filename = f"screenshot_{update.effective_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(folder_path, filename)
        await file.download_to_drive(filepath)

        bot_instance = context.bot_data.get('bot_instance')
        user_id = update.effective_user.id
        username = context.user_data.get('username')

        if context.user_data['contribution_type'] == 'family':
            context.user_data['family_members'].append({
                'family_member_name': context.user_data['current_family_name'],
                'amount': context.user_data['current_amount'],
                'screenshot_path': filepath
            })

            await update.message.reply_text(f"✅ Screenshot saved for {context.user_data['current_family_name']}.")

            keyboard = [
                [InlineKeyboardButton("Yes", callback_data="more_yes")],
                [InlineKeyboardButton("No", callback_data="more_no")]
            ]
            await update.message.reply_text(
                "Do you want to add another family member?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
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
                f"✅ Your contribution has been successfully recorded!\n\n"
                f"Summary:\n"
                f"Year: {context.user_data['year']}\n"
                f"Month: {month}\n"
                f"Type: self\n"
                f"Member: Self\n"
                f"Amount: {context.user_data['current_amount']}\n"
                f"Screenshot: Saved\n\n"
                "Type /start to add another contribution."
            )
            context.user_data.clear()
            return ConversationHandler.END
    else:
        await update.message.reply_text("Please upload a screenshot (photo) of your contribution:")
        return SCREENSHOT


async def more_family_handler(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    bot_instance = context.bot_data.get('bot_instance')
    user_id = update.effective_user.id
    username = context.user_data.get('username')
    month = context.user_data['month']

    if query.data == "more_yes":
        await query.message.reply_text("Please enter the next family member's name:")
        return FAMILY_NAME
    else:
        summary_text = f"✅ All family contributions recorded successfully!\n\nSummary:\n"
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
            summary_text += (
                f"Member: {member['family_member_name']}\n"
                f"Amount: {member['amount']}\n"
                f"Screenshot: Saved\n\n"
            )

        await query.message.reply_text(summary_text + "Type /start to add another contribution.")
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context) -> int:
    await update.message.reply_text("Operation cancelled. Type /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END


async def export_excel(update: Update, context) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You are not authorized to access this data")
        return

    bot_instance = context.bot_data.get('bot_instance')
    output_file = bot_instance.export_to_excel()
    await update.message.reply_document(open(output_file, 'rb'))


# ---------------- Main ------------------

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
            MORE_FAMILY: [CallbackQueryHandler(more_family_handler, pattern='^more_')],
            SCREENSHOT: [MessageHandler(filters.PHOTO, screenshot_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('export_excel', export_excel))
    application.add_handler(CommandHandler('cancel', cancel))

    logger.info("Starting Contribution Bot...")
    application.run_polling()


if __name__ == '__main__':
    main()
