from acfqp import construction_k7_domain_registry_extension_v91r1 as v91r1
from acfqp import construction_k7_domain_registry_extension_v91r2 as v91r2


def test_v91r2_domains_are_fresh_unique_and_disjoint_from_v91r1():
    assert len(v91r2.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R2) == 5
    assert len(v91r2.K7_DOMAIN_TAG_EXTENSION_V91R2) == 5
    assert v91r2.K7_DOMAIN_TAG_EXTENSION_V91R2.isdisjoint(
        v91r1.K7_DOMAIN_TAG_EXTENSION_V91R1
    )
