from acfqp import construction_k7_domain_registry_extension_v160 as v160
from acfqp import construction_k7_domain_registry_extension_v161 as v161


def test_v161_domains_are_additive_and_disjoint():
    assert len(v161.K7_DOMAIN_TAG_EXTENSION_V161) == 7
    assert v161.K7_DOMAIN_TAG_EXTENSION_V161.isdisjoint(
        v160.K7_DOMAIN_TAG_EXTENSION_V160
    )
