import pytest

from acfqp import construction_k7_domain_registry_extension_v178r1 as domains


def test_v178r1_domain_registry_is_fresh_and_complete():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V178R1) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V178R1) == 5
    assert all(tag.endswith(":v178r1") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V178R1)


def test_v178r1_unregistered_domain_is_rejected():
    with pytest.raises(ValueError, match="absent"):
        domains.extension_content_id_v178r1("acfqp:not-registered:v178r1", {})
