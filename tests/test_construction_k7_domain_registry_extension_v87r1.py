import pytest

from acfqp import construction_k7_domain_registry_extension_v87r1 as domains


def test_v87r1_domain_registry_is_additive_and_complete():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V87R1) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V87R1) == 5
    assert all(value.endswith(":v87r1") for value in domains.K7_DOMAIN_TAG_EXTENSION_V87R1)


def test_v87r1_content_ids_are_domain_separated():
    rows = [
        domains.extension_content_id_v87r1(domain, {"value": 1})
        for domain in domains.K7_DOMAIN_TAG_EXTENSION_V87R1
    ]
    assert len(set(rows)) == 5
    with pytest.raises(ValueError):
        domains.extension_content_id_v87r1("acfqp:foreign", {"value": 1})
