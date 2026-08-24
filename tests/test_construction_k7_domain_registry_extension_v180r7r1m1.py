import pytest

from acfqp import construction_k7_domain_registry_extension_v180r7r1 as predecessor
from acfqp import construction_k7_domain_registry_extension_v180r7r1m1 as domains


def test_v180r7r1m1_domains_are_fresh_additive_and_exact() -> None:
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1M1) == {
        "materialized_source_tree",
        "materialized_source_tree_manifest",
        "materialized_source_tree_failure",
    }
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1M1) == 3
    assert all(
        value.endswith(":v180r7r1m1")
        for value in domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1M1
    )
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1M1.isdisjoint(
        predecessor.K7_DOMAIN_TAG_EXTENSION_V180R7R1
    )


def test_v180r7r1m1_content_ids_reject_predecessor_domains() -> None:
    payload = {"scientific_occurrence_executed": False}
    value = domains.extension_content_id_v180r7r1m1(
        domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_V180R7R1M1_DOMAIN,
        payload,
    )
    assert len(value) == 64
    with pytest.raises(ValueError, match="absent from V180r7r1m1"):
        domains.extension_content_id_v180r7r1m1(
            predecessor.CONSTRUCTION_K7_FALLBACK_SOURCE_CLOSURE_REPAIR_V180R7R1_DOMAIN,
            payload,
        )
