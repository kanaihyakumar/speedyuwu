"""Round-based quizzes where anybody can answer by typing (or tapping a button).

One engine (`RoundQuiz`) drives maths, trivia, word scramble, riddles, flags and Pokémon.
"""
import asyncio
import difflib
import random
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Optional

import discord

from .. import api, images, mathgen
from ..core import PALETTE, load_json_data
from ..session import Session, ephemeral, safe_edit, safe_react
from .solo import WORDS, png_file

MEDALS = ['🥇', '🥈', '🥉']
RIDDLES = (load_json_data('riddles.json') or {}).get('riddles', [])


@dataclass
class Round:
    embed: discord.Embed
    file: Optional[discord.File] = None
    check: Optional[Callable[[str], Optional[bool]]] = None
    answer: str = ''
    hint: Optional[str] = None
    seconds: int = 45
    explanation: str = ''
    choices: Optional[list] = None
    correct_index: int = -1
    reveal_file: Optional[Callable[[], discord.File]] = None
    done: bool = False
    started: float = 0.0
    locked: set = field(default_factory=set)
    timer: Optional[asyncio.Task] = None


class ChoiceButton(discord.ui.Button):
    def __init__(self, index, letter):
        super().__init__(label=letter, style=discord.ButtonStyle.primary, row=0)
        self.index = index

    async def callback(self, interaction):
        await self.view.quiz.on_choice(interaction, self.index)


class RoundView(discord.ui.View):
    def __init__(self, quiz, rnd):
        super().__init__(timeout=rnd.seconds + 120)
        self.quiz = quiz
        self.rnd = rnd
        if rnd.choices:
            for index in range(len(rnd.choices)):
                self.add_item(ChoiceButton(index, 'ABCD'[index]))
        elif rnd.hint:
            self.add_item(self.make_hint())
        self.add_item(self.make_skip())

    def make_hint(self):
        button = discord.ui.Button(label='Hint', emoji='💡', style=discord.ButtonStyle.secondary, row=1)

        async def callback(interaction):
            await ephemeral(interaction, f'💡 {self.rnd.hint}')

        button.callback = callback
        return button

    def make_skip(self):
        button = discord.ui.Button(label='Skip', emoji='⏭️', style=discord.ButtonStyle.secondary, row=1)

        async def callback(interaction):
            await self.quiz.on_skip(interaction, self.rnd)

        button.callback = callback
        return button


class RoundQuiz(Session):
    color = PALETTE['blurple']
    intro = 'First correct answer wins each round - just type it in chat!'

    def __init__(self, bot, channel, host, rounds=5, **_):
        super().__init__(bot, channel, host)
        self.total = max(1, min(int(rounds), 20))
        self.round_no = 0
        self.scores = {}
        self.users = {}
        self.current = None
        self.empty_streak = 0

    def is_participant(self, user_id):
        return user_id in self.scores

    async def prepare(self):
        return True

    async def make_round(self, number):
        raise NotImplementedError

    async def start(self):
        if not await self.prepare():
            self.teardown()
            await self.channel.send("⚠️ I couldn't load questions right now - please try again in a moment.")
            return
        await self.channel.send(f'{self.emoji} **{self.title}** - **{self.total}** round{"s" if self.total != 1 else ""}! {self.intro}')
        await self.advance()

    async def advance(self):
        if self.ended:
            return
        if self.round_no >= self.total:
            return await self.finish_quiz()
        if self.empty_streak >= 2:
            await self.channel.send('😴 Nobody is answering, so I will wrap up here.')
            return await self.finish_quiz()
        self.round_no += 1
        rnd = await self.make_round(self.round_no)
        if rnd is None:
            await self.channel.send("⚠️ Couldn't load the next question - wrapping up.")
            return await self.finish_quiz()
        hint = 'tap A-D or type the letter' if rnd.choices else 'type your answer'
        rnd.embed.set_footer(text=f'Round {self.round_no}/{self.total} • ⏱ {rnd.seconds}s • {hint}')
        rnd.started = time.monotonic()
        self.current = rnd
        kwargs = {'embed': rnd.embed, 'view': RoundView(self, rnd)}
        if rnd.file:
            kwargs['file'] = rnd.file
        self.message = await self.channel.send(**kwargs)
        self.touch()
        rnd.timer = self.spawn(self.timeout(rnd))

    async def timeout(self, rnd):
        await asyncio.sleep(rnd.seconds)
        async with self.lock:
            if rnd.done or self.ended:
                return
            rnd.done = True
            self.empty_streak += 1
        await self.round_over(rnd, None)

    def points_for(self, rnd):
        elapsed = time.monotonic() - rnd.started
        return 10 + int(max(0.0, 1 - elapsed / rnd.seconds) * 10)

    async def handle_message(self, message):
        rnd = self.current
        if rnd is None or rnd.done or rnd.check is None or self.ended:
            return False
        verdict = rnd.check(message.content)
        if verdict is None:
            return False
        async with self.lock:
            if rnd.done:
                return False
            if message.author.id in rnd.locked:
                return True
            if not verdict:
                if rnd.choices:
                    rnd.locked.add(message.author.id)
                await safe_react(message, '❌')
                return True
            rnd.done = True
        await self.score_round(rnd, message.author)
        return True

    async def score_round(self, rnd, user):
        self.touch()
        if rnd.timer:
            rnd.timer.cancel()
        points = self.points_for(rnd)
        self.scores[user.id] = self.scores.get(user.id, 0) + points
        self.users[user.id] = user
        self.empty_streak = 0
        self.spawn(self.round_over(rnd, user, points))

    async def on_choice(self, interaction, index):
        rnd = self.current
        if rnd is None or rnd.done or interaction.message.id != getattr(self.message, 'id', None):
            return await ephemeral(interaction, '⌛ That round is already over.')
        async with self.lock:
            if rnd.done:
                return await ephemeral(interaction, '⌛ Someone just got it!')
            if interaction.user.id in rnd.locked:
                return await ephemeral(interaction, '🔒 You already answered this one.')
            if index != rnd.correct_index:
                rnd.locked.add(interaction.user.id)
                return await ephemeral(interaction, '❌ Not quite - you are locked out of this round.')
            rnd.done = True
        await interaction.response.defer()
        await self.score_round(rnd, interaction.user)

    async def on_skip(self, interaction, rnd):
        perms = getattr(interaction.user, 'guild_permissions', None)
        allowed = interaction.user.id == self.host.id or bool(perms and perms.manage_messages)
        if not allowed:
            return await ephemeral(interaction, f'Only {self.host.display_name} (who started this) can skip.')
        async with self.lock:
            if rnd.done or rnd is not self.current:
                return await ephemeral(interaction, '⌛ That round is already over.')
            rnd.done = True
        if rnd.timer:
            rnd.timer.cancel()
        await interaction.response.defer()
        await self.round_over(rnd, None, skipped=True)

    async def round_over(self, rnd, winner, points=0, skipped=False):
        if winner:
            embed = discord.Embed(title='✅ Correct!', description=f'**{winner.display_name}** got it - **+{points} pts**', color=PALETTE['green'])
        elif skipped:
            embed = discord.Embed(title='⏭️ Skipped', color=PALETTE['orange'])
        else:
            embed = discord.Embed(title="⏰ Time's up!", color=PALETTE['orange'])
        embed.add_field(name='Answer', value=f'**{rnd.answer}**', inline=False)
        if rnd.explanation:
            embed.add_field(name='Why', value=rnd.explanation, inline=False)
        kwargs = {'embed': embed}
        if rnd.reveal_file:
            reveal = rnd.reveal_file()
            kwargs['file'] = reveal
            embed.set_image(url=f'attachment://{reveal.filename}')
        try:
            await self.channel.send(**kwargs)
        except discord.HTTPException:
            pass
        await safe_edit(self.message, view=None)
        await asyncio.sleep(2.5 if winner else 3.5)
        await self.advance()

    async def finish_quiz(self):
        ranking = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
        embed = discord.Embed(title=f'🏁 {self.title} - final scores', color=PALETTE['gold'])
        if not ranking:
            embed.description = 'No points this time - try again with `splay`!'
        else:
            lines = []
            for place, (user_id, points) in enumerate(ranking[:10]):
                medal = MEDALS[place] if place < 3 else f'`{place + 1}.`'
                lines.append(f'{medal} {self.users[user_id].mention} - **{points}** pts')
                self.award(self.users[user_id], points, place == 0)
            embed.description = '\n'.join(lines)
            embed.set_footer(text='Points are added to your XP - check sprofile!')
        self.teardown()
        await self.channel.send(embed=embed)

    async def stop(self, by=None):
        if self.current and not self.current.done:
            self.current.done = True
            await self.channel.send(f'🛑 Stopped. The answer was **{self.current.answer}**.')
        await self.finish_quiz()


def classify(check_fn):
    return lambda text: {'correct': True, 'wrong': False}.get(check_fn(text))


# ------------------------------------------------------------------ Maths

class MathQuiz(RoundQuiz):
    key = 'math'
    emoji = '🧮'

    def __init__(self, bot, channel, host, topic=None, level=2, rounds=5, **_):
        super().__init__(bot, channel, host, rounds=rounds)
        self.topic_key = topic
        self.level = level
        if topic:
            info = mathgen.TOPICS[topic]
            self.title = f'{info.title} ({mathgen.LEVEL_NAMES[level]})'
            self.emoji = info.emoji
            self.color = discord.Color.from_rgb(*info.colors[0])
        else:
            self.title = f'Maths Mix ({mathgen.LEVEL_NAMES[level]})'

    async def make_round(self, number):
        key = self.topic_key or random.choice(list(mathgen.TOPICS))
        topic = mathgen.TOPICS[key]
        question = mathgen.generate(key, self.level)
        data = await asyncio.to_thread(
            images.question_card, topic.title, question.prompt, mathgen.LEVEL_NAMES[self.level],
            f'Round {number}/{self.total}', topic.colors, question.diagram)
        file = png_file(data, 'question.png', question.prompt)
        embed = discord.Embed(title=f'{topic.emoji} {topic.title}', color=self.color)
        embed.set_image(url='attachment://question.png')
        seconds = {1: 40, 2: 60, 3: 90}[self.level] + (25 if question.diagram else 0)
        return Round(embed, file, classify(lambda text: mathgen.check_answer(question, text)), question.display,
                     question.hint, seconds, question.explanation)


# ------------------------------------------------------------------ Trivia

TRIVIA_CATEGORIES = {
    'general': 9, 'books': 10, 'film': 11, 'movies': 11, 'music': 12, 'games': 15, 'videogames': 15, 'science': 17,
    'computers': 18, 'tech': 18, 'math': 19, 'maths': 19, 'mythology': 20, 'sports': 21, 'geography': 22, 'history': 23,
    'animals': 27, 'vehicles': 28, 'comics': 29, 'anime': 31, 'cartoons': 32,
}


class TriviaQuiz(RoundQuiz):
    key = 'trivia'
    title = 'Trivia'
    emoji = '🧠'
    color = PALETTE['purple']
    intro = 'Tap the right button (or type A-D). First correct answer wins the round!'

    def __init__(self, bot, channel, host, rounds=5, category=None, difficulty=None, **_):
        super().__init__(bot, channel, host, rounds=rounds)
        self.category = category
        self.difficulty = difficulty
        self.questions = []

    async def prepare(self):
        self.questions = await api.fetch_trivia(self.total, self.category, self.difficulty) or []
        if self.questions:
            self.total = len(self.questions)
        return bool(self.questions)

    async def make_round(self, number):
        if not self.questions:
            return None
        item = self.questions.pop(0)
        letters = 'ABCD'
        options = item['options'][:4]
        text = '\n'.join(f'**{letters[i]}.** {option}' for i, option in enumerate(options))
        embed = discord.Embed(title=item['question'], description=text, color=self.color)
        embed.set_author(name=f"{item['category']} • {item['difficulty'].title()}")
        correct_index = options.index(item['correct'])
        normalized = {re.sub(r'\W', '', option.lower()): i for i, option in enumerate(options)}

        def check(raw):
            cleaned = re.sub(r'\W', '', raw.strip().lower())
            if len(cleaned) == 1 and cleaned in 'abcd'[:len(options)]:
                return 'abcd'.index(cleaned) == correct_index
            if cleaned in normalized:
                return normalized[cleaned] == correct_index
            return None

        return Round(embed, None, check, f'{letters[correct_index]}. {item["correct"]}', None, 25, '', options, correct_index)


# ------------------------------------------------------------------ Word scramble

class ScrambleQuiz(RoundQuiz):
    key = 'scramble'
    title = 'Word Scramble'
    emoji = '🔤'
    color = PALETTE['orange']

    def __init__(self, bot, channel, host, rounds=5, **_):
        super().__init__(bot, channel, host, rounds=rounds)
        self.words = random.sample(WORDS.get('scramble', ['scramble']), k=min(self.total, len(WORDS.get('scramble', ['x']))))

    async def make_round(self, number):
        word = self.words[(number - 1) % len(self.words)]
        letters = list(word)
        for _ in range(20):
            random.shuffle(letters)
            if ''.join(letters) != word:
                break
        embed = discord.Embed(title='Unscramble the word!', description=f'## {" ".join(letters).upper()}\n{len(word)} letters', color=self.color)

        def check(raw):
            text = raw.strip().lower()
            if text == word:
                return True
            if text.isalpha() and len(text) == len(word):
                return False
            return None

        return Round(embed, None, check, word.upper(), f'It starts with **{word[0].upper()}** and ends with **{word[-1].upper()}**.', 40)


# ------------------------------------------------------------------ Riddles

class RiddleQuiz(RoundQuiz):
    key = 'riddle'
    title = 'Riddles'
    emoji = '🕵️'
    color = PALETTE['teal']

    def __init__(self, bot, channel, host, rounds=5, **_):
        super().__init__(bot, channel, host, rounds=rounds)
        self.pool = random.sample(RIDDLES, k=min(self.total, len(RIDDLES)))

    async def make_round(self, number):
        item = self.pool[(number - 1) % len(self.pool)]
        answers = {re.sub(r'[^a-z0-9 ]', '', a.lower()).strip() for a in item['a']}
        embed = discord.Embed(title='🧩 Riddle me this…', description=f"*{item['q']}*", color=self.color)

        def check(raw):
            text = re.sub(r'[^a-z0-9 ]', '', raw.lower()).strip()
            text = re.sub(r'^(a|an|the) ', '', text)
            if text in answers or any(text == re.sub(r'^(a|an|the) ', '', a) for a in answers):
                return True
            return False if 0 < len(text.split()) <= 3 and len(text) <= 24 else None

        first = item['a'][0]
        return Round(embed, None, check, first.title(), f'The answer has **{len(first)}** letters and starts with **{first[0].upper()}**.', 60)


# ------------------------------------------------------------------ Flags

POPULAR_FLAGS = (
    'in us gb ca au nz de fr it es pt nl be ch at se no dk fi is ie pl cz sk hu ro bg gr tr ru ua by cn jp kr kp th vn id my sg ph pk bd lk np bt '
    'af ir iq sa ae qa kw om ye jo lb sy il eg ly tn dz ma sd et ke tz ug ng gh za zw zm ao mz mg sn cm ci cd br ar cl pe co ve ec bo py uy mx cu '
    'jm ht do cr pa gt hn ni sv hr rs ba si mk al ee lv lt mt cy lu mn kz uz mm kh la tw ps ge am az'
).split()

FLAG_ALIASES = {
    'usa': 'united states', 'us': 'united states', 'america': 'united states', 'united states of america': 'united states',
    'uk': 'united kingdom', 'britain': 'united kingdom', 'great britain': 'united kingdom', 'england': 'united kingdom',
    'uae': 'united arab emirates', 'holland': 'netherlands', 'czech republic': 'czechia', 'burma': 'myanmar',
    'drc': 'dr congo', 'congo': 'dr congo', 'korea': 'south korea',
}


def squash(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    text = re.sub(r"[^a-z0-9 ]", ' ', text.lower())
    text = re.sub(r'^the ', '', ' '.join(text.split()))
    return text


def names_match(guess, names):
    guess = squash(guess)
    guess = FLAG_ALIASES.get(guess, guess)
    for name in names:
        name = squash(name)
        if guess == name:
            return True
        if len(name) >= 5 and len(guess) >= 4 and difflib.SequenceMatcher(None, guess, name).ratio() >= 0.88:
            return True
    return False


class FlagQuiz(RoundQuiz):
    key = 'flag'
    title = 'Guess the Flag'
    emoji = '🏳️'
    color = PALETTE['sky']

    def __init__(self, bot, channel, host, rounds=5, **_):
        super().__init__(bot, channel, host, rounds=rounds)
        self.codes = {}
        self.deck = []

    async def prepare(self):
        codes = await api.fetch_flag_codes()
        if not codes:
            return False
        self.codes = {code: codes[code] for code in POPULAR_FLAGS if code in codes}
        self.deck = random.sample(list(self.codes), k=min(self.total, len(self.codes)))
        return bool(self.deck)

    async def make_round(self, number):
        code = self.deck[(number - 1) % len(self.deck)]
        full = self.codes[code]
        name = full.split(' (')[0]
        names = [name, full] + re.findall(r'\(([^)]+)\)', full)
        embed = discord.Embed(title='Which country does this flag belong to?', color=self.color)
        embed.set_image(url=f'https://flagcdn.com/w640/{code}.png')

        def check(raw):
            text = raw.strip()
            if names_match(text, names):
                return True
            return False if 0 < len(text.split()) <= 4 and len(text) <= 30 and re.fullmatch(r"[A-Za-zÀ-ÿ .'-]+", text) else None

        return Round(embed, None, check, name, f'It starts with **{name[0]}** and has **{len(name)}** characters.', 30)


# ------------------------------------------------------------------ Pokémon

class PokemonQuiz(RoundQuiz):
    key = 'pokemon'
    title = "Who's That Pokémon?"
    emoji = '⚡'
    color = 0xFFCB05

    async def make_round(self, number):
        for _ in range(3):
            info = await api.fetch_pokemon(random.randint(1, 386))
            art = await api.get_bytes(info['art']) if info and info.get('art') else None
            if info and art:
                break
        else:
            return None
        pretty = info['name'].replace('-', ' ').title()
        accepted = {re.sub(r'[^a-z0-9]', '', info['name']), re.sub(r'[^a-z0-9]', '', info['name'].split('-')[0])}
        silhouette = await asyncio.to_thread(images.pokemon_card, art, False)
        embed = discord.Embed(title="Who's that Pokémon?", color=self.color)
        embed.set_image(url='attachment://pokemon.png')

        def check(raw):
            text = re.sub(r'[^a-z0-9]', '', raw.lower())
            if not text:
                return None
            if text in accepted or any(len(a) >= 5 and difflib.SequenceMatcher(None, text, a).ratio() >= 0.88 for a in accepted):
                return True
            return False if len(raw.split()) <= 2 and len(raw) <= 20 else None

        def reveal():
            return png_file(images.pokemon_card(art, True, pretty), 'reveal.png', pretty)

        hint = f"Type: **{', '.join(t.title() for t in info['types'])}** • starts with **{pretty[0]}**"
        return Round(embed, png_file(silhouette, 'pokemon.png', 'Pokémon silhouette'), check, pretty, hint, 30,
                     f"#{info['id']} • {info['height']} m • {info['weight']} kg", reveal_file=reveal)
