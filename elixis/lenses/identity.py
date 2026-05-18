"""Identity output lens — SOUL.md generation for the pattern synthesis.

Wraps the existing synthesis module as an output lens.
"""

from ..synthesis import synthesize_soulmd, synthesize_soulmd_stream


def generate_identity(entities, graph):
    """Generate a SOUL.md identity document from entities and pattern graph.

    This is the primary identity lens. Delegates to synthesis.synthesize_soulmd
    for backward compatibility.
    """
    return synthesize_soulmd(entities, graph)


def generate_identity_stream(entities, graph, stage_timings=None):
    """Stream SOUL.md generation. Yields SSE-compatible events."""
    yield from synthesize_soulmd_stream(entities, graph, stage_timings)
