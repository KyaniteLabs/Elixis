"""Cross-domain connection for the pattern synthesis engine."""

from __future__ import annotations


RELATIONSHIPS = (
    "admires",
    "identifies_with",
    "fascinated_by",
    "fears_becoming",
    "contrasts_with",
    "aspires_to",
    "rivals",
    "mentored_by",
    "complements",
    "parallels",
)


def is_cross_domain_thread_data(thread: dict) -> bool:
    """Return True when serialized thread data bridges distinct domains."""
    domains = [d for d in thread.get("domains_bridged", []) if d]
    return bool(thread.get("isomorphic") or (len(domains) >= 2 and domains[0] != domains[1]))


def serialize_thread(thread) -> dict:
    """Return public thread data for Thread instances or dict-like fixtures."""
    if isinstance(thread, dict):
        return thread
    if hasattr(thread, "to_dict"):
        return thread.to_dict()
    return {}


def serialize_threads(threads) -> list[dict]:
    """Serialize thread collections while ignoring non-public placeholders."""
    return [data for data in (serialize_thread(thread) for thread in threads or []) if data]


class Thread:
    """A connection between two Beads across domains."""

    __slots__ = (
        "bead_a",
        "bead_b",
        "relationship",
        "strength",
        "isomorphic",
        "domains_bridged",
        "evidence",
    )

    def __init__(
        self,
        bead_a: str = "",
        bead_b: str = "",
        relationship: str = "parallels",
        strength: float = 0.5,
        isomorphic: bool = False,
        domains_bridged: tuple[str, str] = ("", ""),
        evidence: list[str] | None = None,
    ) -> None:
        self.bead_a = bead_a
        self.bead_b = bead_b
        self.relationship = relationship
        self.strength = strength
        self.isomorphic = isomorphic
        self.domains_bridged = tuple(domains_bridged)
        self.evidence = list(evidence) if evidence else []

    def validate(self) -> Thread:
        """Clamp strength to [0, 1] and return self."""
        self.strength = max(0.0, min(1.0, self.strength))
        return self

    def to_dict(self) -> dict:
        return {
            "bead_a": self.bead_a,
            "bead_b": self.bead_b,
            "relationship": self.relationship,
            "strength": self.strength,
            "isomorphic": self.isomorphic,
            "domains_bridged": list(self.domains_bridged),
            "evidence": list(self.evidence),
        }

    def is_cross_domain(self) -> bool:
        return is_cross_domain_thread_data(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> Thread:
        return cls(
            bead_a=data.get("bead_a", ""),
            bead_b=data.get("bead_b", ""),
            relationship=data.get("relationship", "parallels"),
            strength=data.get("strength", 0.5),
            isomorphic=data.get("isomorphic", False),
            domains_bridged=tuple(data.get("domains_bridged", ("", ""))),
            evidence=data.get("evidence"),
        )

    def __repr__(self) -> str:
        return f"{self.bead_a} --{self.relationship}--> {self.bead_b}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Thread):
            return NotImplemented
        return (self.bead_a, self.bead_b, self.relationship) == (
            other.bead_a,
            other.bead_b,
            other.relationship,
        )

    def __hash__(self) -> int:
        return hash((self.bead_a, self.bead_b, self.relationship))
