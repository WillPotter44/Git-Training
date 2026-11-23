# Oakhollow RPG – a text adventure for Slack and Discord

A turn-based fantasy RPG you play inside a Slack or Discord channel. Each person creates
their own hero, explores, fights monsters, levels up, buys gear, and works
toward slaying **Vyrmoth, the Cinder Wyrm**. Their progress shows up on a
leaderboard everyone in the workspace (or Discord server) shares.

- **Three classes**: Warrior, Mage, Rogue, each with its own special skill
- **Five areas**: a safe village (shop + inn), three wilderness areas of rising difficulty, and a boss lair
- **Turn-based combat** with crits, skills, potions and fleeing
- **Loot, gold, equipment, XP and levels** (up to level 20)
- **Clickable buttons** for every action, or type commands
- **Private play, public glory**: game messages are visible only to the player; new heroes, level-ups, deaths and boss kills are announced to the channel
- Saves to SQLite, so progress survives restarts

## Playing

| How | Example |
| --- | --- |
| Slash command | `/rpg`, `/rpg explore`, `/rpg buy iron sword` |
| Mention the bot | `@Oakhollow attack` |
| DM the bot | `status` |

On Discord it's the same, except the slash command takes its text in a
`command` box: `/rpg command:explore`.

Type `/rpg help` for the full command list. Most of the time you'll just click buttons.

## Setting it up in Slack (about 10 minutes)

1. **Create the app.** Go to <https://api.slack.com/apps> → *Create New App* →
   *From a manifest* → pick your workspace → paste in [`manifest.yml`](manifest.yml) → *Create*.
2. **Get an app-level token.** *Basic Information* → *App-Level Tokens* →
   *Generate Token and Scopes* → add the `connections:write` scope → copy the `xapp-…` token.
3. **Install the app.** *Install App* → *Install to Workspace* → copy the
   *Bot User OAuth Token* (`xoxb-…`).
4. **Configure the bot.**
   ```bash
   cp .env.example .env    # then paste both tokens into .env
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
5. **Invite it to your channel.** In Slack, type `/invite @Oakhollow` in the
   channel, then `/rpg` to play.

The app uses **Socket Mode**: it opens an outbound connection to Slack, so you
don't need a public URL, an HTTPS certificate or open firewall ports.

## Setting it up in Discord (about 5 minutes)

1. **Create the bot.** Go to <https://discord.com/developers/applications> →
   *New Application* → name it (e.g. Oakhollow). Open the *Bot* tab →
   *Reset Token* → copy the token. No privileged intents are needed.
2. **Configure and run it.**
   ```bash
   cp .env.example .env    # paste the token into DISCORD_BOT_TOKEN
   pip install -r requirements.txt
   python discord_bot.py
   ```
3. **Invite it to your server.** When it starts, the bot prints an invite link
   in its log (`Invite link: https://discord.com/oauth2/authorize?...`). Open
   it and pick your server.
4. Type `/rpg` in any channel the bot can see.

`/rpg` can take up to an hour to appear the first time Discord registers it.
To make it show up instantly, set `DISCORD_GUILD_ID` to your server's ID
(right-click the server icon → *Copy Server ID*; turn on *Developer Mode*
under User Settings → Advanced if you don't see it).

Like Slack's Socket Mode, the Discord bot connects outward, so it needs no
public URL. Saves are kept separately for each Discord server, and DMs with
the bot count as their own separate save.

### Options (`.env`)

| Variable | Default | Meaning |
| --- | --- | --- |
| `RPG_PUBLIC` | `false` | `true` makes every game message visible to the whole channel |
| `RPG_ANNOUNCE_CHANNEL` | *(where it happened)* | Slack channel ID that receives all level-up and boss-kill announcements |
| `DISCORD_ANNOUNCE_CHANNEL_ID` | *(where it happened)* | The same, for Discord |
| `DISCORD_GUILD_ID` | *(none)* | Your Discord server ID, so `/rpg` registers instantly |
| `RPG_DB_PATH` | `rpg.db` | Where save data lives |
| `RPG_SLASH_COMMAND` | `/rpg` | Slack only: change this if you renamed the command in the manifest |

Slack and Discord can share one `rpg.db`; their saves don't mix.

## Deploying so it runs 24/7

The bot is a single long-running process with one SQLite file, so anything that
can run a Docker container with a persistent disk works: a small VM, Fly.io,
Railway, Render (background worker) and so on.

```bash
docker build -t oakhollow-rpg .
docker run -d --restart unless-stopped --env-file .env -v rpg-data:/data oakhollow-rpg                         # Slack
docker run -d --restart unless-stopped --env-file .env -v rpg-data:/data oakhollow-rpg python discord_bot.py  # Discord
```

Keep the `/data` volume, because your players' saves are stored there.

## Developing

```bash
pip install -r requirements-dev.txt
pytest                  # run tests
python play_cli.py      # play in your terminal, no Slack needed
```

| File | What's in it |
| --- | --- |
| `rpg/data.py` | All game content: classes, monsters, items, areas. Edit this to add your own. |
| `rpg/engine.py` | Game rules. Pure Python with no Slack code. |
| `rpg/storage.py` | SQLite save/load |
| `app.py` | Slack glue: slash command, buttons, mentions, DMs |
| `discord_bot.py` | Discord glue: the same features for Discord |
| `rpg/formatting.py` | Converts the game's Slack-style text (`*bold*`, `:emoji:`) for Discord |
| `play_cli.py` | Terminal version for quick testing |

To add a new monster, add it to `MONSTERS` in `rpg/data.py` and list it in the
`monsters` of a location in `LOCATIONS`. That's all. If you use a new
`:emoji_code:` in game text, add it to `EMOJI` in `rpg/formatting.py` too.
A test fails if you forget.
