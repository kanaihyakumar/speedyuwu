"""Maths section: topic quizzes (algebra, surds, trig, ...) and a calculator."""
import math

import discord
from discord.ext import commands

from .. import mathgen
from ..core import PALETTE
from ..games.quiz import MathQuiz
from ..mathgen import TOPICS, LEVEL_NAMES, ExprError


def parse_math_args(args):
    topic, level, rounds = None, 2, 5
    for arg in args:
        lowered = arg.lower()
        found = mathgen.find_topic(lowered)
        if found:
            topic = found.key
        elif lowered in mathgen.LEVELS and not lowered.isdigit():
            level = mathgen.LEVELS[lowered]
        elif lowered.isdigit():
            rounds = max(1, min(int(lowered), 20))
        elif lowered in ('mix', 'random', 'all'):
            topic = None
    return topic, level, rounds


class MathMenu(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.level = 2
        topic_options = [discord.SelectOption(label='Random mix', value='mix', emoji='🎲', description='A bit of everything')]
        topic_options += [discord.SelectOption(label=t.title, value=t.key, emoji=t.emoji, description=t.blurb[:100])
                          for t in TOPICS.values()]
        topic_select = discord.ui.Select(placeholder='📚 Pick a topic to start…', options=topic_options, row=0)
        topic_select.callback = self.topic_chosen
        level_select = discord.ui.Select(
            placeholder='🎚️ Difficulty: Medium', row=1,
            options=[discord.SelectOption(label=name, value=str(level), emoji=emoji) for level, name, emoji in [(1, 'Easy', '🟢'), (2, 'Medium', '🟡'), (3, 'Hard', '🔴')]])
        level_select.callback = self.level_chosen
        self.add_item(topic_select)
        self.add_item(level_select)

    async def level_chosen(self, interaction):
        self.level = int(interaction.data['values'][0])
        for item in self.children:
            if isinstance(item, discord.ui.Select) and item.row == 1:
                item.placeholder = f'🎚️ Difficulty: {LEVEL_NAMES[self.level]}'
        await interaction.response.edit_message(view=self)

    async def topic_chosen(self, interaction):
        value = interaction.data['values'][0]
        busy = self.cog.bot.sessions.get(interaction.channel.id)
        if busy:
            return await interaction.response.send_message(f'⏳ **{busy.title}** is already running here - `sstop` ends it.', ephemeral=True)
        await interaction.response.send_message(f'🧮 Starting {"a mixed round" if value == "mix" else TOPICS[value].title} on {LEVEL_NAMES[self.level]}!', ephemeral=True)
        await self.cog.start_quiz(interaction.channel, interaction.user, None if value == 'mix' else value, self.level, 5)


class MathCog(commands.Cog, name='Maths'):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        taken = set(self.bot.sticker_names)
        for topic in TOPICS.values():
            for name in (topic.key, *topic.aliases):
                command_name = f's{name}'
                if command_name in taken or self.bot.get_command(command_name) or name == 'calc':
                    continue
                self.bot.add_command(self.make_topic_command(topic.key, command_name))

    def make_topic_command(self, topic_key, command_name):
        async def callback(ctx, *, rest: str = ''):
            _, level, rounds = parse_math_args(rest.split())
            await self.start_quiz(ctx.channel, ctx.author, topic_key, level, rounds)

        return commands.Command(callback, name=command_name, help=f'Practise {TOPICS[topic_key].title}')

    async def start_quiz(self, channel, user, topic, level, rounds):
        busy = self.bot.sessions.get(channel.id)
        if busy:
            return await channel.send(f'⏳ **{busy.title}** is already running here. Finish it or type `sstop`.')
        session = MathQuiz(self.bot, channel, user, topic=topic, level=level, rounds=rounds)
        if self.bot.sessions.claim(session):
            try:
                await session.start()
            except Exception:
                session.teardown()
                raise

    def menu_embed(self):
        embed = discord.Embed(
            title='🧮 Speedyuwu Maths Lab',
            description=('Pick a topic below - the question appears as a picture card and **you just type the answer**.\n'
                         'First correct answer wins the round. Exact surds (`3√2`), fractions (`3/4`), `π`, and `x^2+5x+6` all work!'),
            color=PALETTE['pink'],
        )
        for topic in TOPICS.values():
            embed.add_field(name=f'{topic.emoji} {topic.title}', value=f'{topic.blurb}\n`s{topic.key}`', inline=True)
        embed.add_field(
            name='How to start',
            value=('`smath` - this menu\n`smath surds hard 10` - topic, difficulty (`easy`/`medium`/`hard`) and rounds\n'
                   '`smath mix` - random mix\n`scalc 3√2 × 4` - calculator\n`sfactor 360` - prime factors'),
            inline=False,
        )
        return embed

    async def send_menu(self, channel):
        await channel.send(embed=self.menu_embed(), view=MathMenu(self))

    @commands.command(name='smath', aliases=['smaths'])
    async def smath(self, ctx, *, rest: str = ''):
        words = rest.split()
        if not words:
            return await self.send_menu(ctx.channel)
        topic, level, rounds = parse_math_args(words)
        if topic is None and not any(w.lower() in ('mix', 'random', 'all') for w in words) and not any(w.lower() in mathgen.LEVELS or w.isdigit() for w in words):
            await ctx.send(f'🤔 Unknown topic `{words[0]}`. Pick one from the menu:')
            return await self.send_menu(ctx.channel)
        await self.start_quiz(ctx.channel, ctx.author, topic, level, rounds)

    @commands.command(name='scalc', aliases=['scalculate', 'sevaluate'])
    async def scalc(self, ctx, *, expression: str = ''):
        if not expression.strip():
            return await ctx.send('Usage: `scalc 3√2 × 4`, `scalc sin(30°)`, `scalc 5!`, `scalc 2^10`, `scalc 15% * 80`')
        try:
            value = mathgen.evaluate(expression)
        except ExprError:
            return await ctx.send("🤷 I couldn't understand that. Try things like `scalc (3+4)*2`, `scalc √50` or `scalc sin(45°)`.")
        shown = mathgen.fmt(value)
        embed = discord.Embed(title='🧮 Calculator', color=PALETTE['teal'])
        embed.add_field(name='Expression', value=f'`{expression.strip()[:200]}`', inline=False)
        embed.add_field(name='Result', value=f'**{shown}**', inline=False)
        multiple = value / math.pi
        if abs(value) > 1e-9 and abs(multiple - round(multiple * 12) / 12) < 1e-9 and abs(multiple) < 100 and value != round(value):
            embed.add_field(name='In terms of π', value=f'{mathgen.fmt(round(multiple * 12) / 12)}π', inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='sfactor', aliases=['sfactors', 'sprimefactors'])
    async def sfactor(self, ctx, number: int = 0):
        if not 2 <= number <= 10 ** 12:
            return await ctx.send('Usage: `sfactor 360` (a whole number from 2 to 1,000,000,000,000)')
        n, factors, divisor = number, {}, 2
        while divisor * divisor <= n:
            while n % divisor == 0:
                factors[divisor] = factors.get(divisor, 0) + 1
                n //= divisor
            divisor += 1
        if n > 1:
            factors[n] = factors.get(n, 0) + 1
        product = ' × '.join(f'{p}{mathgen.sup(e) if e > 1 else ""}' for p, e in factors.items())
        prime = len(factors) == 1 and next(iter(factors.values())) == 1
        embed = discord.Embed(title=f'🧩 {number:,}', description=f'**{"Prime number! ✨" if prime else product}**', color=PALETTE['purple'])
        if number <= 10 ** 6:
            divisors = [d for d in range(1, number + 1) if number % d == 0]
            embed.add_field(name=f'Factors ({len(divisors)})', value=', '.join(map(str, divisors))[:1000], inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MathCog(bot))
