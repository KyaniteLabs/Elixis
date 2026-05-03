"""Output lens system for the Glass Bead Game.

Each lens takes (entities: list[dict], graph: dict) and returns a markdown string.
Register new lenses by adding them to LENS_REGISTRY.
"""

from .brand import generate_brand
from .design import generate_design
from .identity import generate_identity, generate_identity_stream as generate_identity_stream

LENS_REGISTRY = {
    "identity": generate_identity,
    "brand": generate_brand,
    "design": generate_design,
}

AVAILABLE_LENSES = sorted(LENS_REGISTRY.keys())
