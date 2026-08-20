import pytest

from acfqp import construction_k7_domain_registry_extension_v79 as domains


def test_v79_domains_are_additive_and_closed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V79) == 4
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V79.values())) == 4
    for value in domains.K7_DOMAIN_TAG_EXTENSION_V79:
        assert domains.extension_content_id_v79(value, {"x": 1}) == (
            domains.extension_content_id_v79(value, {"x": 1})
        )
    with pytest.raises(ValueError):
        domains.extension_content_id_v79("acfqp:foreign", {})
