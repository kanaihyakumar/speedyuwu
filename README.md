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
