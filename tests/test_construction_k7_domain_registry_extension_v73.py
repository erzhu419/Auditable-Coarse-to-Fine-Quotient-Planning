import pytest

from acfqp import construction_k7_domain_registry_extension_v73 as domains


def test_v73_domain_registry_is_disjoint_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V73) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V73) == 5
    assert all(value.endswith(":v73") for value in domains.K7_DOMAIN_TAG_EXTENSION_V73)
    tag = domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_CAMPAIGN_V73_DOMAIN
    assert domains.extension_content_id_v73(tag, {"a": 1}) == domains.extension_content_id_v73(
        tag, {"a": 1}
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v73("acfqp:foreign:v73", {})
