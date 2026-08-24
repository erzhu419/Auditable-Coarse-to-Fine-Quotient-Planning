import pytest

from acfqp import construction_k7_domain_registry_extension_v180r7 as predecessor
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains


def test_v180r7r1_domain_registry_is_fresh_additive_and_exact() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1) == 9
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1) == 9
    assert all(
        tag.endswith(":v180r7r1")
        for tag in domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1
    )
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1.isdisjoint(
        predecessor.K7_DOMAIN_TAG_EXTENSION_V180R7
    )
    assert {
        "fallback_source_inventory_preregistration",
        "fallback_source_closure_repair",
        "fallback_execution_authorization",
        "fallback_execution_failure",
        "fallback_occurrence_receipt",
        "fallback_v9_lift_lineage",
        "fallback_execution_terminal",
        "fallback_execution_verification",
        "fallback_verification_failure",
    } == set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1)


def test_v180r7r1_content_ids_reject_predecessor_domains() -> None:
    payload = {"outcome_accessed": False}
    value = domains.extension_content_id_v180r7r1(
        domains.CONSTRUCTION_K7_FALLBACK_SOURCE_INVENTORY_PREREGISTRATION_V180R7R1_DOMAIN,
        payload,
    )
    assert len(value) == 64
    with pytest.raises(ValueError, match="absent from V180r7r1"):
        domains.extension_content_id_v180r7r1(
            predecessor.CONSTRUCTION_K7_FALLBACK_EXECUTION_AUTHORIZATION_V180R7_DOMAIN,
            payload,
        )
