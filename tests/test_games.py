import asyncio
import random

import pytest

from speedy.games import quiz, solo, versus
from speedy.games.solo import wordle_score
from tests.fakes import FakeBot, FakeChannel, FakeInteraction, FakeMessage, FakeUser

REAL_SLEEP = asyncio.sleep


@pytest.fixture
def env(tmp_path, monkeypatch):
    async def fast_sleep(delay, *args):
        await REAL_SLEEP(0.005 if delay <= 4 else delay)

    monkeypatch.setattr(versus.asyncio, 'sleep', fast_sleep)
    monkeypatch.setattr(quiz.asyncio, 'sleep', fast_sleep)
    bot = FakeBot(tmp_path)
    return bot, FakeChannel(), FakeUser('Alice')


async def launch(bot, session):
    assert bot.sessions.claim(session)
    await session.start()
    return session


def say(channel, user, text):
    return FakeMessage(channel, text, user)


# ------------------------------------------------------------------ session manager

async def test_one_session_per_channel(env):
    bot, channel, alice = env
    first = await launch(bot, solo.GuessNumber(bot, channel, alice))
    assert not bot.sessions.claim(solo.Wordle(bot, channel, alice))
    first.teardown()
    assert bot.sessions.get(channel.id) is None


# ------------------------------------------------------------------ versus games

@pytest.mark.parametrize('cls', [versus.TicTacToe, versus.ConnectFour, versus.Nim])
async def test_games_against_bot_always_finish(env, cls):
    bot, channel, alice = env
    random.seed(7)
    game = await launch(bot, cls(bot, channel, alice, opponent=bot.user))
    limit = {'TicTacToe': 9, 'ConnectFour': 7, 'Nim': 3}[cls.__name__]
    for _ in range(80):
        if game.ended:
            break
        if game.current.id == alice.id:
            await game.play(alice, random.randint(1, limit))
        else:
            await REAL_SLEEP(0.02)
    assert game.ended, 'game should reach an outcome'
    assert bot.scores.get(alice.id)['played'] == 1


async def test_ttt_human_win_and_buttons(env):
    bot, channel, alice = env
    bob = FakeUser('Bob')
    game = await launch(bot, versus.TicTacToe(bot, channel, alice, opponent=bob))
    first, second = game.players
    # first player takes top row (1,2,3); second plays 4,5
    for number, player in [(1, first), (4, second), (2, first), (5, second), (3, first)]:
        await game.play(player, number)
    assert game.ended
    assert game.outcome == ('win', 0)
    assert bot.scores.get(first.id)['wins'] == {'ttt': 1}
    assert bot.scores.get(second.id)['xp'] == 5


async def test_out_of_turn_and_taken_square_rejected(env):
    bot, channel, alice = env
    bob = FakeUser('Bob')
    game = await launch(bot, versus.TicTacToe(bot, channel, alice, opponent=bob))
    first, second = game.players
    interaction = FakeInteraction(second)
    await game.play(second, 5, interaction=interaction)
    assert 'turn' in interaction.response.calls[0][1]
    await game.play(first, 5)
    interaction = FakeInteraction(second)
    await game.play(second, 5, interaction=interaction)
    assert 'taken' in interaction.response.calls[0][1]


async def test_typed_number_only_counts_for_players(env):
    bot, channel, alice = env
    bob, carol = FakeUser('Bob'), FakeUser('Carol')
    game = await launch(bot, versus.ConnectFour(bot, channel, alice, opponent=bob))
    assert await game.handle_message(say(channel, carol, '4')) is False
    assert await game.handle_message(say(channel, alice, 'hello')) is False
    mover = game.current
    assert await game.handle_message(say(channel, mover, '4')) is True
    assert game.board[5][3] != '.'


async def test_connect4_vertical_win(env):
    bot, channel, alice = env
    bob = FakeUser('Bob')
    game = await launch(bot, versus.ConnectFour(bot, channel, alice, opponent=bob))
    first, second = game.players
    for _ in range(3):
        await game.play(first, 1)
        await game.play(second, 2)
    await game.play(first, 1)
    assert game.ended and game.outcome == ('win', 0)


async def test_resign_gives_win_to_opponent(env):
    bot, channel, alice = env
    bob = FakeUser('Bob')
    game = await launch(bot, versus.Nim(bot, channel, alice, opponent=bob))
    await game.resign(FakeInteraction(alice))
    assert game.ended
    assert game.outcome == ('win', 1 - game.index_of(alice.id))


async def test_nim_bot_plays_optimally_when_it_can(env):
    bot, channel, alice = env
    game = versus.Nim(bot, channel, alice, opponent=bot.user)
    game.stones = 6
    random.seed(1)
    assert sum(game.bot_choice() == 2 for _ in range(200)) > 150


def test_ttt_minimax_blocks_and_wins():
    board = list('XX OO    ')
    assert versus.ttt_best_move(board, 'X', 'O') == 2
    board = list('XX  O    ')
    assert versus.ttt_best_move(board, 'O', 'X') == 2


async def test_rps_vs_bot_best_of_three(env):
    bot, channel, alice = env
    game = await launch(bot, versus.RockPaperScissors(bot, channel, alice, opponent=bot.user))
    for _ in range(30):
        if game.ended:
            break
        await game.pick(FakeInteraction(alice), random.choice(['rock', 'paper', 'scissors']))
    assert game.ended
    assert max(game.scores) == 2


async def test_lobby_flow_join_and_bot(env):
    bot, channel, alice = env
    game = await launch(bot, versus.Nim(bot, channel, alice))
    assert game.phase == 'lobby'
    host_click = FakeInteraction(alice, message=channel.sent[0])
    await game.on_join(host_click)
    assert game.phase == 'lobby'
    bob = FakeUser('Bob')
    join = FakeInteraction(bob, message=channel.sent[0])
    await game.on_join(join)
    assert game.phase == 'playing'
    assert {p.id for p in game.players} == {alice.id, bob.id}


# ------------------------------------------------------------------ open games

async def test_guess_number_flow(env):
    bot, channel, alice = env
    bob = FakeUser('Bob')
    game = await launch(bot, solo.GuessNumber(bot, channel, alice))
    game.target = 42
    assert await game.handle_message(say(channel, alice, 'hello')) is False
    assert await game.handle_message(say(channel, alice, '30')) is True
    assert 'Higher' in channel.sent[-1].content
    assert await game.handle_message(say(channel, bob, '90')) is True
    assert 'Lower' in channel.sent[-1].content
    assert 'range **31–89**' in channel.sent[-1].content
    msg = say(channel, bob, '999999')
    assert await game.handle_message(msg) is False
    assert await game.handle_message(say(channel, bob, '42')) is True
    assert game.ended
    assert bot.scores.get(bob.id)['wins'] == {'guess': 1}
    assert bot.scores.get(alice.id)['xp'] == 5


async def test_guess_number_runs_out_of_guesses(env):
    bot, channel, alice = env
    game = await launch(bot, solo.GuessNumber(bot, channel, alice, args=['easy']))
    game.target = 50
    for _ in range(game.attempts):
        await game.handle_message(say(channel, alice, '1'))
    assert game.ended


async def test_hangman_win_and_loss(env):
    bot, channel, alice = env
    game = await launch(bot, solo.Hangman(bot, channel, alice))
    game.word = 'cat'
    await game.handle_message(say(channel, alice, 'c'))
    assert await game.handle_message(say(channel, alice, 'c')) is True  # duplicate gets a reaction, not an error
    assert await game.handle_message(say(channel, alice, 'hello there')) is False
    await game.handle_message(say(channel, alice, 'a'))
    await game.handle_message(say(channel, alice, 't'))
    assert game.ended
    assert bot.scores.get(alice.id)['wins'] == {'hangman': 1}

    game = await launch(bot, solo.Hangman(bot, channel, alice))
    game.word = 'cat'
    for letter in 'zxqwjv':
        await game.handle_message(say(channel, alice, letter))
    assert game.ended


async def test_hangman_whole_word_guess(env):
    bot, channel, alice = env
    game = await launch(bot, solo.Hangman(bot, channel, alice))
    game.word = 'rocket'
    await game.handle_message(say(channel, alice, 'planet'))
    assert not game.ended and game.wrong == ['planet']
    await game.handle_message(say(channel, alice, 'rocket'))
    assert game.ended


def test_wordle_scoring_handles_duplicates():
    assert wordle_score('crane', 'crane') == 'ggggg'
    assert wordle_score('speed', 'abide') == 'xxyxy'
    assert wordle_score('eerie', 'cheer') == 'yyyxx'
    assert wordle_score('llama', 'hello') == 'yyxxx'


async def test_wordle_flow(env):
    bot, channel, alice = env
    game = await launch(bot, solo.Wordle(bot, channel, alice))
    game.answer = 'crane'
    assert await game.handle_message(say(channel, alice, 'hi')) is False
    assert await game.handle_message(say(channel, alice, 'slope')) is True
    assert await game.handle_message(say(channel, alice, 'crane')) is True
    assert game.ended
    assert bot.scores.get(alice.id)['wins'] == {'wordle': 1}


# ------------------------------------------------------------------ quizzes

async def finish_quiz(game, channel, user, rounds):
    for _ in range(rounds):
        for _ in range(100):
            if game.current and not game.current.done:
                break
            await REAL_SLEEP(0.01)
        current = game.current
        assert await game.handle_message(say(channel, user, 'zz definitely wrong ~')) is False
        assert await game.handle_message(say(channel, user, current.answer)) is True
    for _ in range(200):
        if game.ended:
            break
        await REAL_SLEEP(0.01)


@pytest.mark.parametrize('topic', ['arithmetic', 'algebra', 'surds', 'trig'])
async def test_math_quiz_end_to_end(env, topic):
    bot, channel, alice = env
    game = await launch(bot, quiz.MathQuiz(bot, channel, alice, topic=topic, level=2, rounds=2))
    await finish_quiz(game, channel, alice, 2)
    assert game.ended
    assert bot.scores.get(alice.id)['wins'] == {'math': 1}
    assert bot.scores.get(alice.id)['xp'] >= 20
    assert any('final scores' in (e.title or '') for e in channel.embeds())


async def test_math_quiz_wrong_answer_gets_reaction_and_round_stays_open(env):
    bot, channel, alice = env
    game = await launch(bot, quiz.MathQuiz(bot, channel, alice, topic='arithmetic', level=1, rounds=1))
    msg = say(channel, alice, '-1234567')
    assert await game.handle_message(msg) is True
    assert msg.reactions == ['❌']
    assert not game.current.done
    game.teardown()


async def test_scramble_and_riddle_quizzes(env):
    bot, channel, alice = env
    game = await launch(bot, quiz.ScrambleQuiz(bot, channel, alice, rounds=1))
    answer = game.current.answer.lower()
    assert await game.handle_message(say(channel, alice, answer)) is True
    await REAL_SLEEP(0.1)
    game = await launch(bot, quiz.RiddleQuiz(bot, channel, alice, rounds=1))
    assert await game.handle_message(say(channel, alice, 'this is a long chat message not an answer')) is False
    assert await game.handle_message(say(channel, alice, game.current.answer)) is True
    await REAL_SLEEP(0.1)


async def test_trivia_buttons_and_typed_letters(env, monkeypatch):
    bot, channel, alice = env
    bob = FakeUser('Bob')

    async def fake_fetch(amount, category=None, difficulty=None):
        return [{'question': 'Capital of France?', 'correct': 'Paris', 'options': ['Rome', 'Paris', 'Berlin', 'Madrid'],
                 'category': 'Geography', 'difficulty': 'easy'}]

    monkeypatch.setattr(quiz.api, 'fetch_trivia', fake_fetch)
    game = await launch(bot, quiz.TriviaQuiz(bot, channel, alice, rounds=1))
    message = channel.sent[-1]
    wrong = FakeInteraction(bob, message=message)
    await game.on_choice(wrong, 0)
    assert 'locked out' in wrong.response.calls[0][1]
    again = FakeInteraction(bob, message=message)
    await game.on_choice(again, 1)
    assert 'already answered' in again.response.calls[0][1]
    assert await game.handle_message(say(channel, alice, 'b')) is True
    for _ in range(100):
        if game.ended:
            break
        await REAL_SLEEP(0.01)
    assert game.ended
    assert bot.scores.get(alice.id)['wins'] == {'trivia': 1}


def test_flag_name_matching():
    assert quiz.names_match('usa', ['United States'])
    assert quiz.names_match('Cote dIvoire', ["Côte d'Ivoire"])
    assert quiz.names_match('germny', ['Germany'])
    assert not quiz.names_match('india', ['Indonesia'])
    assert not quiz.names_match('oman', ['Romania'])


async def test_stop_reveals_answer(env):
    bot, channel, alice = env
    game = await launch(bot, solo.GuessNumber(bot, channel, alice))
    game.target = 7
    assert game.can_stop(alice)
    await game.stop(alice)
    assert game.ended and '7' in channel.sent[-1].content


def test_flag_parenthetical_names():
    names = ["Côte d'Ivoire", "Côte d'Ivoire (Ivory Coast)", 'Ivory Coast']
    assert quiz.names_match('ivory coast', names)
    assert quiz.names_match("cote d'ivoire", names)


async def test_trivia_typed_wrong_answer_locks_user_out(env, monkeypatch):
    bot, channel, alice = env

    async def fake_fetch(amount, category=None, difficulty=None):
        return [{'question': 'Q?', 'correct': 'Paris', 'options': ['Rome', 'Paris', 'Berlin', 'Madrid'],
                 'category': 'Geography', 'difficulty': 'easy'}]

    monkeypatch.setattr(quiz.api, 'fetch_trivia', fake_fetch)
    game = await launch(bot, quiz.TriviaQuiz(bot, channel, alice, rounds=1))
    await game.handle_message(say(channel, alice, 'a'))
    await game.handle_message(say(channel, alice, 'b'))
    assert not game.current.done
    game.teardown()
