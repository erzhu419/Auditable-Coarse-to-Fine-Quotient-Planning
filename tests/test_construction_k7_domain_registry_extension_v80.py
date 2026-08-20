import pytest

from acfqp import construction_k7_domain_registry_extension_v80 as domains


def test_v80_domains_are_additive_and_closed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V80) == 4
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V80.values())) == 4
    for value in domains.K7_DOMAIN_TAG_EXTENSION_V80:
        assert domains.extension_content_id_v80(value, {"x": 1}) == (
            domains.extension_content_id_v80(value, {"x": 1})
        )
    with pytest.raises(ValueError):
        domains.extension_content_id_v80("acfqp:foreign", {})
