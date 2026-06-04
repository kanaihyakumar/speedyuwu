import json
import os
import random
import ssl

import aiohttp
import certifi
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


def load_json_data(filename):
    try:
        filepath = os.path.join(os.path.dirname(__file__), 'data', filename)
        with open(filepath, 'r', encoding='utf-8') as file_handle:
            return json.load(file_handle)
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found in data directory!")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: {filename} contains invalid JSON!")
        return None
    except Exception as exc:
        print(f"❌ Error loading {filename}: {exc}")
        return None


def configure_ssl_certificates():
    ca_bundle = certifi.where()
    os.environ.setdefault('SSL_CERT_FILE', ca_bundle)
    os.environ.setdefault('REQUESTS_CA_BUNDLE', ca_bundle)
    original_create_default_context = ssl.create_default_context

    def patched_create_default_context(*args, **kwargs):
        if not args and 'cafile' not in kwargs and 'capath' not in kwargs and 'cadata' not in kwargs:
            kwargs['cafile'] = ca_bundle
        return original_create_default_context(*args, **kwargs)

    ssl.create_default_context = patched_create_default_context
    ssl._create_default_https_context = patched_create_default_context


configure_ssl_certificates()


async def fetch_cat_image():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.thecatapi.com/v1/images/search') as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        return data[0].get('url')
    except Exception:
        pass

    try:
        return f"https://cataas.com/cat?{random.randint(1, 10000)}"
    except Exception:
        return None


async def fetch_cat_fact():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meowfacts.herokuapp.com/') as response:
                if response.status == 200:
                    data = await response.json()
                    if data and 'data' in data:
                        return data['data'][0]
    except Exception:
        return None


async def fetch_random_emoji():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://emojihub.yurace.pro/api/random') as response:
                if response.status == 200:
                    data = await response.json()
                    emoji = data.get('htmlCode', [''])[0] if data else None
                    name = data.get('name', 'Random Emoji')
                    category = data.get('category', '')
                    if emoji:
                        emoji_char = chr(int(emoji.replace('&#', '').replace(';', '')))
                        return f"{emoji_char} **{name}** ({category})"
    except Exception:
        return None


async def fetch_chuck_norris_joke():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.chucknorris.io/jokes/random') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('value')
    except Exception:
        return None


async def fetch_random_joke():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://official-joke-api.appspot.com/random_joke') as response:
                if response.status == 200:
                    data = await response.json()
                    setup = data.get('setup', '')
                    punchline = data.get('punchline', '')
                    if setup and punchline:
                        return f"{setup}\n{punchline}"
    except Exception:
        return None


print('📂 Loading bot data from JSON files...')
quotes_data = load_json_data('quotes.json')
greetings_data = load_json_data('greetings.json')
jokes_data = load_json_data('jokes.json')
birthday_data = load_json_data('birthday.json')
memes_data = load_json_data('memes.json')
stickers_data = load_json_data('stickers.json')

SPEEDY_QUOTES = quotes_data.get('quotes', []) if quotes_data else []
MEOW_GREETS = greetings_data.get('greetings', []) if greetings_data else []
KNOCK_KNOCK_JOKES = jokes_data.get('jokes', []) if jokes_data else []
BIRTHDAY_MESSAGES = birthday_data.get('messages', []) if birthday_data else []
MEME_GIFS = memes_data.get('gifs', []) if memes_data else []
STICKER_GIFS = stickers_data if stickers_data else {}

CORE_COMMANDS = ['speedy', 'meow', 'happy birthday', 'knock knock', 'smeme', 'shelp', 'sgames']
API_COMMANDS = ['scat', 'catfact', 'semoji', 'sjoke', 'schuck']
GAME_COMMANDS = [
    'sgames',
    'sgame create <game>',
    'sgame join <id>',
    'sgame start <id>',
    'sgame move <id> <move>',
    'sgame status <id>',
    'sgame leave <id>',
    'sgame cancel <id>',
    'sgame rules <game>'
]

GAME_CATALOG = {
    'tictactoe': {
        'title': 'Tic Tac Toe',
        'description': 'Classic 3x3 duel. Use slots 1-9.',
        'min_players': 2,
        'max_players': 2,
        'move_template': 'sgame move {id} <1-9>',
        'aliases': ['ttt', 'tic-tac-toe']
    },
    'connect4': {
        'title': 'Connect 4',
        'description': 'Drop discs into columns 1-7 and connect four.',
        'min_players': 2,
        'max_players': 2,
        'move_template': 'sgame move {id} <1-7>',
        'aliases': ['connectfour', 'c4']
    },
    'nim': {
        'title': 'Nim',
        'description': 'Take 1-3 stones. The player taking the last stone wins.',
        'min_players': 2,
        'max_players': 2,
        'move_template': 'sgame move {id} <1-3>',
        'aliases': ['stones', '21']
    },
    'guessnumber': {
        'title': 'Guess Number',
        'description': 'Players take turns guessing a secret number from 1 to 50.',
        'min_players': 1,
        'max_players': 6,
        'move_template': 'sgame move {id} <1-50>',
        'aliases': ['guess', 'numberguess']
    }
}

ACTIVE_GAMES = {}
GAME_COUNTER = 1


def chunk_commands(commands_list, max_length=900):
    chunks = []
    current_chunk = []
    current_length = 0

    for command in commands_list:
        formatted = f'`{command}`'
        extra = len(formatted) + (2 if current_chunk else 0)
        if current_chunk and current_length + extra > max_length:
            chunks.append(', '.join(current_chunk))
            current_chunk = [formatted]
            current_length = len(formatted)
        else:
            current_chunk.append(formatted)
            current_length += extra

    if current_chunk:
        chunks.append(', '.join(current_chunk))

    return chunks


def mention_user(user_id):
    return f'<@{user_id}>'


def normalize_game_type(raw_name):
    if not raw_name:
        return None
    candidate = raw_name.lower().replace('_', '').replace('-', '')
    for game_type, info in GAME_CATALOG.items():
        candidates = [game_type] + info['aliases']
        for alias in candidates:
            if candidate == alias.lower().replace('_', '').replace('-', ''):
                return game_type
    return None


def generate_game_id():
    global GAME_COUNTER
    game_id = f'g{GAME_COUNTER:03d}'
    GAME_COUNTER += 1
    return game_id


def get_channel_games(channel_id):
    return [game for game in ACTIVE_GAMES.values() if game['channel_id'] == channel_id]


def get_channel_game(game_id, channel_id):
    game = ACTIVE_GAMES.get(game_id.lower())
    if game and game['channel_id'] == channel_id:
        return game
    return None


def format_players(player_ids):
    if not player_ids:
        return 'No players yet.'
    return '\n'.join(f'{index}. {mention_user(player_id)}' for index, player_id in enumerate(player_ids, start=1))


def build_help_embed():
    embed = discord.Embed(
        title='Speedyuwu Commands',
        description='Type any command exactly as shown.',
        color=discord.Color.blurple()
    )
    embed.add_field(name='Core', value=', '.join(f'`{command}`' for command in CORE_COMMANDS), inline=False)
    embed.add_field(name='API', value=', '.join(f'`{command}`' for command in API_COMMANDS), inline=False)
    embed.add_field(name='Game Commands', value=', '.join(f'`{command}`' for command in GAME_COMMANDS), inline=False)
    embed.add_field(
        name='Supported Games',
        value='\n'.join(
            f'`{game_name}` ({info["min_players"]}-{info["max_players"]} players): {info["description"]}'
            for game_name, info in GAME_CATALOG.items()
        ),
        inline=False
    )

    sticker_chunks = chunk_commands(sorted(STICKER_GIFS.keys()))
    for index, chunk in enumerate(sticker_chunks, start=1):
        field_name = 'Sticker Commands' if index == 1 else f'Sticker Commands {index}'
        embed.add_field(name=field_name, value=chunk, inline=False)

    embed.set_footer(text=f'{len(STICKER_GIFS)} sticker commands and {len(GAME_CATALOG)} multiplayer games available')
    return embed


def build_games_overview_embed(channel_id):
    embed = discord.Embed(
        title='Speedyuwu Multiplayer Games',
        description='Games use IDs, so multiple matches can run at the same time. Joined players only can make moves.',
        color=discord.Color.dark_teal()
    )

    for game_name, info in GAME_CATALOG.items():
        embed.add_field(
            name=info['title'],
            value=(
                f"{info['description']}\n"
                f"Players: {info['min_players']}-{info['max_players']}\n"
                f"Create: `sgame create {game_name}`\n"
                f"Move: `{info['move_template'].format(id='abc123')}`"
            ),
            inline=False
        )

    games = get_channel_games(channel_id)
    if games:
        embed.add_field(
            name='Current Channel Games',
            value='\n'.join(
                f"`{game['id']}` - {GAME_CATALOG[game['game_type']]['title']} - {game['status']} - {len(game['players'])}/{GAME_CATALOG[game['game_type']]['max_players']} players"
                for game in sorted(games, key=lambda item: item['id'])
            ),
            inline=False
        )
    else:
        embed.add_field(name='Current Channel Games', value='No active or waiting game lobbies in this channel.', inline=False)

    return embed


def render_tictactoe_board(board):
    rows = []
    for row_start in range(0, 9, 3):
        row = []
        for index in range(row_start, row_start + 3):
            row.append(board[index] if board[index] != ' ' else str(index + 1))
        rows.append(' | '.join(row))
    return '\n---------\n'.join(rows)


def get_tictactoe_winner(board):
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6)
    ]
    for first, second, third in lines:
        if board[first] in {'X', 'O'} and board[first] == board[second] == board[third]:
            return board[first]
    return None


def create_connect4_board():
    return [['.' for _ in range(7)] for _ in range(6)]


def render_connect4_board(board):
    rows = ['1 2 3 4 5 6 7']
    rows.extend(' '.join(row) for row in board)
    return '\n'.join(rows)


def drop_connect4_piece(board, column_index, marker):
    for row_index in range(len(board) - 1, -1, -1):
        if board[row_index][column_index] == '.':
            board[row_index][column_index] = marker
            return row_index
    return None


def connect4_has_winner(board, marker):
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    row_count = len(board)
    column_count = len(board[0])

    for row_index in range(row_count):
        for column_index in range(column_count):
            if board[row_index][column_index] != marker:
                continue
            for row_step, column_step in directions:
                matched = True
                for offset in range(1, 4):
                    next_row = row_index + row_step * offset
                    next_column = column_index + column_step * offset
                    if not (0 <= next_row < row_count and 0 <= next_column < column_count):
                        matched = False
                        break
                    if board[next_row][next_column] != marker:
                        matched = False
                        break
                if matched:
                    return True
    return False


def render_nim_state(stones_left):
    visible = min(stones_left, 21)
    return f"Stones left: {stones_left}\n" + ' '.join('o' for _ in range(visible))


def render_guessnumber_state(history):
    if not history:
        return 'No guesses yet.'
    return '\n'.join(
        f"{mention_user(entry['player_id'])}: {entry['guess']} ({entry['result']})"
        for entry in history[-6:]
    )


def initialize_game_state(game):
    if game['game_type'] == 'tictactoe':
        game['state'] = {
            'board': [str(index) for index in range(1, 10)],
            'markers': {
                game['players'][0]: 'X',
                game['players'][1]: 'O'
            }
        }
    elif game['game_type'] == 'connect4':
        game['state'] = {
            'board': create_connect4_board(),
            'markers': {
                game['players'][0]: 'R',
                game['players'][1]: 'Y'
            }
        }
    elif game['game_type'] == 'nim':
        game['state'] = {'stones_left': 21}
    elif game['game_type'] == 'guessnumber':
        game['state'] = {'target': random.randint(1, 50), 'history': []}


def render_game_state(game):
    if game['game_type'] == 'tictactoe':
        return 'Board', render_tictactoe_board(game['state']['board'])
    if game['game_type'] == 'connect4':
        return 'Board', render_connect4_board(game['state']['board'])
    if game['game_type'] == 'nim':
        return 'Stones', render_nim_state(game['state']['stones_left'])
    if game['game_type'] == 'guessnumber':
        return 'Guesses', render_guessnumber_state(game['state']['history'])
    return 'State', 'No state available.'


def build_game_embed(game, description=None):
    info = GAME_CATALOG[game['game_type']]
    color = discord.Color.blurple() if game['status'] == 'lobby' else discord.Color.green()
    embed = discord.Embed(
        title=f"{info['title']} [{game['id']}]",
        description=description or info['description'],
        color=color
    )
    embed.add_field(name='Status', value=game['status'].title(), inline=True)
    embed.add_field(name='Host', value=mention_user(game['host_id']), inline=True)
    embed.add_field(name='Players', value=f"{len(game['players'])}/{info['max_players']}", inline=True)
    embed.add_field(name='Participants', value=format_players(game['players']), inline=False)

    if game['status'] == 'lobby':
        embed.add_field(name='Join', value=f'`sgame join {game["id"]}`', inline=True)
        embed.add_field(name='Start', value=f'`sgame start {game["id"]}`', inline=True)
        embed.add_field(name='Rules', value=info['description'], inline=False)
    else:
        embed.add_field(name='Turn', value=mention_user(game['players'][game['turn_index'] % len(game['players'])]), inline=True)
        embed.add_field(name='Move', value=f"`{info['move_template'].format(id=game['id'])}`", inline=True)
        state_name, state_value = render_game_state(game)
        embed.add_field(name=state_name, value=f'```\n{state_value}\n```', inline=False)

    return embed


def build_finished_game_embed(game, description):
    info = GAME_CATALOG[game['game_type']]
    embed = discord.Embed(
        title=f"{info['title']} [{game['id']}] Finished",
        description=description,
        color=discord.Color.gold()
    )
    embed.add_field(name='Participants', value=format_players(game['players']), inline=False)
    state_name, state_value = render_game_state(game)
    embed.add_field(name=state_name, value=f'```\n{state_value}\n```', inline=False)
    return embed


def create_game_lobby(game_type, host_id, channel_id):
    game_id = generate_game_id()
    game = {
        'id': game_id,
        'game_type': game_type,
        'channel_id': channel_id,
        'host_id': host_id,
        'players': [host_id],
        'status': 'lobby',
        'turn_index': 0,
        'state': {}
    }
    ACTIVE_GAMES[game_id] = game
    return game


def cleanup_game(game):
    ACTIVE_GAMES.pop(game['id'], None)


def start_game(game):
    random.shuffle(game['players'])
    game['status'] = 'active'
    game['turn_index'] = 0
    initialize_game_state(game)


def get_game_rules_text(game_type):
    info = GAME_CATALOG[game_type]
    return f"{info['description']} Use `{info['move_template'].format(id='abc123')}` once the game starts."


def apply_tictactoe_move(game, player_id, move_value):
    if not move_value.isdigit():
        return False, 'Choose a slot from 1 to 9.', False

    slot = int(move_value)
    if slot < 1 or slot > 9:
        return False, 'Choose a slot from 1 to 9.', False

    board = game['state']['board']
    index = slot - 1
    if board[index] in {'X', 'O'}:
        return False, 'That slot is already taken.', False

    marker = game['state']['markers'][player_id]
    board[index] = marker
    winner = get_tictactoe_winner(board)
    if winner:
        return True, f'{mention_user(player_id)} wins with **{winner}**!', True

    if all(cell in {'X', 'O'} for cell in board):
        return True, 'It is a draw.', True

    game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    return True, f'{mention_user(player_id)} placed **{marker}** on slot **{slot}**.', False


def apply_connect4_move(game, player_id, move_value):
    if not move_value.isdigit():
        return False, 'Choose a column from 1 to 7.', False

    column = int(move_value)
    if column < 1 or column > 7:
        return False, 'Choose a column from 1 to 7.', False

    marker = game['state']['markers'][player_id]
    row_index = drop_connect4_piece(game['state']['board'], column - 1, marker)
    if row_index is None:
        return False, 'That column is full.', False

    if connect4_has_winner(game['state']['board'], marker):
        return True, f'{mention_user(player_id)} wins with **{marker}**!', True

    if all(cell != '.' for row in game['state']['board'] for cell in row):
        return True, 'It is a draw.', True

    game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    return True, f'{mention_user(player_id)} dropped **{marker}** into column **{column}**.', False


def apply_nim_move(game, player_id, move_value):
    if not move_value.isdigit():
        return False, 'Remove 1, 2, or 3 stones.', False

    amount = int(move_value)
    if amount < 1 or amount > 3:
        return False, 'Remove 1, 2, or 3 stones.', False

    stones_left = game['state']['stones_left']
    if amount > stones_left:
        return False, f'There are only {stones_left} stones left.', False

    game['state']['stones_left'] -= amount
    if game['state']['stones_left'] == 0:
        return True, f'{mention_user(player_id)} took the last stone and wins!', True

    game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    return True, f'{mention_user(player_id)} removed **{amount}** stone(s).', False


def apply_guessnumber_move(game, player_id, move_value):
    if not move_value.isdigit():
        return False, 'Guess a number from 1 to 50.', False

    guess = int(move_value)
    if guess < 1 or guess > 50:
        return False, 'Guess a number from 1 to 50.', False

    target = game['state']['target']
    if guess == target:
        game['state']['history'].append({'player_id': player_id, 'guess': guess, 'result': 'correct'})
        return True, f'{mention_user(player_id)} guessed **{guess}** and wins!', True

    result = 'higher' if guess < target else 'lower'
    game['state']['history'].append({'player_id': player_id, 'guess': guess, 'result': result})
    game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    return True, f'{mention_user(player_id)} guessed **{guess}**. Try {result}.', False


def apply_game_move(game, player_id, move_value):
    if game['game_type'] == 'tictactoe':
        return apply_tictactoe_move(game, player_id, move_value)
    if game['game_type'] == 'connect4':
        return apply_connect4_move(game, player_id, move_value)
    if game['game_type'] == 'nim':
        return apply_nim_move(game, player_id, move_value)
    if game['game_type'] == 'guessnumber':
        return apply_guessnumber_move(game, player_id, move_value)
    return False, 'That game is not implemented yet.', False


def build_start_message(game):
    first_player = mention_user(game['players'][game['turn_index'] % len(game['players'])])
    if game['game_type'] == 'tictactoe':
        first_id, second_id = game['players'][0], game['players'][1]
        return f'Game started. {mention_user(first_id)} is **X**, {mention_user(second_id)} is **O**. {first_player} goes first.'
    if game['game_type'] == 'connect4':
        first_id, second_id = game['players'][0], game['players'][1]
        return f'Game started. {mention_user(first_id)} is **R**, {mention_user(second_id)} is **Y**. {first_player} goes first.'
    return f'Game started. {first_player} goes first.'


async def send_game_usage(channel):
    embed = build_games_overview_embed(channel.id)
    embed.add_field(
        name='Lobby Flow',
        value='Create with `sgame create <game>`, join with `sgame join <id>`, then the host starts with `sgame start <id>`.',
        inline=False
    )
    embed.add_field(
        name='Control',
        value='Use `sgame status <id>` to inspect a game, `sgame leave <id>` to leave, and `sgame cancel <id>` for the host to stop a game.',
        inline=False
    )
    await channel.send(embed=embed)


async def handle_game_command(message, raw_content):
    parts = raw_content.strip().split()
    if len(parts) == 1:
        await send_game_usage(message.channel)
        return

    subcommand = parts[1].lower()
    args = parts[2:]

    if subcommand in {'help', 'list', 'games', 'active'}:
        await message.channel.send(embed=build_games_overview_embed(message.channel.id))
        return

    if subcommand == 'rules':
        if not args:
            await message.channel.send('Usage: `sgame rules <game>`')
            return
        game_type = normalize_game_type(args[0])
        if not game_type:
            await message.channel.send('Unknown game. Use `sgames` to see supported games.')
            return
        await message.channel.send(get_game_rules_text(game_type))
        return

    if subcommand == 'create':
        if not args:
            await message.channel.send('Usage: `sgame create <game>`')
            return
        game_type = normalize_game_type(args[0])
        if not game_type:
            await message.channel.send('Unknown game. Use `sgames` to see supported games.')
            return
        game = create_game_lobby(game_type, message.author.id, message.channel.id)
        await message.channel.send(embed=build_game_embed(game, f'{mention_user(message.author.id)} created a lobby.'))
        return

    if not args:
        await message.channel.send('This subcommand needs a game ID. Use `sgames` to inspect current lobbies.')
        return

    game_id = args[0].lower()
    game = get_channel_game(game_id, message.channel.id)
    if not game:
        await message.channel.send(f'No game with ID `{game_id}` exists in this channel.')
        return

    if subcommand == 'join':
        if game['status'] != 'lobby':
            await message.channel.send('That game has already started.')
            return
        if message.author.id in game['players']:
            await message.channel.send('You already joined that lobby.')
            return
        if len(game['players']) >= GAME_CATALOG[game['game_type']]['max_players']:
            await message.channel.send('That lobby is already full.')
            return
        game['players'].append(message.author.id)
        await message.channel.send(embed=build_game_embed(game, f'{mention_user(message.author.id)} joined the lobby.'))
        return

    if subcommand == 'leave':
        if message.author.id not in game['players']:
            await message.channel.send('You are not part of that game.')
            return
        if game['status'] == 'lobby':
            game['players'].remove(message.author.id)
            if not game['players']:
                cleanup_game(game)
                await message.channel.send(f'Game `{game_id}` closed because everyone left.')
                return
            if message.author.id == game['host_id']:
                game['host_id'] = game['players'][0]
            await message.channel.send(embed=build_game_embed(game, f'{mention_user(message.author.id)} left the lobby.'))
            return

        remaining_players = [player_id for player_id in game['players'] if player_id != message.author.id]
        if remaining_players:
            result = f'{mention_user(remaining_players[0])} wins by forfeit.'
        else:
            result = 'The game ended because nobody remained.'
        embed = build_finished_game_embed(game, result)
        cleanup_game(game)
        await message.channel.send(embed=embed)
        return

    if subcommand == 'start':
        if message.author.id != game['host_id']:
            await message.channel.send('Only the host can start that game.')
            return
        if game['status'] != 'lobby':
            await message.channel.send('That game is already running.')
            return
        if len(game['players']) < GAME_CATALOG[game['game_type']]['min_players']:
            await message.channel.send('Not enough players joined yet.')
            return
        start_game(game)
        await message.channel.send(embed=build_game_embed(game, build_start_message(game)))
        return

    if subcommand == 'status':
        await message.channel.send(embed=build_game_embed(game))
        return

    if subcommand == 'cancel':
        if message.author.id != game['host_id']:
            await message.channel.send('Only the host can cancel that game.')
            return
        title = GAME_CATALOG[game['game_type']]['title']
        cleanup_game(game)
        await message.channel.send(f'{mention_user(message.author.id)} canceled **{title}** game `{game_id}`.')
        return

    if subcommand == 'move':
        if len(args) < 2:
            usage = GAME_CATALOG[game['game_type']]['move_template'].format(id=game['id'])
            await message.channel.send(f'Usage: `{usage}`')
            return
        if game['status'] != 'active':
            await message.channel.send('That game has not started yet.')
            return
        if message.author.id not in game['players']:
            await message.channel.send('Only joined players can make moves in that game.')
            return
        if message.author.id != game['players'][game['turn_index'] % len(game['players'])]:
            await message.channel.send('It is not your turn.')
            return

        success, result_message, finished = apply_game_move(game, message.author.id, args[1])
        if not success:
            await message.channel.send(result_message)
            return
        if finished:
            embed = build_finished_game_embed(game, result_message)
            cleanup_game(game)
            await message.channel.send(embed=embed)
            return
        await message.channel.send(embed=build_game_embed(game, result_message))
        return

    await message.channel.send('Unknown game command. Use `sgames` for the full list.')


if not SPEEDY_QUOTES:
    print('⚠️  Warning: No quotes loaded!')
if not MEOW_GREETS:
    print('⚠️  Warning: No greetings loaded!')
if not KNOCK_KNOCK_JOKES:
    print('⚠️  Warning: No jokes loaded!')
if not BIRTHDAY_MESSAGES:
    print('⚠️  Warning: No birthday messages loaded!')
if not MEME_GIFS:
    print('⚠️  Warning: No meme GIFs loaded!')
if not STICKER_GIFS:
    print('⚠️  Warning: No sticker GIFs loaded!')
else:
    print(f'✅ Loaded {len(SPEEDY_QUOTES)} quotes, {len(MEOW_GREETS)} greetings, {len(KNOCK_KNOCK_JOKES)} jokes')
    print(f'✅ Loaded {len(BIRTHDAY_MESSAGES)} birthday messages, {len(MEME_GIFS)} meme GIFs')
    print(f'✅ Loaded {len(STICKER_GIFS)} sticker categories and {len(GAME_CATALOG)} games')


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='', intents=intents)


@bot.event
async def on_ready():
    print(f'🚀 {bot.user} is now online!')
    print(f'📝 Bot ID: {bot.user.id}')
    print(
        f'✅ Speedyuwu is ready to serve with {len(SPEEDY_QUOTES)} quotes, '
        f'{len(STICKER_GIFS)} sticker commands, and {len(GAME_CATALOG)} games!'
    )


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    raw_content = message.content.strip()
    content = raw_content.lower()

    if content == 'speedy':
        if SPEEDY_QUOTES:
            await message.channel.send(random.choice(SPEEDY_QUOTES))
        else:
            await message.channel.send('⚠️ No quotes available!')
        return

    if content == 'meow':
        if MEOW_GREETS:
            await message.channel.send(random.choice(MEOW_GREETS))
        else:
            await message.channel.send('⚠️ No greetings available!')
        return

    if content == 'happy birthday':
        if BIRTHDAY_MESSAGES:
            await message.channel.send(random.choice(BIRTHDAY_MESSAGES))
            await message.channel.send(random.choice(BIRTHDAY_MESSAGES))
            await message.channel.send('🎉 Double the wishes for double the happiness! Don\'t forget to throw a party! 🎊')
        else:
            await message.channel.send('⚠️ No birthday messages available!')
        return

    if content == 'knock knock':
        if KNOCK_KNOCK_JOKES:
            await message.channel.send(random.choice(KNOCK_KNOCK_JOKES))
        else:
            await message.channel.send('⚠️ No jokes available!')
        return

    if content == 'smeme':
        if MEME_GIFS:
            embed = discord.Embed(title='😂 Random Meme!', color=discord.Color.random())
            embed.set_image(url=random.choice(MEME_GIFS))
            await message.channel.send(embed=embed)
        else:
            await message.channel.send('⚠️ No meme GIFs available!')
        return

    if content == 'shelp':
        await message.channel.send(embed=build_help_embed())
        return

    if content == 'sgames':
        await message.channel.send(embed=build_games_overview_embed(message.channel.id))
        return

    if content.startswith('sgame '):
        await handle_game_command(message, raw_content)
        return

    if content in STICKER_GIFS:
        stickers = STICKER_GIFS.get(content, [])
        if stickers:
            embed = discord.Embed(color=discord.Color.random())
            embed.set_image(url=random.choice(stickers))
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(f'⚠️ No GIFs available for {content}!')
        return

    if content == 'scat':
        cat_url = await fetch_cat_image()
        if cat_url:
            embed = discord.Embed(title='🐱 Random Cat Picture!', color=discord.Color.orange())
            embed.set_image(url=cat_url)
            embed.set_footer(text='Powered by TheCatAPI & CATAAS')
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a cat image right now. Try again!")
        return

    if content == 'catfact':
        fact = await fetch_cat_fact()
        if fact:
            embed = discord.Embed(title='🐱 Cat Fact!', description=fact, color=discord.Color.blue())
            embed.set_footer(text='Powered by MeowFacts')
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a cat fact right now. Try again!")
        return

    if content == 'semoji':
        emoji_info = await fetch_random_emoji()
        if emoji_info:
            embed = discord.Embed(title='✨ Random Emoji!', description=emoji_info, color=discord.Color.gold())
            embed.set_footer(text='Powered by EmojiHub')
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch an emoji right now. Try again!")
        return

    if content == 'schuck':
        joke = await fetch_chuck_norris_joke()
        if joke:
            embed = discord.Embed(title='💪 Chuck Norris Joke', description=joke, color=discord.Color.red())
            embed.set_footer(text='Powered by api.chucknorris.io')
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a Chuck Norris joke right now. Try again!")
        return

    if content == 'sjoke':
        joke = await fetch_random_joke()
        if joke:
            embed = discord.Embed(title='😄 Random Joke', description=joke, color=discord.Color.green())
            embed.set_footer(text='Powered by Official Joke API')
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("⚠️ Couldn't fetch a joke right now. Try again!")
        return


if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('❌ Error: DISCORD_BOT_TOKEN not found in environment variables!')
        print('📝 Please create a .env file with your bot token.')
    else:
        bot.run(token)