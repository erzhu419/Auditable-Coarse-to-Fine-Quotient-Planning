import pytest

from acfqp import construction_k7_domain_registry_extension_v175r1 as domains


def test_v175r1_domains_are_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V175R1) == 5
    assert all(tag.endswith(":v175r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V175R1)
    first = domains.extension_content_id_v175r1(
        domains.CONSTRUCTION_K7_CAMPAIGN_V175R1_DOMAIN, {"value": 1}
    )
    second = domains.extension_content_id_v175r1(
        domains.CONSTRUCTION_K7_CAMPAIGN_V175R1_DOMAIN, {"value": 2}
    )
    assert first != second
    with pytest.raises(ValueError, match="absent"):
        domains.extension_content_id_v175r1("acfqp:unknown:v175r1", {})
