import pytest

from acfqp import construction_k7_domain_registry_extension_v180r7r1 as predecessor
from acfqp import construction_k7_domain_registry_extension_v180r7r1p as domains


def test_v180r7r1p_protocol_domains_are_fresh_additive_and_exact() -> None:
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1P) == {
        "fallback_execution_authorization_evidence",
        "fallback_execution_protocol",
        "fallback_production_execution_slot",
    }
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1P) == 3
    assert all(
        value.endswith(":v180r7r1p")
        for value in domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1P
    )
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R7R1P.isdisjoint(
        predecessor.K7_DOMAIN_TAG_EXTENSION_V180R7R1
    )


def test_v180r7r1p_ids_reject_predecessor_domains() -> None:
    payload = {"production_outcome_accessed": False}
    assert len(
        domains.extension_content_id_v180r7r1p(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_PROTOCOL_V180R7R1P_DOMAIN,
            payload,
        )
    ) == 64
    assert len(
        domains.extension_content_id_v180r7r1p(
            domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1P[
                "fallback_execution_authorization_evidence"
            ],
            payload,
        )
    ) == 64
    with pytest.raises(ValueError, match="absent from V180r7r1p"):
        domains.extension_content_id_v180r7r1p(
            predecessor.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1[
                "fallback_execution_authorization"
            ],
            payload,
        )
