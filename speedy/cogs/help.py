"""`shelp` — a categorised help menu with a dropdown."""
import discord
from discord.ext import commands

from ..core import PALETTE
from .fun import ACTIONS
from .games import GAMES
from ..mathgen import TOPICS

CLASSIC = ['speedy', 'meow', 'happy birthday', 'knock knock', 'smeme']
CLASSIC_API = ['scat', 'catfact', 'semoji', 'sjoke', 'schuck']

SECTIONS = {
    'home': ('🏠', 'Overview', 'Where to start'),
    'games': ('🎮', 'Games', 'Board games, word games, quizzes'),
    'math': ('🧮', 'Maths', 'Algebra, surds, trig, calculus…'),
    'fun': ('🎉', 'Fun & Media', 'Animals, memes, facts, Pokédex'),
    'gifs': ('🎞️', 'GIF Reactions', 'Hug, pat, dance… and stickers'),
    'classic': ('⭐', 'Classics', 'Quotes, jokes, cats & more'),
}


def chunk(items, limit=950):
    chunks, current = [], ''
    for item in items:
        piece = f'`{item}`'
        if current and len(current) + len(piece) + 2 > limit:
            chunks.append(current)
            current = piece
        else:
            current = f'{current}, {piece}' if current else piece
    if current:
        chunks.append(current)
    return chunks


def build_section(section, bot):
    emoji, title, _ = SECTIONS[section]
    embed = discord.Embed(title=f'{emoji} {title}', color=PALETTE['blurple'])

    if section == 'home':
        embed.title = '🚀 Speedyuwu — Help'
        embed.description = (
            "Everything is **one short word**. No long commands, no IDs.\n"
            "Pick a category from the dropdown below, or try these:"
        )
        embed.add_field(name='🎮 Games', value='`splay` — menu with buttons\n`sguess` `sttt` `swordle` `strivia` — start any game by name\nMoves are just **numbers or words** you type!', inline=False)
        embed.add_field(name='🧮 Maths', value='`smath` — pick a topic, type the answer\n`smath surds hard` • `salgebra` • `strig`', inline=False)
        embed.add_field(name='🎉 Fun', value='`sdog` `sfox` `sfact` `swyr` `spokemon pikachu`\n`shug @friend` — send a GIF hug!', inline=False)
        embed.add_field(name='📊 Progress', value='`sprofile` — your XP card • `sboard` — leaderboard • `sstop` — end the current game', inline=False)
        embed.set_footer(text='Tip: games run one per channel — everyone in the channel can join in!')
    elif section == 'games':
        embed.description = 'Start with a **one-word command**. Then just type your move — numbers for boards, letters/words for word games.'
        for heading, kind in [('⚔️ 2 players (friend or bot)', 'versus'), ('👥 Everyone plays', 'open'), ('🧠 Quizzes', 'quiz')]:
            lines = [f'{spec.emoji} **{spec.title}**\n`{spec.usage}`' for spec in GAMES if spec.kind == kind]
            embed.add_field(name=heading, value='\n'.join(lines), inline=False)
        embed.add_field(name='Controls', value='`splay` menu • `sstop` end game • `sprofile` XP card • `sboard` leaderboard', inline=False)
    elif section == 'math':
        embed.description = 'Questions appear as picture cards. **Just type the answer** — first correct answer wins the round!'
        for topic in TOPICS.values():
            embed.add_field(name=f'{topic.emoji} {topic.title}', value=f'`s{topic.key}`', inline=True)
        embed.add_field(
            name='Options',
            value='`smath` menu • `smath <topic> [easy|medium|hard] [rounds]`\n`scalc 3√2 × 4` calculator • `sfactor 360` prime factors',
            inline=False,
        )
        embed.add_field(name='Answer formats', value='`3√2` `sqrt(3)/2` `5π/6` `3/4` `x^2+5x+6` `2, 3` `x=1, y=2`', inline=False)
    elif section == 'fun':
        embed.add_field(name='🐾 Animals', value='`sdog` `sfox` `sduck` `scat` `skitty`', inline=False)
        embed.add_field(name='🧠 Facts & words', value='`sfact` `catfact` `sadvice` `szen` `sdadjoke` `sjoke` `schuck`', inline=False)
        embed.add_field(name='🖼️ Pictures', value='`sreddit` fresh memes • `snasa` space picture of the day • `sgif <query>` (needs GIPHY key) • `semoji`', inline=False)
        embed.add_field(name='⚡ Pokédex', value='`spokemon pikachu` • `spokemon` for a random one', inline=False)
        embed.add_field(name='🎲 Tools & party', value='`sflip` `sroll 2d6` `s8ball <question>` `schoose a, b, c` `swyr` `struth` `sdare` `sping`', inline=False)
    elif section == 'gifs':
        embed.description = '`s<action> @friend` sends an anime GIF — and they get a button to react back! Without a mention it is just you.'
        for index, piece in enumerate(chunk([f's{action}' for action in ACTIONS])):
            embed.add_field(name='Reactions' if index == 0 else 'More', value=piece, inline=False)
        for index, piece in enumerate(chunk(sorted(bot.sticker_names))):
            embed.add_field(name=f'Stickers ({len(bot.sticker_names)})' if index == 0 else 'Stickers (cont.)', value=piece, inline=False)
    else:
        embed.add_field(name='Text', value=', '.join(f'`{c}`' for c in CLASSIC), inline=False)
        embed.add_field(name='Live APIs', value=', '.join(f'`{c}`' for c in CLASSIC_API), inline=False)
    return embed


class HelpView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        select = discord.ui.Select(
            placeholder='📖 Choose a help category…',
            options=[discord.SelectOption(label=title, value=key, emoji=emoji, description=desc) for key, (emoji, title, desc) in SECTIONS.items()],
        )
        select.callback = self.changed
        self.add_item(select)

    async def changed(self, interaction):
        await interaction.response.edit_message(embed=build_section(interaction.data['values'][0], self.bot), view=self)


class HelpCog(commands.Cog, name='Help'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='shelp', aliases=['shelpme', 'smenu'])
    async def shelp(self, ctx, *, topic: str = ''):
        topic = topic.strip().lower()
        aliases = {'game': 'games', 'maths': 'math', 'algebra': 'math', 'sticker': 'gifs', 'stickers': 'gifs', 'gif': 'gifs',
                   'reactions': 'gifs', 'media': 'fun', 'api': 'classic', 'classics': 'classic'}
        section = aliases.get(topic, topic) if topic else 'home'
        if section not in SECTIONS:
            section = 'home'
        await ctx.send(embed=build_section(section, self.bot), view=HelpView(self.bot))


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
