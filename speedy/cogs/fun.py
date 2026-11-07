"""Fun stuff: animal pics, anime reaction GIFs, facts, memes, Pokédex and tiny random tools."""
import random
import re

import discord
from discord.ext import commands

from .. import api
from ..core import PALETTE, load_json_data, random_color

FUN = load_json_data('fun.json') or {}

# action -> (sentence with a target, sentence without one)
ACTIONS = {
    'hug': ('{a} hugs {b} 🤗', '{a} wants a hug 🤗'),
    'pat': ('{a} pats {b} 🥰', '{a} would love some head pats 🥰'),
    'cuddle': ('{a} cuddles {b} 🧸', '{a} needs a cuddle 🧸'),
    'kiss': ('{a} sends a kiss to {b} 😘', '{a} blows a kiss 😘'),
    'slap': ('{a} slaps {b} 👋', '{a} slaps the air 👋'),
    'poke': ('{a} pokes {b} 👉', '{a} pokes around 👉'),
    'bite': ('{a} bites {b} 😬', '{a} bites… nothing 😬'),
    'tickle': ('{a} tickles {b} 🤭', '{a} is feeling tickly 🤭'),
    'highfive': ('{a} high-fives {b} 🙌', '{a} is looking for a high five 🙌'),
    'wave': ('{a} waves at {b} 👋', '{a} waves hello 👋'),
    'handhold': ('{a} holds hands with {b} 🤝', '{a} wants to hold hands 🤝'),
    'bonk': ('{a} bonks {b} 🔨', '{a} bonks the air 🔨'),
    'yeet': ('{a} yeets {b} 🚀', '{a} yeets something 🚀'),
    'kick': ('{a} kicks {b} 🦵', '{a} kicks the air 🦵'),
    'punch': ('{a} punches {b} 🥊', '{a} throws a punch 🥊'),
    'wink': ('{a} winks at {b} 😉', '{a} winks 😉'),
    'nom': ('{a} nom-noms {b} 😋', '{a} goes nom nom 😋'),
    'stare': ('{a} stares at {b} 👀', '{a} stares into the void 👀'),
    'facepalm': ('{a} facepalms at {b} 🤦', '{a} facepalms 🤦'),
    'shrug': ('{a} shrugs at {b} 🤷', '{a} shrugs 🤷'),
    'smug': ('{a} is smug at {b} 😏', '{a} feels smug 😏'),
    'bored': ('{a} is bored with {b} 🥱', '{a} is bored 🥱'),
    'dance': ('{a} dances with {b} 💃', '{a} dances 💃'),
    'cry': ('{a} cries on {b} 😭', '{a} cries 😭'),
    'laugh': ('{a} laughs at {b} 😂', '{a} laughs 😂'),
    'blush': ('{a} blushes at {b} 😊', '{a} blushes 😊'),
    'smile': ('{a} smiles at {b} 😄', '{a} smiles 😄'),
    'happy': ('{a} is happy with {b} 😁', '{a} is happy 😁'),
    'sleep': ('{a} falls asleep on {b} 😴', '{a} falls asleep 😴'),
    'think': ('{a} thinks about {b} 🤔', '{a} thinks 🤔'),
    'thumbsup': ('{a} gives {b} a thumbs up 👍', '{a} gives a thumbs up 👍'),
}

TYPE_COLORS = {
    'fire': 0xF08030, 'water': 0x6890F0, 'grass': 0x78C850, 'electric': 0xF8D030, 'psychic': 0xF85888, 'ice': 0x98D8D8,
    'dragon': 0x7038F8, 'dark': 0x705848, 'fairy': 0xEE99AC, 'normal': 0xA8A878, 'fighting': 0xC03028, 'flying': 0xA890F0,
    'poison': 0xA040A0, 'ground': 0xE0C068, 'rock': 0xB8A038, 'bug': 0xA8B820, 'ghost': 0x705898, 'steel': 0xB8B8D0,
}


def image_embed(title, url, color=None, footer=None, description=None):
    embed = discord.Embed(title=title, description=description, color=color or random_color())
    embed.set_image(url=url)
    if footer:
        embed.set_footer(text=footer)
    return embed


class BackView(discord.ui.View):
    def __init__(self, cog, action, giver, target):
        super().__init__(timeout=180)
        self.cog, self.action, self.giver, self.target = cog, action, giver, target
        button = discord.ui.Button(label=f'{action.title()} back', emoji='↩️', style=discord.ButtonStyle.primary)
        button.callback = self.back
        self.add_item(button)

    async def back(self, interaction):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message(f'Only {self.target.display_name} can answer this one 😉', ephemeral=True)
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog.send_reaction(interaction.channel, self.action, self.target, self.giver, allow_back=False)


class WyrView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=180)
        self.options = options
        self.votes = {}
        for index, text in enumerate(options):
            button = discord.ui.Button(label=text[:78], style=discord.ButtonStyle.primary if index == 0 else discord.ButtonStyle.danger)
            button.callback = self.make_callback(index)
            self.add_item(button)

    def make_callback(self, index):
        async def callback(interaction):
            self.votes[interaction.user.id] = index
            await interaction.response.edit_message(embed=self.embed())
        return callback

    def embed(self):
        counts = [sum(1 for vote in self.votes.values() if vote == i) for i in range(2)]
        total = sum(counts) or 1
        embed = discord.Embed(title='🤔 Would you rather…', color=PALETTE['pink'])
        for index, text in enumerate(self.options):
            bar = '█' * round(counts[index] / total * 10) + '░' * (10 - round(counts[index] / total * 10))
            embed.add_field(name=f'{"🅰️" if index == 0 else "🅱️"} {text}', value=f'`{bar}` {counts[index]} vote{"s" if counts[index] != 1 else ""}', inline=False)
        embed.set_footer(text='Tap a button to vote - you can change your mind!')
        return embed


class FunCog(commands.Cog, name='Fun'):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        for action in ACTIONS:
            name = f's{action}'
            if not self.bot.get_command(name):
                self.bot.add_command(self.make_action_command(action, name))

    def make_action_command(self, action, name):
        @commands.cooldown(1, 4, commands.BucketType.user)
        async def callback(ctx, *, rest: str = ''):
            target = next((m for m in ctx.message.mentions if m.id != ctx.author.id), None)
            if target is None and ctx.message.mentions:
                target = ctx.message.mentions[0]
            await self.send_reaction(ctx.channel, action, ctx.author, target)

        return commands.Command(callback, name=name, help=f'{action.title()} someone with a GIF')

    async def send_reaction(self, channel, action, giver, target, allow_back=True):
        found = await api.fetch_reaction_gif(action)
        if not found:
            return await channel.send("⚠️ Couldn't fetch a GIF right now. Try again!")
        url, anime = found
        with_target, without = ACTIONS[action]
        text = with_target.format(a=f'**{giver.display_name}**', b=f'**{target.display_name}**') if target else without.format(a=f'**{giver.display_name}**')
        embed = image_embed(text, url, footer=f'from {anime} • nekos.best' if anime else 'nekos.best')
        view = BackView(self, action, giver, target) if (target and allow_back and target.id != giver.id and not target.bot) else None
        if view:
            await channel.send(embed=embed, view=view)
        else:
            await channel.send(embed=embed)

    # ---- animals

    async def animal(self, ctx, fetcher, title, color, source):
        url = await fetcher()
        if not url:
            return await ctx.send("⚠️ Couldn't fetch one right now. Try again!")
        await ctx.send(embed=image_embed(title, url, color, f'Powered by {source}'))

    @commands.command(name='sdog', aliases=['sdoggo', 'spuppy'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sdog(self, ctx):
        await self.animal(ctx, api.fetch_dog_image, '🐶 Woof!', PALETTE['orange'], 'dog.ceo')

    @commands.command(name='sfox')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sfox(self, ctx):
        await self.animal(ctx, api.fetch_fox_image, '🦊 What does the fox say?', PALETTE['red'], 'randomfox.ca')

    @commands.command(name='sduck', aliases=['squack'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sduck(self, ctx):
        await self.animal(ctx, api.fetch_duck_image, '🦆 Quack!', PALETTE['gold'], 'random-d.uk')

    # ---- text APIs

    async def text_embed(self, ctx, fetcher, title, color, source):
        text = await fetcher()
        if not text:
            return await ctx.send("⚠️ Couldn't fetch that right now. Try again!")
        embed = discord.Embed(title=title, description=text, color=color)
        embed.set_footer(text=f'Powered by {source}')
        await ctx.send(embed=embed)

    @commands.command(name='sfact', aliases=['sfacts'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sfact(self, ctx):
        await self.text_embed(ctx, api.fetch_useless_fact, '🤯 Did you know?', PALETTE['sky'], 'uselessfacts.jsph.pl')

    @commands.command(name='sadvice')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sadvice(self, ctx):
        await self.text_embed(ctx, api.fetch_advice, '💡 Advice', PALETTE['teal'], 'Advice Slip')

    @commands.command(name='sdadjoke', aliases=['sdad'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sdadjoke(self, ctx):
        await self.text_embed(ctx, api.fetch_dad_joke, '👨 Dad joke', PALETTE['green'], 'icanhazdadjoke.com')

    @commands.command(name='szen', aliases=['sinspire', 'swisdom'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def szen(self, ctx):
        await self.text_embed(ctx, api.fetch_zen_quote, '🧘 Words of wisdom', PALETTE['purple'], 'ZenQuotes')

    @commands.command(name='sreddit', aliases=['srmeme', 'smemes'])
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def sreddit(self, ctx):
        meme = await api.fetch_reddit_meme()
        if not meme:
            return await ctx.send("⚠️ Couldn't fetch a meme right now. Try again!")
        await ctx.send(embed=image_embed(meme.get('title', 'Meme')[:250], meme['url'], PALETTE['orange'],
                                         f"r/{meme.get('subreddit', 'memes')} • 👍 {meme.get('ups', 0)}"))

    @commands.command(name='snasa', aliases=['sspace', 'sapod'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def snasa(self, ctx):
        data = await api.fetch_nasa_apod()
        if not data:
            return await ctx.send('🔭 NASA is not answering right now (or today\'s picture is a video). Try again later!')
        embed = image_embed(f"🚀 {data.get('title', 'Astronomy Picture of the Day')}", data.get('url'), PALETTE['blurple'],
                            f"NASA APOD • {data.get('date', '')}", (data.get('explanation') or '')[:900])
        await ctx.send(embed=embed)

    @commands.command(name='sgif')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sgif(self, ctx, *, query: str = ''):
        if not query.strip():
            return await ctx.send('Usage: `sgif <what you want>` - e.g. `sgif happy dance`')
        result = await api.fetch_giphy(query.strip())
        if result == 'no-key':
            return await ctx.send('🔑 `sgif` needs a free GIPHY key. Add `GIPHY_API_KEY=...` to the `.env` file (get one at developers.giphy.com).')
        if not result:
            return await ctx.send(f"🤷 Couldn't find a GIF for `{query[:50]}`.")
        await ctx.send(embed=image_embed(f'🎞️ {query[:100]}', result, footer='Powered by GIPHY'))

    @commands.command(name='spokemon', aliases=['spokedex', 'sdex'])
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def spokemon(self, ctx, *, name: str = ''):
        ident = re.sub(r'[^a-z0-9-]', '', name.strip().lower().replace(' ', '-')) or str(random.randint(1, 1025))
        info = await api.fetch_pokemon(ident)
        if not info:
            return await ctx.send(f"🔎 I couldn't find a Pokémon called `{name[:40]}`. Try `spokemon pikachu` or just `spokemon` for a random one!")
        color = TYPE_COLORS.get(info['types'][0], PALETTE['blurple']) if info['types'] else PALETTE['blurple']
        embed = discord.Embed(title=f"#{info['id']} {info['name'].replace('-', ' ').title()}", color=color,
                              description=' '.join(f'`{t.title()}`' for t in info['types']))
        if info['art']:
            embed.set_image(url=info['art'])
        labels = {'hp': 'HP', 'attack': 'ATK', 'defense': 'DEF', 'special-attack': 'SP.ATK', 'special-defense': 'SP.DEF', 'speed': 'SPD'}
        lines = [f"`{labels[key]:<6}` {'█' * min(value // 15, 10)}{'░' * (10 - min(value // 15, 10))} {value}" for key, value in info['stats'].items() if key in labels]
        embed.add_field(name='Base stats', value='\n'.join(lines), inline=False)
        embed.add_field(name='Height', value=f"{info['height']} m", inline=True)
        embed.add_field(name='Weight', value=f"{info['weight']} kg", inline=True)
        embed.set_footer(text='Powered by PokéAPI')
        await ctx.send(embed=embed)

    # ---- tiny tools

    @commands.command(name='sflip', aliases=['scoin', 'scoinflip'])
    async def sflip(self, ctx):
        await ctx.send(f"🪙 {random.choice(['**Heads!** 👑', '**Tails!** 🦅'])}")

    @commands.command(name='sroll', aliases=['sdice'])
    async def sroll(self, ctx, *, spec: str = '1d6'):
        match = re.fullmatch(r'(\d{1,2})?\s*d\s*(\d{1,4})', spec.strip().lower()) or re.fullmatch(r'()(\d{1,4})', spec.strip())
        if not match:
            return await ctx.send('🎲 Try `sroll`, `sroll 2d6` or `sroll d20`.')
        count, sides = int(match.group(1) or 1), int(match.group(2))
        if not (1 <= count <= 20 and 2 <= sides <= 1000):
            return await ctx.send('🎲 Use 1-20 dice with 2-1000 sides.')
        rolls = [random.randint(1, sides) for _ in range(count)]
        detail = f" ({' + '.join(map(str, rolls))})" if count > 1 else ''
        await ctx.send(f'🎲 {ctx.author.display_name} rolled **{sum(rolls)}**{detail} on {count}d{sides}')

    @commands.command(name='s8ball', aliases=['seightball', 'sask'])
    async def s8ball(self, ctx, *, question: str = ''):
        if not question.strip():
            return await ctx.send('🎱 Ask me a question: `s8ball will I pass my exam?`')
        embed = discord.Embed(title='🎱 Magic 8-Ball', color=PALETTE['purple'])
        embed.add_field(name='Question', value=question[:200], inline=False)
        embed.add_field(name='Answer', value=random.choice(FUN.get('eightball', ['Maybe.'])), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='schoose', aliases=['spick'])
    async def schoose(self, ctx, *, options: str = ''):
        choices = [item.strip() for item in re.split(r'\||,|\bor\b', options) if item.strip()]
        if len(choices) < 2:
            return await ctx.send('🤷 Give me at least two options: `schoose pizza, burger, tacos`')
        await ctx.send(f'🎯 I choose… **{random.choice(choices)}**!')

    @commands.command(name='swyr', aliases=['swouldyourather'])
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def swyr(self, ctx):
        options = random.choice(FUN.get('would_you_rather', [['Yes', 'No']]))
        view = WyrView(options)
        await ctx.send(embed=view.embed(), view=view)

    @commands.command(name='struth')
    async def struth(self, ctx):
        await ctx.send(f"🫢 **Truth:** {random.choice(FUN.get('truths', ['Tell us a secret!']))}")

    @commands.command(name='sdare')
    async def sdare(self, ctx):
        await ctx.send(f"😈 **Dare:** {random.choice(FUN.get('dares', ['Do a silly dance!']))}")

    @commands.command(name='sping')
    async def sping(self, ctx):
        await ctx.send(f'🏓 Pong! `{round(self.bot.latency * 1000)} ms`')


async def setup(bot):
    await bot.add_cog(FunCog(bot))
