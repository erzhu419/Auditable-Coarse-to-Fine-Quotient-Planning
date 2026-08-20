import pytest

from acfqp import construction_k7_domain_registry_extension_v83 as domains


def test_v83_domains_are_additive_and_closed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V83) == 4
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V83.values())) == 4
    for value in domains.K7_DOMAIN_TAG_EXTENSION_V83:
        assert domains.extension_content_id_v83(value, {"x": 1}) == (
            domains.extension_content_id_v83(value, {"x": 1})
        )
    with pytest.raises(ValueError):
        domains.extension_content_id_v83("acfqp:foreign", {})
