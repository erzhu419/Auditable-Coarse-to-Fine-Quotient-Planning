from acfqp import construction_k7_domain_registry_extension_v165 as v165
from acfqp import construction_k7_domain_registry_extension_v166 as v166


def test_v166_domains_are_additive_and_disjoint():
    assert len(v166.K7_DOMAIN_TAG_EXTENSION_V166) == 4
    assert v166.K7_DOMAIN_TAG_EXTENSION_V166.isdisjoint(
        v165.K7_DOMAIN_TAG_EXTENSION_V165
    )
