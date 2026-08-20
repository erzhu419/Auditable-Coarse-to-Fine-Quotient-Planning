import pytest

from acfqp import construction_k7_domain_registry_extension_v84 as domains


def test_v84_domains_are_additive_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V84) == 4
    assert all(value.endswith(":v84") for value in domains.K7_DOMAIN_TAG_EXTENSION_V84)
    domain = domains.CONSTRUCTION_K7_CONTEXTUAL_ORDINAL_CAMPAIGN_V84_DOMAIN
    assert domains.extension_content_id_v84(domain, {"x": 1}) == domains.extension_content_id_v84(domain, {"x": 1})
    with pytest.raises(ValueError):
        domains.extension_content_id_v84("acfqp:foreign", {})
