import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from my_game.characters.player import Player
from my_game.characters.character_class import CharacterClass
from my_game.items.item import GearItem, PotionItem
from my_game.items.enums import ItemSlot, ItemClass, ItemQuality


def test_equip_item_stats():
    player = Player(id=1, username="tester")
    pc = player.create_character("Hero", CharacterClass.WARRIOR)
    gear = GearItem(
        name="Helm",
        price=10,
        slot=ItemSlot.HEAD,
        quality=ItemQuality.FINE,
        allowed_classes=[ItemClass.WARRIOR],
        stats={"strength": 2, "health": 5},
    )

    base_str = pc.strength
    base_hp = pc.max_health
    pc.equip_item(gear)

    assert pc.equipment[ItemSlot.HEAD] is gear
    assert pc.strength == base_str + 2
    assert pc.max_health == base_hp + 5


def test_consume_potion():
    player = Player(id=2, username="tester")
    pc = player.create_character("Mage", CharacterClass.MAGE)
    pc.health = pc.max_health - 30
    pc.mana = pc.base_mana - 10

    potion = PotionItem(name="Elixir", price=0, heal=20, mana=5)
    pc.consume_potion(potion)

    assert pc.health == pc.max_health - 10
    assert pc.mana == pc.base_mana - 5
