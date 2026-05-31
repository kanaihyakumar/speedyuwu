#!/bin/bash
# Stop the bot safely

echo "🛑 Stopping Speedyuwu bot..."

if pgrep -f "python.*bot.py" > /dev/null; then
    pkill -f "python.*bot.py"
    sleep 1
    
    # Check if it's still running
    if pgrep -f "python.*bot.py" > /dev/null; then
        echo "⚠️  Bot didn't stop gracefully, forcing..."
        pkill -9 -f "python.*bot.py"
        sleep 1
    fi
    
    echo "✅ Bot stopped successfully!"
else
    echo "ℹ️  Bot is not running"
fi
