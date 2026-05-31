import discord
from discord.ext import commands
import random
import os
import ssl
import json
import aiohttp
from dotenv import load_dotenv
import certifi

# Load environment variables
load_dotenv()


# JSON data loading functions
def load_json_data(filename):
    """Load JSON data from the data directory with error handling."""
    try:
        filepath = os.path.join(os.path.dirname(__file__), 'data', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found in data directory!")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: {filename} contains invalid JSON!")
        return None
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return None


def configure_ssl_certificates():
    ca_bundle = certifi.where()
    os.environ.setdefault('SSL_CERT_FILE', ca_bundle)
    os.environ.setdefault('REQUESTS_CA_BUNDLE', ca_bundle)
    original_create_default_context = ssl.create_default_context

    def patched_create_default_context(*args, **kwargs):
        if not args and 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
            kwargs['cafile'] = ca_bundle
        return original_create_default_context(*args, **kwargs)

    ssl.create_default_context = patched_create_default_context
    ssl._create_default_https_context = patched_create_default_context


configure_ssl_certificates()


# API Helper Functions
async def fetch_cat_image():
    """Fetch a random cat image from TheCatAPI or CATAAS."""
    try:
        async with aiohttp.ClientSession() as session:
            # Try TheCatAPI first
            async with session.get('https://api.thecatapi.com/v1/images/search') as response:
                if response.status == 200:
                    data = await response.json()
                    return data[0]['url'] if data else None
    except:
        pass
    
    # Fallback to CATAAS
    try:
        return f"https://cataas.com/cat?{random.randint(1, 10000)}"
    except:
        return None


async def fetch_cat_fact():
    """Fetch a random cat fact from MeowFacts API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meowfacts.herokuapp.com/') as response:
                if response.status == 200:
                    data = await response.json()
                    return data['data'][0] if data and 'data' in data else None
    except:
        return None


async def fetch_random_emoji():
    """Fetch a random emoji from EmojiHub API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://emojihub.yurace.pro/api/random') as response:
                if response.status == 200:
                    data = await response.json()
                    emoji = data.get('htmlCode', [''])[0] if data else None
                    name = data.get('name', 'Random Emoji')
                    category = data.get('category', '')
                    if emoji:
                        # Convert HTML code to actual emoji
                        emoji_char = chr(int(emoji.replace('&#', '').replace(';', '')))
                        return f"{emoji_char} **{name}** ({category})"
                    return None
    except:
        return None


async def fetch_chuck_norris_joke():
    """Fetch a random Chuck Norris joke."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.chucknorris.io/jokes/random') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value')
    except:
        return None


async def fetch_random_joke():
    """Fetch a random joke from Official Joke API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://official-joke-api.appspot.com/random_joke') as response:
                if response.status == 200:
                    data = await response.json()
                    setup = data.get('setup', '')
                    punchline = data.get('punchline', '')
                    return f"{setup}\n{punchline}" if setup and punchline else None
    except:
        return None


configure_ssl_certificates()

# Load all data from JSON files
print("📂 Loading bot data from JSON files...")
quotes_data = load_json_data('quotes.json')
greetings_data = load_json_data('greetings.json')
jokes_data = load_json_data('jokes.json')
birthday_data = load_json_data('birthday.json')
memes_data = load_json_data('memes.json')
stickers_data = load_json_data('stickers.json')

# Extract data with fallback to empty lists if loading failed
SPEEDY_QUOTES = quotes_data.get('quotes', []) if quotes_data else []
MEOW_GREETS = greetings_data.get('greetings', []) if greetings_data else []
KNOCK_KNOCK_JOKES = jokes_data.get('jokes', []) if jokes_data else []
BIRTHDAY_MESSAGES = birthday_data.get('messages', []) if birthday_data else []
MEME_GIFS = memes_data.get('gifs', []) if memes_data else []
STICKER_GIFS = stickers_data if stickers_data else {}

# Validate loaded data
if not SPEEDY_QUOTES:
    print("⚠️  Warning: No quotes loaded!")
if not MEOW_GREETS:
    print("⚠️  Warning: No greetings loaded!")
if not KNOCK_KNOCK_JOKES:
    print("⚠️  Warning: No jokes loaded!")
if not BIRTHDAY_MESSAGES:
    print("⚠️  Warning: No birthday messages loaded!")
if not MEME_GIFS:
    print("⚠️  Warning: No meme GIFs loaded!")
if not STICKER_GIFS:
    print("⚠️  Warning: No sticker GIFs loaded!")
else:
    print(f"✅ Loaded {len(SPEEDY_QUOTES)} quotes, {len(MEOW_GREETS)} greetings, {len(KNOCK_KNOCK_JOKES)} jokes")
    print(f"✅ Loaded {len(BIRTHDAY_MESSAGES)} birthday messages, {len(MEME_GIFS)} meme GIFs")
    print(f"✅ Loaded {len(STICKER_GIFS)} sticker categories")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='', intents=intents)


@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is now online!')
    print(f'📝 Bot ID: {bot.user.id}')
    print(f'✅ Speedyuwu is ready to serve with {len(SPEEDY_QUOTES)} quotes and {len(STICKER_GIFS)} sticker commands!')


@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    content = message.content.lower().strip()
    
    # speedy command - Random quotes
    if content == 'speedy':
        if SPEEDY_QUOTES:
            quote = random.choice(SPEEDY_QUOTES)
            await message.channel.send(quote)
        else:
            await message.channel.send("⚠️ No quotes available!")
        return
    
    # meow command - Random greetings
    if content == 'meow':
        if MEOW_GREETS:
            greet = random.choice(MEOW_GREETS)
            await message.channel.send(greet)
        else:
            await message.channel.send("⚠️ No greetings available!")
        return
    
    # happy birthday command - Responds twice (exact match only)
    if content == 'happy birthday':
        if BIRTHDAY_MESSAGES:
            birthday_msg1 = random.choice(BIRTHDAY_MESSAGES)
            birthday_msg2 = random.choice(BIRTHDAY_MESSAGES)
            await message.channel.send(birthday_msg1)
            await message.channel.send(birthday_msg2)
            await message.channel.send("🎉 Double the wishes for double the happiness! Don't forget to throw a party! 🎊")
        else:
            await message.channel.send("⚠️ No birthday messages available!")
        return
    
    # knock knock command - Knock knock jokes
    if content == 'knock knock':
        if KNOCK_KNOCK_JOKES:
            joke = random.choice(KNOCK_KNOCK_JOKES)
            await message.channel.send(joke)
        else:
            await message.channel.send("⚠️ No jokes available!")
        return
    
    # smeme command - Random meme GIFs
    if content == 'smeme':
        if MEME_GIFS:
            meme = random.choice(MEME_GIFS)
            embed = discord.Embed(title="😂 Random Meme!", color=discord.Color.random())
            embed.set_image(url=meme)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ No meme GIFs available!")
        return
    
    # Sticker commands
    if content in STICKER_GIFS:
        stickers = STICKER_GIFS.get(content, [])
        if stickers:
            sticker = random.choice(stickers)
            embed = discord.Embed(color=discord.Color.random())
            embed.set_image(url=sticker)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(f"⚠️ No GIFs available for {content}!")
        return
    
    # API-based commands
    # scat - Random cat image
    if content == 'scat':
        cat_url = await fetch_cat_image()
        if cat_url:
            embed = discord.Embed(title="🐱 Random Cat Picture!", color=discord.Color.orange())
            embed.set_image(url=cat_url)
            embed.set_footer(text="Powered by TheCatAPI & CATAAS")
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a cat image right now. Try again!")
        return
    
    # catfact - Random cat fact
    if content == 'catfact':
        fact = await fetch_cat_fact()
        if fact:
            embed = discord.Embed(
                title="🐱 Cat Fact!",
                description=fact,
                color=discord.Color.blue()
            )
            embed.set_footer(text="Powered by MeowFacts")
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a cat fact right now. Try again!")
        return
    
    # semoji - Random emoji
    if content == 'semoji':
        emoji_info = await fetch_random_emoji()
        if emoji_info:
            embed = discord.Embed(
                title="✨ Random Emoji!",
                description=emoji_info,
                color=discord.Color.gold()
            )
            embed.set_footer(text="Powered by EmojiHub")
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch an emoji right now. Try again!")
        return
    
    # schuck - Chuck Norris joke
    if content == 'schuck':
        joke = await fetch_chuck_norris_joke()
        if joke:
            embed = discord.Embed(
                title="💪 Chuck Norris Joke",
                description=joke,
                color=discord.Color.red()
            )
            embed.set_footer(text="Powered by api.chucknorris.io")
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a Chuck Norris joke right now. Try again!")
        return
    
    # sjoke - Random joke
    if content == 'sjoke':
        joke = await fetch_random_joke()
        if joke:
            embed = discord.Embed(
                title="😄 Random Joke",
                description=joke,
                color=discord.Color.green()
            )
            embed.set_footer(text="Powered by Official Joke API")
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a joke right now. Try again!")
        return



# Run the bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("📝 Please create a .env file with your bot token.")
    else:
        bot.run(TOKEN)
