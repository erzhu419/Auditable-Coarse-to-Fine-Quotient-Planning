from acfqp import construction_k7_domain_registry_extension_v162 as v162
from acfqp import construction_k7_domain_registry_extension_v163 as v163


def test_v163_domains_are_additive_and_disjoint():
    assert len(v163.K7_DOMAIN_TAG_EXTENSION_V163) == 4
    assert v163.K7_DOMAIN_TAG_EXTENSION_V163.isdisjoint(
        v162.K7_DOMAIN_TAG_EXTENSION_V162
    )
