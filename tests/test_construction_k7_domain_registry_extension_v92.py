from acfqp import construction_k7_domain_registry_extension_v91r3 as v91r3
from acfqp import construction_k7_domain_registry_extension_v92 as v92


def test_v92_domains_are_fresh_unique_and_disjoint_from_v91r3():
    assert len(v92.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V92) == 6
    assert len(v92.K7_DOMAIN_TAG_EXTENSION_V92) == 6
    assert v92.K7_DOMAIN_TAG_EXTENSION_V92.isdisjoint(
        v91r3.K7_DOMAIN_TAG_EXTENSION_V91R3
    )
