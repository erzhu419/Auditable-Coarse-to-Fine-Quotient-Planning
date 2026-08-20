import pytest

from acfqp import construction_k7_domain_registry_extension_v75r2 as domains


def test_v75r2_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R2) == 6
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V75R2) == 6
    assert all(value.endswith(":v75r2") for value in domains.K7_DOMAIN_TAG_EXTENSION_V75R2)
    tag = domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_CAMPAIGN_V75R2_DOMAIN
    assert domains.extension_content_id_v75r2(tag, {"a": 1}) == domains.extension_content_id_v75r2(
        tag, {"a": 1}
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v75r2("acfqp:foreign:v75r2", {})
