"""Tests for elixis.thread — Thread class and RELATIONSHIPS constant."""


from elixis.thread import RELATIONSHIPS, Thread, is_cross_domain_thread_data, serialize_threads


# ---------------------------------------------------------------------------
# RELATIONSHIPS constant
# ---------------------------------------------------------------------------

class TestRelationshipsConstant:
    def test_is_tuple(self):
        assert isinstance(RELATIONSHIPS, tuple)

    def test_contains_expected_values(self):
        assert "admires" in RELATIONSHIPS
        assert "parallels" in RELATIONSHIPS
        assert "fears_becoming" in RELATIONSHIPS
        assert "contrasts_with" in RELATIONSHIPS

    def test_minimum_count(self):
        assert len(RELATIONSHIPS) >= 8


# ---------------------------------------------------------------------------
# Thread construction
# ---------------------------------------------------------------------------

class TestThreadConstruction:
    def test_default_construction(self):
        t = Thread()
        assert t.bead_a == ""
        assert t.bead_b == ""
        assert t.relationship == "parallels"
        assert t.strength == 0.5
        assert t.isomorphic is False
        assert t.domains_bridged == ("", "")
        assert t.evidence == []

    def test_full_construction(self):
        t = Thread(
            bead_a="Mozart",
            bead_b="Beethoven",
            relationship="rivals",
            strength=0.8,
            isomorphic=True,
            domains_bridged=("music", "music"),
            evidence=["both composed symphonies"],
        )
        assert t.bead_a == "Mozart"
        assert t.bead_b == "Beethoven"
        assert t.relationship == "rivals"
        assert t.strength == 0.8
        assert t.isomorphic is True
        assert t.domains_bridged == ("music", "music")
        assert t.evidence == ["both composed symphonies"]

    def test_domains_bridged_converted_to_tuple(self):
        t = Thread(domains_bridged=["music", "philosophy"])
        assert isinstance(t.domains_bridged, tuple)
        assert t.domains_bridged == ("music", "philosophy")

    def test_evidence_is_copied(self):
        ev = ["a"]
        t = Thread(evidence=ev)
        ev.append("b")
        assert t.evidence == ["a"]

    def test_evidence_none_becomes_empty_list(self):
        t = Thread(evidence=None)
        assert t.evidence == []


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------

class TestThreadValidate:
    def test_clamp_strength_high(self):
        t = Thread(strength=3.0)
        t.validate()
        assert t.strength == 1.0

    def test_clamp_strength_negative(self):
        t = Thread(strength=-0.5)
        t.validate()
        assert t.strength == 0.0

    def test_valid_strength_unchanged(self):
        t = Thread(strength=0.7)
        t.validate()
        assert t.strength == 0.7

    def test_boundary_values(self):
        t0 = Thread(strength=0.0)
        t0.validate()
        assert t0.strength == 0.0

        t1 = Thread(strength=1.0)
        t1.validate()
        assert t1.strength == 1.0

    def test_returns_self(self):
        t = Thread()
        result = t.validate()
        assert result is t


# ---------------------------------------------------------------------------
# cross-domain classification
# ---------------------------------------------------------------------------

class TestThreadCrossDomain:
    def test_isomorphic_thread_counts_as_cross_domain(self):
        t = Thread(isomorphic=True, domains_bridged=("philosophy", "literature"))

        assert t.is_cross_domain() is True

    def test_distinct_non_empty_domains_count_as_cross_domain(self):
        data = {"isomorphic": False, "domains_bridged": ["philosophy", "literature"]}

        assert is_cross_domain_thread_data(data) is True

    def test_empty_bridge_domains_do_not_count_as_cross_domain(self):
        t = Thread(relationship="bridges", domains_bridged=("", ""))

        assert t.is_cross_domain() is False

    def test_serialize_threads_ignores_non_public_placeholders(self):
        t = Thread(bead_a="A", bead_b="B", relationship="complements")

        assert serialize_threads([object(), t]) == [t.to_dict()]


# ---------------------------------------------------------------------------
# to_dict / from_dict
# ---------------------------------------------------------------------------

class TestThreadSerialization:
    def test_to_dict_keys(self):
        t = Thread()
        d = t.to_dict()
        expected_keys = {
            "bead_a", "bead_b", "relationship", "strength",
            "isomorphic", "domains_bridged", "evidence",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_converts_tuple_to_list(self):
        t = Thread(domains_bridged=("music", "philosophy"))
        d = t.to_dict()
        assert isinstance(d["domains_bridged"], list)
        assert d["domains_bridged"] == ["music", "philosophy"]

    def test_to_dict_converts_evidence_to_list(self):
        t = Thread(evidence=["x", "y"])
        d = t.to_dict()
        assert isinstance(d["evidence"], list)

    def test_roundtrip(self):
        original = Thread(
            bead_a="A",
            bead_b="B",
            relationship="admires",
            strength=0.9,
            isomorphic=True,
            domains_bridged=("music", "philosophy"),
            evidence=["they met"],
        )
        d = original.to_dict()
        restored = Thread.from_dict(d)
        assert restored.bead_a == original.bead_a
        assert restored.bead_b == original.bead_b
        assert restored.relationship == original.relationship
        assert restored.strength == original.strength
        assert restored.isomorphic == original.isomorphic
        assert restored.domains_bridged == original.domains_bridged
        assert restored.evidence == original.evidence

    def test_from_dict_missing_keys_uses_defaults(self):
        d = {}
        t = Thread.from_dict(d)
        assert t.bead_a == ""
        assert t.bead_b == ""
        assert t.relationship == "parallels"
        assert t.strength == 0.5
        assert t.isomorphic is False

    def test_from_dict_partial(self):
        d = {"bead_a": "X", "bead_b": "Y"}
        t = Thread.from_dict(d)
        assert t.bead_a == "X"
        assert t.bead_b == "Y"
        assert t.relationship == "parallels"  # default

    def test_from_dict_converts_domains_to_tuple(self):
        d = {"domains_bridged": ["music", "science"]}
        t = Thread.from_dict(d)
        assert isinstance(t.domains_bridged, tuple)
        assert t.domains_bridged == ("music", "science")

    def test_from_dict_evidence_none(self):
        d = {"evidence": None}
        t = Thread.from_dict(d)
        assert t.evidence == []


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestThreadRepr:
    def test_repr_format(self):
        t = Thread(bead_a="Mozart", bead_b="Beethoven", relationship="rivals")
        assert repr(t) == "Mozart --rivals--> Beethoven"

    def test_repr_empty(self):
        t = Thread()
        assert repr(t) == " --parallels--> "


# ---------------------------------------------------------------------------
# __eq__
# ---------------------------------------------------------------------------

class TestThreadEq:
    def test_equal_same_fields(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        b = Thread(bead_a="X", bead_b="Y", relationship="admires")
        assert a == b

    def test_not_equal_different_a(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        b = Thread(bead_a="Z", bead_b="Y", relationship="admires")
        assert a != b

    def test_not_equal_different_relationship(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        b = Thread(bead_a="X", bead_b="Y", relationship="rivals")
        assert a != b

    def test_strength_not_compared(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires", strength=0.1)
        b = Thread(bead_a="X", bead_b="Y", relationship="admires", strength=0.9)
        assert a == b

    def test_eq_with_non_thread_returns_not_implemented(self):
        t = Thread(bead_a="X", bead_b="Y", relationship="admires")
        result = t.__eq__("not a thread")
        assert result is NotImplemented

    def test_eq_with_none(self):
        t = Thread()
        assert t != None  # noqa: E711


# ---------------------------------------------------------------------------
# __hash__
# ---------------------------------------------------------------------------

class TestThreadHash:
    def test_equal_threads_same_hash(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        b = Thread(bead_a="X", bead_b="Y", relationship="admires")
        assert hash(a) == hash(b)

    def test_different_threads_different_hash(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        b = Thread(bead_a="Z", bead_b="Y", relationship="admires")
        assert hash(a) != hash(b)

    def test_usable_in_set(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        b = Thread(bead_a="X", bead_b="Y", relationship="admires")
        s = {a, b}
        assert len(s) == 1

    def test_usable_as_dict_key(self):
        a = Thread(bead_a="X", bead_b="Y", relationship="admires")
        d = {a: "value"}
        b = Thread(bead_a="X", bead_b="Y", relationship="admires")
        assert d[b] == "value"
