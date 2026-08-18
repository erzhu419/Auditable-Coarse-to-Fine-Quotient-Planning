from acfqp import construction_k7_domain_registry_extension_v58r1 as previous
from acfqp import construction_k7_domain_registry_extension_v59 as subject


def test_v59_domains_are_fresh_and_disjoint():
    assert len(subject.K7_DOMAIN_TAG_EXTENSION_V59) == 8
    assert subject.K7_DOMAIN_TAG_EXTENSION_V59.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V58R1
    )
