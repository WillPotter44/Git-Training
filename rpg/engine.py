"""Core game logic. Pure Python: no Slack dependencies, so it is easy to test.

Every player action goes through ``Game.handle(team, user, display_name, text)``
which returns a ``Reply``: message text, suggested buttons (each button maps to
a command string), and an optional public ``announce`` line for big moments.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .data import (CLASSES, INN_COST, ITEMS, LOCATIONS, MAX_LEVEL, MONSTERS,
                   SHOP_STOCK, xp_to_next)
from .storage import Store

Button = tuple[str, str, str | None]  # (label, command, style: "primary"|"danger"|None)


@dataclass
class Reply:
    text: str
    buttons: list[Button] = field(default_factory=list)
    announce: str | None = None


HELP = """*:scroll: How to play*
`start <warrior|mage|rogue> [name]` – create your hero
`status` – your stats  ·  `inventory` – your bag  ·  `look` – where you are
`explore` – search the area for monsters and treasure
`travel <place>` – move to a neighboring area
`attack` · `skill` · `use <item>` · `flee` – combat actions
`shop` · `buy <item>` · `sell <item>` · `rest` – village services
`equip <item>` – wield a weapon or wear armor
`leaderboard` – the channel's greatest heroes
`reset confirm` – delete your hero and start over
Tip: you can just click the buttons."""


def bar(cur: int, mx: int, width: int = 10) -> str:
    filled = 0 if mx <= 0 else max(0, min(width, round(width * cur / mx)))
    return "▰" * filled + "▱" * (width - filled)


def find_item(query: str, keys) -> str | None:
    q = query.strip().lower().replace(" ", "_").replace("'", "")
    if not q:
        return None
    keys = list(keys)
    for k in keys:
        if q == k or q == ITEMS[k]["name"].lower().replace(" ", "_").replace("'", ""):
            return k
    for k in keys:  # prefix / partial match
        name = ITEMS[k]["name"].lower().replace(" ", "_")
        if k.startswith(q) or q in name:
            return k
    return None


def find_location(query: str, keys) -> str | None:
    q = query.strip().lower()
    for k in keys:
        name = LOCATIONS[k]["name"].lower()
        if q == k or q == name or (q and (q in name or name.startswith(q))):
            return k
    return None


class Game:
    def __init__(self, store: Store, rng: random.Random | None = None):
        self.store = store
        self.rng = rng or random.Random()

    # ------------------------------------------------------------------ entry
    def handle(self, team: str, user: str, display_name: str, text: str) -> Reply:
        words = (text or "").strip().split()
        cmd = words[0].lower() if words else "menu"
        args = " ".join(words[1:])
        cmd = ALIASES.get(cmd, cmd)

        with self.store.lock:
            p = self.store.load(team, user)
            if cmd == "help":
                return Reply(HELP, self.menu_buttons(p))
            if cmd == "leaderboard":
                return self.leaderboard(team, p)
            if p is None:
                if cmd == "start":
                    reply, p = self.start(user, display_name, args)
                    if p:
                        self.store.save(team, user, p)
                    return reply
                return self.intro()
            if cmd == "start":
                return Reply("You already have a hero! Use `reset confirm` to start over.",
                             self.menu_buttons(p))
            if cmd == "reset":
                if args.lower() == "confirm":
                    self.store.delete(team, user)
                    return Reply(":wastebasket: Your hero has retired. " + self.intro().text,
                                 self.intro().buttons)
                return Reply("Are you sure? This deletes your hero forever.",
                             [("Yes, delete my hero", "reset confirm", "danger"),
                              ("No, keep playing", "menu", None)])

            handler = COMMANDS.get(cmd)
            if handler is None:
                reply = Reply(f"I don't know `{cmd}`. Try `help`.", self.menu_buttons(p))
            elif p["combat"] and cmd not in COMBAT_OK:
                reply = Reply(":warning: You're in the middle of a fight!\n\n" + self.combat_text(p),
                              self.menu_buttons(p))
            else:
                reply = handler(self, p, args)
            self.store.save(team, user, p)
            return reply

    # ---------------------------------------------------------------- helpers
    def intro(self) -> Reply:
        lines = ["*:crossed_swords: Welcome to the Realm of Oakhollow!*",
                 "A cinder wyrm stirs beneath Emberpeak. Choose your class to begin:\n"]
        for key, c in CLASSES.items():
            lines.append(f"{c['emoji']} *{key.title()}* – {c['desc']}")
        lines.append("\nOr type `start <class> <name>`.")
        buttons = [(f"Play {k.title()}", f"start {k}", "primary") for k in CLASSES]
        return Reply("\n".join(lines), buttons)

    @staticmethod
    def atk(p: dict) -> int:
        return p["base_atk"] + (ITEMS[p["weapon"]]["power"] if p["weapon"] else 0)

    @staticmethod
    def defense(p: dict) -> int:
        return p["base_def"] + (ITEMS[p["armor"]]["power"] if p["armor"] else 0)

    def menu_buttons(self, p: dict | None) -> list[Button]:
        if p is None:
            return self.intro().buttons
        if p["combat"]:
            skill = CLASSES[p["cls"]]["skill"]
            b = [("Attack", "attack", "primary"),
                 (f"{skill['name']} ({skill['cost']} MP)", "skill", None)]
            if p["inventory"].get("elixir"):
                b.append(("Elixir", "use elixir", None))
            if p["inventory"].get("potion"):
                b.append(("Potion", "use potion", None))
            b.append(("Flee", "flee", "danger"))
            return b
        loc = LOCATIONS[p["location"]]
        b: list[Button] = []
        if loc["safe"]:
            b += [("Shop", "shop", None), (f"Rest ({INN_COST}g)", "rest", None)]
        else:
            b.append(("Explore", "explore", "primary"))
            if p["inventory"].get("potion") and p["hp"] < p["max_hp"]:
                b.append(("Potion", "use potion", None))
        for e in loc["exits"]:
            b.append((f"Go: {LOCATIONS[e]['name']}", f"travel {e}", None))
        b += [("Status", "status", None), ("Bag", "inventory", None)]
        return b

    def combat_text(self, p: dict) -> str:
        m = MONSTERS[p["combat"]["monster"]]
        mhp = p["combat"]["hp"]
        return (f"{m['emoji']} *{m['name']}*  {bar(mhp, m['hp'])} {mhp}/{m['hp']} HP\n"
                f":bust_in_silhouette: *{p['name']}*  {bar(p['hp'], p['max_hp'])} "
                f"{p['hp']}/{p['max_hp']} HP · {p['mp']}/{p['max_mp']} MP")

    # --------------------------------------------------------------- commands
    def start(self, user: str, display_name: str, args: str):
        parts = args.split()
        if not parts or parts[0].lower() not in CLASSES:
            return self.intro(), None
        cls = parts[0].lower()
        name = " ".join(parts[1:]).strip()[:32] or display_name or "Hero"
        c = CLASSES[cls]
        p = {
            "user": user, "name": name, "cls": cls, "level": 1, "xp": 0,
            "hp": c["hp"], "max_hp": c["hp"], "mp": c["mp"], "max_mp": c["mp"],
            "base_atk": c["atk"], "base_def": c["def"], "gold": 30,
            "location": "town", "inventory": {"potion": 3},
            "weapon": "dagger", "armor": "cloth_tunic", "combat": None,
            "kills": 0, "deaths": 0, "boss_kills": 0,
        }
        text = (f"{c['emoji']} *{name} the {cls.title()}* steps into Oakhollow Village.\n"
                "The elder hands you 3 potions and 30 gold. _\"Whisperwood lies east. "
                "Grow strong, then end the wyrm.\"_\n\n" + self.look_text(p))
        return Reply(text, self.menu_buttons(p),
                     announce=f":tada: *{name}* the {cls.title()} has joined the adventure!"), p

    def look_text(self, p: dict) -> str:
        loc = LOCATIONS[p["location"]]
        exits = ", ".join(LOCATIONS[e]["name"] for e in loc["exits"])
        return f"{loc['emoji']} *{loc['name']}*\n{loc['desc']}\n_Paths lead to: {exits}_"

    def cmd_menu(self, p: dict, _args: str) -> Reply:
        if p["combat"]:
            return Reply(self.combat_text(p), self.menu_buttons(p))
        return Reply(self.look_text(p), self.menu_buttons(p))

    def cmd_status(self, p: dict, _args: str) -> Reply:
        c = CLASSES[p["cls"]]
        w = ITEMS[p["weapon"]]["name"] if p["weapon"] else "nothing"
        a = ITEMS[p["armor"]]["name"] if p["armor"] else "nothing"
        lvl = f"{p['xp']}/{xp_to_next(p['level'])} XP" if p["level"] < MAX_LEVEL else "MAX"
        text = (f"{c['emoji']} *{p['name']}* – Level {p['level']} {p['cls'].title()} ({lvl})\n"
                f":heart: HP {bar(p['hp'], p['max_hp'])} {p['hp']}/{p['max_hp']}\n"
                f":large_blue_diamond: MP {bar(p['mp'], p['max_mp'])} {p['mp']}/{p['max_mp']}\n"
                f":crossed_swords: ATK {self.atk(p)}  ·  :shield: DEF {self.defense(p)}  ·  "
                f":moneybag: {p['gold']}g\n"
                f"Wielding *{w}*, wearing *{a}*\n"
                f":skull: {p['kills']} kills · {p['deaths']} deaths"
                + (f" · :dragon: {p['boss_kills']} wyrm slain" if p["boss_kills"] else "")
                + f"\n:round_pushpin: {LOCATIONS[p['location']]['name']}")
        return Reply(text, self.menu_buttons(p))

    def cmd_inventory(self, p: dict, _args: str) -> Reply:
        if not p["inventory"]:
            return Reply(":school_satchel: Your bag is empty.", self.menu_buttons(p))
        lines = [":school_satchel: *Your bag*"]
        buttons: list[Button] = []
        for k, n in sorted(p["inventory"].items()):
            it = ITEMS[k]
            lines.append(f"• *{it['name']}* ×{n} – {it['desc']}")
            if it["type"] in ("weapon", "armor") and not p["combat"]:
                buttons.append((f"Equip {it['name']}", f"equip {k}", None))
            elif it["type"] in ("heal", "mana"):
                buttons.append((f"Use {it['name']}", f"use {k}", None))
        return Reply("\n".join(lines), buttons[:10] + self.menu_buttons(p))

    def cmd_look(self, p: dict, _args: str) -> Reply:
        return Reply(self.look_text(p), self.menu_buttons(p))

    def cmd_travel(self, p: dict, args: str) -> Reply:
        loc = LOCATIONS[p["location"]]
        dest = find_location(args, loc["exits"])
        if not dest:
            names = ", ".join(f"`{e}`" for e in loc["exits"])
            return Reply(f"You can't get there from here. Paths: {names}", self.menu_buttons(p))
        target = LOCATIONS[dest]
        if target.get("boss") and p["level"] < target["min_level"]:
            return Reply(f":no_entry: A wall of heat drives you back. You must be at least "
                         f"level {target['min_level']} to enter *{target['name']}*.",
                         self.menu_buttons(p))
        p["location"] = dest
        text = self.look_text(p)
        if p["level"] < target["min_level"]:
            text += f"\n:warning: _This area is dangerous for your level (recommended Lv {target['min_level']}+)._"
        return Reply(text, self.menu_buttons(p))

    def cmd_explore(self, p: dict, _args: str) -> Reply:
        loc = LOCATIONS[p["location"]]
        if loc["safe"]:
            return Reply("Nothing dangerous here. Head out of the village to explore!",
                         self.menu_buttons(p))
        roll = self.rng.random()
        if loc.get("boss") or roll < 0.65:
            keys, weights = zip(*loc["monsters"])
            mkey = self.rng.choices(keys, weights=weights)[0]
            m = MONSTERS[mkey]
            p["combat"] = {"monster": mkey, "hp": m["hp"]}
            intro = (":rotating_light: *The ground shakes. Vyrmoth, the Cinder Wyrm, rises from the ash!*"
                     if m.get("boss") else f"A wild *{m['name']}* appears!")
            return Reply(f"{intro}\n\n{self.combat_text(p)}", self.menu_buttons(p))
        if roll < 0.80:
            g = self.rng.randint(3, 8) * (1 + loc["min_level"])
            p["gold"] += g
            return Reply(f":coin: You find a pouch with *{g} gold* half-buried in the dirt.",
                         self.menu_buttons(p))
        if roll < 0.90:
            k = self.rng.choice(["potion", "potion", "ether"] + (["elixir"] if loc["min_level"] >= 3 else []))
            p["inventory"][k] = p["inventory"].get(k, 0) + 1
            return Reply(f":gift: You discover a *{ITEMS[k]['name']}*!", self.menu_buttons(p))
        flavor = self.rng.choice([
            "You wander for a while but find only birdsong.",
            "Old footprints lead nowhere. You turn back.",
            "You rest on a mossy stump. Peaceful, for now.",
            "A distant howl. You decide not to investigate.",
        ])
        return Reply(f":leaves: {flavor}", self.menu_buttons(p))

    # ---------------------------------------------------------------- combat
    def _player_hit(self, p: dict, mult: float = 1.0, pierce: float = 0.0,
                    bonus: int = 0, force_crit: bool = False) -> tuple[int, bool]:
        m = MONSTERS[p["combat"]["monster"]]
        base = self.atk(p) + bonus - (m["def"] * (1 - pierce)) // 2 + self.rng.randint(-1, 2)
        crit = force_crit or self.rng.random() < CLASSES[p["cls"]]["crit"]
        dmg = max(1, round(base * mult * (1.5 if crit else 1.0)))
        p["combat"]["hp"] = max(0, p["combat"]["hp"] - dmg)
        return dmg, crit

    def _monster_turn(self, p: dict) -> tuple[list[str], str | None]:
        m = MONSTERS[p["combat"]["monster"]]
        if self.rng.random() < 0.08:
            return [f"The {m['name']} misses!"], None
        dmg = max(1, m["atk"] - self.defense(p) // 2 + self.rng.randint(-2, 2))
        p["hp"] = max(0, p["hp"] - dmg)
        lines = [f"The {m['name']} hits you for *{dmg}*."]
        if p["hp"] == 0:
            death_lines, announce = self._die(p)
            return lines + death_lines, announce
        return lines, None

    def _die(self, p: dict) -> tuple[list[str], str]:
        m = MONSTERS[p["combat"]["monster"]]
        lost = p["gold"] // 2
        p.update(gold=p["gold"] - lost, hp=p["max_hp"], mp=p["max_mp"],
                 location="town", combat=None, deaths=p["deaths"] + 1)
        return ([f":skull: *You have fallen!* You wake up at the Oakhollow inn, {lost} gold lighter."],
                f":skull: *{p['name']}* was defeated by the {m['name']}.")

    def _victory(self, p: dict) -> tuple[list[str], str | None]:
        mkey = p["combat"]["monster"]
        m = MONSTERS[mkey]
        gold = self.rng.randint(*m["gold"])
        p["gold"] += gold
        p["kills"] += 1
        p["combat"] = None
        lines = [f":trophy: *The {m['name']} is defeated!* +{m['xp']} XP, +{gold} gold."]
        for item, chance in m["loot"]:
            if self.rng.random() < chance:
                p["inventory"][item] = p["inventory"].get(item, 0) + 1
                lines.append(f":gift: It dropped *{ITEMS[item]['name']}*!")
        announce = None
        if m.get("boss"):
            p["boss_kills"] += 1
            announce = (f":dragon: :crown: *{p['name']}* has slain *{m['name']}*! "
                        "Oakhollow is saved! :tada:")
        lvl_lines, lvl_announce = self._gain_xp(p, m["xp"])
        return lines + lvl_lines, announce or lvl_announce

    def _gain_xp(self, p: dict, xp: int) -> tuple[list[str], str | None]:
        if p["level"] >= MAX_LEVEL:
            return [], None
        p["xp"] += xp
        lines = []
        g = CLASSES[p["cls"]]["growth"]
        while p["level"] < MAX_LEVEL and p["xp"] >= xp_to_next(p["level"]):
            p["xp"] -= xp_to_next(p["level"])
            p["level"] += 1
            p["max_hp"] += g["hp"]
            p["max_mp"] += g["mp"]
            p["base_atk"] += g["atk"]
            p["base_def"] += g["def"]
            p["hp"], p["mp"] = p["max_hp"], p["max_mp"]
            lines.append(f":star2: *LEVEL UP!* You are now level {p['level']}. "
                         f"(+{g['hp']} HP, +{g['atk']} ATK, +{g['def']} DEF, fully restored)")
        if lines:
            return lines, f":star2: *{p['name']}* reached level {p['level']}!"
        return lines, None

    def _resolve(self, p: dict, lines: list[str]) -> Reply:
        announce = None
        if p["combat"]["hp"] == 0:
            more, announce = self._victory(p)
            lines += more
            if p["location"] != "town":
                lines.append("\n" + self.look_text(p))
        else:
            more, announce = self._monster_turn(p)
            lines += more
            if p["combat"]:
                lines.append("\n" + self.combat_text(p))
        return Reply("\n".join(lines), self.menu_buttons(p), announce)

    def cmd_attack(self, p: dict, _args: str) -> Reply:
        if not p["combat"]:
            return Reply("There's nothing to attack. Try `explore`.", self.menu_buttons(p))
        m = MONSTERS[p["combat"]["monster"]]
        dmg, crit = self._player_hit(p)
        verb = ":boom: *Critical hit!* You strike" if crit else "You strike"
        return self._resolve(p, [f"{verb} the {m['name']} for *{dmg}*."])

    def cmd_skill(self, p: dict, _args: str) -> Reply:
        if not p["combat"]:
            return Reply("Save your strength for a fight.", self.menu_buttons(p))
        s = CLASSES[p["cls"]]["skill"]
        if p["mp"] < s["cost"]:
            return Reply(f"Not enough MP for {s['name']} ({p['mp']}/{s['cost']}).\n\n"
                         + self.combat_text(p), self.menu_buttons(p))
        p["mp"] -= s["cost"]
        m = MONSTERS[p["combat"]["monster"]]
        dmg, crit = self._player_hit(p, mult=s["mult"], pierce=s["pierce"],
                                     bonus=s.get("bonus", 0) + p["level"],
                                     force_crit=p["cls"] == "rogue")
        tag = " *Critical!*" if crit else ""
        return self._resolve(p, [f":sparkles: *{s['name']}!*{tag} The {m['name']} takes *{dmg}* damage."])

    def cmd_use(self, p: dict, args: str) -> Reply:
        k = find_item(args or "potion", p["inventory"].keys())
        if not k:
            return Reply(f"You don't have `{args}`.", self.menu_buttons(p))
        it = ITEMS[k]
        if it["type"] == "heal":
            if p["hp"] >= p["max_hp"] and not p["combat"]:
                return Reply("You're already at full health.", self.menu_buttons(p))
            amt = min(it["power"], p["max_hp"] - p["hp"])
            p["hp"] += amt
            line = f":green_heart: You drink the {it['name']} and recover *{amt} HP*."
        elif it["type"] == "mana":
            amt = min(it["power"], p["max_mp"] - p["mp"])
            p["mp"] += amt
            line = f":large_blue_diamond: You drink the {it['name']} and recover *{amt} MP*."
        elif it["type"] in ("weapon", "armor"):
            if p["combat"]:
                return Reply("No time to change gear mid-fight!\n\n" + self.combat_text(p),
                             self.menu_buttons(p))
            return self.cmd_equip(p, k)
        else:
            return Reply(f"The {it['name']} isn't useful in your hands. Try selling it.",
                         self.menu_buttons(p))
        p["inventory"][k] -= 1
        if p["inventory"][k] <= 0:
            del p["inventory"][k]
        if p["combat"]:
            more, announce = self._monster_turn(p)
            lines = [line] + more
            if p["combat"]:
                lines.append("\n" + self.combat_text(p))
            return Reply("\n".join(lines), self.menu_buttons(p), announce)
        return Reply(line, self.menu_buttons(p))

    def cmd_flee(self, p: dict, _args: str) -> Reply:
        if not p["combat"]:
            return Reply("You run in a small circle. Nobody is chasing you.", self.menu_buttons(p))
        m = MONSTERS[p["combat"]["monster"]]
        chance = 0.8 if p["cls"] == "rogue" else 0.55
        if m.get("boss"):
            chance -= 0.2
        if self.rng.random() < chance:
            p["combat"] = None
            return Reply(f":dash: You escape from the {m['name']}!\n\n" + self.look_text(p),
                         self.menu_buttons(p))
        more, announce = self._monster_turn(p)
        lines = [f"You try to flee, but the {m['name']} blocks your path!"] + more
        if p["combat"]:
            lines.append("\n" + self.combat_text(p))
        return Reply("\n".join(lines), self.menu_buttons(p), announce)

    # ------------------------------------------------------------- equipment
    def cmd_equip(self, p: dict, args: str) -> Reply:
        k = find_item(args, [i for i in p["inventory"] if ITEMS[i]["type"] in ("weapon", "armor")])
        if not k:
            return Reply(f"You have no weapon or armor called `{args}`.", self.menu_buttons(p))
        slot = ITEMS[k]["type"]
        old = p[slot]
        p[slot] = k
        p["inventory"][k] -= 1
        if p["inventory"][k] <= 0:
            del p["inventory"][k]
        if old:
            p["inventory"][old] = p["inventory"].get(old, 0) + 1
        stat = "ATK" if slot == "weapon" else "DEF"
        val = self.atk(p) if slot == "weapon" else self.defense(p)
        return Reply(f":ok_hand: You equip the *{ITEMS[k]['name']}*. {stat} is now {val}.",
                     self.menu_buttons(p))

    # --------------------------------------------------------------- village
    def _require_town(self, p: dict) -> Reply | None:
        if not LOCATIONS[p["location"]]["safe"]:
            return Reply("You need to be in Oakhollow Village for that.", self.menu_buttons(p))
        return None

    def cmd_shop(self, p: dict, _args: str) -> Reply:
        if (r := self._require_town(p)):
            return r
        lines = [f":convenience_store: *Bramble's Provisions* – you have {p['gold']}g"]
        buttons: list[Button] = []
        for k in SHOP_STOCK:
            it = ITEMS[k]
            lines.append(f"• *{it['name']}* – {it['price']}g – {it['desc']}")
            if p["gold"] >= it["price"]:
                buttons.append((f"Buy {it['name']} ({it['price']}g)", f"buy {k}", None))
        sellable = [k for k in p["inventory"] if ITEMS[k]["price"] > 0]
        if sellable:
            lines.append("\n_Sell items with `sell <item>`._")
            for k in sellable[:4]:
                buttons.append((f"Sell {ITEMS[k]['name']} ({self.sell_price(k)}g)", f"sell {k}", None))
        return Reply("\n".join(lines), buttons + [("Back", "menu", None)])

    @staticmethod
    def sell_price(k: str) -> int:
        it = ITEMS[k]
        return it["price"] if it["type"] == "junk" else it["price"] // 2

    def cmd_buy(self, p: dict, args: str) -> Reply:
        if (r := self._require_town(p)):
            return r
        k = find_item(args, SHOP_STOCK)
        if not k:
            return Reply("The shopkeeper squints. _\"Don't sell that here.\"_", self.menu_buttons(p))
        it = ITEMS[k]
        if p["gold"] < it["price"]:
            return Reply(f"You can't afford the {it['name']} ({it['price']}g, you have {p['gold']}g).",
                         [("Shop", "shop", None), ("Back", "menu", None)])
        p["gold"] -= it["price"]
        p["inventory"][k] = p["inventory"].get(k, 0) + 1
        buttons: list[Button] = []
        if it["type"] in ("weapon", "armor"):
            buttons.append((f"Equip {it['name']}", f"equip {k}", "primary"))
        return Reply(f":shopping_bags: You buy a *{it['name']}* for {it['price']}g. "
                     f"({p['gold']}g left)", buttons + [("Shop", "shop", None), ("Back", "menu", None)])

    def cmd_sell(self, p: dict, args: str) -> Reply:
        if (r := self._require_town(p)):
            return r
        k = find_item(args, p["inventory"].keys())
        if not k or ITEMS[k]["price"] <= 0:
            return Reply("You have nothing like that to sell.", self.menu_buttons(p))
        price = self.sell_price(k)
        p["gold"] += price
        p["inventory"][k] -= 1
        if p["inventory"][k] <= 0:
            del p["inventory"][k]
        return Reply(f":moneybag: Sold *{ITEMS[k]['name']}* for {price}g. ({p['gold']}g total)",
                     [("Shop", "shop", None), ("Back", "menu", None)])

    def cmd_rest(self, p: dict, _args: str) -> Reply:
        if (r := self._require_town(p)):
            return r
        if p["hp"] == p["max_hp"] and p["mp"] == p["max_mp"]:
            return Reply("You're well rested already.", self.menu_buttons(p))
        if p["gold"] < INN_COST:
            return Reply(f"A room costs {INN_COST}g and you only have {p['gold']}g.",
                         self.menu_buttons(p))
        p["gold"] -= INN_COST
        p["hp"], p["mp"] = p["max_hp"], p["max_mp"]
        return Reply(f":bed: You sleep soundly at the Sleepy Badger Inn. HP and MP fully restored. "
                     f"(-{INN_COST}g)", self.menu_buttons(p))

    # ------------------------------------------------------------ leaderboard
    def leaderboard(self, team: str, p: dict | None) -> Reply:
        players = self.store.all_players(team)
        if not players:
            return Reply("No heroes yet. Be the first!", self.menu_buttons(p))
        players.sort(key=lambda x: (x["boss_kills"], x["level"], x["xp"]), reverse=True)
        medals = [":first_place_medal:", ":second_place_medal:", ":third_place_medal:"]
        lines = [":trophy: *Heroes of Oakhollow*"]
        for i, x in enumerate(players[:10]):
            rank = medals[i] if i < 3 else f"{i + 1}."
            crown = " :dragon:" * min(x["boss_kills"], 3)
            lines.append(f"{rank} *{x['name']}* – Lv {x['level']} {x['cls'].title()}, "
                         f"{x['kills']} kills{crown}")
        return Reply("\n".join(lines), self.menu_buttons(p))


COMMANDS = {
    "menu": Game.cmd_menu, "status": Game.cmd_status, "inventory": Game.cmd_inventory,
    "look": Game.cmd_look, "travel": Game.cmd_travel, "explore": Game.cmd_explore,
    "attack": Game.cmd_attack, "skill": Game.cmd_skill, "use": Game.cmd_use,
    "flee": Game.cmd_flee, "equip": Game.cmd_equip, "shop": Game.cmd_shop,
    "buy": Game.cmd_buy, "sell": Game.cmd_sell, "rest": Game.cmd_rest,
}
COMBAT_OK = {"menu", "status", "inventory", "attack", "skill", "use", "flee", "look"}
ALIASES = {
    "stats": "status", "s": "status", "inv": "inventory", "i": "inventory", "bag": "inventory",
    "l": "look", "go": "travel", "move": "travel", "e": "explore", "a": "attack",
    "fight": "attack", "run": "flee", "inn": "rest", "sleep": "rest", "store": "shop",
    "top": "leaderboard", "lb": "leaderboard", "new": "start", "wear": "equip",
    "wield": "equip", "drink": "use", "?": "help", "m": "menu",
}
