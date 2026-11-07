"""Async wrappers around free, keyless public APIs. Every fetcher returns None on failure."""
import html
import os
import random
from urllib.parse import quote

import aiohttp

_session = None

HEADERS = {'User-Agent': 'Speedyuwu-DiscordBot/3.0', 'Accept': 'application/json'}


def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10), headers=HEADERS)
    return _session


async def close_session():
    if _session is not None and not _session.closed:
        await _session.close()


async def get_json(url, **kwargs):
    try:
        async with get_session().get(url, **kwargs) as response:
            if response.status == 200:
                return await response.json(content_type=None)
    except Exception:
        pass
    return None


async def get_bytes(url, limit=5_000_000):
    try:
        async with get_session().get(url) as response:
            if response.status == 200 and (response.content_length or 0) <= limit:
                return await response.read()
    except Exception:
        pass
    return None


async def fetch_cat_image():
    data = await get_json('https://api.thecatapi.com/v1/images/search')
    if data:
        return data[0].get('url')
    return f'https://cataas.com/cat?{random.randint(1, 10000)}'


async def fetch_cat_fact():
    data = await get_json('https://meowfacts.herokuapp.com/')
    if data and 'data' in data:
        return data['data'][0]
    return None


async def fetch_random_emoji():
    data = await get_json('https://emojihub.yurace.pro/api/random')
    try:
        code = data['htmlCode'][0]
        char = chr(int(code.replace('&#', '').replace(';', '')))
        return f"{char} **{data.get('name', 'Random Emoji')}** ({data.get('category', '')})"
    except Exception:
        return None


async def fetch_chuck_norris_joke():
    data = await get_json('https://api.chucknorris.io/jokes/random')
    return data.get('value') if data else None


async def fetch_random_joke():
    data = await get_json('https://official-joke-api.appspot.com/random_joke')
    if data and data.get('setup') and data.get('punchline'):
        return f"{data['setup']}\n||{data['punchline']}||"
    return None


async def fetch_dad_joke():
    data = await get_json('https://icanhazdadjoke.com/')
    return data.get('joke') if data else None


async def fetch_dog_image():
    data = await get_json('https://dog.ceo/api/breeds/image/random')
    return data.get('message') if data else None


async def fetch_fox_image():
    data = await get_json('https://randomfox.ca/floof/')
    return data.get('image') if data else None


async def fetch_duck_image():
    data = await get_json('https://random-d.uk/api/v2/random')
    return data.get('url') if data else None


async def fetch_useless_fact():
    data = await get_json('https://uselessfacts.jsph.pl/api/v2/facts/random?language=en')
    return data.get('text') if data else None


async def fetch_advice():
    data = await get_json('https://api.adviceslip.com/advice')
    try:
        return data['slip']['advice']
    except Exception:
        return None


async def fetch_zen_quote():
    data = await get_json('https://zenquotes.io/api/random')
    try:
        return f"“{data[0]['q']}”\n— {data[0]['a']}"
    except Exception:
        return None


async def fetch_reddit_meme():
    for _ in range(3):
        data = await get_json('https://meme-api.com/gimme')
        if data and data.get('url') and not data.get('nsfw'):
            return data
    return None


async def fetch_nasa_apod():
    data = await get_json('https://api.nasa.gov/planetary/apod', params={'api_key': os.getenv('NASA_API_KEY', 'DEMO_KEY')})
    if data and data.get('media_type') == 'image':
        return data
    return None


async def fetch_reaction_gif(action):
    """Anime reaction GIFs from nekos.best (SFW only)."""
    data = await get_json(f'https://nekos.best/api/v2/{action}')
    try:
        result = data['results'][0]
        return result['url'], result.get('anime_name')
    except Exception:
        return None


async def fetch_giphy(query):
    """Optional: needs a free GIPHY_API_KEY in .env."""
    key = os.getenv('GIPHY_API_KEY')
    if not key:
        return 'no-key'
    data = await get_json('https://api.giphy.com/v1/gifs/search', params={
        'api_key': key, 'q': query, 'limit': 25, 'rating': 'pg-13'
    })
    try:
        return random.choice(data['data'])['images']['original']['url']
    except Exception:
        return None


async def fetch_trivia(amount=1, category=None, difficulty=None):
    params = {'amount': amount, 'type': 'multiple'}
    if category:
        params['category'] = category
    if difficulty:
        params['difficulty'] = difficulty
    data = await get_json('https://opentdb.com/api.php', params=params)
    if not data or data.get('response_code') != 0:
        return None
    questions = []
    for item in data['results']:
        correct = html.unescape(item['correct_answer'])
        options = [html.unescape(answer) for answer in item['incorrect_answers']] + [correct]
        random.shuffle(options)
        questions.append({
            'question': html.unescape(item['question']),
            'correct': correct,
            'options': options,
            'category': html.unescape(item['category']),
            'difficulty': item['difficulty'],
        })
    return questions


_flag_codes = None


async def fetch_flag_codes():
    global _flag_codes
    if _flag_codes is None:
        data = await get_json('https://flagcdn.com/en/codes.json')
        if data:
            # Drop sub-national codes like "us-ca" so questions are recognisable countries.
            _flag_codes = {code: name for code, name in data.items() if '-' not in code}
    return _flag_codes


async def fetch_pokemon(pokemon_id):
    data = await get_json(f"https://pokeapi.co/api/v2/pokemon/{quote(str(pokemon_id), safe='')}")
    if not data or 'id' not in data:
        return None
    art = (data.get('sprites', {}).get('other', {}).get('official-artwork', {}) or {}).get('front_default')
    return {
        'id': data['id'],
        'name': data['name'],
        'art': art or data.get('sprites', {}).get('front_default'),
        'types': [slot['type']['name'] for slot in data.get('types', [])],
        'height': data.get('height', 0) / 10,
        'weight': data.get('weight', 0) / 10,
        'stats': {stat['stat']['name']: stat['base_stat'] for stat in data.get('stats', [])},
    }
