import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r1 as predecessor
from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains


def test_v180r12r2_parent_domains_are_fresh_additive_and_exact() -> None:
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R2
    assert set(registry) == {
        "aggregation_protocol",
        "execution_authorization",
        "aggregation_execution_slot",
        "authorization_evidence",
        "stale_predecessor",
        "terminal_bundle",
        "verification",
        "failure",
    }
    assert len(registry) == len(set(registry.values())) == 8
    assert all(tag.endswith(":v180r12r2") for tag in registry.values())
    assert set(registry.values()).isdisjoint(
        predecessor.K7_DOMAIN_TAG_EXTENSION_V180R12R1
    )


def test_v180r12r2_parent_content_ids_reject_predecessor_domains() -> None:
    payload = {"outcome_accessed": False}
    content_id = domains.extension_content_id_v180r12r2(
        domains.CONSTRUCTION_K7_AGGREGATION_EXECUTION_SLOT_V180R12R2_DOMAIN,
        payload,
    )
    assert len(content_id) == 64
    stale_id = domains.extension_content_id_v180r12r2(
        domains.CONSTRUCTION_K7_STALE_PREDECESSOR_V180R12R2_DOMAIN,
        payload,
    )
    assert len(stale_id) == 64
    assert stale_id != content_id
    with pytest.raises(ValueError, match="absent from V180r12r2"):
        domains.extension_content_id_v180r12r2(
            predecessor.CONSTRUCTION_K7_EXECUTION_AUTHORIZATION_V180R12R1_DOMAIN,
            payload,
        )
