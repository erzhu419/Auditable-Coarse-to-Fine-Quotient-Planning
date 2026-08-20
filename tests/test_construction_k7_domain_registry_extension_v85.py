import pytest

from acfqp import construction_k7_domain_registry_extension_v85 as domains


def test_v85_domains_are_additive_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V85) == 4
    assert all(value.endswith(":v85") for value in domains.K7_DOMAIN_TAG_EXTENSION_V85)
    domain = domains.CONSTRUCTION_K7_PROJECTED_DISAGREEMENT_CAMPAIGN_V85_DOMAIN
    assert domains.extension_content_id_v85(domain, {"x": 1}) == domains.extension_content_id_v85(domain, {"x": 1})
    with pytest.raises(ValueError):
        domains.extension_content_id_v85("acfqp:foreign", {})
