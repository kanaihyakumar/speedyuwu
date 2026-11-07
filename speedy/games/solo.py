"""Open games: anybody in the channel can just type - no joining, no commands."""
import io
import math
import random

import discord

from .. import images
from ..core import PALETTE, load_json_data
from ..session import Session, safe_react

WORDS = load_json_data('words.json') or {}


class OpenGame(Session):
    """Anyone in the channel can play; participants are remembered for XP."""

    def __init__(self, bot, channel, host, **_):
        super().__init__(bot, channel, host)
        self.participants = {}

    def is_participant(self, user_id):
        return user_id in self.participants

    async def repost(self, embed, file=None):
        old = self.message
        kwargs = {'embed': embed}
        if file:
            kwargs['file'] = file
        self.message = await self.channel.send(**kwargs)
        if old is not None:
            try:
                await old.delete()
            except discord.HTTPException:
                pass


def png_file(buffer, name, description=None):
    return discord.File(io.BytesIO(buffer.getvalue()), filename=name, description=description)


class GuessNumber(OpenGame):
    key = 'guess'
    title = 'Guess the Number'
    emoji = '🔢'

    PRESETS = {'easy': 50, 'medium': 100, 'hard': 1000}

    def __init__(self, bot, channel, host, args=(), **_):
        super().__init__(bot, channel, host)
        self.maximum = 100
        for arg in args:
            arg = arg.lower()
            if arg in self.PRESETS:
                self.maximum = self.PRESETS[arg]
            elif arg.isdigit():
                self.maximum = min(max(int(arg), 10), 100_000)
        self.target = random.randint(1, self.maximum)
        self.low, self.high = 1, self.maximum
        self.attempts = math.ceil(math.log2(self.maximum)) + 3
        self.used = 0

    async def start(self):
        embed = discord.Embed(
            title=f'{self.emoji} {self.title}',
            description=(
                f"I'm thinking of a number between **1** and **{self.maximum}**.\n\n"
                f'✍️ **Just type a number** - anyone in the channel can guess!\n'
                f'🎯 You have **{self.attempts}** guesses as a team.'
            ),
            color=PALETTE['teal'],
        )
        embed.set_footer(text='Type sstop to give up • try sguess hard for 1-1000')
        self.message = await self.channel.send(embed=embed)

    async def handle_message(self, message):
        text = message.content.strip()
        if not text.isdigit() or len(text) > 7:
            return False
        guess = int(text)
        if guess < 1 or guess > self.maximum:
            if guess <= self.maximum * 10:
                await safe_react(message, '❓')
                return True
            return False
        async with self.lock:
            if self.ended:
                return False
            self.touch()
            self.used += 1
            self.participants[message.author.id] = message.author
            left = self.attempts - self.used
            if guess == self.target:
                await self.win(message, left)
                return True
            if guess < self.target:
                self.low, arrow, word = max(self.low, guess + 1), '📈', 'Higher'
            else:
                self.high, arrow, word = min(self.high, guess - 1), '📉', 'Lower'
            if left <= 0:
                await self.lose(message)
                return True
            closeness = abs(guess - self.target) / self.maximum
            temperature = '🔥 burning hot' if closeness <= 0.03 else '♨️ hot' if closeness <= 0.08 else '🌤️ warm' if closeness <= 0.2 else '❄️ cold'
            await message.reply(f'{arrow} **{word}!** {temperature} · range **{self.low}–{self.high}** · {left} guess{"es" if left != 1 else ""} left',
                                mention_author=False)
            return True

    async def win(self, message, left):
        xp = 20 + left * 3
        for user in self.participants.values():
            self.award(user, xp if user.id == message.author.id else 5, user.id == message.author.id)
        embed = discord.Embed(
            title='🎉 Got it!',
            description=f'{message.author.mention} guessed **{self.target}** after **{self.used}** guess{"es" if self.used != 1 else ""}!\n+{xp} XP 🏅',
            color=PALETTE['gold'],
        )
        self.teardown()
        await message.reply(embed=embed, mention_author=False)

    async def lose(self, message):
        self.teardown()
        embed = discord.Embed(title='💥 Out of guesses!', description=f'The number was **{self.target}**. Try again with `sguess`!', color=PALETTE['red'])
        await message.reply(embed=embed, mention_author=False)

    async def stop(self, by=None):
        self.teardown()
        await self.channel.send(f'🏳️ Game over - the number was **{self.target}**.')


class Hangman(OpenGame):
    key = 'hangman'
    title = 'Hangman'
    emoji = '🪢'
    MAX_LIVES = 6

    def __init__(self, bot, channel, host, args=(), **_):
        super().__init__(bot, channel, host)
        categories = WORDS.get('hangman', {'Words': ['hangman']})
        chosen = next((name for name in categories if args and name.lower() == args[0].lower()), None)
        self.category = chosen or random.choice(list(categories))
        self.word = random.choice(categories[self.category])
        self.guessed = set()
        self.wrong = []
        self.contrib = {}

    def pattern(self):
        return ''.join(letter if letter in self.guessed else '_' for letter in self.word)

    async def render(self, state='playing', description=None):
        data = images.hangman_image(self.pattern(), self.wrong, self.MAX_LIVES, self.category, state)
        file = png_file(data, 'hangman.png', f'Hangman: {self.pattern()}')
        color = {'playing': PALETTE['purple'], 'won': PALETTE['green'], 'lost': PALETTE['red']}[state]
        embed = discord.Embed(title=f'{self.emoji} Hangman', description=description or 'Type a **letter** - or guess the **whole word**!', color=color)
        embed.set_image(url='attachment://hangman.png')
        if state == 'playing':
            embed.set_footer(text=f'{len(self.word)} letters • category: {self.category} • anyone can guess')
        await self.repost(embed, file)

    async def start(self):
        await self.render()

    async def handle_message(self, message):
        text = message.content.strip().lower()
        if not text.isalpha() or not (len(text) == 1 or len(text) == len(self.word)):
            return False
        async with self.lock:
            if self.ended:
                return False
            self.touch()
            user = message.author
            if len(text) == 1:
                if text in self.guessed or text in self.wrong:
                    await safe_react(message, '🔁')
                    return True
                self.participants[user.id] = user
                if text in self.word:
                    self.guessed.add(text)
                    self.contrib[user.id] = self.contrib.get(user.id, 0) + 1
                    await safe_react(message, '✅')
                    if all(letter in self.guessed for letter in self.word):
                        return await self.finish_round(user, True) or True
                else:
                    self.wrong.append(text)
                    await safe_react(message, '❌')
            else:
                self.participants[user.id] = user
                if text == self.word:
                    self.guessed.update(self.word)
                    return await self.finish_round(user, True) or True
                self.wrong.append(text)
                await safe_react(message, '❌')
            if len(self.wrong) >= self.MAX_LIVES:
                return await self.finish_round(user, False) or True
            await self.render()
            return True

    async def finish_round(self, user, won):
        if won:
            for member in self.participants.values():
                self.award(member, 25 if member.id == user.id else (8 if self.contrib.get(member.id) else 2), member.id == user.id)
            await self.render('won', f'🎉 **{user.display_name}** solved it! The word was **{self.word.upper()}**.')
        else:
            for member in self.participants.values():
                self.award(member, 2, False)
            await self.render('lost', f'💀 Out of lives! The word was **{self.word.upper()}**.')
        self.teardown()

    async def stop(self, by=None):
        self.teardown()
        await self.channel.send(f'🏳️ Hangman stopped - the word was **{self.word.upper()}**.')


def wordle_score(guess, answer):
    result = ['x'] * len(answer)
    remaining = list(answer)
    for index, letter in enumerate(guess):
        if answer[index] == letter:
            result[index] = 'g'
            remaining[index] = None
    for index, letter in enumerate(guess):
        if result[index] == 'x' and letter in remaining:
            result[index] = 'y'
            remaining[remaining.index(letter)] = None
    return ''.join(result)


class Wordle(OpenGame):
    key = 'wordle'
    title = 'Wordle'
    emoji = '🟩'
    LENGTH, ROWS = 5, 6

    def __init__(self, bot, channel, host, **_):
        super().__init__(bot, channel, host)
        self.answer = random.choice(WORDS.get('wordle', ['crane']))
        self.rows, self.scores, self.guessers = [], [], []

    async def render(self, state='playing', description=None):
        data = images.wordle_image(self.rows, self.scores, self.ROWS, self.LENGTH)
        file = png_file(data, 'wordle.png', 'Wordle board')
        color = {'playing': PALETTE['green'], 'won': PALETTE['gold'], 'lost': PALETTE['red']}[state]
        history = '\n'.join(f'`{index}.` **{word.upper()}** - {who.display_name}' for index, (word, who) in enumerate(zip(self.rows, self.guessers), start=1))
        embed = discord.Embed(
            title=f'{self.emoji} Wordle',
            description=(description or 'Guess the **5-letter word** in 6 tries. Just type a word - anyone can guess!\n🟩 right spot · 🟨 wrong spot · ⬛ not in word')
            + (f'\n\n{history}' if history else ''),
            color=color,
        )
        embed.set_image(url='attachment://wordle.png')
        await self.repost(embed, file)

    async def start(self):
        await self.render()

    async def handle_message(self, message):
        text = message.content.strip().lower()
        if not text.isalpha() or len(text) != self.LENGTH:
            return False
        async with self.lock:
            if self.ended:
                return False
            if text in self.rows:
                await safe_react(message, '🔁')
                return True
            self.touch()
            user = message.author
            self.participants[user.id] = user
            self.rows.append(text)
            self.scores.append(wordle_score(text, self.answer))
            self.guessers.append(user)
            if text == self.answer:
                tries = len(self.rows)
                xp = max(50 - 6 * (tries - 1), 15)
                for member in self.participants.values():
                    self.award(member, xp if member.id == user.id else 8, member.id == user.id)
                await self.render('won', f'🎉 **{user.display_name}** got **{self.answer.upper()}** in {tries}/{self.ROWS}! +{xp} XP')
                self.teardown()
            elif len(self.rows) >= self.ROWS:
                for member in self.participants.values():
                    self.award(member, 3, False)
                await self.render('lost', f'😵 Out of tries! The word was **{self.answer.upper()}**.')
                self.teardown()
            else:
                await self.render()
            return True

    async def stop(self, by=None):
        self.teardown()
        await self.channel.send(f'🏳️ Wordle stopped - the word was **{self.answer.upper()}**.')
