import pytest

from acfqp import construction_k7_domain_registry_extension_v81 as domains


def test_v81_domains_are_additive_and_closed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V81) == 4
    assert len(set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V81.values())) == 4
    for value in domains.K7_DOMAIN_TAG_EXTENSION_V81:
        assert domains.extension_content_id_v81(value, {"x": 1}) == (
            domains.extension_content_id_v81(value, {"x": 1})
        )
    with pytest.raises(ValueError):
        domains.extension_content_id_v81("acfqp:foreign", {})
