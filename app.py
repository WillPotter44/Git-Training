"""Slack front-end for the Oakhollow text RPG.

Runs in Socket Mode, so no public URL is needed. Players interact via:
  * the ``/rpg`` slash command  (e.g. ``/rpg explore``)
  * @-mentioning the bot         (e.g. ``@Oakhollow attack``)
  * direct messages to the bot
  * clicking the buttons under each game message

Game replies are private (ephemeral) by default so a busy channel isn't
flooded; big moments (new heroes, level-ups, deaths, boss kills) are announced
publicly. Set RPG_PUBLIC=true to make every reply visible to the channel.
"""

import logging
import os
import re

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from rpg.engine import Game, Reply
from rpg.storage import Store

load_dotenv()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

PUBLIC = os.environ.get("RPG_PUBLIC", "false").lower() in ("1", "true", "yes")
ANNOUNCE_CHANNEL = os.environ.get("RPG_ANNOUNCE_CHANNEL")  # optional channel ID
SLASH = os.environ.get("RPG_SLASH_COMMAND", "/rpg")

app = App(token=os.environ["SLACK_BOT_TOKEN"])
game = Game(Store(os.environ.get("RPG_DB_PATH", "rpg.db")))


# ----------------------------------------------------------------- rendering
def to_blocks(reply: Reply, owner: str) -> list[dict]:
    blocks: list[dict] = [{"type": "section", "text": {"type": "mrkdwn", "text": reply.text[:2900]}}]
    buttons = reply.buttons[:25]
    for start in range(0, len(buttons), 5):
        elements = []
        for i, (label, command, style) in enumerate(buttons[start:start + 5], start):
            btn = {
                "type": "button",
                "action_id": f"rpg_btn_{i}",
                "text": {"type": "plain_text", "text": label[:75], "emoji": True},
                "value": f"{owner}|{command}",
            }
            if style:
                btn["style"] = style
            elements.append(btn)
        blocks.append({"type": "actions", "elements": elements})
    return blocks


_names: dict[str, str] = {}


def display_name(client, user_id: str) -> str:
    if user_id not in _names:
        try:
            prof = client.users_info(user=user_id)["user"]["profile"]
            _names[user_id] = prof.get("display_name") or prof.get("real_name") or "Hero"
        except Exception:  # noqa: BLE001 - missing users:read scope etc.
            return "Hero"
    return _names[user_id]


def play(client, team: str, user: str, text: str) -> Reply:
    return game.handle(team, user, display_name(client, user), text)


def announce(client, channel: str | None, reply: Reply) -> None:
    target = ANNOUNCE_CHANNEL or channel
    if not reply.announce or not target:
        return
    try:
        client.chat_postMessage(channel=target, text=reply.announce)
    except Exception as e:  # noqa: BLE001 - bot not in channel, DM, etc.
        logging.warning("Could not announce in %s: %s", target, e)


def send(client, channel: str, user: str, reply: Reply, thread_ts: str | None = None) -> None:
    kwargs = dict(channel=channel, text=reply.text, blocks=to_blocks(reply, user))
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    if PUBLIC or channel.startswith("D"):
        client.chat_postMessage(**kwargs)
    else:
        client.chat_postEphemeral(user=user, **kwargs)


# ------------------------------------------------------------------ handlers
@app.command(SLASH)
def on_slash(ack, body, respond, client):
    ack()
    reply = play(client, body["team_id"], body["user_id"], body.get("text", ""))
    respond(text=reply.text, blocks=to_blocks(reply, body["user_id"]),
            response_type="in_channel" if PUBLIC else "ephemeral")
    announce(client, body.get("channel_id"), reply)


@app.action(re.compile(r"^rpg_btn_\d+$"))
def on_button(ack, body, action, respond, client):
    ack()
    user = body["user"]["id"]
    team = body.get("team", {}).get("id") or body["user"].get("team_id", "")
    owner, _, command = action["value"].partition("|")
    if owner != user:
        respond(text=f"That's someone else's adventure! Type `{SLASH}` to start your own.",
                response_type="ephemeral", replace_original=False)
        return
    reply = play(client, team, user, command)
    respond(text=reply.text, blocks=to_blocks(reply, user), replace_original=True)
    announce(client, (body.get("channel") or {}).get("id"), reply)


MENTION = re.compile(r"<@[A-Z0-9]+>")


@app.event("app_mention")
def on_mention(event, body, client):
    text = MENTION.sub("", event.get("text", "")).strip()
    reply = play(client, body["team_id"], event["user"], text)
    send(client, event["channel"], event["user"], reply,
         thread_ts=event.get("thread_ts") if PUBLIC else None)
    announce(client, event["channel"], reply)


@app.event("message")
def on_dm(event, body, client):
    # Only respond to plain user messages in a DM with the bot.
    if event.get("channel_type") != "im" or event.get("subtype") or event.get("bot_id"):
        return
    reply = play(client, body["team_id"], event["user"], event.get("text", ""))
    send(client, event["channel"], event["user"], reply)


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
