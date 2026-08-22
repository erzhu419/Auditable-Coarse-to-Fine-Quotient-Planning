from acfqp import construction_k7_domain_registry_extension_v158 as previous
from acfqp import construction_k7_domain_registry_extension_v159 as current


def test_v159_domains_are_additive_and_disjoint():
    assert len(current.K7_DOMAIN_TAG_EXTENSION_V159) == 7
    assert not (
        current.K7_DOMAIN_TAG_EXTENSION_V159 & previous.K7_DOMAIN_TAG_EXTENSION_V158
    )
    assert len(current.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V159) == 7
