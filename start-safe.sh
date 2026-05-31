#!/bin/bash
# Safe bot starter - prevents multiple instances

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BOT_DIR"

# Check if bot is already running
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "   Process ID(s): $(pgrep -f 'python.*bot.py')"
    echo ""
    echo "To stop the bot, run: ./stop.sh"
    echo "Or manually: pkill -f 'bot.py'"
    exit 1
fi

echo "🚀 Starting Speedyuwu bot..."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please create a .env file with your DISCORD_BOT_TOKEN"
    exit 1
fi

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import discord" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Run the bot
echo "✅ Starting bot in background..."
nohup python3 bot.py > bot.log 2>&1 &
BOT_PID=$!

sleep 2

# Check if bot started successfully
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Bot started successfully! (PID: $BOT_PID)"
    echo "📝 Logs are being written to bot.log"
    echo ""
    echo "To view logs: tail -f bot.log"
    echo "To stop bot: ./stop.sh"
else
    echo "❌ Bot failed to start. Check bot.log for errors."
    exit 1
fi
