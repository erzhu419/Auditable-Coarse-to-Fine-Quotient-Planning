from acfqp import construction_k7_domain_registry_extension_v91 as v91
from acfqp import construction_k7_domain_registry_extension_v91r1 as v91r1


def test_v91r1_domains_are_fresh_unique_and_disjoint_from_v91():
    assert len(v91r1.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R1) == 4
    assert len(v91r1.K7_DOMAIN_TAG_EXTENSION_V91R1) == 4
    assert v91r1.K7_DOMAIN_TAG_EXTENSION_V91R1.isdisjoint(
        v91.K7_DOMAIN_TAG_EXTENSION_V91
    )
