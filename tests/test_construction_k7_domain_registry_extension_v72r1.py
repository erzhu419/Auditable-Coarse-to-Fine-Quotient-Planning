import pytest

from acfqp import construction_k7_domain_registry_extension_v72r1 as domains


def test_v72r1_domains_are_five_unique_tags():
    tags = tuple(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V72R1.values())
    assert len(tags) == len(set(tags)) == 5
    assert len({domains.extension_content_id_v72r1(tag, {}) for tag in tags}) == 5


def test_v72r1_rejects_foreign_domain():
    with pytest.raises(ValueError, match="absent from V72r1"):
        domains.extension_content_id_v72r1("acfqp:foreign", {})
