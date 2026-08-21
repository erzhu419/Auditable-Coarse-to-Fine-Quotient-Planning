from acfqp import construction_k7_domain_registry_extension_v91r2 as v91r2
from acfqp import construction_k7_domain_registry_extension_v91r3 as v91r3


def test_v91r3_domains_are_fresh_unique_and_disjoint_from_v91r2():
    assert len(v91r3.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R3) == 3
    assert len(v91r3.K7_DOMAIN_TAG_EXTENSION_V91R3) == 3
    assert v91r3.K7_DOMAIN_TAG_EXTENSION_V91R3.isdisjoint(
        v91r2.K7_DOMAIN_TAG_EXTENSION_V91R2
    )
