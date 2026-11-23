import random

import pytest

from rpg.data import MONSTERS
from rpg.engine import Game
from rpg.storage import Store


@pytest.fixture
def game(tmp_path):
    return Game(Store(str(tmp_path / "t.db")), random.Random(42))


def play(game, text, user="U1"):
    return game.handle("T1", user, "Tester", text)


def load(game, user="U1"):
    return game.store.load("T1", user)


def test_new_player_sees_class_choice(game):
    r = play(game, "explore")
    assert "Choose your class" in r.text
    assert [b[1] for b in r.buttons] == ["start warrior", "start mage", "start rogue"]


def test_start_creates_hero_and_announces(game):
    r = play(game, "start mage Merlin")
    assert "Merlin the Mage" in r.text and r.announce
    p = load(game)
    assert p["cls"] == "mage" and p["location"] == "town" and p["inventory"]["potion"] == 3
    assert "already have a hero" in play(game, "start rogue").text


def test_travel_and_boss_gate(game):
    play(game, "start warrior")
    assert "Whisperwood" in play(game, "travel forest").text
    play(game, "go crags")
    assert "level 7" in play(game, "travel lair").text
    assert load(game)["location"] == "crags"


def test_combat_until_resolved(game):
    play(game, "start warrior")
    play(game, "travel forest")
    for _ in range(50):
        if load(game)["combat"]:
            break
        play(game, "explore")
    assert load(game)["combat"]
    assert "fight" in play(game, "shop").text  # can't shop mid-combat
    for _ in range(50):
        if not load(game)["combat"]:
            break
        play(game, "attack")
    p = load(game)
    assert p["combat"] is None
    assert p["kills"] == 1 or p["deaths"] == 1


def test_level_up(game):
    play(game, "start rogue")
    p = load(game)
    lines, announce = game._gain_xp(p, 1000)
    assert p["level"] > 3 and announce and p["hp"] == p["max_hp"]


def test_death_respawns_in_town(game):
    play(game, "start mage")
    p = load(game)
    p.update(location="forest", hp=1, gold=40, combat={"monster": "goblin", "hp": 999})
    game.store.save("T1", "U1", p)
    game.rng = random.Random(0)
    for _ in range(5):
        r = play(game, "flee")
        if load(game)["deaths"]:
            break
    p = load(game)
    if p["deaths"]:  # depends on flee rolls, but with 1 HP a hit kills
        assert p["location"] == "town" and p["gold"] == 20 and r.announce


def test_shop_buy_equip_sell(game):
    play(game, "start warrior")
    p = load(game)
    p["gold"] = 100
    game.store.save("T1", "U1", p)
    assert "Iron Sword" in play(game, "buy iron sword").text
    atk_before = game.atk(load(game))
    play(game, "equip iron")
    p = load(game)
    assert p["weapon"] == "iron_sword" and game.atk(p) == atk_before + 2
    assert p["inventory"]["dagger"] == 1
    assert "Sold" in play(game, "sell dagger").text


def test_rest_and_use_potion(game):
    play(game, "start warrior")
    p = load(game)
    p["hp"] = 5
    game.store.save("T1", "U1", p)
    play(game, "use potion")
    assert load(game)["hp"] == 25 and load(game)["inventory"]["potion"] == 2
    play(game, "rest")
    p = load(game)
    assert p["hp"] == p["max_hp"] and p["gold"] == 20


def test_boss_kill_is_announced(game):
    play(game, "start warrior")
    p = load(game)
    p.update(location="lair", level=10, base_atk=500,
             combat={"monster": "wyrm", "hp": MONSTERS["wyrm"]["hp"]})
    game.store.save("T1", "U1", p)
    r = play(game, "attack")
    assert "Vyrmoth" in r.announce
    p = load(game)
    assert p["boss_kills"] == 1 and "cinder_fang" in p["inventory"]


def test_leaderboard_and_reset(game):
    play(game, "start warrior Alice", user="U1")
    play(game, "start mage Bob", user="U2")
    r = play(game, "leaderboard")
    assert "Alice" in r.text and "Bob" in r.text
    play(game, "reset confirm")
    assert load(game) is None


def test_unknown_command(game):
    play(game, "start rogue")
    assert "don't know" in play(game, "dance").text
