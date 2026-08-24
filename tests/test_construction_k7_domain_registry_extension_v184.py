from acfqp import construction_k7_domain_registry_extension_v183 as previous
from acfqp import construction_k7_domain_registry_extension_v184 as domains


def test_v184_domains_are_additive_and_disjoint() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V184) == 10
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V184) == 10
    assert domains.K7_DOMAIN_TAG_EXTENSION_V184.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V183
    )
    for key, value in domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V184.items():
        assert key
        assert value.startswith("acfqp:")
        assert value.endswith(":v184")
