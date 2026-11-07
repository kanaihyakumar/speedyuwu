"""Game launcher: one-word start commands, a pick-a-game menu, profile and leaderboard."""
import re
from dataclasses import dataclass, field

import discord
from discord.ext import commands

from .. import images, mathgen
from ..core import PALETTE, level_for, rank_for, xp_for_level
from ..games import quiz, solo, versus


@dataclass
class GameSpec:
    key: str
    title: str
    emoji: str
    blurb: str
    kind: str
    factory: object
    commands: tuple
    aliases: tuple = ()
    usage: str = ''
    extra: dict = field(default_factory=dict)


def _rounds(args, default=5):
    for arg in args:
        if arg.isdigit():
            return max(1, min(int(arg), 20))
    return default


def _trivia(bot, channel, user, args, opponent):
    category = next((TRIVIA_IDS[a.lower()] for a in args if a.lower() in TRIVIA_IDS), None)
    difficulty = next((a.lower() for a in args if a.lower() in ('easy', 'medium', 'hard')), None)
    return quiz.TriviaQuiz(bot, channel, user, rounds=_rounds(args), category=category, difficulty=difficulty)


def _math(bot, channel, user, args, opponent):
    topic, level = None, 2
    for arg in args:
        found = mathgen.find_topic(arg)
        if found:
            topic = found.key
        elif arg.lower() in mathgen.LEVELS and not arg.isdigit():
            level = mathgen.LEVELS[arg.lower()]
    return quiz.MathQuiz(bot, channel, user, topic=topic, level=level, rounds=_rounds(args))


TRIVIA_IDS = quiz.TRIVIA_CATEGORIES

GAMES = [
    GameSpec('ttt', 'Tic Tac Toe', '❌', 'Classic 3×3 — tap a square or type 1-9.', 'versus',
             lambda bot, ch, u, a, o: versus.TicTacToe(bot, ch, u, opponent=o), ('sttt', 'stictactoe'),
             ('ttt', 'tictactoe', 'tic-tac-toe', 'xo'), 'sttt  or  sttt @friend'),
    GameSpec('c4', 'Connect 4', '🔴', 'Drop discs, connect four — tap a column or type 1-7.', 'versus',
             lambda bot, ch, u, a, o: versus.ConnectFour(bot, ch, u, opponent=o), ('sc4', 'sconnect4'),
             ('c4', 'connect4', 'connectfour', 'connect'), 'sc4  or  sc4 @friend'),
    GameSpec('nim', 'Nim (21 Stones)', '🪨', 'Take 1-3 stones; last stone wins.', 'versus',
             lambda bot, ch, u, a, o: versus.Nim(bot, ch, u, opponent=o), ('snim',), ('nim', 'stones', '21'), 'snim  or  snim @friend'),
    GameSpec('rps', 'Rock Paper Scissors', '✌️', 'Best of 3 with secret picks.', 'versus',
             lambda bot, ch, u, a, o: versus.RockPaperScissors(bot, ch, u, opponent=o), ('srps',),
             ('rps', 'rockpaperscissors'), 'srps  or  srps @friend'),
    GameSpec('guess', 'Guess the Number', '🔢', 'Everyone just types numbers. Hot/cold hints!', 'open',
             lambda bot, ch, u, a, o: solo.GuessNumber(bot, ch, u, args=a), ('sguess', 'sguessnumber'),
             ('guess', 'guessnumber', 'number'), 'sguess  •  sguess hard  •  sguess 500'),
    GameSpec('hangman', 'Hangman', '🪢', 'Type letters or the whole word.', 'open',
             lambda bot, ch, u, a, o: solo.Hangman(bot, ch, u, args=a), ('shangman',), ('hangman', 'hang'),
             'shangman  •  shangman animals'),
    GameSpec('wordle', 'Wordle', '🟩', 'Guess the 5-letter word in 6 tries.', 'open',
             lambda bot, ch, u, a, o: solo.Wordle(bot, ch, u), ('swordle',), ('wordle',), 'swordle'),
    GameSpec('scramble', 'Word Scramble', '🔤', 'Unscramble the word before time runs out.', 'quiz',
             lambda bot, ch, u, a, o: quiz.ScrambleQuiz(bot, ch, u, rounds=_rounds(a)), ('sscramble',),
             ('scramble', 'unscramble', 'jumble'), 'sscramble  •  sscramble 10'),
    GameSpec('riddle', 'Riddles', '🕵️', 'Brain teasers — type the answer.', 'quiz',
             lambda bot, ch, u, a, o: quiz.RiddleQuiz(bot, ch, u, rounds=_rounds(a)), ('sriddle',), ('riddle', 'riddles'), 'sriddle'),
    GameSpec('trivia', 'Trivia', '🧠', 'Multiple choice from thousands of questions.', 'quiz', _trivia, ('strivia', 'squiz'),
             ('trivia', 'quiz'), 'strivia  •  strivia science hard 10'),
    GameSpec('flag', 'Guess the Flag', '🏳️', 'Name the country from its flag.', 'quiz',
             lambda bot, ch, u, a, o: quiz.FlagQuiz(bot, ch, u, rounds=_rounds(a)), ('sflag', 'sflags'), ('flag', 'flags'), 'sflag'),
    GameSpec('pokemon', "Who's That Pokémon?", '⚡', 'Guess the silhouette (Gen 1-3).', 'quiz',
             lambda bot, ch, u, a, o: quiz.PokemonQuiz(bot, ch, u, rounds=_rounds(a)), ('spokequiz', 'swtp'),
             ('pokemon', 'poke', 'pokequiz', 'wtp'), 'spokequiz'),
    GameSpec('math', 'Maths', '🧮', 'Algebra, surds, trig, calculus & more — 14 topics.', 'quiz', _math, ('smathquiz',),
             ('math', 'maths'), 'smath  •  smath surds hard'),
]
BY_ALIAS = {}
for _spec in GAMES:
    for _name in (_spec.key, *_spec.aliases, *(c[1:] for c in _spec.commands)):
        BY_ALIAS[_name.lower()] = _spec


def find_game(name):
    return BY_ALIAS.get((name or '').lower().strip())


class GamePicker(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        options = [discord.SelectOption(label=spec.title, value=spec.key, emoji=spec.emoji, description=spec.blurb[:100]) for spec in GAMES]
        select = discord.ui.Select(placeholder='🎮 Pick a game to start it instantly…', options=options)
        select.callback = self.picked
        self.add_item(select)

    async def picked(self, interaction):
        spec = next(game for game in GAMES if game.key == interaction.data['values'][0])
        if spec.key == 'math':
            await interaction.response.defer()
            return await self.cog.bot.get_cog('Maths').send_menu(interaction.channel)
        busy = self.cog.bot.sessions.get(interaction.channel.id)
        if busy:
            return await interaction.response.send_message(f'⏳ **{busy.title}** is already running here — type `sstop` to end it.', ephemeral=True)
        await interaction.response.send_message(f'{spec.emoji} Starting **{spec.title}**!', ephemeral=True)
        await self.cog.launch(interaction.channel, interaction.user, spec, [], None)


class GamesCog(commands.Cog, name='Games'):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        for spec in GAMES:
            for name in spec.commands:
                self.bot.add_command(self.make_command(spec, name))

    def make_command(self, spec, name):
        async def callback(ctx, *, rest: str = ''):
            await self.launch(ctx.channel, ctx.author, spec, rest.split(), self.opponent_from(ctx.message))

        return commands.Command(callback, name=name, help=f'Start {spec.title}')

    def opponent_from(self, message):
        for member in message.mentions:
            if member.id != message.author.id and member.id != self.bot.user.id and not member.bot:
                return member
        return None

    async def launch(self, channel, user, spec, args, opponent):
        busy = self.bot.sessions.get(channel.id)
        if busy:
            await channel.send(f'⏳ **{busy.title}** is already running in this channel. Finish it, or type `sstop` to end it.')
            return None
        session = spec.factory(self.bot, channel, user, args, opponent)
        if not self.bot.sessions.claim(session):
            return None
        try:
            await session.start()
        except Exception:
            session.teardown()
            raise
        return session

    async def natural_start(self, message):
        """'play guess', "let's play wordle", 'start trivia' …"""
        match = re.fullmatch(r"(?:s?play|let'?s play|start|lets play)\s+(.+)", message.content.strip().lower())
        if not match:
            return False
        words = match.group(1).split()
        spec = find_game(words[0])
        if not spec:
            return False
        if spec.key == 'math':
            await self.launch(message.channel, message.author, spec, words[1:], None)
        else:
            await self.launch(message.channel, message.author, spec, words[1:], self.opponent_from(message))
        return True

    # ---- menu

    def menu_embed(self):
        embed = discord.Embed(
            title='🎮 Speedyuwu Arcade',
            description='Starting a game is **one word**. Moves are just numbers or words — no long commands!',
            color=PALETTE['blurple'],
        )
        groups = [
            ('⚔️ 2 players — challenge a friend or play the bot', 'versus'),
            ('👥 Everyone plays — just type in chat', 'open'),
            ('🧠 Quiz time — first right answer wins', 'quiz'),
        ]
        for heading, kind in groups:
            lines = [f'{spec.emoji} **{spec.title}** — `{spec.commands[0]}`\n┗ {spec.blurb}' for spec in GAMES if spec.kind == kind]
            embed.add_field(name=heading, value='\n'.join(lines), inline=False)
        embed.add_field(
            name='Handy',
            value='`splay <game>` start any game • `sstop` end the game • `sprofile` your XP card • `sboard` leaderboard • `shelp` all commands',
            inline=False,
        )
        return embed

    @commands.command(name='sgames', aliases=['splay', 'sarcade'])
    async def sgames(self, ctx, *, rest: str = ''):
        words = rest.split()
        if words:
            spec = find_game(words[0])
            if spec:
                if spec.key == 'math':
                    return await self.launch(ctx.channel, ctx.author, spec, words[1:], None)
                return await self.launch(ctx.channel, ctx.author, spec, words[1:], self.opponent_from(ctx.message))
            await ctx.send(f"🤔 I don't know a game called `{words[0]}`. Here's what I've got:")
        await ctx.send(embed=self.menu_embed(), view=GamePicker(self))

    @commands.command(name='sgame')
    async def sgame_legacy(self, ctx, *, rest: str = ''):
        words = rest.split()
        if len(words) >= 2 and words[0].lower() == 'create' and find_game(words[1]):
            spec = find_game(words[1])
            return await self.launch(ctx.channel, ctx.author, spec, words[2:], self.opponent_from(ctx.message))
        await ctx.send('✨ Games got way easier! Just type `splay` for the menu, or a one-word start like `sguess`, `sttt` or `swordle`. '
                       'Moves are just numbers or words — no game IDs needed.')

    @commands.command(name='sstop', aliases=['sendgame', 'squit'])
    async def sstop(self, ctx):
        session = self.bot.sessions.get(ctx.channel.id)
        if not session:
            return await ctx.send('Nothing is running in this channel. Start something with `splay`!')
        if not session.can_stop(ctx.author):
            return await ctx.send(f'Only {session.host.display_name} or a moderator can stop **{session.title}**.')
        await session.stop(ctx.author)

    # ---- profile & leaderboard

    @commands.command(name='sprofile', aliases=['sxp', 'srank'])
    async def sprofile(self, ctx, *, rest: str = ''):
        member = ctx.message.mentions[0] if ctx.message.mentions else ctx.author
        entry = self.bot.scores.get(member.id)
        if not entry:
            who = 'You have' if member == ctx.author else f'{member.display_name} has'
            return await ctx.send(f'🌱 {who} no XP yet — play a game with `splay` to get on the board!')
        xp = entry['xp']
        level = level_for(xp)
        wins = entry.get('wins', {})
        favourite = 'None yet'
        if wins:
            favourite = next((spec.title for spec in GAMES if spec.key == max(wins, key=wins.get)), max(wins, key=wins.get))
        try:
            avatar = await member.display_avatar.replace(size=256, format='png').read()
        except discord.HTTPException:
            avatar = None
        data = images.profile_card(member.display_name, avatar, level, rank_for(level), xp, xp_for_level(level), xp_for_level(level + 1),
                                   entry['played'], sum(wins.values()), favourite)
        await ctx.send(file=discord.File(data, filename='profile.png'))

    @commands.command(name='sboard', aliases=['sleaderboard', 'stop10'])
    async def sboard(self, ctx):
        top = self.bot.scores.top(10)
        if not top:
            return await ctx.send('🏜️ Nobody has scored yet. Be the first — type `splay`!')
        lines = []
        for place, (user_id, entry) in enumerate(top):
            medal = quiz.MEDALS[place] if place < 3 else f'`{place + 1}.`'
            level = level_for(entry['xp'])
            lines.append(f"{medal} **{entry['name']}** — {entry['xp']} XP • Lv {level} {rank_for(level)}")
        embed = discord.Embed(title='🏆 Speedyuwu Leaderboard', description='\n'.join(lines), color=PALETTE['gold'])
        embed.set_footer(text='Earn XP by winning games, quizzes and maths rounds')
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GamesCog(bot))
