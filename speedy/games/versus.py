"""Two-player games: lobby with Join / Play-vs-Bot buttons, button moves and typed moves."""
import asyncio
import io
import random

import discord

from .. import images
from ..core import PALETTE
from ..session import Session, ephemeral, safe_edit


class LobbyView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=180)
        self.game = game

    @discord.ui.button(label='Join & Play', emoji='⚔️', style=discord.ButtonStyle.success)
    async def join(self, interaction, button):
        await self.game.on_join(interaction)

    @discord.ui.button(label='Play vs Bot', emoji='🤖', style=discord.ButtonStyle.primary)
    async def vs_bot(self, interaction, button):
        await self.game.on_bot(interaction)

    @discord.ui.button(label='Cancel', emoji='✖️', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await self.game.on_cancel(interaction)

    async def on_timeout(self):
        await self.game.on_lobby_timeout()


class GameView(discord.ui.View):
    """Base view for running games: only the players may press buttons."""

    def __init__(self, game, timeout=900):
        super().__init__(timeout=timeout)
        self.game = game

    async def interaction_check(self, interaction):
        if self.game.index_of(interaction.user.id) is None:
            await ephemeral(interaction, '👀 You are spectating this one — start your own with `splay`!')
            return False
        return True

    async def on_timeout(self):
        await self.game.on_view_timeout(self)


class ResignButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label='Resign', emoji='🏳️', style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction):
        await self.view.game.resign(interaction)


class MoveButton(discord.ui.Button):
    def __init__(self, value, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    async def callback(self, interaction):
        await self.view.game.play(interaction.user, self.value, interaction=interaction)


class VersusGame(Session):
    min_players = 2
    blurb = ''
    color = PALETTE['blurple']

    def __init__(self, bot, channel, host, opponent=None, **_):
        super().__init__(bot, channel, host)
        self.opponent = opponent
        self.players = []
        self.phase = 'lobby'
        self.turn = 0
        self.outcome = None
        self.note = ''
        self.view = None
        self.lobby_view = None

    # ---- lobby

    async def start(self):
        if self.opponent:
            self.players = [self.host, self.opponent]
            await self.begin()
            return
        embed = discord.Embed(
            title=f'{self.emoji} {self.title}',
            description=f'{self.host.mention} wants to play!\n\n{self.blurb}',
            color=self.color,
        )
        embed.set_footer(text='Press ⚔️ Join & Play to take them on — or the host can play against the bot.')
        self.lobby_view = LobbyView(self)
        self.message = await self.channel.send(embed=embed, view=self.lobby_view)

    async def on_join(self, interaction):
        if self.phase != 'lobby':
            return await ephemeral(interaction, 'That game already started.')
        if interaction.user.id == self.host.id:
            return await ephemeral(interaction, 'You are the host 😄 — wait for a challenger, or press 🤖 Play vs Bot.')
        self.players = [self.host, interaction.user]
        self.lobby_view.stop()
        await self.begin(interaction)

    async def on_bot(self, interaction):
        if self.phase != 'lobby':
            return await ephemeral(interaction, 'That game already started.')
        if interaction.user.id != self.host.id:
            return await ephemeral(interaction, f'Only {self.host.display_name} can pick the bot. Press ⚔️ Join & Play instead!')
        self.players = [self.host, self.bot.user]
        self.lobby_view.stop()
        await self.begin(interaction)

    async def on_cancel(self, interaction):
        if interaction.user.id != self.host.id and not self.can_stop(interaction.user):
            return await ephemeral(interaction, 'Only the host can cancel this lobby.')
        self.teardown()
        self.lobby_view.stop()
        await interaction.response.edit_message(content='🚫 Lobby cancelled.', embed=None, view=None)

    async def on_lobby_timeout(self):
        if self.phase == 'lobby' and not self.ended:
            self.teardown()
            await safe_edit(self.message, content='⌛ Nobody joined, so the lobby closed. Start again any time!', embed=None, view=None)

    async def stop(self, by=None):
        if self.lobby_view:
            self.lobby_view.stop()
        self.teardown()
        await safe_edit(self.message, view=None)
        await self.channel.send(f'🛑 **{self.title}** ended.')

    async def on_view_timeout(self, view):
        if view is self.view and not self.ended:
            self.teardown()
            await safe_edit(self.message, content='⌛ Game timed out from inactivity.', view=None)

    # ---- flow

    def is_bot(self, user):
        return user.id == self.bot.user.id

    def index_of(self, user_id):
        for index, player in enumerate(self.players):
            if player.id == user_id:
                return index
        return None

    def is_participant(self, user_id):
        return self.index_of(user_id) is not None

    @property
    def current(self):
        return self.players[self.turn]

    async def begin(self, interaction=None):
        self.phase = 'playing'
        random.shuffle(self.players)
        self.turn = 0
        self.setup()
        self.touch()
        await self.show(interaction)
        await self.maybe_bot_move()

    async def show(self, interaction=None, repost=False, final=False):
        embed, file, view = self.build(final)
        self.view = view
        kwargs = {'embed': embed}
        if view is not None:
            kwargs['view'] = view
        if interaction is not None and not interaction.response.is_done():
            if file:
                kwargs['attachments'] = [file]
            if view is None:
                kwargs['view'] = None
            await interaction.response.edit_message(**kwargs)
            self.message = interaction.message
        elif repost or self.message is None:
            old = self.message
            if file:
                kwargs['file'] = file
            self.message = await self.channel.send(**kwargs)
            if old is not None:
                try:
                    await old.delete()
                except discord.HTTPException:
                    pass
        else:
            if file:
                kwargs['attachments'] = [file]
            if view is None:
                kwargs['view'] = None
            await safe_edit(self.message, **kwargs)

    async def reject(self, interaction, message, text):
        if interaction is not None:
            await ephemeral(interaction, text)
        elif message is not None:
            try:
                await message.reply(text, mention_author=False, delete_after=6)
            except discord.HTTPException:
                pass

    async def handle_message(self, message):
        if self.phase != 'playing' or self.ended:
            return False
        text = message.content.strip()
        if not text.isdigit() or len(text) > 2:
            return False
        if self.index_of(message.author.id) is None:
            return False
        await self.play(message.author, int(text), message=message)
        return True

    async def play(self, user, value, interaction=None, message=None):
        async with self.lock:
            if self.ended or self.phase != 'playing':
                return await self.reject(interaction, message, 'That game is over.')
            index = self.index_of(user.id)
            if index != self.turn:
                return await self.reject(interaction, message, f"⏳ It's {self.current.display_name}'s turn.")
            error = self.apply(index, value)
            if error:
                return await self.reject(interaction, message, error)
            self.touch()
            if self.outcome:
                return await self.conclude(interaction, repost=message is not None)
            self.turn = 1 - self.turn
            await self.show(interaction, repost=message is not None)
        await self.maybe_bot_move()

    async def maybe_bot_move(self):
        if self.ended or self.phase != 'playing' or not self.is_bot(self.current):
            return
        await asyncio.sleep(random.uniform(0.8, 1.5))
        async with self.lock:
            if self.ended or self.phase != 'playing':
                return
            self.apply(self.turn, self.bot_choice())
            if self.outcome:
                return await self.conclude(None)
            self.turn = 1 - self.turn
            await self.show()

    async def resign(self, interaction):
        index = self.index_of(interaction.user.id)
        async with self.lock:
            if self.ended or index is None or self.phase != 'playing':
                return
            self.outcome = ('win', 1 - index)
            self.note = f'🏳️ {interaction.user.display_name} resigned.'
            await self.conclude(interaction)

    async def conclude(self, interaction, repost=False):
        self.phase = 'done'
        await self.show(interaction, repost=repost, final=True)
        kind, winner = self.outcome
        humans = [player for player in self.players if not self.is_bot(player)]
        vs_bot = len(humans) == 1
        for player in humans:
            index = self.index_of(player.id)
            if kind == 'draw':
                self.award(player, 8, False)
            elif winner == index:
                self.award(player, 12 if vs_bot else 30, True)
            else:
                self.award(player, 2 if vs_bot else 5, False)
        self.teardown()

    # ---- shared embed helpers

    def result_text(self):
        kind, winner = self.outcome
        if kind == 'draw':
            return "🤝 It's a draw!"
        return f'🏆 **{self.players[winner].display_name}** wins!'

    def new_embed(self, final=False):
        color = PALETTE['gold'] if final else self.color
        title = f'{self.emoji} {self.title}' + (' — Game over' if final else '')
        embed = discord.Embed(title=title, color=color)
        if final:
            embed.description = (self.note + '\n' if self.note else '') + self.result_text()
        else:
            embed.description = f"🎯 {self.current.mention}'s turn"
        return embed

    # ---- hooks for subclasses

    def setup(self):
        raise NotImplementedError

    def apply(self, index, value):
        raise NotImplementedError

    def bot_choice(self):
        raise NotImplementedError

    def build(self, final=False):
        raise NotImplementedError


# ------------------------------------------------------------------ Tic Tac Toe

TTT_LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def ttt_winner(board):
    for line in TTT_LINES:
        a, b, c = line
        if board[a] != ' ' and board[a] == board[b] == board[c]:
            return board[a], line
    return None, None


def ttt_best_move(board, me, opp):
    memo = {}

    def score(state, turn):
        key = (state, turn)
        if key in memo:
            return memo[key]
        winner, _ = ttt_winner(state)
        if winner:
            result = 1 if winner == me else -1
        elif ' ' not in state:
            result = 0
        else:
            results = []
            for index in range(9):
                if state[index] == ' ':
                    nxt = state[:index] + turn + state[index + 1:]
                    results.append(score(nxt, opp if turn == me else me))
            result = max(results) if turn == me else min(results)
        memo[key] = result
        return result

    empties = [index for index in range(9) if board[index] == ' ']
    if len(empties) == 9:
        return random.choice([0, 2, 4, 6, 8])
    state = ''.join(board)
    scored = [(score(state[:i] + me + state[i + 1:], opp), i) for i in empties]
    best = max(value for value, _ in scored)
    return random.choice([i for value, i in scored if value == best])


class TicTacToe(VersusGame):
    key = 'ttt'
    title = 'Tic Tac Toe'
    emoji = '❌'
    blurb = 'Get three in a row! Tap a square — or just type its number **1-9**.'
    color = PALETTE['pink']
    MARKS = ('X', 'O')
    ICONS = {'X': '❌', 'O': '⭕'}

    def setup(self):
        self.board = [' '] * 9
        self.win_line = None

    def apply(self, index, value):
        if not 1 <= value <= 9:
            return 'Pick a square from 1 to 9.'
        if self.board[value - 1] != ' ':
            return '🚫 That square is already taken.'
        self.board[value - 1] = self.MARKS[index]
        winner, line = ttt_winner(self.board)
        if winner:
            self.outcome, self.win_line = ('win', self.MARKS.index(winner)), line
        elif ' ' not in self.board:
            self.outcome = ('draw', None)
        return None

    def bot_choice(self):
        me, opp = self.MARKS[self.turn], self.MARKS[1 - self.turn]
        empties = [i for i in range(9) if self.board[i] == ' ']
        if random.random() < 0.15:
            return random.choice(empties) + 1
        return ttt_best_move(self.board, me, opp) + 1

    def build(self, final=False):
        embed = self.new_embed(final)
        embed.add_field(name='Players', value=' vs '.join(f'{self.ICONS[self.MARKS[i]]} {p.mention}' for i, p in enumerate(self.players)), inline=False)
        if not final:
            embed.set_footer(text='Tip: you can also just type a number 1-9')
        view = GameView(self)
        for cell in range(9):
            mark = self.board[cell]
            kwargs = {'row': cell // 3}
            if mark == ' ':
                kwargs.update(label=str(cell + 1), style=discord.ButtonStyle.secondary, disabled=final)
            else:
                highlight = self.win_line and cell in self.win_line
                style = discord.ButtonStyle.success if highlight else (discord.ButtonStyle.danger if mark == 'X' else discord.ButtonStyle.primary)
                kwargs.update(emoji=self.ICONS[mark], style=style, disabled=True)
            view.add_item(MoveButton(cell + 1, **kwargs))
        if not final:
            view.add_item(ResignButton(row=3))
        return embed, None, view


# ------------------------------------------------------------------ Connect 4

C4_ROWS, C4_COLS = 6, 7


def c4_winner(board, marker):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for row in range(C4_ROWS):
        for col in range(C4_COLS):
            for dr, dc in directions:
                cells = [(row + dr * step, col + dc * step) for step in range(4)]
                if all(0 <= r < C4_ROWS and 0 <= c < C4_COLS and board[r][c] == marker for r, c in cells):
                    return cells
    return None


def c4_drop(board, col, marker):
    for row in range(C4_ROWS - 1, -1, -1):
        if board[row][col] == '.':
            board[row][col] = marker
            return row
    return None


class ConnectFour(VersusGame):
    key = 'c4'
    title = 'Connect 4'
    emoji = '🔴'
    blurb = 'Drop discs and connect four! Tap a column — or just type **1-7**.'
    color = PALETTE['sky']
    MARKS = ('R', 'Y')
    ICONS = {'R': '🔴', 'Y': '🟡'}

    def setup(self):
        self.board = [['.'] * C4_COLS for _ in range(C4_ROWS)]
        self.last = None
        self.win_cells = None

    def full_column(self, col):
        return self.board[0][col] != '.'

    def apply(self, index, value):
        if not 1 <= value <= C4_COLS:
            return 'Pick a column from 1 to 7.'
        if self.full_column(value - 1):
            return '🚫 That column is full.'
        marker = self.MARKS[index]
        row = c4_drop(self.board, value - 1, marker)
        self.last = (row, value - 1)
        cells = c4_winner(self.board, marker)
        if cells:
            self.outcome, self.win_cells = ('win', index), cells
        elif all(self.full_column(col) for col in range(C4_COLS)):
            self.outcome = ('draw', None)
        return None

    def bot_choice(self):
        me, opp = self.MARKS[self.turn], self.MARKS[1 - self.turn]
        valid = [c for c in range(C4_COLS) if not self.full_column(c)]

        def wins(col, marker):
            board = [row[:] for row in self.board]
            if c4_drop(board, col, marker) is None:
                return False
            return c4_winner(board, marker) is not None

        for col in valid:
            if wins(col, me):
                return col + 1
        for col in valid:
            if wins(col, opp):
                return col + 1
        def gives_win(col):
            board = [row[:] for row in self.board]
            c4_drop(board, col, me)
            for other in range(C4_COLS):
                trial = [row[:] for row in board]
                if c4_drop(trial, other, opp) is not None and c4_winner(trial, opp):
                    return True
            return False

        safe = [col for col in valid if not gives_win(col)]
        pool = safe or valid
        weights = [4 - abs(3 - col) + 0.5 for col in pool]
        return random.choices(pool, weights=weights)[0] + 1

    def build(self, final=False):
        embed = self.new_embed(final)
        embed.add_field(name='Players', value=' vs '.join(f'{self.ICONS[self.MARKS[i]]} {p.mention}' for i, p in enumerate(self.players)), inline=False)
        data = images.connect4_image(self.board, self.last, self.win_cells)
        file = discord.File(io.BytesIO(data.getvalue()), filename='board.png', description='Connect 4 board')
        embed.set_image(url='attachment://board.png')
        if not final:
            embed.set_footer(text='Tip: you can also just type a column number 1-7')
        view = None
        if not final:
            view = GameView(self)
            for col in range(C4_COLS):
                view.add_item(MoveButton(col + 1, label=str(col + 1), style=discord.ButtonStyle.primary,
                                         disabled=self.full_column(col), row=0 if col < 5 else 1))
            view.add_item(ResignButton(row=1))
        return embed, file, view


# ------------------------------------------------------------------ Nim

class Nim(VersusGame):
    key = 'nim'
    title = 'Nim (21 Stones)'
    emoji = '🪨'
    blurb = 'Take **1, 2 or 3** stones each turn. Whoever takes the **last** stone wins! Tap a button or type 1-3.'
    color = PALETTE['orange']

    def setup(self):
        self.stones = 21

    def apply(self, index, value):
        if not 1 <= value <= 3:
            return 'Take 1, 2 or 3 stones.'
        if value > self.stones:
            return f'Only {self.stones} stone(s) left!'
        self.stones -= value
        if self.stones == 0:
            self.outcome = ('win', index)
        return None

    def bot_choice(self):
        optimal = self.stones % 4
        if optimal and random.random() < 0.85:
            return optimal
        return random.randint(1, min(3, self.stones))

    def build(self, final=False):
        embed = self.new_embed(final)
        rows = []
        remaining = self.stones
        while remaining > 0:
            rows.append('🪨' * min(7, remaining))
            remaining -= 7
        embed.add_field(name=f'Stones left: {self.stones}', value='\n'.join(rows) or '🕳️ All gone!', inline=False)
        embed.add_field(name='Players', value=' vs '.join(p.mention for p in self.players), inline=False)
        view = None
        if not final:
            view = GameView(self)
            for amount in (1, 2, 3):
                view.add_item(MoveButton(amount, label=f'Take {amount}', emoji='🪨', style=discord.ButtonStyle.primary, disabled=amount > self.stones))
            view.add_item(ResignButton(row=0))
            embed.set_footer(text='Tip: you can also just type 1, 2 or 3')
        return embed, None, view


# ------------------------------------------------------------------ Rock Paper Scissors

RPS_ICONS = {'rock': '✊', 'paper': '✋', 'scissors': '✌️'}
RPS_BEATS = {'rock': 'scissors', 'paper': 'rock', 'scissors': 'paper'}


class RpsButton(discord.ui.Button):
    def __init__(self, choice):
        super().__init__(label=choice.title(), emoji=RPS_ICONS[choice], style=discord.ButtonStyle.primary)
        self.choice = choice

    async def callback(self, interaction):
        await self.view.game.pick(interaction, self.choice)


class RockPaperScissors(VersusGame):
    key = 'rps'
    title = 'Rock Paper Scissors'
    emoji = '✌️'
    blurb = 'Best of 3. Picks are secret until both players have chosen!'
    color = PALETTE['purple']

    def setup(self):
        self.picks = {}
        self.scores = [0, 0]
        self.round = 1
        self.last_round = None

    async def handle_message(self, message):
        return False

    def apply(self, index, value):
        return None

    def bot_choice(self):
        return random.choice(list(RPS_ICONS))

    async def maybe_bot_move(self):
        return

    async def pick(self, interaction, choice):
        index = self.index_of(interaction.user.id)
        async with self.lock:
            if self.ended or self.phase != 'playing' or index is None:
                return await ephemeral(interaction, 'That game is over.')
            if index in self.picks:
                return await ephemeral(interaction, '🔒 You already locked in this round.')
            self.picks[index] = choice
            self.touch()
            await ephemeral(interaction, f'{RPS_ICONS[choice]} You picked **{choice}** — shhh, it is secret!')
            other = 1 - index
            if self.is_bot(self.players[other]):
                self.picks[other] = self.bot_choice()
            if len(self.picks) < 2:
                return await self.show()
            await self.resolve()

    async def resolve(self):
        first, second = self.picks[0], self.picks[1]
        if first == second:
            winner = None
        else:
            winner = 0 if RPS_BEATS[first] == second else 1
        if winner is not None:
            self.scores[winner] += 1
        self.last_round = (first, second, winner)
        self.picks = {}
        self.round += 1
        if max(self.scores) >= 2:
            winner_index = self.scores.index(max(self.scores))
            self.outcome = ('win', winner_index)
            return await self.conclude(None)
        await self.show()

    def build(self, final=False):
        embed = self.new_embed(final)
        if not final:
            embed.description = f'**Round {self.round}** — pick your move! Choices stay secret until both players lock in.'
        lines = []
        for index, player in enumerate(self.players):
            status = '' if final else (' ✅ locked in' if index in self.picks else ' ⏳')
            lines.append(f'{player.mention} — **{self.scores[index]}**{status}')
        embed.add_field(name='Score (first to 2)', value='\n'.join(lines), inline=False)
        file = None
        if self.last_round:
            first, second, winner = self.last_round
            data = images.rps_banner(self.players[0].display_name, self.players[1].display_name, first, second)
            file = discord.File(io.BytesIO(data.getvalue()), filename='rps.png', description='Rock paper scissors result')
            embed.set_image(url='attachment://rps.png')
            verdict = 'Tie — go again!' if winner is None else f'{self.players[winner].display_name} takes the round!'
            embed.add_field(name='Last round', value=verdict, inline=False)
        view = None
        if not final:
            view = GameView(self)
            for choice in RPS_ICONS:
                view.add_item(RpsButton(choice))
        return embed, file, view
