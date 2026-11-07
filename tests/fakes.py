"""Minimal stand-ins for discord objects so game logic can be tested without a connection."""
import itertools

from speedy.core import ScoreStore
from speedy.session import SessionManager

_ids = itertools.count(1000)


class FakeUser:
    def __init__(self, name='Player', bot=False):
        self.id = next(_ids)
        self.display_name = name
        self.mention = f'<@{self.id}>'
        self.bot = bot


class FakeMessage:
    def __init__(self, channel, content='', author=None, **sent):
        self.id = next(_ids)
        self.channel = channel
        self.content = content
        self.author = author
        self.sent = sent
        self.reactions = []
        self.edits = []
        self.deleted = False

    async def edit(self, **kwargs):
        self.edits.append(kwargs)

    async def delete(self):
        self.deleted = True

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)

    async def reply(self, content=None, **kwargs):
        return await self.channel.send(content, **kwargs)


class FakeChannel:
    def __init__(self):
        self.id = next(_ids)
        self.sent = []

    async def send(self, content=None, **kwargs):
        message = FakeMessage(self, content or '', None, **kwargs)
        self.sent.append(message)
        return message

    def embeds(self):
        return [m.sent['embed'] for m in self.sent if 'embed' in m.sent]


class FakeBot:
    def __init__(self, tmp_path):
        self.user = FakeUser('SpeedyBot', bot=True)
        self.sessions = SessionManager()
        self.scores = ScoreStore(tmp_path / 'scores.json')


class FakeResponse:
    def __init__(self):
        self._done = False
        self.calls = []

    def is_done(self):
        return self._done

    async def edit_message(self, **kwargs):
        self._done = True
        self.calls.append(('edit', kwargs))

    async def send_message(self, content=None, **kwargs):
        self._done = True
        self.calls.append(('send', content, kwargs))

    async def defer(self, **kwargs):
        self._done = True
        self.calls.append(('defer',))


class FakeInteraction:
    def __init__(self, user, message=None, channel=None):
        self.user = user
        self.message = message
        self.channel = channel
        self.response = FakeResponse()
        self.data = {}
