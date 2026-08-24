from acfqp import construction_k7_domain_registry_extension_v179 as v179
from acfqp import construction_k7_domain_registry_extension_v180 as v180


def test_v180_domains_are_additive_and_disjoint() -> None:
    assert len(v180.K7_DOMAIN_TAG_EXTENSION_V180) == 3
    assert v180.K7_DOMAIN_TAG_EXTENSION_V180.isdisjoint(
        v179.K7_DOMAIN_TAG_EXTENSION_V179
    )
    assert len(set(v180.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180.values())) == 3


def test_v180_rejects_unregistered_domain() -> None:
    try:
        v180.extension_content_id_v180("acfqp:not-registered:v180", {})
    except ValueError as error:
        assert "absent from V180" in str(error)
    else:  # pragma: no cover
        raise AssertionError("unregistered V180 domain was accepted")
