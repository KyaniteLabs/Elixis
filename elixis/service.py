"""Elixis use cases: the one module the CLI, HTTP and MCP adapters call.

Adapters parse requests and present results (exit codes, MCP envelopes, HTTP
response shapes). Input validation, engine orchestration and reading results
out of engine state live here once, so a capability or a fix lands in one
place for every surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .engine import GameEngine
from .entities import extract_entities
from .patterns import build_pattern_graph
from .process_trace import process_trace_from_state
from .thread import serialize_threads
from .validation import validate_brain_dump

LENSES = ("identity", "brand", "design")


class InvalidInput(ValueError):
    """Input rejected before any work ran; the message is safe to show a caller."""


def prepare_text(text: str) -> str:
    """Validate a brain dump and return its sanitized form."""
    is_valid, error, meta = validate_brain_dump(text)
    if not is_valid:
        raise InvalidInput(error)
    return meta.get("sanitized_text", text)


@dataclass(frozen=True)
class SynthesisRun:
    """A finished pipeline run: the lens output plus what the engine learned."""

    lens: str
    output: str
    state: Any

    @property
    def graph(self) -> dict:
        return self.state.metadata.get("pattern_graph", {})

    @property
    def entities(self) -> list[dict]:
        return [bead.to_dict() for bead in self.state.beads]

    @property
    def threads(self) -> list:
        return self.graph.get("threads") or serialize_threads(self.state.threads)

    @property
    def thread_count(self) -> int:
        return self.graph.get("thread_count", len(self.state.threads))

    @property
    def cross_domain_thread_count(self) -> int:
        return self.graph.get("cross_domain_thread_count", 0)

    @property
    def tensions(self) -> list:
        return self.state.tensions

    @property
    def timings(self) -> dict:
        return self.state.timings

    def process_trace(self) -> dict:
        return process_trace_from_state(self.state, lens=self.lens)

    def summary(self) -> dict:
        """The compact result the CLI (--json) and MCP tools report."""
        graph = self.graph
        return {
            "lens": self.lens,
            "entity_count": len(self.state.beads),
            "thread_count": self.thread_count,
            "cross_domain_thread_count": self.cross_domain_thread_count,
            "threads": self.threads[:8],
            "tension_count": len(self.state.tensions),
            "top_patterns": [p.get("name") for p in graph.get("patterns", [])[:3]],
            "emergent_topic": graph.get("emergent_topic"),
            "emergent_theme": graph.get("emergent_theme"),
            "consensus_score": graph.get("consensus_score"),
            "process_trace": self.process_trace(),
            "output": self.output,
        }


def synthesize(text: str, lens: str = "identity") -> SynthesisRun:
    """Run the full pipeline on text already returned by prepare_text.

    Raises InvalidInput for an unknown lens; engine failures (RuntimeError)
    propagate so each adapter can report them in its own shape.
    """
    if lens not in LENSES:
        raise InvalidInput(f"lens must be one of {', '.join(LENSES)}")
    engine = GameEngine()
    output = engine.run_full(text, lens=lens)
    return SynthesisRun(lens=lens, output=output, state=engine.state)


def patterns(text: str) -> dict:
    """Extract entities from prepared text and build their pattern graph."""
    return build_pattern_graph(extract_entities(text), text)


def name_from_identity(text: str, source: str = "taxonomy") -> dict:
    """Name candidates grounded in the identity the pipeline finds in text."""
    engine = GameEngine()
    engine.declare_themes(text)
    engine.elaborate()
    engine.connect_domains()
    return engine.name(source=source)
