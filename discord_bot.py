"""Discord front-end for the Oakhollow text RPG.

Players interact via:
  * the ``/rpg`` slash command   (e.g. ``/rpg command:explore``)
  * @-mentioning the bot          (e.g. ``@Oakhollow attack``)
  * direct messages to the bot
  * clicking the buttons under each game message

``/rpg`` replies are private ("only you can see this") by default; big
moments are announced publicly. Set RPG_PUBLIC=true to make every reply
public. Saves are kept per Discord server (DMs count as their own "server").
No privileged intents are needed: bots can always read DMs and messages that
mention them.
"""

import logging
import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv

from rpg.engine import Game, Reply
from rpg.formatting import to_discord
from rpg.storage import Store

load_dotenv()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("oakhollow")

PUBLIC = os.environ.get("RPG_PUBLIC", "false").lower() in ("1", "true", "yes")
ANNOUNCE_CHANNEL_ID = int(os.environ.get("DISCORD_ANNOUNCE_CHANNEL_ID") or 0)
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID") or 0)  # instant command sync for one server
MAX_LEN = 2000

game = Game(Store(os.environ.get("RPG_DB_PATH", "rpg.db")))

STYLES = {
    "primary": discord.ButtonStyle.primary,
    "danger": discord.ButtonStyle.danger,
    None: discord.ButtonStyle.secondary,
}


def team_key(guild: discord.Guild | None) -> str:
    return f"discord:{guild.id}" if guild else "discord:dm"


def play(user: discord.abc.User, guild: discord.Guild | None, text: str) -> Reply:
    return game.handle(team_key(guild), str(user.id), user.display_name, text)


def render(reply: Reply) -> str:
    text = to_discord(reply.text)
    return text if len(text) <= MAX_LEN else text[: MAX_LEN - 1] + "…"


class GameButton(discord.ui.DynamicItem[discord.ui.Button],
                 template=r"rpg:(?P<owner>\d+):(?P<idx>\d+):(?P<cmd>.*)"):
    """A button whose custom_id carries the owner and command, so it keeps
    working after the bot restarts."""

    def __init__(self, owner: int, idx: int, command: str,
                 label: str = "…", style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(discord.ui.Button(
            label=label[:80], style=style, row=idx // 5,
            custom_id=f"rpg:{owner}:{idx}:{command}"[:100],
        ))
        self.owner = owner
        self.command = command

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match):
        return cls(int(match["owner"]), int(match["idx"]), match["cmd"])

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner:
            await interaction.response.send_message(
                "That's someone else's adventure! Use `/rpg` to start your own.", ephemeral=True)
            return
        reply = play(interaction.user, interaction.guild, self.command)
        await interaction.response.edit_message(content=render(reply),
                                                view=build_view(reply, self.owner))
        await announce(interaction.channel, reply)


def build_view(reply: Reply, owner: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for idx, (label, command, style) in enumerate(reply.buttons[:25]):
        view.add_item(GameButton(owner, idx, command, label, STYLES.get(style, STYLES[None])))
    return view


async def announce(channel, reply: Reply) -> None:
    if not reply.announce:
        return
    target = client.get_channel(ANNOUNCE_CHANNEL_ID) if ANNOUNCE_CHANNEL_ID else channel
    if target is None or isinstance(target, discord.DMChannel):
        return
    try:
        await target.send(to_discord(reply.announce))
    except discord.HTTPException as e:
        log.warning("Could not announce in %s: %s", target, e)


class RPGClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self.add_dynamic_items(GameButton)
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        perms = discord.Permissions(view_channel=True, send_messages=True,
                                    read_message_history=True)
        url = discord.utils.oauth_url(self.user.id, permissions=perms,
                                      scopes=("bot", "applications.commands"))
        log.info("Logged in as %s. Invite link: %s", self.user, url)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        is_dm = isinstance(message.channel, discord.DMChannel)
        if not is_dm and self.user not in message.mentions:
            return
        text = re.sub(rf"<@!?{self.user.id}>", "", message.content).strip()
        reply = play(message.author, message.guild, text)
        await message.reply(render(reply), view=build_view(reply, message.author.id),
                            mention_author=False)
        await announce(message.channel, reply)


client = RPGClient()


@client.tree.command(name="rpg", description="Play the Oakhollow text RPG")
@app_commands.describe(command="e.g. explore, attack, shop, status, help. Leave empty for the menu.")
async def rpg_command(interaction: discord.Interaction, command: str = "") -> None:
    reply = play(interaction.user, interaction.guild, command)
    await interaction.response.send_message(render(reply),
                                            view=build_view(reply, interaction.user.id),
                                            ephemeral=not PUBLIC)
    await announce(interaction.channel, reply)


if __name__ == "__main__":
    client.run(os.environ["DISCORD_BOT_TOKEN"], log_handler=None)
