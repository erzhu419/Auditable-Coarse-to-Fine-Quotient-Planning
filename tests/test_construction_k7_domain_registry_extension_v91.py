import pytest

from acfqp import construction_k7_domain_registry_extension_v91 as domains


def test_v91_domain_registry_is_additive_and_strict():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91) == 4
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V91) == 4
    assert all(row.endswith(":v91") for row in domains.K7_DOMAIN_TAG_EXTENSION_V91)
    with pytest.raises(ValueError):
        domains.extension_content_id_v91("acfqp:foreign", {})
