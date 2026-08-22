from acfqp import construction_k7_domain_registry_extension_v163 as v163
from acfqp import construction_k7_domain_registry_extension_v164 as v164


def test_v164_domains_are_additive_and_disjoint():
    assert len(v164.K7_DOMAIN_TAG_EXTENSION_V164) == 4
    assert v164.K7_DOMAIN_TAG_EXTENSION_V164.isdisjoint(
        v163.K7_DOMAIN_TAG_EXTENSION_V163
    )
