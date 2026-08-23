import pytest

from acfqp import construction_k7_domain_registry_extension_v177 as domains


def test_v177_domain_registry_is_complete_and_disjoint():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V177) == 9
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V177) == 9
    assert all(tag.endswith(":v177") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V177)


def test_v177_content_id_rejects_unregistered_domain():
    with pytest.raises(ValueError, match="absent"):
        domains.extension_content_id_v177("acfqp:not-registered:v177", {})
