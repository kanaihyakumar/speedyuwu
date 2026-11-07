"""Pillow renderers: question cards, boards, hangman, wordle tiles, profile cards."""
import io
import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .core import DATA_DIR

FONT_DIR = DATA_DIR / 'fonts'
INK = (28, 30, 52)


@lru_cache(maxsize=64)
def font(size, bold=False):
    path = FONT_DIR / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size)


def to_file_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=False)
    buffer.seek(0)
    return buffer


def gradient(width, height, start, end):
    base = Image.new('RGB', (width, height), start)
    top = Image.new('RGB', (width, height), end)
    mask = Image.linear_gradient('L').resize((width, height))
    return Image.composite(top, base, mask)


def _bubbles(image, accent):
    layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    width, height = image.size
    for cx, cy, radius, alpha in [(width * 0.92, height * 0.1, 140, 40), (width * 0.05, height * 0.95, 120, 36), (width * 0.75, height * 0.9, 70, 30)]:
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*accent, alpha))
    image.paste(Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB'))


def wrap(draw, text, fnt, max_width):
    lines = []
    for paragraph in text.split('\n'):
        words, current = paragraph.split(' '), ''
        for word in words:
            trial = f'{current} {word}'.strip()
            if draw.textlength(trial, font=fnt) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_triangle(draw, box, spec):
    left, top, right, bottom = box
    angle_value = spec.get('angle_value')
    theta = angle_value if isinstance(angle_value, (int, float)) else spec.get('angle')
    theta = float(theta) if isinstance(theta, (int, float)) else 35.0
    theta = min(max(theta, 15.0), 70.0)
    width_available, height_available = right - left, bottom - top
    base = width_available
    rise = base * math.tan(math.radians(theta))
    if rise > height_available:
        base, rise = height_available / math.tan(math.radians(theta)), height_available
    ax, ay = left + (width_available - base) / 2, bottom
    bx, by = ax + base, bottom
    cx, cy = bx, bottom - rise
    draw.polygon([(ax, ay), (bx, by), (cx, cy)], fill=(235, 240, 255), outline=(60, 80, 200))
    draw.line([(ax, ay), (bx, by), (cx, cy), (ax, ay)], fill=(60, 80, 200), width=5, joint='curve')
    size = 22
    draw.line([(bx - size, by), (bx - size, by - size), (bx, by - size)], fill=(60, 80, 200), width=3)

    arc_box = (ax - 46, ay - 46, ax + 46, ay + 46)
    draw.arc(arc_box, -theta, 0, fill=(231, 76, 60), width=4)
    angle_label = spec.get('angle')
    if angle_label not in ('', None):
        label = 'θ' if angle_label == '?' else f'{angle_label}°'
        draw.text((ax + 56, ay - 34), label, font=font(24, True), fill=(231, 76, 60))

    def put(text, xy, anchor):
        if text:
            color = (231, 76, 60) if text == 'x' else INK
            draw.text(xy, text, font=font(28, True), fill=color, anchor=anchor)

    put(spec.get('adj', ''), ((ax + bx) / 2, by + 8), 'ma')
    put(spec.get('opp', ''), (bx + 12, (by + cy) / 2), 'lm')
    put(spec.get('hyp', ''), ((ax + cx) / 2 - 14, (ay + cy) / 2 - 14), 'rb')


def question_card(topic_title, prompt, level_name, round_text, colors, diagram=None):
    width = 900
    scratch = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    prompt_font = font(40, True)
    lines = wrap(scratch, prompt, prompt_font, width - 140 - (0 if not diagram else 0))
    text_height = len(lines) * 56
    diagram_height = 270 if diagram else 0
    height = max(150 + text_height + diagram_height + 50, 280)

    image = gradient(width, height, *colors)
    _bubbles(image, (255, 255, 255))
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.text((44, 34), topic_title.upper(), font=font(26, True), fill=(255, 255, 255))
    draw.text((width - 44, 34), f'{round_text}  •  {level_name}', font=font(24), fill=(255, 255, 255, 230), anchor='ra')
    draw.rounded_rectangle((30, 84, width - 30, height - 28), radius=28, fill=(255, 255, 255, 240))

    y = 110 if diagram else 84 + (height - 28 - 84 - text_height) // 2
    for line in lines:
        draw.text((width / 2, y), line, font=prompt_font, fill=INK, anchor='ma')
        y += 56
    if diagram:
        draw_triangle(draw, (width / 2 - 190, y + 20, width / 2 + 190, y + 20 + 200), diagram)
    return to_file_bytes(image)


def connect4_image(board, last_move=None, winning=None):
    cell, pad, header = 90, 22, 54
    rows, cols = len(board), len(board[0])
    width, height = cols * cell + pad * 2, rows * cell + pad * 2 + header
    image = gradient(width, height, (25, 30, 70), (70, 40, 120))
    draw = ImageDraw.Draw(image, 'RGBA')
    for col in range(cols):
        draw.text((pad + col * cell + cell / 2, header / 2 + 4), str(col + 1), font=font(30, True), fill=(255, 255, 255, 230), anchor='mm')
    draw.rounded_rectangle((8, header, width - 8, height - 8), radius=26, fill=(30, 80, 220))
    colors = {'R': ((231, 76, 60), (255, 140, 120)), 'Y': ((247, 202, 24), (255, 238, 140)), '.': ((16, 20, 48), (16, 20, 48))}
    winning = set(winning or [])
    for row in range(rows):
        for col in range(cols):
            cx, cy = pad + col * cell + cell / 2, header + pad + row * cell + cell / 2
            radius = cell / 2 - 9
            main, shine = colors[board[row][col]]
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=main)
            if board[row][col] != '.':
                inner = radius * 0.62
                draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), outline=shine, width=4)
            if (row, col) in winning:
                draw.ellipse((cx - radius - 4, cy - radius - 4, cx + radius + 4, cy + radius + 4), outline=(255, 255, 255), width=7)
            elif last_move == (row, col):
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(255, 255, 255, 220), width=4)
    return to_file_bytes(image)


def hangman_image(pattern, wrong_letters, max_lives, category, state='playing'):
    width, height = 760, 430
    palette = {'playing': ((30, 33, 80), (80, 50, 140)), 'won': ((17, 100, 80), (56, 200, 120)), 'lost': ((110, 20, 40), (200, 60, 70))}
    image = gradient(width, height, *palette[state])
    draw = ImageDraw.Draw(image, 'RGBA')
    wood = (222, 184, 135)
    draw.line([(60, 380), (260, 380)], fill=wood, width=10)
    draw.line([(110, 380), (110, 60)], fill=wood, width=10)
    draw.line([(105, 60), (240, 60)], fill=wood, width=10)
    draw.line([(235, 60), (235, 100)], fill=wood, width=6)
    stage = min(len(wrong_letters), max_lives)
    stage = round(stage / max_lives * 6) if max_lives != 6 else stage
    ink = (255, 255, 255)
    if stage >= 1:
        draw.ellipse((210, 100, 260, 150), outline=ink, width=5)
    if stage >= 2:
        draw.line([(235, 150), (235, 250)], fill=ink, width=5)
    if stage >= 3:
        draw.line([(235, 170), (200, 215)], fill=ink, width=5)
    if stage >= 4:
        draw.line([(235, 170), (270, 215)], fill=ink, width=5)
    if stage >= 5:
        draw.line([(235, 250), (205, 310)], fill=ink, width=5)
    if stage >= 6:
        draw.line([(235, 250), (265, 310)], fill=ink, width=5)
        draw.text((235, 125), '×  ×', font=font(16, True), fill=ink, anchor='mm')

    draw.text((320, 50), category.upper(), font=font(22, True), fill=(255, 255, 255, 200))
    spaced = ' '.join(pattern.upper())
    size = 54
    while size > 20 and draw.textlength(spaced, font=font(size, True)) > width - 340:
        size -= 4
    draw.text((320, 150), spaced, font=font(size, True), fill=(255, 255, 255))
    draw.text((320, 280), f'Lives: {max_lives - len(wrong_letters)} / {max_lives}', font=font(28, True), fill=(255, 220, 120))
    wrong = ' '.join(sorted(letter.upper() for letter in wrong_letters)) or '—'
    draw.text((320, 330), f'Wrong: {wrong}', font=font(26), fill=(255, 255, 255, 230))
    return to_file_bytes(image)


WORDLE_COLORS = {'g': (83, 141, 78), 'y': (181, 159, 59), 'x': (58, 58, 60)}


def wordle_image(rows, scores, total_rows=6, length=5):
    tile, gap, pad = 84, 10, 24
    width = length * tile + (length - 1) * gap + pad * 2
    height = total_rows * tile + (total_rows - 1) * gap + pad * 2
    image = Image.new('RGB', (width, height), (18, 18, 19))
    draw = ImageDraw.Draw(image)
    for row in range(total_rows):
        for col in range(length):
            x, y = pad + col * (tile + gap), pad + row * (tile + gap)
            if row < len(rows):
                draw.rounded_rectangle((x, y, x + tile, y + tile), radius=8, fill=WORDLE_COLORS[scores[row][col]])
                draw.text((x + tile / 2, y + tile / 2 + 2), rows[row][col].upper(), font=font(44, True), fill=(255, 255, 255), anchor='mm')
            else:
                draw.rounded_rectangle((x, y, x + tile, y + tile), radius=8, outline=(70, 71, 73), width=3)
    return to_file_bytes(image)


def _circle_avatar(avatar_bytes, size, initials, colors):
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert('RGBA').resize((size, size))
        except Exception:
            avatar = None
    else:
        avatar = None
    if avatar is None:
        avatar = gradient(size, size, *colors).convert('RGBA')
        ImageDraw.Draw(avatar).text((size / 2, size / 2), initials, font=font(size // 2, True), fill=(255, 255, 255), anchor='mm')
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    avatar.putalpha(mask)
    return avatar


def profile_card(name, avatar_bytes, level, rank, xp, xp_floor, xp_ceiling, played, wins, favourite):
    width, height = 900, 320
    image = gradient(width, height, (106, 17, 203), (37, 117, 252))
    _bubbles(image, (255, 255, 255))
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=30, fill=(15, 15, 40, 150))
    avatar = _circle_avatar(avatar_bytes, 190, (name[:1] or '?').upper(), ((255, 154, 68), (255, 94, 98)))
    draw.ellipse((46, 66, 256, 276), fill=(255, 255, 255, 230))
    image.paste(avatar, (56, 76), avatar)
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.text((290, 62), name[:22], font=font(44, True), fill=(255, 255, 255))
    draw.text((290, 120), f'Level {level}  •  {rank}', font=font(28), fill=(255, 220, 120))

    span = max(xp_ceiling - xp_floor, 1)
    progress = min(max((xp - xp_floor) / span, 0), 1)
    draw.rounded_rectangle((290, 176, 840, 206), radius=15, fill=(255, 255, 255, 60))
    if progress > 0:
        draw.rounded_rectangle((290, 176, 290 + 550 * progress, 206), radius=15, fill=(255, 215, 90))
    draw.text((290, 214), f'{xp} XP  /  {xp_ceiling} XP to level {level + 1}', font=font(20), fill=(255, 255, 255, 220))
    draw.text((290, 252), f'Played {played}   •   Wins {wins}   •   Fav: {favourite}', font=font(22, True), fill=(255, 255, 255))
    return to_file_bytes(image)


def pokemon_card(art_bytes, reveal, label=''):
    size = 560
    image = gradient(size, size, (255, 203, 5), (59, 76, 202) if not reveal else (255, 94, 98))
    draw = ImageDraw.Draw(image, 'RGBA')
    for radius, alpha in [(260, 40), (200, 50), (140, 60)]:
        draw.ellipse((size / 2 - radius, size / 2 - radius, size / 2 + radius, size / 2 + radius), fill=(255, 255, 255, alpha))
    sprite = Image.open(io.BytesIO(art_bytes)).convert('RGBA')
    sprite.thumbnail((470, 470))
    if not reveal:
        silhouette = Image.new('RGBA', sprite.size, (15, 15, 40, 255))
        silhouette.putalpha(sprite.getchannel('A'))
        sprite = silhouette
    image.paste(sprite, ((size - sprite.width) // 2, (size - sprite.height) // 2 - 10), sprite)
    draw = ImageDraw.Draw(image, 'RGBA')
    text = label if reveal else "Who's that Pokémon?"
    draw.rounded_rectangle((60, size - 74, size - 60, size - 20), radius=22, fill=(15, 15, 40, 200))
    draw.text((size / 2, size - 47), text, font=font(28, True), fill=(255, 255, 255), anchor='mm')
    return to_file_bytes(image)


def rps_banner(left_label, right_label, left_pick, right_pick):
    width, height = 720, 260
    image = gradient(width, height, (52, 31, 151), (200, 80, 192))
    draw = ImageDraw.Draw(image, 'RGBA')
    symbols = {'rock': 'ROCK', 'paper': 'PAPER', 'scissors': 'SCISSORS'}
    draw.text((180, 40), left_label[:16], font=font(26, True), fill=(255, 255, 255), anchor='ma')
    draw.text((540, 40), right_label[:16], font=font(26, True), fill=(255, 255, 255), anchor='ma')
    draw.text((360, 140), 'VS', font=font(54, True), fill=(255, 220, 120), anchor='mm')
    draw.rounded_rectangle((60, 100, 300, 200), radius=20, fill=(255, 255, 255, 230))
    draw.rounded_rectangle((420, 100, 660, 200), radius=20, fill=(255, 255, 255, 230))
    draw.text((180, 150), symbols[left_pick], font=font(34, True), fill=INK, anchor='mm')
    draw.text((540, 150), symbols[right_pick], font=font(34, True), fill=INK, anchor='mm')
    return to_file_bytes(image)
