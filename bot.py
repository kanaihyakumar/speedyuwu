import discord
from discord.ext import commands
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='', intents=intents)

# Random quotes for 'speedy' command
SPEEDY_QUOTES = [
    "Speed is the essence of war! ⚡",
    "Fast and furious, that's how I roll! 🏎️",
    "Life's too short to be slow! 💨",
    "Catch me if you can! 😎",
    "Speedy gonzales at your service! 🐭",
    "Zoom zoom! Let's go! 🚀",
    "Time waits for no one! ⏰",
    "Gotta go fast! 💙",
    "Quick like a ninja! 🥷",
    "Speed is my middle name! ⚡️"
]

# Random greetings for 'meow' command
MEOW_GREETS = [
    "Meow meow! Hello there! 🐱",
    "Nya~ How are you doing? 😸",
    "Meow! *purrs* 🐾",
    "Hewwo! *waves paw* 🐱‍👤",
    "Meow meow! Nice to see you! 😺",
    "Nyaa~ *stretches* 🐱",
    "Meow! *headbutts gently* 😻",
    "Purr purr~ Hello! 🐈",
    "Meow! What's up? 😼",
    "*meows loudly* Hi there! 🐱‍🏍"
]

# Knock knock jokes
KNOCK_KNOCK_JOKES = [
    "Knock knock!\nWho's there?\nBoo.\nBoo who?\nDon't cry, it's just a joke! 😂",
    "Knock knock!\nWho's there?\nOrange.\nOrange who?\nOrange you glad I didn't say banana? 🍊",
    "Knock knock!\nWho's there?\nLettuce.\nLettuce who?\nLettuce in, it's cold out here! 🥬",
    "Knock knock!\nWho's there?\nCanoe.\nCanoe who?\nCanoe help me with my homework? 🛶",
    "Knock knock!\nWho's there?\nYo-yo.\nYo-yo who?\nYo-yo mama! 😄",
    "Knock knock!\nWho's there?\nAtch.\nAtch who?\nBless you! 🤧",
    "Knock knock!\nWho's there?\nInterrupting cow.\nInterrupting cow wh—\nMOOOO! 🐄",
    "Knock knock!\nWho's there?\nHoney bee.\nHoney bee who?\nHoney bee a dear and get me some water! 🐝"
]

# Birthday messages
BIRTHDAY_MESSAGES = [
    "🎂 HAPPY BIRTHDAY! 🎉 Wishing you an amazing day filled with joy and cake! 🎈",
    "🎊 Happy Birthday! 🎁 May all your wishes come true! 🌟",
    "🎉 HAPPY BIRTHDAY! 🥳 Have a fantastic celebration! 🎂",
    "🎈 Wishing you the happiest of birthdays! 🎊 Enjoy your special day! 🎁"
]

# Meme GIFs (using Tenor GIF URLs)
MEME_GIFS = [
    "https://media.tenor.com/images/f9c52b58f210da99e7c2a6e6b4b0b0c5/tenor.gif",
    "https://media.tenor.com/images/8d3f8b8f8b8f8b8f8b8f8b8f8b8f8b8f/tenor.gif",
    "https://media1.tenor.com/m/3OZLfZUeeEAAAAAC/laugh-laughing.gif",
    "https://media1.tenor.com/m/kHcmsWBJsKgAAAAC/laugh-funny.gif",
    "https://media1.tenor.com/m/lx2WSGRk8bcAAAAC/coding-hacking.gif",
    "https://media1.tenor.com/m/Xvth4PiN9bwAAAAC/cat-computer.gif"
]

# Sticker/reaction GIFs for mood commands
STICKER_GIFS = {
    "smood": [
        "https://media1.tenor.com/m/t8YHcaK2BlQAAAAC/mood-vibes.gif",
        "https://media1.tenor.com/m/x8v-m8ENfellows-AAAAC/mood.gif"
    ],
    "skitty": [
        "https://media1.tenor.com/m/D3RqWnWxcK0AAAAC/kitty-cat.gif",
        "https://media1.tenor.com/m/nBB2DGkPQwcAAAAC/cat-cute.gif"
    ],
    "scry": [
        "https://media1.tenor.com/m/mYnJd4w4X0YAAAAC/cry-crying.gif",
        "https://media1.tenor.com/m/7w7p8TqxdowAAAAC/sad-cry.gif"
    ],
    "ssmile": [
        "https://media1.tenor.com/m/ZbGT63X-VFUAAAAC/smile-happy.gif",
        "https://media1.tenor.com/m/4Zzu0VI8HggAAAAC/smile-smiling.gif"
    ],
    "sblush": [
        "https://media1.tenor.com/m/bDLWjx8wOv8AAAAC/blush-shy.gif",
        "https://media1.tenor.com/m/AyVv4bh-rEMAAAAC/anime-blush.gif"
    ],
    "sdance": [
        "https://media1.tenor.com/m/0UAl-3lBbVEAAAAC/dance-dancing.gif",
        "https://media1.tenor.com/m/sNOp8p56gc0AAAAC/happy-dance.gif"
    ],
    "ssleepy": [
        "https://media1.tenor.com/m/0TfhzJqpJfgAAAAC/sleepy-tired.gif",
        "https://media1.tenor.com/m/GCNV1cCv5WAAAAAC/sleep-sleeping.gif"
    ],
    "sthink": [
        "https://media1.tenor.com/m/JmQLz2I_y_sAAAAC/think-thinking.gif",
        "https://media1.tenor.com/m/1VVDMK-ys7wAAAAC/hmm-thinking.gif"
    ],
    "shappy": [
        "https://media1.tenor.com/m/JWhrzkAfbgkAAAAC/happy-excited.gif",
        "https://media1.tenor.com/m/AW3cwFY6RU8AAAAC/happy-joy.gif"
    ],
    "skiss": [
        "https://media1.tenor.com/m/f2H9ijHw-7sAAAAC/kiss-blow-kiss.gif",
        "https://media1.tenor.com/m/Ja8VXnXzR4cAAAAC/kiss-anime.gif"
    ],
    "shug": [
        "https://media1.tenor.com/m/CqWC0wlYc8YAAAAC/hug-hugs.gif",
        "https://media1.tenor.com/m/gH6F0K3y5G0AAAAC/hug-anime.gif"
    ],
    "sfight": [
        "https://media1.tenor.com/m/jBHFaYq8LnAAAAAC/fight-fighting.gif",
        "https://media1.tenor.com/m/2cKzNnrWRxEAAAAC/anime-fight.gif"
    ]
}


@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is now online!')
    print(f'📝 Bot ID: {bot.user.id}')
    print('✅ Speedyuwu is ready to serve!')


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    content = message.content.lower()
    
    # speedy command - Random quotes
    if content == 'speedy':
        quote = random.choice(SPEEDY_QUOTES)
        await message.channel.send(quote)
    
    # meow command - Random greetings
    elif content == 'meow':
        greet = random.choice(MEOW_GREETS)
        await message.channel.send(greet)
    
    # happy birthday command - Responds twice
    elif 'happy birthday' in content:
        birthday_msg1 = random.choice(BIRTHDAY_MESSAGES)
        birthday_msg2 = random.choice(BIRTHDAY_MESSAGES)
        await message.channel.send(birthday_msg1)
        await message.channel.send(birthday_msg2)
        await message.channel.send("🎉 Double the wishes for double the happiness! Don't forget to throw a party! 🎊")
    
    # knock knock command - Knock knock jokes
    elif content == 'knock knock':
        joke = random.choice(KNOCK_KNOCK_JOKES)
        await message.channel.send(joke)
    
    # smeme command - Random meme GIFs
    elif content == 'smeme':
        meme = random.choice(MEME_GIFS)
        embed = discord.Embed(title="😂 Random Meme!", color=discord.Color.random())
        embed.set_image(url=meme)
        await message.channel.send(embed=embed)
    
    # Sticker commands
    elif content in STICKER_GIFS:
        sticker = random.choice(STICKER_GIFS[content])
        embed = discord.Embed(color=discord.Color.random())
        embed.set_image(url=sticker)
        await message.channel.send(embed=embed)


# Run the bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("📝 Please create a .env file with your bot token.")
    else:
        bot.run(TOKEN)
