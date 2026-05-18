"""Data loader for Elixis knowledge files.

Loads and caches JSON data from elixis/data/ on first access.
All accessors return plain Python data structures (dicts, lists).
"""

import json
import logging
import os
from functools import lru_cache

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
logger = logging.getLogger("elixis.knowledge")


def _load_json(filename):
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Knowledge JSON file missing: %s", filename)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in %s: %s", filename, exc)
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
                    except json.JSONDecodeError as exc:
                        logger.warning("Skipping invalid JSONL row in %s: %s", filename, exc)
                        continue
    except FileNotFoundError:
        logger.warning("Knowledge JSONL file missing: %s", filename)
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


@lru_cache(maxsize=1)
def taxonomy():
    """Scientific taxonomy dataset for naming (JSON array)."""
    return _load_json("taxonomy.json")


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


def taxonomy_by_name(name):
    """Return a single taxonomy entry by name (case-insensitive), or None."""
    key = name.lower()
    for entry in taxonomy():
        if entry.get("name", "").lower() == key:
            return entry
    return None


def taxonomy_by_kingdom(kingdom):
    """Return all taxonomy entries matching a kingdom (e.g. 'plantae')."""
    k = kingdom.lower()
    return [e for e in taxonomy() if e.get("kingdom", "").lower() == k]


def taxonomy_search(query, limit=10):
    """Search taxonomy by name, common_name, etymology, or keywords."""
    q = query.lower()
    scored = []
    for entry in taxonomy():
        score = 0.0
        if q in entry.get("name", "").lower():
            score += 3.0
        if q in entry.get("common_name", "").lower():
            score += 2.0
        for kw in entry.get("keywords", []):
            if q in kw.lower():
                score += 1.5
                break
        if q in entry.get("etymology", "").lower():
            score += 1.0
        for theme in entry.get("themes", []):
            if q in theme.lower():
                score += 1.0
                break
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]


def clear_cache():
    """Clear all cached data. Useful after data file updates."""
    traits.cache_clear()
    archetypes.cache_clear()
    domains.cache_clear()
    relationships.cache_clear()
    entity_types.cache_clear()
    characters.cache_clear()
    taxonomy.cache_clear()
