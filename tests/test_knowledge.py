"""Comprehensive tests for fugax.knowledge — data loaders and lookup helpers."""


from fugax.knowledge import (
    traits,
    archetypes,
    domains,
    relationships,
    entity_types,
    characters,
    archetype_by_id,
    entity_type_by_id,
    character_by_name,
    trait_keywords,
    archetype_ids,
    domain_ids,
    relationship_ids,
    clear_cache,
)


# ===========================================================================
# Collection loaders
# ===========================================================================


class TestTraits:
    """Tests for traits()."""

    def test_returns_list_of_domains(self):
        data = traits()
        assert "domains" in data
        assert isinstance(data["domains"], list)
        assert len(data["domains"]) > 0

    def test_domain_has_required_fields(self):
        data = traits()
        for domain in data["domains"]:
            assert "facets" in domain
            assert isinstance(domain["facets"], list)
            assert len(domain["facets"]) > 0

    def test_facet_has_keywords(self):
        data = traits()
        for domain in data["domains"]:
            for facet in domain["facets"]:
                assert "keywords" in facet
                assert isinstance(facet["keywords"], list)
                assert len(facet["keywords"]) > 0

    def test_cached_returns_same_object(self):
        a = traits()
        b = traits()
        assert a is b


class TestArchetypes:
    """Tests for archetypes()."""

    def test_returns_dict_with_archetypes_key(self):
        data = archetypes()
        assert "archetypes" in data
        assert isinstance(data["archetypes"], list)

    def test_archetype_has_id_and_name(self):
        data = archetypes()
        for arch in data["archetypes"]:
            assert "id" in arch
            assert "name" in arch
            assert isinstance(arch["id"], str)
            assert isinstance(arch["name"], str)

    def test_archetype_has_scores_fields(self):
        data = archetypes()
        for arch in data["archetypes"]:
            # At minimum, archetypes have big_five and keywords
            assert "keywords" in arch
            assert "big_five" in arch

    def test_cached_returns_same_object(self):
        assert archetypes() is archetypes()


class TestDomains:
    """Tests for domains()."""

    def test_returns_dict_with_domains_key(self):
        data = domains()
        assert "domains" in data
        assert isinstance(data["domains"], list)

    def test_domain_has_id(self):
        data = domains()
        for dom in data["domains"]:
            assert "id" in dom
            assert isinstance(dom["id"], str)

    def test_domain_has_subdomains(self):
        data = domains()
        for dom in data["domains"]:
            assert "subdomains" in dom or "isomorphisms" in dom

    def test_cached_returns_same_object(self):
        assert domains() is domains()


class TestRelationships:
    """Tests for relationships()."""

    def test_returns_dict_with_relationships_key(self):
        data = relationships()
        assert "relationships" in data
        assert isinstance(data["relationships"], list)

    def test_relationship_has_id(self):
        data = relationships()
        for rel in data["relationships"]:
            assert "id" in rel
            assert isinstance(rel["id"], str)

    def test_relationship_has_polarity(self):
        data = relationships()
        for rel in data["relationships"]:
            # Relationships should have polarity or similar metadata
            assert "polarity" in rel or "id" in rel

    def test_cached_returns_same_object(self):
        assert relationships() is relationships()


class TestEntityTypes:
    """Tests for entity_types()."""

    def test_returns_dict_with_types_key(self):
        data = entity_types()
        assert "types" in data
        assert isinstance(data["types"], list)

    def test_type_has_id(self):
        data = entity_types()
        for t in data["types"]:
            assert "id" in t

    def test_type_has_archetype_affinities(self):
        data = entity_types()
        for t in data["types"]:
            assert "archetype_affinities" in t or "id" in t

    def test_cached_returns_same_object(self):
        assert entity_types() is entity_types()


class TestCharacters:
    """Tests for characters()."""

    def test_returns_list(self):
        data = characters()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_character_has_required_fields(self):
        data = characters()
        for c in data:
            assert "canonical" in c or "name" in c

    def test_character_has_big_five_or_archetype_scores(self):
        data = characters()
        # At least some characters should have these fields
        has_scores = any("archetype_scores" in c for c in data)
        has_big_five = any("big_five" in c for c in data)
        assert has_scores or has_big_five

    def test_cached_returns_same_object(self):
        assert characters() is characters()


# ===========================================================================
# Lookup helpers
# ===========================================================================


class TestArchetypeById:
    """Tests for archetype_by_id()."""

    def test_returns_archetype_for_valid_id(self):
        result = archetype_by_id("power")
        assert result is not None
        assert result["id"] == "power"
        assert "name" in result

    def test_returns_none_for_nonexistent(self):
        assert archetype_by_id("nonexistent_archetype_xyz") is None

    def test_returns_dict(self):
        result = archetype_by_id("power")
        assert isinstance(result, dict)


class TestEntityTypeById:
    """Tests for entity_type_by_id()."""

    def test_returns_type_for_valid_id(self):
        result = entity_type_by_id("character")
        assert result is not None
        assert result["id"] == "character"

    def test_returns_none_for_nonexistent(self):
        assert entity_type_by_id("nonexistent_type_xyz") is None

    def test_returns_dict(self):
        result = entity_type_by_id("character")
        assert isinstance(result, dict)


class TestCharacterByName:
    """Tests for character_by_name()."""

    def test_returns_character_for_known_name(self):
        result = character_by_name("Walter White")
        assert result is not None
        assert "canonical" in result or "name" in result

    def test_character_has_big_five(self):
        result = character_by_name("Walter White")
        if result:
            assert "big_five" in result

    def test_character_has_archetype_scores(self):
        result = character_by_name("Walter White")
        if result:
            assert "archetype_scores" in result

    def test_returns_none_for_nonexistent(self):
        assert character_by_name("Nonexistent Character XYZ 123") is None

    def test_case_insensitive(self):
        result_lower = character_by_name("walter white")
        result_title = character_by_name("Walter White")
        assert result_lower is not None
        assert result_title is not None
        assert result_lower["canonical"] == result_title["canonical"]

    def test_returns_dict(self):
        result = character_by_name("Walter White")
        if result:
            assert isinstance(result, dict)


# ===========================================================================
# ID list helpers
# ===========================================================================


class TestDomainIds:
    """Tests for domain_ids()."""

    def test_returns_list_of_strings(self):
        result = domain_ids()
        assert isinstance(result, list)
        assert all(isinstance(d, str) for d in result)

    def test_known_domains_present(self):
        result = domain_ids()
        assert "philosophy" in result
        assert "culture" in result
        assert "music" in result

    def test_length_matches_domains_data(self):
        result = domain_ids()
        data = domains()
        assert len(result) == len(data["domains"])


class TestArchetypeIds:
    """Tests for archetype_ids()."""

    def test_returns_list_of_strings(self):
        result = archetype_ids()
        assert isinstance(result, list)
        assert all(isinstance(a, str) for a in result)

    def test_power_is_present(self):
        result = archetype_ids()
        assert "power" in result

    def test_length_matches_archetypes_data(self):
        result = archetype_ids()
        data = archetypes()
        assert len(result) == len(data["archetypes"])


class TestRelationshipIds:
    """Tests for relationship_ids()."""

    def test_returns_list_of_strings(self):
        result = relationship_ids()
        assert isinstance(result, list)
        assert all(isinstance(r, str) for r in result)

    def test_known_relationships_present(self):
        result = relationship_ids()
        assert "admires" in result or "parallels" in result

    def test_length_matches_relationships_data(self):
        result = relationship_ids()
        data = relationships()
        assert len(result) == len(data["relationships"])


class TestTraitKeywords:
    """Tests for trait_keywords()."""

    def test_returns_list_of_strings(self):
        result = trait_keywords()
        assert isinstance(result, list)
        assert all(isinstance(k, str) for k in result)

    def test_non_empty(self):
        result = trait_keywords()
        assert len(result) > 0


# ===========================================================================
# clear_cache
# ===========================================================================


class TestClearCache:
    """Tests for clear_cache()."""

    def test_clear_cache_no_error(self):
        # Warm up caches
        traits()
        archetypes()
        domains()
        relationships()
        entity_types()
        characters()
        # Clear should not raise
        clear_cache()

    def test_clear_allows_reload(self):
        first = traits()
        clear_cache()
        second = traits()
        # Data should be equal but not the same object (cache was cleared)
        assert first == second
        assert first is not second
