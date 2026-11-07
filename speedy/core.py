"""Shared helpers: data loading, SSL setup, colours, and the persistent score store."""
import json
import os
import random
import ssl
import tempfile
from pathlib import Path

import certifi

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
STATE_DIR = Path(os.getenv('SPEEDY_STATE_DIR') or BASE_DIR / '.speedy')

PALETTE = {
    'blurple': 0x5865F2,
    'green': 0x2ECC71,
    'red': 0xE74C3C,
    'gold': 0xF1C40F,
    'orange': 0xE67E22,
    'pink': 0xFF6FB5,
    'teal': 0x1ABC9C,
    'purple': 0x9B59B6,
    'sky': 0x3498DB,
}


def random_color():
    return random.choice(list(PALETTE.values()))


def load_json_data(filename):
    try:
        with open(DATA_DIR / filename, 'r', encoding='utf-8') as file_handle:
            return json.load(file_handle)
    except FileNotFoundError:
        print(f"❌ Error: {filename} not found in data directory!")
    except json.JSONDecodeError:
        print(f"❌ Error: {filename} contains invalid JSON!")
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


RANKS = ['Rookie', 'Speedster', 'Brainiac', 'Wizard', 'Legend', 'Mythic', 'Galaxy Brain']


def level_for(xp):
    return 1 + int((max(xp, 0) / 40) ** 0.5)


def xp_for_level(level):
    return 40 * (level - 1) ** 2


def rank_for(level):
    return RANKS[min((level - 1) // 3, len(RANKS) - 1)]


class ScoreStore:
    """Tiny JSON-backed XP / win tracker. Writes are atomic so a crash can't corrupt it."""

    def __init__(self, path=None):
        self.path = Path(path) if path else STATE_DIR / 'scores.json'
        self.data = {}
        self._load()

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as handle:
                self.data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix='.tmp')
            with os.fdopen(handle, 'w', encoding='utf-8') as tmp:
                json.dump(self.data, tmp)
            os.replace(tmp_name, self.path)
        except OSError as exc:
            print(f'⚠️  Could not save scores: {exc}')

    def record(self, user_id, name, game, xp=0, won=False):
        entry = self.data.setdefault(str(user_id), {'name': name, 'xp': 0, 'played': 0, 'wins': {}})
        entry['name'] = name
        entry['xp'] += max(int(xp), 0)
        entry['played'] += 1
        if won:
            entry['wins'][game] = entry['wins'].get(game, 0) + 1
        self._save()
        return entry

    def get(self, user_id):
        return self.data.get(str(user_id))

    def top(self, limit=10):
        ranked = sorted(self.data.items(), key=lambda item: item[1].get('xp', 0), reverse=True)
        return [(int(user_id), entry) for user_id, entry in ranked[:limit]]
