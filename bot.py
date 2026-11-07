import os
import random
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from speedy import api  # noqa: E402
from speedy.core import ScoreStore, configure_ssl_certificates, load_json_data  # noqa: E402
from speedy.session import SessionManager  # noqa: E402

configure_ssl_certificates()

print('📂 Loading bot data from JSON files...')
quotes_data = load_json_data('quotes.json')
greetings_data = load_json_data('greetings.json')
jokes_data = load_json_data('jokes.json')
birthday_data = load_json_data('birthday.json')
memes_data = load_json_data('memes.json')
stickers_data = load_json_data('stickers.json')

SPEEDY_QUOTES = quotes_data.get('quotes', []) if quotes_data else []
MEOW_GREETS = greetings_data.get('greetings', []) if greetings_data else []
KNOCK_KNOCK_JOKES = jokes_data.get('jokes', []) if jokes_data else []
BIRTHDAY_MESSAGES = birthday_data.get('messages', []) if birthday_data else []
MEME_GIFS = memes_data.get('gifs', []) if memes_data else []
STICKER_GIFS = stickers_data if stickers_data else {}

for label, items in [('quotes', SPEEDY_QUOTES), ('greetings', MEOW_GREETS), ('jokes', KNOCK_KNOCK_JOKES),
                     ('birthday messages', BIRTHDAY_MESSAGES), ('meme GIFs', MEME_GIFS), ('sticker GIFs', STICKER_GIFS)]:
    if not items:
        print(f'⚠️  Warning: No {label} loaded!')
print(f'✅ Loaded {len(SPEEDY_QUOTES)} quotes, {len(MEOW_GREETS)} greetings, {len(KNOCK_KNOCK_JOKES)} jokes, '
      f'{len(BIRTHDAY_MESSAGES)} birthday messages, {len(MEME_GIFS)} meme GIFs, {len(STICKER_GIFS)} sticker categories')

EXTENSIONS = ('speedy.cogs.help', 'speedy.cogs.games', 'speedy.cogs.fun', 'speedy.cogs.maths')


async def send_random_text(message, pool, empty_text):
    await message.channel.send(random.choice(pool) if pool else empty_text)


async def classic_birthday(message):
    if not BIRTHDAY_MESSAGES:
        return await message.channel.send('⚠️ No birthday messages available!')
    await message.channel.send(random.choice(BIRTHDAY_MESSAGES))
    await message.channel.send(random.choice(BIRTHDAY_MESSAGES))
    await message.channel.send("🎉 Double the wishes for double the happiness! Don't forget to throw a party! 🎊")


async def classic_meme(message):
    if not MEME_GIFS:
        return await message.channel.send('⚠️ No meme GIFs available!')
    embed = discord.Embed(title='😂 Random Meme!', color=discord.Color.random())
    embed.set_image(url=random.choice(MEME_GIFS))
    await message.channel.send(embed=embed)


def api_command(fetcher, title, color, source, failure, description=False):
    async def handler(message):
        result = await fetcher()
        if not result:
            return await message.channel.send(failure)
        embed = discord.Embed(title=title, color=color)
        if description:
            embed.description = result
        else:
            embed.set_image(url=result)
        embed.set_footer(text=f'Powered by {source}')
        await message.channel.send(embed=embed)
    return handler


CLASSIC_HANDLERS = {
    'speedy': lambda m: send_random_text(m, SPEEDY_QUOTES, '⚠️ No quotes available!'),
    'meow': lambda m: send_random_text(m, MEOW_GREETS, '⚠️ No greetings available!'),
    'happy birthday': classic_birthday,
    'knock knock': lambda m: send_random_text(m, KNOCK_KNOCK_JOKES, '⚠️ No jokes available!'),
    'smeme': classic_meme,
    'scat': api_command(api.fetch_cat_image, '🐱 Random Cat Picture!', discord.Color.orange(), 'TheCatAPI & CATAAS',
                        "⚠️ Couldn't fetch a cat image right now. Try again!"),
    'catfact': api_command(api.fetch_cat_fact, '🐱 Cat Fact!', discord.Color.blue(), 'MeowFacts',
                           "⚠️ Couldn't fetch a cat fact right now. Try again!", description=True),
    'semoji': api_command(api.fetch_random_emoji, '✨ Random Emoji!', discord.Color.gold(), 'EmojiHub',
                          "⚠️ Couldn't fetch an emoji right now. Try again!", description=True),
    'schuck': api_command(api.fetch_chuck_norris_joke, '💪 Chuck Norris Joke', discord.Color.red(), 'api.chucknorris.io',
                          "⚠️ Couldn't fetch a Chuck Norris joke right now. Try again!", description=True),
    'sjoke': api_command(api.fetch_random_joke, '😄 Random Joke', discord.Color.green(), 'Official Joke API',
                         "⚠️ Couldn't fetch a joke right now. Try again!", description=True),
}


class SpeedyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix='',
            intents=intents,
            case_insensitive=True,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False),
        )
        self.sessions = SessionManager()
        self.scores = ScoreStore()
        self.sticker_names = sorted(STICKER_GIFS)

    async def setup_hook(self):
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        print(f'✅ Loaded {len(self.commands)} commands from {len(EXTENSIONS)} modules')

    async def close(self):
        await api.close_session()
        await super().close()

    async def on_ready(self):
        print(f'🚀 {self.user} is now online!')
        print(f'📝 Bot ID: {self.user.id}')
        await self.change_presence(activity=discord.Game(name='shelp • splay • smath'))

    def is_known_command(self, content):
        if content in CLASSIC_HANDLERS or content in STICKER_GIFS:
            return True
        return self.get_command(content.split(' ', 1)[0]) is not None

    async def on_message(self, message):
        if message.author.bot:
            return
        content = message.content.strip().lower()
        if not content:
            return

        # Plain chat ("23", "a", "crane") feeds the running game, unless it is a real command.
        if not self.is_known_command(content):
            session = self.sessions.get(message.channel.id)
            if session and await session.handle_message(message):
                return
            games = self.get_cog('Games')
            if games and await games.natural_start(message):
                return

        if content in CLASSIC_HANDLERS:
            return await CLASSIC_HANDLERS[content](message)

        if content in STICKER_GIFS:
            stickers = STICKER_GIFS.get(content, [])
            if stickers:
                embed = discord.Embed(color=discord.Color.random())
                embed.set_image(url=random.choice(stickers))
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f'⚠️ No GIFs available for {content}!')
            return

        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f'⏳ Easy there! Try again in {error.retry_after:.0f}s.', delete_after=5)
        if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument, commands.UserInputError)):
            return await ctx.send('🤔 I did not understand that. Type `shelp` to see how it works.')
        if isinstance(error, commands.CheckFailure):
            return
        original = getattr(error, 'original', error)
        traceback.print_exception(type(original), original, original.__traceback__)
        try:
            await ctx.send('💥 Oops, something went wrong on my side. Please try again!')
        except discord.HTTPException:
            pass


bot = SpeedyBot()

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('❌ Error: DISCORD_BOT_TOKEN not found in environment variables!')
        print('📝 Please create a .env file with your bot token.')
    else:
        bot.run(token)
