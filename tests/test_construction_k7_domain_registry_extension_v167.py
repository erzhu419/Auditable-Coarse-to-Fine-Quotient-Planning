from acfqp import construction_k7_domain_registry_extension_v166 as v166
from acfqp import construction_k7_domain_registry_extension_v167 as v167


def test_v167_domains_are_additive_and_disjoint_from_v166():
    assert len(v167.K7_DOMAIN_TAG_EXTENSION_V167) == 6
    assert v167.K7_DOMAIN_TAG_EXTENSION_V167.isdisjoint(
        v166.K7_DOMAIN_TAG_EXTENSION_V166
    )
    assert set(v167.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V167.values()) == set(
        v167.K7_DOMAIN_TAG_EXTENSION_V167
    )
