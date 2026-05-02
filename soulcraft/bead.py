"""Universal concept node for the Glass Bead Game engine."""


VALID_TYPES = frozenset({
    "character", "person", "historical_figure", "work", "concept",
    "archetype", "mythological", "place",
})

VALID_DOMAINS = frozenset({
    "music", "mathematics", "philosophy", "literature", "visual_art",
    "science", "psychology", "martial_arts", "spirituality", "technology",
    "nature", "culture",
})

VALID_THEMES = frozenset({
    "transformation", "power", "outsider", "creation", "shadow", "wisdom",
    "connection", "struggle", "freedom", "spiritual", "trickster",
    "explorer", "caregiver", "sage", "achiever", "loyalist", "enthusiast",
    "challenger", "peacemaker", "reformer",
})

VALID_PROVENANCE = frozenset({"first-hand", "second-hand", "inferred", ""})


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


class Bead:
    """A universal concept node in the Glass Bead Game.

    Represents any entity -- character, person, work, concept, archetype,
    mythological figure, or place -- that can participate in bead connections.
    """

    __slots__ = (
        "name", "canonical", "type", "domains", "themes", "traits",
        "sentiment", "intensity", "confidence", "provenance", "enrichment",
        "related",
    )

    def __init__(
        self,
        name: str = "",
        canonical: str = "",
        type: str = "concept",
        domains: list | None = None,
        themes: list | None = None,
        traits: list | None = None,
        sentiment: float = 0.0,
        intensity: float = 0.5,
        confidence: float = 0.5,
        provenance: str = "",
        enrichment: dict | None = None,
        related: list | None = None,
    ):
        self.name = name
        self.canonical = canonical or name
        self.type = type if type in VALID_TYPES else "concept"
        self.domains = list(domains) if domains else []
        self.themes = list(themes) if themes else []
        self.traits = list(traits) if traits else []
        self.sentiment = float(sentiment)
        self.intensity = float(intensity)
        self.confidence = float(confidence)
        self.provenance = provenance if provenance in VALID_PROVENANCE else ""
        self.enrichment = dict(enrichment) if enrichment else {}
        self.related = list(related) if related else []

    def validate(self) -> "Bead":
        """Clamp numeric fields to their valid ranges and return self."""
        self.sentiment = _clamp(self.sentiment, -1.0, 1.0)
        self.intensity = _clamp(self.intensity, 0.0, 1.0)
        self.confidence = _clamp(self.confidence, 0.0, 1.0)
        if self.type not in VALID_TYPES:
            self.type = "concept"
        if self.provenance not in VALID_PROVENANCE:
            self.provenance = ""
        return self

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "canonical": self.canonical,
            "type": self.type,
            "domains": self.domains,
            "themes": self.themes,
            "traits": self.traits,
            "sentiment": self.sentiment,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "enrichment": self.enrichment,
            "related": self.related,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Bead":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            canonical=data.get("canonical", ""),
            type=data.get("type", "concept"),
            domains=data.get("domains"),
            themes=data.get("themes"),
            traits=data.get("traits"),
            sentiment=data.get("sentiment", 0.0),
            intensity=data.get("intensity", 0.5),
            confidence=data.get("confidence", 0.5),
            provenance=data.get("provenance", ""),
            enrichment=data.get("enrichment"),
            related=data.get("related"),
        )

    def update_from_dict(self, data: dict) -> "Bead":
        """Merge enrichment data from a dict back onto this Bead.

        Only updates fields that are present and non-empty in data.
        Themes are merged (union), not replaced.
        """
        desc = data.get("description", "")
        if desc and "wikipedia" not in self.enrichment:
            self.enrichment["wikipedia"] = desc
        elif desc:
            self.enrichment["wikipedia"] = desc

        wiki_themes = data.get("themes", [])
        if wiki_themes:
            existing = set(self.themes)
            self.themes = sorted(existing | set(wiki_themes))

        for key in ("source", "knowledge_base", "big_five"):
            val = data.get(key)
            if val and key not in self.enrichment:
                self.enrichment[key] = val

        return self

    def __repr__(self) -> str:
        return f"Bead({self.canonical!r}, type={self.type!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Bead):
            return NotImplemented
        return self.canonical.lower() == other.canonical.lower()

    def __hash__(self) -> int:
        return hash(self.canonical.lower())
