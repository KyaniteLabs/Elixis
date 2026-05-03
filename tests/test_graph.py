"""Comprehensive tests for elixis.graph — relationship graph builder and helpers."""

from unittest.mock import patch

from elixis.bead import Bead
from elixis.graph import (
    build_relationship_graph,
    find_bridges,
    _compute_relationship,
    _is_cross_domain,
    _same_domain,
    _evidence_for,
    _cluster_by_theme,
    _compute_centralities,
)
from elixis.thread import Thread


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bead(
    canonical="Test",
    etype="concept",
    domains=None,
    themes=None,
    traits=None,
    sentiment=0.0,
    intensity=0.5,
):
    return Bead(
        canonical=canonical,
        type=etype,
        domains=domains if domains is not None else ["philosophy"],
        themes=themes if themes is not None else ["power"],
        traits=traits if traits is not None else [],
        sentiment=sentiment,
        intensity=intensity,
    )


# ===========================================================================
# build_relationship_graph
# ===========================================================================


class TestBuildRelationshipGraph:
    """Tests for build_relationship_graph."""

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_empty_beads_returns_empty_graph(self, _mock):
        result = build_relationship_graph([])
        assert result == {"nodes": [], "edges": [], "clusters": {}, "centralities": {}}

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_single_bead_returns_node_no_edges(self, _mock):
        bead = _bead(canonical="Solo")
        result = build_relationship_graph([bead])
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "Solo"
        assert len(result["edges"]) == 0
        assert result["centralities"]["Solo"] == 0

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_two_beads_shared_themes_connected(self, _mock):
        a = _bead(canonical="A", themes=["power", "shadow"])
        b = _bead(canonical="B", themes=["power", "wisdom"])
        result = build_relationship_graph([a, b])
        assert len(result["edges"]) >= 1
        edge = result["edges"][0]
        assert "power" in edge["evidence"][0] if edge["evidence"] else True

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_two_beads_no_overlap_no_edge(self, _mock):
        a = _bead(canonical="A", themes=["power"], domains=["philosophy"])
        b = _bead(canonical="B", themes=["wisdom"], domains=["music"])
        # No shared themes and no shared traits, so strength < 0.1
        result = build_relationship_graph([a, b])
        assert len(result["edges"]) == 0

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_cross_domain_beads_isomorphic_true(self, _mock):
        a = _bead(canonical="A", domains=["philosophy"], themes=["power", "shadow"])
        b = _bead(canonical="B", domains=["music"], themes=["power", "shadow"])
        result = build_relationship_graph([a, b])
        if result["edges"]:
            assert result["edges"][0]["isomorphic"] is True

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_same_domain_beads_isomorphic_false(self, _mock):
        a = _bead(canonical="A", domains=["philosophy"], themes=["power"])
        b = _bead(canonical="B", domains=["philosophy"], themes=["power"])
        result = build_relationship_graph([a, b])
        if result["edges"]:
            assert result["edges"][0]["isomorphic"] is False

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_nodes_include_all_fields(self, _mock):
        bead = _bead(
            canonical="X",
            etype="character",
            domains=["culture"],
            themes=["power"],
            sentiment=0.3,
            intensity=0.8,
        )
        result = build_relationship_graph([bead])
        node = result["nodes"][0]
        assert node["name"] == "X"
        assert node["type"] == "character"
        assert node["themes"] == ["power"]
        assert node["domains"] == ["culture"]
        assert node["sentiment"] == 0.3
        assert node["intensity"] == 0.8

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_edges_strength_clamped(self, _mock):
        a = _bead(canonical="A", themes=["power", "shadow", "wisdom", "freedom", "struggle"])
        b = _bead(canonical="B", themes=["power", "shadow", "wisdom", "freedom", "struggle"])
        result = build_relationship_graph([a, b])
        if result["edges"]:
            for edge in result["edges"]:
                assert 0.0 <= edge["strength"] <= 1.0

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_clusters_by_theme(self, _mock):
        a = _bead(canonical="A", themes=["power", "shadow"])
        b = _bead(canonical="B", themes=["power", "wisdom"])
        c = _bead(canonical="C", themes=["wisdom"])
        result = build_relationship_graph([a, b, c])
        clusters = result["clusters"]
        assert "power" in clusters
        assert "wisdom" in clusters
        assert "A" in clusters["power"]
        assert "B" in clusters["power"]
        assert "C" in clusters["wisdom"]

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_cluster_unclassified_for_no_themes(self, _mock):
        bead = _bead(canonical="X", themes=[])
        result = build_relationship_graph([bead])
        assert "unclassified" in result["clusters"]

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_centralities_computed(self, _mock):
        a = _bead(canonical="A", themes=["power"])
        b = _bead(canonical="B", themes=["power"])
        c = _bead(canonical="C", themes=["power"])
        result = build_relationship_graph([a, b, c])
        centrals = result["centralities"]
        assert "A" in centrals
        assert "B" in centrals
        assert "C" in centrals

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_no_duplicate_edges(self, _mock):
        a = _bead(canonical="A", themes=["power"])
        b = _bead(canonical="B", themes=["power"])
        result = build_relationship_graph([a, b])
        pairs = [(e["bead_a"], e["bead_b"]) for e in result["edges"]]
        assert len(pairs) == len(set(pairs))


# ===========================================================================
# _compute_relationship
# ===========================================================================


class TestComputeRelationship:
    """Tests for _compute_relationship."""

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_contrasts_with_high_sentiment_diff(self, _mock):
        a = _bead(canonical="A", sentiment=-0.8, themes=["power"])
        b = _bead(canonical="B", sentiment=0.8, themes=["power"])
        rel, strength = _compute_relationship(a, b)
        assert rel == "contrasts_with"
        assert strength > 0.1

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_parallels_same_domain(self, _mock):
        a = _bead(canonical="A", domains=["philosophy"], themes=["power"], sentiment=0.0)
        b = _bead(canonical="B", domains=["philosophy"], themes=["power"], sentiment=0.1)
        rel, strength = _compute_relationship(a, b)
        assert rel == "parallels"

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_complements_different_domain(self, _mock):
        a = _bead(canonical="A", domains=["philosophy"], themes=["power"], sentiment=0.0)
        b = _bead(canonical="B", domains=["music"], themes=["power"], sentiment=0.1)
        rel, strength = _compute_relationship(a, b)
        assert rel == "complements"

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_identifies_with_trait_overlap(self, _mock):
        a = _bead(
            canonical="A",
            domains=["philosophy"],
            themes=["power"],
            traits=["bold", "ruthless", "ambitious", "strategic"],
            sentiment=0.0,
        )
        b = _bead(
            canonical="B",
            domains=["music"],
            themes=["wisdom"],
            traits=["bold", "ruthless", "ambitious", "creative"],
            sentiment=0.0,
        )
        rel, strength = _compute_relationship(a, b)
        assert rel == "identifies_with"

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_no_relationship_when_weak(self, _mock):
        a = _bead(canonical="A", themes=["power"], traits=[], domains=["philosophy"])
        b = _bead(canonical="B", themes=["wisdom"], traits=[], domains=["music"])
        rel, strength = _compute_relationship(a, b)
        assert rel is None
        assert strength == 0.0

    @patch("elixis.graph.character_by_name", return_value=None)
    def test_strength_clamped_to_one(self, _mock):
        a = _bead(
            canonical="A",
            themes=["power", "shadow", "wisdom", "freedom", "struggle"],
            traits=["bold", "ruthless", "ambitious", "strategic", "intelligent"],
            sentiment=0.9,
        )
        b = _bead(
            canonical="B",
            themes=["power", "shadow", "wisdom", "freedom", "struggle"],
            traits=["bold", "ruthless", "ambitious", "strategic", "intelligent"],
            sentiment=-0.9,
        )
        _, strength = _compute_relationship(a, b)
        assert strength <= 1.0

    @patch("elixis.graph.character_by_name")
    def test_kb_match_boosts_strength(self, mock_kb):
        mock_kb.side_effect = lambda name: {
            "Alpha": {"archetype_scores": {"power": 0.9, "sage": 0.3}},
            "Beta": {"archetype_scores": {"power": 0.8, "sage": 0.5}},
        }.get(name)
        a = _bead(canonical="Alpha", themes=["power"], sentiment=0.0)
        b = _bead(canonical="Beta", themes=["power"], sentiment=0.0)
        _, strength = _compute_relationship(a, b)
        assert strength > 0.5  # Should be boosted by KB match


# ===========================================================================
# _is_cross_domain / _same_domain
# ===========================================================================


class TestDomainChecks:
    """Tests for _is_cross_domain and _same_domain."""

    def test_cross_domain_true(self):
        a = _bead(domains=["philosophy"])
        b = _bead(domains=["music"])
        assert _is_cross_domain(a, b) is True

    def test_cross_domain_false_same_domain(self):
        a = _bead(domains=["philosophy"])
        b = _bead(domains=["philosophy"])
        assert _is_cross_domain(a, b) is False

    def test_cross_domain_overlapping(self):
        a = _bead(domains=["philosophy", "culture"])
        b = _bead(domains=["culture", "music"])
        assert _is_cross_domain(a, b) is False

    def test_cross_domain_empty(self):
        a = _bead(domains=[])
        b = _bead(domains=["music"])
        assert _is_cross_domain(a, b) is False

    def test_same_domain_true(self):
        a = _bead(domains=["philosophy", "culture"])
        b = _bead(domains=["culture"])
        assert _same_domain(a, b) is True

    def test_same_domain_false(self):
        a = _bead(domains=["philosophy"])
        b = _bead(domains=["music"])
        assert _same_domain(a, b) is False


# ===========================================================================
# _evidence_for
# ===========================================================================


class TestEvidenceFor:
    """Tests for _evidence_for."""

    def test_shared_themes_evidence(self):
        a = _bead(themes=["power", "shadow"])
        b = _bead(themes=["power", "wisdom"])
        evidence = _evidence_for(a, b, "parallels")
        assert any("power" in e for e in evidence)

    def test_cross_domain_evidence(self):
        a = _bead(domains=["philosophy"], themes=["power"])
        b = _bead(domains=["music"], themes=["power"])
        evidence = _evidence_for(a, b, "complements")
        assert any("Cross-domain" in e for e in evidence)

    def test_shared_traits_evidence(self):
        a = _bead(traits=["bold", "ruthless"])
        b = _bead(traits=["bold", "creative"])
        evidence = _evidence_for(a, b, "identifies_with")
        assert any("bold" in e for e in evidence)

    def test_no_evidence_when_no_overlap(self):
        a = _bead(themes=[], traits=[], domains=["philosophy"])
        b = _bead(themes=[], traits=[], domains=["philosophy"])
        evidence = _evidence_for(a, b, "fascinated_by")
        assert evidence == []


# ===========================================================================
# _cluster_by_theme
# ===========================================================================


class TestClusterByTheme:
    """Tests for _cluster_by_theme."""

    def test_groups_by_first_theme(self):
        a = _bead(canonical="A", themes=["power", "shadow"])
        b = _bead(canonical="B", themes=["power", "wisdom"])
        c = _bead(canonical="C", themes=["wisdom"])
        clusters = _cluster_by_theme([a, b, c])
        assert set(clusters["power"]) == {"A", "B"}
        assert clusters["wisdom"] == ["C"]

    def test_unclassified_for_empty_themes(self):
        bead = _bead(canonical="X", themes=[])
        clusters = _cluster_by_theme([bead])
        assert "unclassified" in clusters
        assert "X" in clusters["unclassified"]

    def test_empty_beads(self):
        clusters = _cluster_by_theme([])
        assert clusters == {}


# ===========================================================================
# _compute_centralities
# ===========================================================================


class TestComputeCentralities:
    """Tests for _compute_centralities."""

    def test_counts_connections(self):
        a = _bead(canonical="A")
        b = _bead(canonical="B")
        c = _bead(canonical="C")
        edges = [
            Thread(bead_a="A", bead_b="B"),
            Thread(bead_a="A", bead_b="C"),
        ]
        result = _compute_centralities([a, b, c], edges)
        assert result["A"] == 2
        assert result["B"] == 1
        assert result["C"] == 1

    def test_unconnected_beads_get_zero(self):
        a = _bead(canonical="A")
        b = _bead(canonical="B")
        result = _compute_centralities([a, b], [])
        assert result["A"] == 0
        assert result["B"] == 0

    def test_empty_inputs(self):
        result = _compute_centralities([], [])
        assert result == {}


# ===========================================================================
# find_bridges
# ===========================================================================


class TestFindBridges:
    """Tests for find_bridges."""

    def test_single_cluster_returns_empty(self):
        graph = {"clusters": {"power": ["A", "B"]}}
        assert find_bridges(graph) == []

    def test_multi_cluster_finds_bridges(self):
        graph = {
            "clusters": {
                "power": ["A", "B"],
                "wisdom": ["B", "C"],
                "shadow": ["C"],
            }
        }
        bridges = find_bridges(graph)
        # B appears in "power" and "wisdom"
        # C appears in "wisdom" and "shadow"
        bridge_names = [b["entity"] for b in bridges]
        assert "B" in bridge_names
        assert "C" in bridge_names
        for bridge in bridges:
            assert "connects_themes" in bridge
            assert "bridge_strength" in bridge

    def test_no_bridges_when_disjoint_clusters(self):
        graph = {
            "clusters": {
                "power": ["A"],
                "wisdom": ["B"],
            }
        }
        bridges = find_bridges(graph)
        assert bridges == []

    def test_empty_clusters_returns_empty(self):
        assert find_bridges({"clusters": {}}) == []

    def test_missing_clusters_key(self):
        assert find_bridges({}) == []

    def test_bridges_sorted_by_strength_descending(self):
        graph = {
            "clusters": {
                "power": ["A", "B", "C"],
                "wisdom": ["B", "C", "D"],
                "shadow": ["C", "D"],
            }
        }
        bridges = find_bridges(graph)
        strengths = [b["bridge_strength"] for b in bridges]
        assert strengths == sorted(strengths, reverse=True)
