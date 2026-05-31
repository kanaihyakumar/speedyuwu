# Speedyuwu Discord Bot 🚀

A fun and interactive Discord bot with random quotes, greetings, birthday wishes, jokes, memes, and reaction stickers!

## Features ✨

### Commands:
- **`speedy`** - Get a random motivational speed quote
- **`meow`** - Receive a cute cat greeting
- **`happy birthday`** - Get double birthday wishes (responds twice!)
- **`knock knock`** - Hear a random knock-knock joke
- **`smeme`** - Get a random funny meme GIF

### Sticker/Reaction Commands:
- **`smood`** - Show your mood
- **`skitty`** - Display cute kitty GIFs
- **`scry`** - Express sadness
- **`ssmile`** - Share a smile
- **`sblush`** - Show embarrassment
- **`sdance`** - Dance celebration
- **`ssleepy`** - Feeling sleepy
- **`sthink`** - Thinking hard
- **`shappy`** - Express happiness
- **`skiss`** - Send virtual kisses
- **`shug`** - Give warm hugs
- **`sfight`** - Battle mode!

## Setup Instructions 🛠️

### Prerequisites:
- Python 3.8 or higher
- A Discord account
- A Discord server where you have admin permissions

### Step 1: Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it "Speedyuwu"
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT (optional)
5. Click "Reset Token" and copy your bot token (keep it secret!)

### Step 2: Invite Bot to Your Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ `bot`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Read Messages/View Channels
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Step 4: Configure Bot Token

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and paste your bot token:
   ```
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   ```

### Step 5: Run the Bot

```bash
python bot.py
```

You should see:
```
🚀 Speedyuwu#1234 is now online!
📝 Bot ID: 123456789
✅ Speedyuwu is ready to serve!
```

## Hosting Options 🌐

### 1. **Replit** (Free & Easy)
   - Go to [Replit](https://replit.com/)
   - Create new Repl, select Python
   - Upload your files
   - Add `DISCORD_BOT_TOKEN` to Secrets (lock icon)
   - Click Run
   - Use UptimeRobot or similar to ping your Repl URL to keep it alive

### 2. **Railway.app** (Recommended)
   - Sign up at [Railway.app](https://railway.app/)
   - Connect your GitHub repo or upload files
   - Add `DISCORD_BOT_TOKEN` environment variable
   - Deploy automatically
   - Free $5/month credit

### 3. **Heroku**
   - Create `Procfile`: `worker: python bot.py`
   - Deploy to Heroku
   - Set config vars for bot token
   - Enable worker dyno

### 4. **Your Computer** (24/7)
   - Run `python bot.py`
   - Keep your computer on
   - Use `nohup` or `screen` on Linux/Mac

## Usage 💬

Just type the commands in any channel where the bot has access:

```
meow
→ Meow meow! Hello there! 🐱

speedy
→ Speed is the essence of war! ⚡

happy birthday
→ 🎂 HAPPY BIRTHDAY! 🎉 Wishing you an amazing day filled with joy and cake! 🎈
→ 🎊 Happy Birthday! 🎁 May all your wishes come true! 🌟
→ 🎉 Double the wishes for double the happiness! Don't forget to throw a party! 🎊

knock knock
→ Knock knock!
  Who's there?
  Boo.
  Boo who?
  Don't cry, it's just a joke! 😂

smeme
→ [Random funny meme GIF]

sdance
→ [Dancing GIF]
```

## Customization 🎨

### Adding More Quotes/Jokes:
Edit [bot.py](bot.py) and add items to these lists:
- `SPEEDY_QUOTES` - Add more speed quotes
- `MEOW_GREETS` - Add more cat greetings
- `KNOCK_KNOCK_JOKES` - Add more jokes
- `BIRTHDAY_MESSAGES` - Add more birthday wishes
- `MEME_GIFS` - Add more meme GIF URLs
- `STICKER_GIFS` - Add more reaction GIF URLs

### Adding New Commands:
Add new conditions in the `on_message` event handler.

## Troubleshooting 🔧

### Bot is offline:
- Check if your bot token is correct in `.env`
- Verify intents are enabled in Discord Developer Portal
- Ensure the bot is invited to your server

### Commands not working:
- Make sure MESSAGE CONTENT INTENT is enabled
- Check bot has permissions to read and send messages
- Type commands in lowercase exactly as shown

### GIFs not displaying:
- Ensure bot has "Embed Links" permission
- Check if GIF URLs are still valid
- Try updating GIF URLs from Tenor or Giphy

## Support 📧

For suggestions or issues, DM to: **speedy_speedy**

## License 📄

Free to use and modify for personal or educational purposes!

---

Made with ❤️ for Discord communities
