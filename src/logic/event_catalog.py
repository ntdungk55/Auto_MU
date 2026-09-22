"""Static map catalog used by registered location events."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapDefinition:
    """One selectable game map."""

    id: int
    name: str


MAP_CATALOG: tuple[MapDefinition, ...] = (
    MapDefinition(id=1, name="Lorencia"),
    MapDefinition(id=2, name="Noria"),
    MapDefinition(id=3, name="Dungeon"),
    MapDefinition(id=4, name="Devias"),
    MapDefinition(id=5, name="Devias 2"),
    MapDefinition(id=6, name="Devias 3"),
    MapDefinition(id=7, name="Devias 4"),
    MapDefinition(id=8, name="Elbeland"),
    MapDefinition(id=9, name="Elbeland 2"),
    MapDefinition(id=10, name="Elbeland 3"),
    MapDefinition(id=11, name="Dungeon 2"),
    MapDefinition(id=12, name="Dungeon 3"),
    MapDefinition(id=13, name="Lost Tower"),
    MapDefinition(id=14, name="Lost Tower 2"),
    MapDefinition(id=15, name="Lost Tower 3"),
    MapDefinition(id=16, name="Lost Tower 4"),
    MapDefinition(id=17, name="Lost Tower 5"),
    MapDefinition(id=18, name="Lost Tower 6"),
    MapDefinition(id=19, name="Lost Tower 7"),
    MapDefinition(id=20, name="Atlans"),
    MapDefinition(id=21, name="Atlans 2"),
    MapDefinition(id=22, name="Atlans 3"),
    MapDefinition(id=23, name="Tarkan"),
    MapDefinition(id=24, name="Tarkan 2"),
    MapDefinition(id=25, name="Icarus"),
    MapDefinition(id=26, name="Aida"),
    MapDefinition(id=27, name="Aida 2"),
    MapDefinition(id=28, name="Kanturu Ruins"),
    MapDefinition(id=29, name="Kanturu Ruins 2"),
    MapDefinition(id=30, name="Kanturu Ruins Island"),
    MapDefinition(id=31, name="Kanturu Remain"),
    MapDefinition(id=32, name="Karutan"),
    MapDefinition(id=33, name="Karutan 2"),
    MapDefinition(id=34, name="Vulcanus"),
    MapDefinition(id=35, name="Akeron"),
    MapDefinition(id=36, name="Swamp of Calmness"),
    MapDefinition(id=37, name="Raklion"),
    MapDefinition(id=38, name="Ferea"),
    MapDefinition(id=39, name="Nixies Lake"),
    MapDefinition(id=40, name="Old Kethotum"),
    MapDefinition(id=41, name="Deep Dungeon 1"),
    MapDefinition(id=42, name="Deep Dungeon 2"),
    MapDefinition(id=43, name="Deep Dungeon 3"),
    MapDefinition(id=44, name="Deep Dungeon 4"),
    MapDefinition(id=45, name="Deep Dungeon 5"),
    MapDefinition(id=46, name="Swamp of Darkness"),
    MapDefinition(id=47, name="Barracks"),
    MapDefinition(id=48, name="Refuge"),
    MapDefinition(id=49, name="Crywolf"),
    MapDefinition(id=50, name="Loren Deep"),
    MapDefinition(id=51, name="Kubera Mine"),
    MapDefinition(id=52, name="Abyss of Atlans"),
    MapDefinition(id=53, name="Abyss of Atlans 2"),
    MapDefinition(id=54, name="Abyss of Atlans 3"),
    MapDefinition(id=55, name="Scorched Canyon"),
    MapDefinition(id=56, name="Red Smoke Icarus"),
    MapDefinition(id=57, name="Arenil Temple"),
    MapDefinition(id=58, name="Ashen Aida"),
    MapDefinition(id=59, name="Blaze Kethotum"),
    MapDefinition(id=60, name="Kanturu Undergrounds"),
    MapDefinition(id=61, name="Ignis Volcano"),
    MapDefinition(id=62, name="Bloody Tarkan"),
    MapDefinition(id=63, name="Tormenta Island"),
    MapDefinition(id=64, name="Twisted Karutan"),
    MapDefinition(id=65, name="Kardamahal Underground Temple"),
    MapDefinition(id=66, name="Swamp of Destruction"),
    MapDefinition(id=67, name="Aquilas Temple"),
    MapDefinition(id=68, name="Arena"),
    MapDefinition(id=69, name="Event Square"),
    MapDefinition(id=70, name="Loren Market"),
    MapDefinition(id=71, name="Valley of Loren"),
    MapDefinition(id=72, name="Land of Trial"),
    MapDefinition(id=73, name="Devil Square"),
    MapDefinition(id=74, name="Blood Castle"),
    MapDefinition(id=75, name="Chaos Castle"),
    MapDefinition(id=76, name="Kalima"),
    MapDefinition(id=77, name="Illusion Temple"),
    MapDefinition(id=78, name="Doppelganger"),
    MapDefinition(id=79, name="Empire Guardian"),
    MapDefinition(id=80, name="Santa Village"),
    MapDefinition(id=81, name="Silent Map"),
    MapDefinition(id=82, name="Acheron"),
    MapDefinition(id=83, name="Debenter"),
    MapDefinition(id=84, name="Urk Mountain"),
    MapDefinition(id=85, name="Tormented Square"),
    MapDefinition(id=86, name="Nars"),
    MapDefinition(id=87, name="Boss Battle"),
)


def map_by_id(map_id: int) -> MapDefinition | None:
    """Return a catalog map by ID."""
    return next((item for item in MAP_CATALOG if item.id == int(map_id)), None)
