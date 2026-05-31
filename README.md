# Speedyuwu Discord Bot 🚀

A fun and interactive Discord bot with random quotes, greetings, birthday wishes, jokes, memes, reaction stickers, and **live API integrations** for cat pictures, cat facts, emojis, and jokes! All content is stored in easy-to-edit JSON files for simple customization.

## Features ✨

### Text Commands:
- **`speedy`** - Get a random motivational speed quote (40 variations!)
- **`meow`** - Receive a cute cat greeting (35 variations!)
- **`happy birthday`** - Get double birthday wishes (responds twice, 12 messages!)
- **`knock knock`** - Hear a random knock-knock joke (25 jokes!)

### Media Commands:
- **`smeme`** - Get a random funny meme GIF (30 GIFs!)

### 🆕 API-Powered Commands:
- **`scat`** - Get a random cat picture from TheCatAPI 🐱📸
- **`catfact`** - Learn interesting cat facts from MeowFacts 🐾
- **`semoji`** - Get a random emoji with info from EmojiHub ✨
- **`sjoke`** - Hear a random joke from Official Joke API 😄
- **`schuck`** - Get a Chuck Norris joke 💪

### Sticker/Reaction Commands:
- **`smood`** - Show your mood (10 GIFs)
- **`skitty`** - Display cute kitty GIFs (10 GIFs)
- **`scry`** - Express sadness (10 GIFs)
- **`ssmile`** - Share a smile (10 GIFs)
- **`sblush`** - Show embarrassment (10 GIFs)
- **`sdance`** - Dance celebration (10 GIFs)
- **`ssleepy`** - Feeling sleepy (10 GIFs)
- **`sthink`** - Thinking hard (10 GIFs)
- **`shappy`** - Express happiness (10 GIFs)
- **`skiss`** - Send virtual kisses (10 GIFs)
- **`shug`** - Give warm hugs (10 GIFs)
- **`sfight`** - Battle mode! (10 GIFs)

**Total Content:** 40 quotes + 35 greetings + 25 jokes + 12 birthday messages + 30 memes + 120 sticker GIFs + **∞ Live API content** = **262+ unique responses!**

## Setup Instructions 🛠️

### Prerequisites:
- Python 3.8 or higher
- A Discord account
- A Discord server where you have admin permissions

### Quick Start:

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file with your bot token:**
   ```
   DISCORD_BOT_TOKEN=your_token_here
   ```

4. **Start the bot:**
   ```bash
   # Safe start (prevents multiple instances)
   ./start-safe.sh
   
   # Or manually
   python3 bot.py
   ```

5. **Stop the bot:**
   ```bash
   ./stop.sh
   ```

### Helper Scripts:
- **`start-safe.sh`** - Safely starts the bot, prevents duplicate instances
- **`stop.sh`** - Stops all bot instances
- **`start.sh`** - Original start script (simple)

## Usage 💬

Just type the commands in any channel where the bot has access:

### Static Content Examples:
```
meow
→ Meow meow! Hello there! 🐱

speedy
→ Speed is the essence of war! ⚡

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

### 🆕 API-Powered Examples:
```
scat
→ [Beautiful random cat picture from TheCatAPI]

catfact
→ 🐱 Cat Fact!
  "A cat's purr vibrates at a frequency of 25 to 150 hertz, which is the same frequency at which muscles and bones repair themselves."

semoji
→ ✨ Random Emoji!
  🎉 Party Popper (activities)

sjoke
→ 😄 Random Joke
  Why don't scientists trust atoms?
  Because they make up everything!

schuck
→ 💪 Chuck Norris Joke
  Chuck Norris can divide by zero.
```

## Project Structure 📁

```
speedyuwu/
├── bot.py              # Main bot code
├── data/               # JSON data files (easy to edit!)
│   ├── quotes.json     # 40 speed quotes
│   ├── greetings.json  # 35 cat greetings
│   ├── jokes.json      # 25 knock-knock jokes
│   ├── birthday.json   # 12 birthday messages
│   ├── memes.json      # 30 meme GIF URLs
│   └── stickers.json   # 120 sticker GIFs (12 categories × 10)
├── .env                # Bot token (create this)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Customization 🎨

### Easy Way: Edit JSON Files (Recommended!)

All bot content is now stored in easy-to-edit JSON files in the `data/` folder. You can add, remove, or modify content without touching Python code!

#### Adding More Quotes:
Edit `data/quotes.json`:
```json
{
  "quotes": [
    "Speed is the essence of war! ⚡",
    "Your new quote here! 🚀",
    "Add as many as you want! 💨"
  ]
}
```

#### Adding More Greetings:
Edit `data/greetings.json`:
```json
{
  "greetings": [
    "Meow meow! Hello there! 🐱",
    "Your custom greeting! 😸"
  ]
}
```

#### Adding More Jokes:
Edit `data/jokes.json`:
```json
{
  "jokes": [
    "Knock knock!\nWho's there?\nYour setup.\nYour setup who?\nYour punchline! 😂"
  ]
}
```

#### Adding More Birthday Messages:
Edit `data/birthday.json`:
```json
{
  "messages": [
    "🎂 HAPPY BIRTHDAY! 🎉",
    "Your custom birthday wish! 🎈"
  ]
}
```

#### Adding More Meme GIFs:
Edit `data/memes.json`:
```json
{
  "gifs": [
    "https://media.giphy.com/media/YOUR_GIPHY_ID/giphy.gif",
    "Add more Giphy GIF URLs here!"
  ]
}
```

#### Adding More Sticker GIFs:
Edit `data/stickers.json`:
```json
{
  "smood": [
    "https://media.giphy.com/media/GIPHY_ID_1/giphy.gif",
    "https://media.giphy.com/media/GIPHY_ID_2/giphy.gif"
  ],
  "skitty": [
    "https://media.giphy.com/media/GIPHY_ID_3/giphy.gif"
  ]
}
```

### Finding Working GIF URLs:

1. Go to [giphy.com](https://giphy.com)
2. Search for your desired GIF (e.g., "happy dance")
3. Click on a GIF you like
4. Right-click the GIF → "Copy image address"
5. Paste the URL into your JSON file

**Valid URL format:** `https://media.giphy.com/media/[ID]/giphy.gif`

⚠️ **Don't use Tenor URLs** - They're deprecated and return 404 errors. Use Giphy instead!

### Adding New Commands:

To add completely new commands, edit `bot.py` and add new conditions in the `on_message` event handler.

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
- Check if GIF URLs are still valid (test in browser)
- Use valid Tenor URL format: `https://media1.tenor.com/m/[ID]/[name].gif`
- Avoid old/broken placeholder URLs

### JSON Loading Errors:
- Check JSON syntax is valid (use [jsonlint.com](https://jsonlint.com))
- Ensure all JSON files exist in `data/` folder
- Check file encoding is UTF-8
- Look for error messages in bot startup logs

### API Commands Not Working:
- Check your internet connection
- APIs are free and require no authentication
- Bot will show error messages if APIs are unreachable
- Each API call has a fallback error message
- Try again after a few seconds if an API is temporarily down

### Bot Responding Multiple Times:
- **Check for multiple bot instances:** Run `ps aux | grep bot.py`
- **Stop all instances:** Run `./stop.sh` or `pkill -f bot.py`
- **Start safely:** Use `./start-safe.sh` to prevent multiple instances
- **Fixed in v2.1:** Commands now use `return` to prevent fall-through

## Content Statistics 📊

- **Speed Quotes:** 40 unique motivational messages
- **Cat Greetings:** 35 varied meow greetings
- **Knock-Knock Jokes:** 25 family-friendly jokes
- **Birthday Messages:** 12 celebratory wishes
- **Meme GIFs:** 30 curated funny GIFs from Tenor
- **Sticker GIFs:** 120 reaction GIFs (10 per category × 12 categories)
- **🆕 API-Powered Content:** Unlimited cat pictures, facts, emojis, and jokes!
- **Total Responses:** 262 static + ∞ API content!

## Technical Details 🔧

### Bot Features:
- **JSON-based content:** Easy customization without coding
- **Live API integrations:** Fresh cat pictures, facts, jokes, and emojis
- **Async API calls:** Non-blocking, fast responses using aiohttp
- **Error handling:** Graceful fallbacks if JSON files are missing or APIs are down
- **SSL certificate handling:** Works on macOS and other systems
- **Validation on startup:** Reports missing or invalid data
- **Random selection:** Fresh responses every time
- **Embed formatting:** Professional display for media and API content

### Integrated APIs:
All APIs are **free and require no authentication**:

1. **TheCatAPI** - Random cat pictures
   - URL: https://api.thecatapi.com/
   - Fallback: CATAAS (https://cataas.com/)

2. **MeowFacts** - Interesting cat facts
   - URL: https://meowfacts.herokuapp.com/

3. **EmojiHub** - Random emojis with categories
   - URL: https://emojihub.yurace.pro/

4. **Official Joke API** - Random jokes
   - URL: https://official-joke-api.appspot.com/

5. **Chuck Norris API** - Chuck Norris jokes
   - URL: https://api.chucknorris.io/

### GIF Sources:
All GIFs are sourced from [Giphy](https://giphy.com) using direct CDN URLs. This ensures:
- ✅ Fast loading times
- ✅ No API key required
- ✅ Reliable hosting with stable URLs
- ✅ No rate limits
- ✅ High-quality GIFs that actually work in Discord

**Note:** Previously used Tenor URLs (format: `media1.tenor.com/m/...`) are deprecated and will return 404 errors. All GIFs have been migrated to Giphy's stable CDN.

## Updates & Changelog 📝

### v2.1 - API Integration (Latest)
- 🌐 **NEW:** Integrated 5 free APIs for dynamic content
- 🐱 **NEW:** `scat` command - Random cat pictures from TheCatAPI
- 📚 **NEW:** `catfact` command - Interesting cat facts
- ✨ **NEW:** `semoji` command - Random emojis with info
- 😄 **NEW:** `sjoke` command - Random jokes from Official Joke API
- 💪 **NEW:** `schuck` command - Chuck Norris jokes
- ⚡ Async API calls using aiohttp for fast responses
- 🛡️ Error handling with fallbacks for API failures
- 📦 Added aiohttp dependency

### v2.0 - JSON Data Structure
- ✨ Moved all content to JSON files for easy editing
- 🎨 Expanded content: 40 quotes, 35 greetings, 25 jokes, 12 birthday messages
- 🖼️ Fixed broken GIF URLs with working Tenor links
- 📦 Added 30 meme GIFs and 120 sticker GIFs (10 per category)
- 🛡️ Added error handling and data validation
- 📊 Added startup logs showing loaded content

### v1.0 - Initial Release
- Basic commands with hardcoded content
- 10 quotes, 10 greetings, 8 jokes, 4 birthday messages
- 6 meme GIFs, 2 GIFs per sticker category

## Contributing 🤝

Feel free to:
- Add more content to JSON files
- Suggest new commands or APIs
- Report broken GIF URLs
- Share your customizations

## 📚 Additional Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[COMMANDS.md](COMMANDS.md)** - Complete command reference
- **[API_INTEGRATION.md](API_INTEGRATION.md)** - API implementation details
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

## Support 📧

For suggestions or issues, DM to: **speedy_speedy**

## License 📄

Free to use and modify for personal or educational purposes!

---

Made with ❤️ for Discord communities
