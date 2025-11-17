# Telegram Contribution Bot

A Telegram bot to help users record contributions (self or family members) and export the data to Excel. Built with Python, `python-telegram-bot`, `Flask`, and `SQLite`.

## Features

- Record contributions for self or family members
- Upload screenshots for verification
- Admins can export all contributions to Excel
- Tracks contributions by year and month
- Flask web server to keep the bot alive on platforms like Render

## Technologies Used

- Python 3.10+
- `python-telegram-bot` for Telegram integration
- `Flask` for web server
- `SQLite` for local database storage
- `pandas` for Excel export
- `python-dotenv` for environment variable management

## Setup

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/contribution-bot.git
cd contribution-bot
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

5. **Run the bot:**

```bash
python bot.py
```

The bot will start polling Telegram updates and run a Flask server for uptime monitoring.

## Usage

- Start the bot with `/start`.
- Follow the prompts to record contributions:
  - Select year
  - Select month
  - Choose contribution type (self or family)
  - Enter family member names and amounts (if applicable)
  - Upload screenshot
- Admins can export all contributions to Excel using `/export_excel`.

## File Structure

```
.
├── bot.py                 # Main bot script
├── contributions.db       # SQLite database (auto-created)
├── screenshots/           # Folder to save uploaded screenshots
├── exports/               # Folder to save Excel exports
├── requirements.txt       # Python dependencies
└── README.md
```

## Admins

Add Telegram user IDs in `ADMINS` list in `bot.py` to allow access to `/export_excel` functionality.

```python
ADMINS = [1255111776, 7854166119]  # Replace with actual admin IDs
```

## Contributing

1. Fork the repository
2. Create a branch (`git checkout -b feature-name`)
3. Make your changes
4. Commit (`git commit -m "Add feature"`)
5. Push (`git push origin feature-name`)
6. Open a Pull Request


