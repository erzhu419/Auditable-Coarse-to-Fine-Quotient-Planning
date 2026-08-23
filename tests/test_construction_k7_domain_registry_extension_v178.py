import pytest

from acfqp import construction_k7_domain_registry_extension_v178 as domains


def test_v178_domain_registry_is_complete_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V178) == 12
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V178) == 12
    assert all(tag.endswith(":v178") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V178)


def test_v178_content_id_rejects_unregistered_domain():
    with pytest.raises(ValueError, match="absent"):
        domains.extension_content_id_v178("acfqp:not-registered:v178", {})
