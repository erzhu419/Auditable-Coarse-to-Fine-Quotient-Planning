import pytest

from acfqp import construction_k7_domain_registry_extension_v75r1 as domains


def test_v75r1_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R1) == 6
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V75R1) == 6
    assert all(value.endswith(":v75r1") for value in domains.K7_DOMAIN_TAG_EXTENSION_V75R1)
    tag = domains.CONSTRUCTION_K7_PORTABLE_PRIORITY_CAMPAIGN_V75R1_DOMAIN
    assert domains.extension_content_id_v75r1(tag, {"a": 1}) == domains.extension_content_id_v75r1(
        tag, {"a": 1}
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v75r1("acfqp:foreign:v75r1", {})
