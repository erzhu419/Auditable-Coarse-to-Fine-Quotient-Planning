import pytest

from acfqp import construction_k7_domain_registry_extension_v72 as domains


def test_v72_domains_are_unique_and_content_ids_are_domain_separated():
    tags = tuple(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V72.values())
    assert len(tags) == len(set(tags)) == 4
    ids = {domains.extension_content_id_v72(tag, {"value": 1}) for tag in tags}
    assert len(ids) == len(tags)
    assert all(len(value) == 64 for value in ids)


def test_v72_rejects_unregistered_domain():
    with pytest.raises(ValueError, match="absent from V72"):
        domains.extension_content_id_v72("acfqp:foreign", {})
