import pytest

from acfqp import construction_k7_domain_registry_extension_v185 as domains


def test_v185_domains_are_additive_and_content_addressed() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V185) == 11
    assert all(value.endswith(":v185") for value in domains.K7_DOMAIN_TAG_EXTENSION_V185)
    payload = {"schema": "acfqp.v185.test", "value": 1}
    value = domains.extension_content_id_v185(
        domains.CONSTRUCTION_K7_MACRO_LIBRARY_V185_DOMAIN,
        payload,
    )
    assert len(value) == 64
    assert value == domains.extension_content_id_v185(
        domains.CONSTRUCTION_K7_MACRO_LIBRARY_V185_DOMAIN,
        payload,
    )
    with pytest.raises(ValueError):
        domains.extension_content_id_v185("acfqp:unregistered:v185", payload)
