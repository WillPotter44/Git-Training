"""Convert the engine's Slack-flavoured text (``*bold*``, ``:emoji:``) for other platforms."""

import re

EMOJI = {
    "bed": "🛏️", "boom": "💥", "bust_in_silhouette": "👤", "coin": "🪙",
    "convenience_store": "🏪", "crocodile": "🐊", "crossed_swords": "⚔️", "crown": "👑",
    "dagger_knife": "🗡️", "dash": "💨", "dragon": "🐉", "eagle": "🦅",
    "evergreen_tree": "🌲", "fire": "🔥", "first_place_medal": "🥇", "fog": "🌫️",
    "gift": "🎁", "green_heart": "💚", "heart": "❤️", "house_with_garden": "🏡",
    "imp": "👿", "japanese_goblin": "👺", "large_blue_diamond": "🔷", "leaves": "🍃",
    "magic_wand": "🪄", "moneybag": "💰", "moyai": "🗿", "no_entry": "⛔",
    "ogre": "🧌", "ok_hand": "👌", "rotating_light": "🚨", "round_pushpin": "📍",
    "school_satchel": "🎒", "scroll": "📜", "second_place_medal": "🥈", "shield": "🛡️",
    "shopping_bags": "🛍️", "skull": "💀", "sparkles": "✨", "star2": "🌟",
    "tada": "🎉", "third_place_medal": "🥉", "trophy": "🏆", "volcano": "🌋",
    "warning": "⚠️", "wastebasket": "🗑️", "wolf": "🐺",
}

EMOJI_CODE = re.compile(r":([a-z0-9_+-]+):")
SLACK_BOLD = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?![*\w])")


def emojize(text: str) -> str:
    return EMOJI_CODE.sub(lambda m: EMOJI.get(m.group(1), m.group(0)), text)


def to_discord(text: str) -> str:
    """Slack mrkdwn -> Discord markdown. ``_italic_`` and ``code`` already match."""
    return SLACK_BOLD.sub(r"**\1**", emojize(text))
