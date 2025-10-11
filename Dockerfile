FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create screenshots directory
RUN mkdir -p screenshots

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "contribution_bot.py"]