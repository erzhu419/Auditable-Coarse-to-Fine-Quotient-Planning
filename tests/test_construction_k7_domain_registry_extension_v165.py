from acfqp import construction_k7_domain_registry_extension_v164 as v164
from acfqp import construction_k7_domain_registry_extension_v165 as v165


def test_v165_domains_are_additive_and_disjoint():
    assert len(v165.K7_DOMAIN_TAG_EXTENSION_V165) == 3
    assert v165.K7_DOMAIN_TAG_EXTENSION_V165.isdisjoint(
        v164.K7_DOMAIN_TAG_EXTENSION_V164
    )
