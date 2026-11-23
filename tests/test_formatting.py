import pathlib

from rpg.formatting import EMOJI, EMOJI_CODE, to_discord


def test_every_emoji_code_in_the_game_is_mapped():
    src = "".join(p.read_text() for p in pathlib.Path("rpg").glob("*.py") if p.name != "formatting.py")
    missing = set(EMOJI_CODE.findall(src)) - set(EMOJI)
    assert not missing, f"add these to rpg/formatting.py EMOJI: {missing}"


def test_bold_and_emoji_conversion():
    assert to_discord(":dragon: *Vyrmoth* hits you for *12*.") == "🐉 **Vyrmoth** hits you for **12**."


def test_leaves_italics_code_and_bullets_alone():
    text = "• *Potion* – 15g – _Restores 20 HP._ Try `buy potion`"
    assert to_discord(text) == "• **Potion** – 15g – _Restores 20 HP._ Try `buy potion`"


def test_unknown_emoji_and_plain_colons_untouched():
    assert to_discord("Paths: `forest` :not_a_real_emoji:") == "Paths: `forest` :not_a_real_emoji:"
