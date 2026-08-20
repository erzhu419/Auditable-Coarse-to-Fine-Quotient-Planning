import pytest

from acfqp import construction_k7_domain_registry_extension_v75 as domains


def test_v75_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75) == 6
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V75) == 6
    assert all(value.endswith(":v75") for value in domains.K7_DOMAIN_TAG_EXTENSION_V75)
    tag = domains.CONSTRUCTION_K7_CROSS_OCCURRENCE_REUSE_CAMPAIGN_V75_DOMAIN
    assert domains.extension_content_id_v75(tag, {"a": 1}) == domains.extension_content_id_v75(
        tag, {"a": 1}
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v75("acfqp:foreign:v75", {})
