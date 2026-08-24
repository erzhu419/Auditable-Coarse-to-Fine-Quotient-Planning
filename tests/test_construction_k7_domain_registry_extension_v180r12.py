import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12 as domains


def test_v180r12_domains_are_additive() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R12) == 5
    payload = {"schema": "acfqp.v180r12.test"}
    value = domains.extension_content_id_v180r12(
        domains.CONSTRUCTION_K7_AGGREGATION_PROTOCOL_V180R12_DOMAIN,
        payload,
    )
    assert len(value) == 64
    with pytest.raises(ValueError):
        domains.extension_content_id_v180r12("acfqp:unknown:v180r12", payload)
