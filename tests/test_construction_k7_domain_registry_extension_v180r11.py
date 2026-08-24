from acfqp import construction_k7_domain_registry_extension_v180r10 as previous
from acfqp import construction_k7_domain_registry_extension_v180r11 as domains


def test_v180r11_domains_are_additive_and_disjoint() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R11) == 5
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V180R11) == 5
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R11.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V180R10
    )
    assert all(tag.endswith(":v180r11") for tag in domains.K7_DOMAIN_TAG_EXTENSION_V180R11)
