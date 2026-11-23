"""Static game content: classes, items, monsters and locations."""

CLASSES = {
    "warrior": {
        "emoji": ":crossed_swords:",
        "desc": "Tough and hard-hitting. Skill: *Power Strike* (double damage).",
        "hp": 34, "mp": 8, "atk": 7, "def": 4,
        "growth": {"hp": 9, "mp": 2, "atk": 3, "def": 2},
        "skill": {"name": "Power Strike", "cost": 3, "mult": 2.0, "pierce": 0},
        "crit": 0.10,
    },
    "mage": {
        "emoji": ":magic_wand:",
        "desc": "Fragile but devastating. Skill: *Fireball* (huge damage, ignores armor).",
        "hp": 24, "mp": 16, "atk": 3, "def": 2,
        "growth": {"hp": 7, "mp": 4, "atk": 1, "def": 1},
        "skill": {"name": "Fireball", "cost": 4, "mult": 2.5, "pierce": 1, "bonus": 6},
        "crit": 0.10,
    },
    "rogue": {
        "emoji": ":dagger_knife:",
        "desc": "Quick and lucky. Skill: *Backstab* (guaranteed critical). Flees easily.",
        "hp": 25, "mp": 9, "atk": 5, "def": 3,
        "growth": {"hp": 6, "mp": 2, "atk": 2, "def": 1},
        "skill": {"name": "Backstab", "cost": 3, "mult": 2.5, "pierce": 0},
        "crit": 0.25,
    },
}

# type: "heal" | "mana" | "weapon" | "armor" | "junk"
ITEMS = {
    "potion": {"name": "Potion", "type": "heal", "power": 20, "price": 15,
               "desc": "Restores 20 HP."},
    "elixir": {"name": "Elixir", "type": "heal", "power": 60, "price": 45,
               "desc": "Restores 60 HP."},
    "ether": {"name": "Ether", "type": "mana", "power": 10, "price": 20,
              "desc": "Restores 10 MP."},
    "dagger": {"name": "Rusty Dagger", "type": "weapon", "power": 1, "price": 10,
               "desc": "+1 ATK."},
    "iron_sword": {"name": "Iron Sword", "type": "weapon", "power": 3, "price": 60,
                   "desc": "+3 ATK."},
    "steel_blade": {"name": "Steel Blade", "type": "weapon", "power": 6, "price": 160,
                    "desc": "+6 ATK."},
    "runed_staff": {"name": "Runed Staff", "type": "weapon", "power": 8, "price": 260,
                    "desc": "+8 ATK."},
    "cinder_fang": {"name": "Cinder Fang", "type": "weapon", "power": 14, "price": 0,
                    "desc": "+14 ATK. Forged from a wyrm's tooth."},
    "cloth_tunic": {"name": "Cloth Tunic", "type": "armor", "power": 1, "price": 10,
                    "desc": "+1 DEF."},
    "leather_armor": {"name": "Leather Armor", "type": "armor", "power": 2, "price": 45,
                      "desc": "+2 DEF."},
    "chainmail": {"name": "Chainmail", "type": "armor", "power": 5, "price": 140,
                  "desc": "+5 DEF."},
    "wyrmscale": {"name": "Wyrmscale Mail", "type": "armor", "power": 10, "price": 0,
                  "desc": "+10 DEF. Still warm."},
    "wolf_pelt": {"name": "Wolf Pelt", "type": "junk", "power": 0, "price": 12,
                  "desc": "Sells for a few coins."},
    "bog_pearl": {"name": "Bog Pearl", "type": "junk", "power": 0, "price": 35,
                  "desc": "Murky, but valuable."},
    "ember_shard": {"name": "Ember Shard", "type": "junk", "power": 0, "price": 60,
                    "desc": "Glows faintly. Collectors love these."},
}

SHOP_STOCK = ["potion", "elixir", "ether", "iron_sword", "steel_blade",
              "runed_staff", "leather_armor", "chainmail"]

# loot: list of (item_key, chance)
MONSTERS = {
    "slime": {"name": "Green Slime", "emoji": ":green_heart:", "hp": 10, "atk": 3, "def": 0,
              "xp": 6, "gold": (2, 6), "loot": [("potion", 0.15)]},
    "wolf": {"name": "Grey Wolf", "emoji": ":wolf:", "hp": 16, "atk": 6, "def": 1,
             "xp": 10, "gold": (3, 8), "loot": [("wolf_pelt", 0.5)]},
    "goblin": {"name": "Goblin Cutpurse", "emoji": ":japanese_goblin:", "hp": 20, "atk": 8, "def": 2,
               "xp": 14, "gold": (8, 16), "loot": [("dagger", 0.15), ("potion", 0.2)]},
    "lurker": {"name": "Bog Lurker", "emoji": ":crocodile:", "hp": 36, "atk": 13, "def": 3,
               "xp": 26, "gold": (10, 20), "loot": [("bog_pearl", 0.35)]},
    "wisp": {"name": "Will-o'-Wisp", "emoji": ":sparkles:", "hp": 26, "atk": 15, "def": 5,
             "xp": 28, "gold": (12, 22), "loot": [("ether", 0.4)]},
    "troll": {"name": "Swamp Troll", "emoji": ":ogre:", "hp": 55, "atk": 17, "def": 4,
              "xp": 40, "gold": (20, 35), "loot": [("elixir", 0.25), ("leather_armor", 0.1)]},
    "harpy": {"name": "Crag Harpy", "emoji": ":eagle:", "hp": 50, "atk": 21, "def": 5,
              "xp": 50, "gold": (20, 40), "loot": [("ember_shard", 0.2)]},
    "golem": {"name": "Stone Golem", "emoji": ":moyai:", "hp": 85, "atk": 20, "def": 10,
              "xp": 70, "gold": (30, 50), "loot": [("chainmail", 0.1), ("ember_shard", 0.3)]},
    "imp": {"name": "Fire Imp", "emoji": ":imp:", "hp": 45, "atk": 24, "def": 6,
            "xp": 60, "gold": (25, 45), "loot": [("ember_shard", 0.4), ("ether", 0.3)]},
    "wyrm": {"name": "Vyrmoth, the Cinder Wyrm", "emoji": ":dragon:", "hp": 320, "atk": 30, "def": 14,
             "xp": 500, "gold": (400, 600), "boss": True,
             "loot": [("cinder_fang", 1.0), ("wyrmscale", 1.0)]},
}

LOCATIONS = {
    "town": {
        "name": "Oakhollow Village", "emoji": ":house_with_garden:", "safe": True,
        "desc": "A cozy village of thatched roofs. The inn's hearth crackles and the shopkeeper waves you over.",
        "exits": ["forest"], "monsters": [], "min_level": 1,
    },
    "forest": {
        "name": "Whisperwood", "emoji": ":evergreen_tree:", "safe": False,
        "desc": "Tall pines murmur overhead. Something rustles in the undergrowth. _(Lv 1-3)_",
        "exits": ["town", "bog", "crags"],
        "monsters": [("slime", 4), ("wolf", 3), ("goblin", 2)], "min_level": 1,
    },
    "bog": {
        "name": "Mirefen Bog", "emoji": ":fog:", "safe": False,
        "desc": "Thick mist hangs over black water. Lights flicker where no lights should be. _(Lv 3-5)_",
        "exits": ["forest"],
        "monsters": [("lurker", 4), ("wisp", 3), ("troll", 2)], "min_level": 3,
    },
    "crags": {
        "name": "Emberpeak Crags", "emoji": ":volcano:", "safe": False,
        "desc": "Jagged rock, hot to the touch. Shrieks echo off the cliffs. _(Lv 5-7)_",
        "exits": ["forest", "lair"],
        "monsters": [("harpy", 3), ("golem", 2), ("imp", 3)], "min_level": 5,
    },
    "lair": {
        "name": "The Ashen Lair", "emoji": ":fire:", "safe": False,
        "desc": "A cavern choked with smoke and bones. Two molten eyes open in the dark. _(BOSS, Lv 7+)_",
        "exits": ["crags"], "monsters": [("wyrm", 1)], "min_level": 7, "boss": True,
    },
}

INN_COST = 10
MAX_LEVEL = 20


def xp_to_next(level: int) -> int:
    return 20 + (level - 1) * 40 + (level - 1) ** 2 * 12
