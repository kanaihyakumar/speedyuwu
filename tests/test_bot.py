import pytest

import bot as bot_module


@pytest.fixture
async def loaded_bot():
    await bot_module.bot.setup_hook()
    yield bot_module.bot
    for extension in list(bot_module.bot.extensions):
        await bot_module.bot.unload_extension(extension)


async def test_known_commands_are_not_swallowed_as_game_input(loaded_bot):
    for text in ['shelp', 'splay', 'sstop', 'sttt @someone', 'smath surds hard', 'scalc 1+1', 'speedy', 'happy birthday', 'shug', 'sfact']:
        assert loaded_bot.is_known_command(text), text
    for text in ['crane', '23', 'a', 'hello there', 'play guess']:
        assert not loaded_bot.is_known_command(text), text


async def test_every_game_and_topic_has_a_command(loaded_bot):
    from speedy.cogs.games import GAMES
    from speedy.mathgen import TOPICS
    for spec in GAMES:
        for name in spec.commands:
            assert loaded_bot.get_command(name), name
    for key in TOPICS:
        assert loaded_bot.get_command(f's{key}'), key


async def test_help_sections_fit_discord_limits(loaded_bot):
    from speedy.cogs.help import SECTIONS, build_section
    for section in SECTIONS:
        embed = build_section(section, loaded_bot)
        assert len(embed) <= 6000
        assert len(embed.fields) <= 25
        assert all(len(field.value) <= 1024 for field in embed.fields), section


async def test_game_menu_and_math_menu_build(loaded_bot):
    from speedy.cogs.games import GamePicker
    from speedy.cogs.maths import MathMenu
    games = loaded_bot.get_cog('Games')
    embed = games.menu_embed()
    assert len(embed) <= 6000 and all(len(f.value) <= 1024 for f in embed.fields)
    assert len(GamePicker(games).children[0].options) <= 25
    maths = loaded_bot.get_cog('Maths')
    assert all(len(f.value) <= 1024 for f in maths.menu_embed().fields)
    assert len(MathMenu(maths).children[0].options) <= 25
