# Oakhollow RPG – a text adventure for Slack

A turn-based fantasy RPG you play inside a Slack channel. Each person creates
their own hero, explores, fights monsters, levels up, buys gear, and works
toward slaying **Vyrmoth, the Cinder Wyrm**. Their progress shows up on a
leaderboard everyone in the workspace shares.

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

### Options (`.env`)

| Variable | Default | Meaning |
| --- | --- | --- |
| `RPG_PUBLIC` | `false` | `true` makes every game message visible to the whole channel |
| `RPG_ANNOUNCE_CHANNEL` | *(where it happened)* | Channel ID that receives all level-up and boss-kill announcements |
| `RPG_DB_PATH` | `rpg.db` | Where save data lives |
| `RPG_SLASH_COMMAND` | `/rpg` | Change this if you renamed the command in the manifest |

## Deploying so it runs 24/7

The bot is a single long-running process with one SQLite file, so anything that
can run a Docker container with a persistent disk works: a small VM, Fly.io,
Railway, Render (background worker) and so on.

```bash
docker build -t oakhollow-rpg .
docker run -d --restart unless-stopped --env-file .env -v rpg-data:/data oakhollow-rpg
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
| `play_cli.py` | Terminal version for quick testing |

To add a new monster, add it to `MONSTERS` in `rpg/data.py` and list it in the
`monsters` of a location in `LOCATIONS`. That's all.
