from acfqp import construction_k7_domain_registry_extension_v85r1 as v85r1
from acfqp import construction_k7_domain_registry_extension_v86 as domains


def test_v86_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V86) == 5
    assert domains.K7_DOMAIN_TAG_EXTENSION_V86.isdisjoint(
        v85r1.K7_DOMAIN_TAG_EXTENSION_V85R1
    )
