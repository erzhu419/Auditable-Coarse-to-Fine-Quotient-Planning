from acfqp import construction_k7_domain_registry_extension_v182r2 as predecessor
from acfqp import construction_k7_domain_registry_extension_v183 as domains


def test_v183_domains_are_additive_and_exact() -> None:
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V183) == 10
    assert domains.K7_DOMAIN_TAG_EXTENSION_V183.isdisjoint(
        predecessor.K7_DOMAIN_TAG_EXTENSION_V182R2
    )
