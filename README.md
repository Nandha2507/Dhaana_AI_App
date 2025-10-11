# Contribution Bot

**Contribution Bot** is a Telegram bot designed to help individuals and families easily record, manage, and track financial contributions. It allows users to log contributions for themselves or multiple family members, upload proof via screenshots, and organize the data by month and year.

## Features

- **Step-by-Step Conversation:** Guides users to select the year, month, and contribution type.  
- **Multiple Family Members:** Add multiple members with individual contributions and upload separate screenshots.  
- **Automated Screenshot Organization:** Screenshots are saved in month-specific folders for easy reference.  
- **Persistent Database:** Stores all contributions in a SQLite database including user names, amounts, and timestamps.  
- **Contribution Summary:** Provides a summary after submission, including year, month, member name, amount, and screenshot confirmation.  
- **Cancel & Restart:** Users can cancel a contribution at any time and restart using `/start`.  

## Installation

1. Clone the repository:

```bash
git clone https://github.com/<your-username>/contribution-bot.git
cd contribution-bot


2. Install dependencies:

pip install -r requirements.txt

3. Create a .env file in the root directory and add your Telegram bot token:

TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN


4. Run the Bot

Run the bot:

Deployment

The bot can be deployed on free hosting platforms such as Render, PythonAnywhere, or Railway to run 24/7. Make sure the environment variable TELEGRAM_BOT_TOKEN is configured on the platform.

Database

All contribution data is stored in a SQLite database named contributions.db in the project folder. Screenshots are saved in a screenshots/<Month> folder.

Usage

Start the bot on Telegram using /start.

Follow the conversation to select year, month, and contribution type.

Enter contribution amounts and upload screenshots.

For family contributions, you can add multiple members with individual screenshots.

After submission, the bot will provide a summary of all recorded contributions.

Tech Stack

Python

python-telegram-bot library

SQLite for storing contribution data

dotenv for environment variable management

License

This project is open-source and free to use.
