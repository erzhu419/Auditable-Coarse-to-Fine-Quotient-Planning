import pytest

from acfqp import construction_k7_domain_registry_extension_v74 as domains


def test_v74_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V74) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V74) == 5
    assert all(value.endswith(":v74") for value in domains.K7_DOMAIN_TAG_EXTENSION_V74)
    tag = domains.CONSTRUCTION_K7_REUSABLE_AMORTIZATION_CAMPAIGN_V74_DOMAIN
    assert domains.extension_content_id_v74(tag, {"a": 1}) == domains.extension_content_id_v74(
        tag, {"a": 1}
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v74("acfqp:foreign:v74", {})
