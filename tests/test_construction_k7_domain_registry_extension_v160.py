from acfqp import construction_k7_domain_registry_extension_v160 as v160
from acfqp import construction_k7_domain_registry_extension_v159 as v159


def test_v160_domains_are_additive_and_disjoint():
    assert len(v160.K7_DOMAIN_TAG_EXTENSION_V160) == 7
    assert v160.K7_DOMAIN_TAG_EXTENSION_V160.isdisjoint(
        v159.K7_DOMAIN_TAG_EXTENSION_V159
    )
    assert all(domain.endswith(":v160") for domain in v160.K7_DOMAIN_TAG_EXTENSION_V160)
