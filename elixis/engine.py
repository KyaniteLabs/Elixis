"""The Game Engine — core orchestrator for the Glass Bead Game.

Manages game state through four phases:
  declaration → elaboration → connection → resolution
"""

import time
from .bead import Bead
from .thread import Thread


class GameState:
    """Immutable snapshot of the game at a point in time."""

    __slots__ = (
        "phase", "beads", "threads", "scores", "provenance",
        "tensions", "raw_input", "timings", "metadata",
    )

    def __init__(self, raw_input="", phase="init"):
        self.phase = phase
        self.beads = []
        self.threads = []
        self.scores = {}
        self.provenance = {}
        self.tensions = []
        self.raw_input = raw_input
        self.timings = {}
        self.metadata = {}

    def to_dict(self):
        return {
            "phase": self.phase,
            "beads": [b.to_dict() for b in self.beads],
            "threads": [t.to_dict() for t in self.threads],
            "scores": self.scores,
            "provenance": self.provenance,
            "tensions": self.tensions,
            "timings": self.timings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data):
        state = cls(raw_input=data.get("raw_input", ""), phase=data.get("phase", "init"))
        state.beads = [Bead.from_dict(b) for b in data.get("beads", [])]
        state.threads = [Thread.from_dict(t) for t in data.get("threads", [])]
        state.scores = data.get("scores", {})
        state.provenance = data.get("provenance", {})
        state.tensions = data.get("tensions", [])
        state.timings = data.get("timings", {})
        state.metadata = data.get("metadata", {})
        return state


class GameEngine:
    """Orchestrates the Glass Bead Game through its four phases.

    Accepts optional dependency overrides for testing. When omitted,
    the default implementations are used.
    """

    def __init__(
        self,
        extract_entities=None,
        enrich_entities=None,
        build_pattern_graph=None,
        build_relationship_graph=None,
        annotate_bead=None,
        deduplicate_beads=None,
        character_by_name=None,
    ):
        self._state = None

        # Lazy imports stored as None mean "import on first use"
        self._extract_entities = extract_entities
        self._enrich_entities = enrich_entities
        self._build_pattern_graph = build_pattern_graph
        self._build_relationship_graph = build_relationship_graph
        self._annotate_bead = annotate_bead
        self._deduplicate_beads = deduplicate_beads
        self._character_by_name = character_by_name

    def _get_extract_entities(self):
        if self._extract_entities is not None:
            return self._extract_entities
        from .entities import extract_entities
        self._extract_entities = extract_entities
        return extract_entities

    def _get_enrich_entities(self):
        if self._enrich_entities is not None:
            return self._enrich_entities
        from .research import enrich_entities
        self._enrich_entities = enrich_entities
        return enrich_entities

    def _get_build_pattern_graph(self):
        if self._build_pattern_graph is not None:
            return self._build_pattern_graph
        from .patterns import build_pattern_graph
        self._build_pattern_graph = build_pattern_graph
        return build_pattern_graph

    def _get_build_relationship_graph(self):
        if self._build_relationship_graph is not None:
            return self._build_relationship_graph
        from .graph import build_relationship_graph
        self._build_relationship_graph = build_relationship_graph
        return build_relationship_graph

    def _get_annotate_bead(self):
        if self._annotate_bead is not None:
            return self._annotate_bead
        from .sentiment import annotate_bead
        self._annotate_bead = annotate_bead
        return annotate_bead

    def _get_deduplicate_beads(self):
        if self._deduplicate_beads is not None:
            return self._deduplicate_beads
        from .resolution import deduplicate_beads
        self._deduplicate_beads = deduplicate_beads
        return deduplicate_beads

    def _get_character_by_name(self):
        if self._character_by_name is not None:
            return self._character_by_name
        from .knowledge import character_by_name
        self._character_by_name = character_by_name
        return character_by_name

    @property
    def state(self):
        return self._state

    def new_game(self, raw_input):
        """Start a new game with raw text input."""
        self._state = GameState(raw_input=raw_input, phase="init")
        return self._state

    # ── Phase 1: Declaration ──────────────────────────────────────────

    def declare_themes(self, raw_input=None):
        """Parse input into beads, resolve entities, detect sentiment/intensity.

        Uses LLM extraction with heuristic fallback.
        """
        if raw_input:
            self.new_game(raw_input)

        state = self._state
        if not state:
            raise RuntimeError("No game in progress. Call new_game() first.")

        start = time.time()
        extract_entities = self._get_extract_entities()
        annotate_bead = self._get_annotate_bead()
        deduplicate_beads = self._get_deduplicate_beads()

        extraction_tele = {}
        raw_entities = extract_entities(state.raw_input, telemetry=extraction_tele)
        state.metadata["extraction_telemetry"] = extraction_tele

        beads = []
        for e in raw_entities:
            annotations = annotate_bead(
                f"{e.get('canonical', '')} {e.get('description', '')} "
                f"{' '.join(e.get('traits', []))}"
            )
            bead = Bead(
                name=e.get("original", e.get("canonical", "")),
                canonical=e.get("canonical", ""),
                type=e.get("type", "concept"),
                domains=_infer_domains(e),
                themes=e.get("themes", []),
                traits=e.get("traits", []),
                sentiment=annotations["sentiment"],
                intensity=annotations["intensity"],
                confidence=e.get("confidence", 0.5),
                provenance="first-hand" if e.get("confidence", 0) > 0.8 else "inferred",
                enrichment={
                    "source": e.get("source", ""),
                    "description": e.get("description", ""),
                    "related": e.get("related", []),
                },
                related=e.get("related", []),
            )
            bead.validate()
            beads.append(bead)

        state.beads = deduplicate_beads(beads)
        state.phase = "declaration"
        state.timings["declaration_ms"] = int((time.time() - start) * 1000)
        state.provenance["bead_count"] = len(state.beads)
        return state

    # ── Phase 2: Elaboration ──────────────────────────────────────────

    def elaborate(self):
        """Enrich beads with external data (Wikipedia, knowledge base).

        Runs research enrichment and cross-references with the curated
        character knowledge base.
        """
        state = self._state
        if not state or state.phase not in ("init", "declaration"):
            raise RuntimeError("Must declare_themes() before elaborate().")

        start = time.time()
        enrich_entities = self._get_enrich_entities()
        character_by_name = self._get_character_by_name()

        entity_dicts = [b.to_dict() for b in state.beads]
        enrich_tele = {}
        enriched = enrich_entities(entity_dicts, telemetry=enrich_tele)
        state.metadata["enrichment_telemetry"] = enrich_tele

        for i, enriched_data in enumerate(enriched):
            if i < len(state.beads):
                bead = state.beads[i]
                bead.update_from_dict(enriched_data)

                known = character_by_name(bead.canonical)
                if known:
                    bead.enrichment["knowledge_base"] = known
                    if known.get("big_five") and "big_five" not in bead.enrichment:
                        bead.enrichment["big_five"] = known["big_five"]
                    if known.get("archetype_scores"):
                        for arch_id, score in known["archetype_scores"].items():
                            state.scores[f"{bead.canonical}::{arch_id}"] = score

        state.phase = "elaboration"
        state.timings["elaboration_ms"] = int((time.time() - start) * 1000)
        return state

    # ── Phase 3: Connection ───────────────────────────────────────────

    def connect_domains(self):
        """Build pattern graph, detect bridges, find cross-domain connections.

        Multi-dimensional scoring: Big Five projection, archetype detection,
        motivation mapping. Creates Threads between beads.
        """
        state = self._state
        if not state or state.phase not in ("declaration", "elaboration"):
            raise RuntimeError("Must elaborate() before connect_domains().")

        start = time.time()
        build_pattern_graph = self._get_build_pattern_graph()

        entity_dicts = [b.to_dict() for b in state.beads]
        pattern_tele = {}
        graph = build_pattern_graph(entity_dicts, state.raw_input, telemetry=pattern_tele)
        state.metadata["pattern_telemetry"] = pattern_tele

        state.metadata["pattern_graph"] = graph
        threads = []

        for bridge in graph.get("bridges", []):
            threads.append(Thread(
                bead_a=bridge["entity"],
                bead_b=bridge["pattern_a"],
                relationship="bridges",
                strength=(bridge["score_a"] + bridge["score_b"]) / 2,
                isomorphic=False,
                domains_bridged=("", ""),
                evidence=[f"Connects {bridge['pattern_a']} ({bridge['score_a']:.0%}) "
                          f"to {bridge['pattern_b']} ({bridge['score_b']:.0%})"],
            ))

        build_rel_graph = self._get_build_relationship_graph()
        rel_graph = build_rel_graph(state.beads)
        for edge in rel_graph["edges"]:
            threads.append(Thread(
                bead_a=edge["bead_a"],
                bead_b=edge["bead_b"],
                relationship=edge["relationship"],
                strength=edge["strength"],
                isomorphic=edge["isomorphic"],
                domains_bridged=edge["domains_bridged"],
                evidence=edge["evidence"],
            ))

        state.threads = threads
        state.phase = "connection"
        state.timings["connection_ms"] = int((time.time() - start) * 1000)

        if graph.get("consensus_score", 0) < 0.3 and len(state.beads) >= 3:
            state.tensions.append({
                "type": "essential_tension",
                "description": f"Low consensus ({graph['consensus_score']:.0%}) — "
                               f"identity draws from diverse, equally weighted influences",
                "patterns": [p["name"] for p in graph.get("patterns", [])[:3]],
            })

        return state

    # ── Phase 4: Resolution ───────────────────────────────────────────

    def resolve(self, lens="identity"):
        """Generate output through the chosen lens.

        Args:
            lens: output lens to use ("identity", "brand", "design", etc.)

        Returns:
            Generated output document (e.g., SOUL.md for identity lens).
        """
        state = self._state
        if not state or state.phase not in ("elaboration", "connection"):
            raise RuntimeError("Must connect_domains() before resolve().")

        start = time.time()
        graph = state.metadata.get("pattern_graph", {})
        entity_dicts = [b.to_dict() for b in state.beads]

        from .lenses import LENS_REGISTRY
        if lens not in LENS_REGISTRY:
            raise RuntimeError(f"Invalid lens '{lens}'. Must be one of: {', '.join(sorted(LENS_REGISTRY))}")
        generator = LENS_REGISTRY[lens]
        output = generator(entity_dicts, graph)

        state.phase = "resolution"
        state.timings["resolution_ms"] = int((time.time() - start) * 1000)
        state.metadata["output"] = output
        state.metadata["lens"] = lens
        return output

    def resolve_stream(self, lens="identity", stage_timings=None):
        """Stream output through the chosen lens. Yields SSE-compatible events."""
        state = self._state
        if not state or state.phase not in ("elaboration", "connection"):
            raise RuntimeError("Must connect_domains() before resolve().")

        graph = state.metadata.get("pattern_graph", {})
        entity_dicts = [b.to_dict() for b in state.beads]
        timings = stage_timings or dict(state.timings)

        if lens == "identity":
            from .lenses.identity import generate_identity_stream
            yield from generate_identity_stream(entity_dicts, graph, timings)
        else:
            output = self.resolve(lens)
            yield {"type": "soulmd_token", "content": output}
            yield {"type": "soulmd_done", "data": {"length": len(output), "source": lens}}

    # ── Phase 5: Naming (optional) ─────────────────────────────────────

    def name(self, source="taxonomy"):
        """Generate naming suggestions grounded in the synthesized identity.

        Must be called after connect_domains(). Consumes the entity data
        and pattern graph to produce identity-aligned name candidates.

        Args:
            source: "taxonomy" (scientific names) or "general" (LLM freeform).

        Returns:
            Naming report dict with variants, semantics, identity_context.
        """
        state = self._state
        if not state or state.phase not in ("connection", "elaboration"):
            raise RuntimeError("Must connect_domains() before name().")

        entity_dicts = [b.to_dict() for b in state.beads]
        graph = state.metadata.get("pattern_graph", {})

        from .naming import research_name_from_identity
        report = research_name_from_identity(entity_dicts, graph, source=source)
        state.metadata["naming_report"] = report
        return report

    # ── Convenience: full pipeline ────────────────────────────────────

    def run_full(self, raw_input, lens="identity"):
        """Run the complete pipeline: declare → elaborate → connect → resolve."""
        self.declare_themes(raw_input)
        self.elaborate()
        self.connect_domains()
        return self.resolve(lens)

    def run_full_stream(self, raw_input, lens="identity"):
        """Run declare → elaborate → connect, then stream resolution."""
        self.declare_themes(raw_input)
        self.elaborate()
        self.connect_domains()
        yield from self.resolve_stream(lens)


# ── Helpers ───────────────────────────────────────────────────────────

def _infer_domains(entity):
    """Infer knowledge domains from entity type, source, and themes."""
    from .knowledge import domain_ids

    etype = entity.get("type", "concept")
    source = entity.get("source", "").lower()
    themes = [t.lower() for t in entity.get("themes", [])]

    domain_map = {
        "character": ["literature", "culture"],
        "person": ["culture"],
        "historical_figure": ["culture", "philosophy"],
        "work": ["literature", "visual_art", "culture"],
        "concept": ["philosophy", "psychology"],
        "archetype": ["philosophy", "spirituality"],
        "mythological": ["literature", "spirituality"],
        "place": ["nature", "culture"],
    }

    domains = list(domain_map.get(etype, ["culture"]))

    theme_domain_hints = {
        "music": ["music", "culture"], "math": ["mathematics"],
        "science": ["science"], "nature": ["nature"],
        "art": ["visual_art"], "sport": ["culture"],
        "game": ["culture"], "film": ["culture", "visual_art"],
        "book": ["literature"], "philosophy": ["philosophy"],
        "spirituality": ["spirituality"], "technology": ["technology"],
        "psychology": ["psychology"], "martial": ["martial_arts"],
    }

    for hint, hint_domains in theme_domain_hints.items():
        if any(hint in source for _ in [1]) or any(hint in t for t in themes):
            for d in hint_domains:
                if d not in domains:
                    domains.append(d)

    valid = set(domain_ids())
    return [d for d in domains if d in valid][:3]


def _check_isomorphism(bead_a, bead_b):
    """Check if two beads share structural similarity across different domains."""
    if not bead_a.domains or not bead_b.domains:
        return False
    shared = set(bead_a.domains) & set(bead_b.domains)
    if shared:
        return False
    shared_themes = set(bead_a.themes) & set(bead_b.themes)
    return len(shared_themes) >= 2
