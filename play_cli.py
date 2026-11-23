"""Play the game in your terminal without Slack: `python play_cli.py`."""

import re
import sys

from rpg.engine import Game
from rpg.storage import Store


def strip(text: str) -> str:
    text = re.sub(r":[a-z0-9_+-]+:", "", text)  # drop Slack emoji codes
    return text.replace("*", "").replace("`", "")


def main() -> None:
    game = Game(Store(sys.argv[1] if len(sys.argv) > 1 else "cli.db"))
    print("Oakhollow RPG (terminal mode). Type commands or a button number. Ctrl-D to quit.\n")
    reply = game.handle("cli", "local", "Traveler", "menu")
    while True:
        print(strip(reply.text))
        for i, (label, _cmd, _style) in enumerate(reply.buttons, 1):
            print(f"  [{i}] {label}")
        try:
            line = input("\n> ").strip()
        except EOFError:
            print()
            return
        if line.isdigit() and 1 <= int(line) <= len(reply.buttons):
            line = reply.buttons[int(line) - 1][1]
        print()
        reply = game.handle("cli", "local", "Traveler", line)
        if reply.announce:
            print(f"[channel] {strip(reply.announce)}")


if __name__ == "__main__":
    main()
