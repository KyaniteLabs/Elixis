"""Data loader for SoulCraft knowledge files.

Loads and caches JSON data from soulcraft/data/ on first access.
All accessors return plain Python data structures (dicts, lists).
"""

import json
import os
from functools import lru_cache

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json(filename):
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        import logging
        logging.getLogger("soulcraft.knowledge").error("Invalid JSON in %s: %s", filename, exc)
        return {}


def _load_jsonl(filename):
    path = os.path.join(_DATA_DIR, filename)
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    return entries


@lru_cache(maxsize=1)
def traits():
    """Big Five 30-facet taxonomy."""
    return _load_json("traits.json")


@lru_cache(maxsize=1)
def archetypes():
    """24-archetype system with profiles, voice, principles."""
    return _load_json("archetypes.json")


@lru_cache(maxsize=1)
def domains():
    """Universal domain taxonomy with isomorphisms."""
    return _load_json("domains.json")


@lru_cache(maxsize=1)
def relationships():
    """Entity relationship type definitions."""
    return _load_json("relationships.json")


@lru_cache(maxsize=1)
def entity_types():
    """Unified entity type schema."""
    return _load_json("entity_types.json")


@lru_cache(maxsize=1)
def characters():
    """Seed knowledge base (JSONL)."""
    return _load_jsonl("characters.jsonl")


# ── Lookup helpers ──────────────────────────────────────────────────


def archetype_by_id(arch_id):
    """Return a single archetype dict by ID, or None."""
    for a in archetypes()["archetypes"]:
        if a["id"] == arch_id:
            return a
    return None


def entity_type_by_id(type_id):
    """Return a single entity type dict by ID, or None."""
    for t in entity_types()["types"]:
        if t["id"] == type_id:
            return t
    return None


def character_by_name(name):
    """Return the first character matching canonical name (case-insensitive)."""
    key = name.lower()
    for c in characters():
        if c.get("canonical", "").lower() == key or c.get("name", "").lower() == key:
            return c
    return None


def trait_keywords():
    """Flat list of all Big Five trait keywords across all facets."""
    kw = []
    for domain in traits()["domains"]:
        for facet in domain["facets"]:
            kw.extend(facet["keywords"])
    return kw


def archetype_ids():
    """List of all archetype IDs in order."""
    return [a["id"] for a in archetypes()["archetypes"]]


def domain_ids():
    """List of all domain IDs."""
    return [d["id"] for d in domains()["domains"]]


def relationship_ids():
    """List of all relationship type IDs."""
    return [r["id"] for r in relationships()["relationships"]]


def clear_cache():
    """Clear all cached data. Useful after data file updates."""
    traits.cache_clear()
    archetypes.cache_clear()
    domains.cache_clear()
    relationships.cache_clear()
    entity_types.cache_clear()
    characters.cache_clear()
