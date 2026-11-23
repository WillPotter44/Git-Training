import re
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import discord_bot as bot
from rpg.engine import Game
from rpg.storage import Store


@pytest.fixture(autouse=True)
def fresh_game(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "game", Game(Store(str(tmp_path / "d.db"))))


def fake_interaction(user_id=111, guild_id=999):
    it = MagicMock()
    it.user.id = user_id
    it.user.display_name = "Tester"
    it.guild.id = guild_id
    it.channel = AsyncMock(spec=discord.TextChannel)
    it.response.send_message = AsyncMock()
    it.response.edit_message = AsyncMock()
    return it


async def test_slash_command_starts_game_and_announces():
    it = fake_interaction()
    await bot.rpg_command.callback(it, "start mage Merlin")
    kwargs = it.response.send_message.call_args.kwargs
    text = it.response.send_message.call_args.args[0]
    assert "**Merlin the Mage**" in text and ":" not in text.split()[0]
    assert kwargs["ephemeral"] is True
    labels = [c.item.label for c in kwargs["view"].children]
    assert labels[0] == "Shop"
    it.channel.send.assert_awaited_once()
    assert "Merlin" in it.channel.send.call_args.args[0]


async def test_button_round_trip_via_custom_id():
    it = fake_interaction()
    await bot.rpg_command.callback(it, "start rogue")
    view = it.response.send_message.call_args.kwargs["view"]
    shop = view.children[0]
    # Simulate a click after a restart: rebuild the button from its custom_id.
    match = re.fullmatch(bot.GameButton.__discord_ui_compiled_template__, shop.item.custom_id)
    button = await bot.GameButton.from_custom_id(it, shop.item, match)
    await button.callback(it)
    assert "Provisions" in it.response.edit_message.call_args.kwargs["content"]


async def test_other_users_cannot_click_your_buttons():
    owner = fake_interaction(user_id=111)
    await bot.rpg_command.callback(owner, "start warrior")
    btn = owner.response.send_message.call_args.kwargs["view"].children[0]
    stranger = fake_interaction(user_id=222)
    await btn.callback(stranger)
    assert "someone else's" in stranger.response.send_message.call_args.args[0]
    stranger.response.edit_message.assert_not_awaited()


def test_buttons_fit_discord_layout_limits():
    reply = bot.Reply("x", [(f"Button {i} " + "y" * 90, f"cmd {i}", None) for i in range(30)])
    view = bot.build_view(reply, 123456789012345678)
    assert len(view.children) == 25
    assert all(len(c.item.label) <= 80 and len(c.item.custom_id) <= 100 for c in view.children)
    assert max(c.item.row for c in view.children) == 4


def test_servers_have_separate_saves():
    a, b = MagicMock(id=1), MagicMock(id=2)
    assert bot.team_key(a) != bot.team_key(b) != bot.team_key(None)


async def test_mention_in_channel_replies_publicly(monkeypatch):
    me = MagicMock(id=42)
    monkeypatch.setattr(type(bot.client), "user", property(lambda self: me))
    msg = MagicMock()
    msg.author.bot = False
    msg.author.id = 111
    msg.author.display_name = "Tester"
    msg.guild.id = 999
    msg.channel = AsyncMock(spec=discord.TextChannel)
    msg.mentions = [me]
    msg.content = "<@42> start warrior Conan"
    msg.reply = AsyncMock()
    await bot.client.on_message(msg)
    assert "**Conan the Warrior**" in msg.reply.call_args.args[0]

    msg.reply.reset_mock()
    msg.mentions = []  # ordinary chatter without a mention is ignored
    await bot.client.on_message(msg)
    msg.reply.assert_not_awaited()
