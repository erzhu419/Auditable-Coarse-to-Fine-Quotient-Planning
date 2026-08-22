from acfqp import construction_k7_domain_registry_extension_v161 as v161
from acfqp import construction_k7_domain_registry_extension_v162 as v162


def test_v162_domains_are_additive_and_disjoint():
    assert len(v162.K7_DOMAIN_TAG_EXTENSION_V162) == 5
    assert v162.K7_DOMAIN_TAG_EXTENSION_V162.isdisjoint(
        v161.K7_DOMAIN_TAG_EXTENSION_V161
    )
