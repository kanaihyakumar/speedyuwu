"""Session plumbing: one live game per channel, plus the lobby used by two-player games."""
import asyncio
import time

import discord

IDLE_SECONDS = 15 * 60


class Session:
    key = 'game'
    title = 'Game'
    emoji = '🎮'

    def __init__(self, bot, channel, host):
        self.bot = bot
        self.channel = channel
        self.host = host
        self.message = None
        self.ended = False
        self.last_active = time.monotonic()
        self.tasks = set()
        self.lock = asyncio.Lock()

    def touch(self):
        self.last_active = time.monotonic()

    def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def start(self):
        raise NotImplementedError

    async def handle_message(self, message):
        """Return True if the message was consumed as game input."""
        return False

    def teardown(self):
        """Synchronous clean-up: cancel timers and free the channel."""
        self.ended = True
        current = asyncio.current_task()
        for task in list(self.tasks):
            if task is not current:
                task.cancel()
        self.bot.sessions.release(self)

    async def stop(self, by=None):
        """Called by `sstop`. Subclasses may override to reveal answers."""
        self.teardown()
        await self.channel.send(f'🛑 **{self.title}** ended.')

    def can_stop(self, member):
        if member.id == self.host.id or self.is_participant(member.id):
            return True
        perms = getattr(member, 'guild_permissions', None)
        return bool(perms and (perms.manage_messages or perms.administrator))

    def is_participant(self, user_id):
        return False

    def award(self, user, xp, won=False):
        if getattr(user, 'bot', False):
            return
        self.bot.scores.record(user.id, user.display_name, self.key, xp, won)


class SessionManager:
    def __init__(self):
        self._sessions = {}

    def get(self, channel_id):
        session = self._sessions.get(channel_id)
        if session is None:
            return None
        if session.ended or time.monotonic() - session.last_active > IDLE_SECONDS:
            session.teardown()
            return None
        return session

    def claim(self, session):
        if self.get(session.channel.id):
            return False
        self._sessions[session.channel.id] = session
        return True

    def release(self, session):
        if self._sessions.get(session.channel.id) is session:
            del self._sessions[session.channel.id]

    def count(self):
        return len(self._sessions)


async def safe_react(message, emoji):
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        pass


async def safe_edit(message, **kwargs):
    if message is None:
        return
    try:
        await message.edit(**kwargs)
    except discord.HTTPException:
        pass


async def ephemeral(interaction, text):
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)
