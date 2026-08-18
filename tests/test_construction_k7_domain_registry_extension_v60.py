from acfqp import construction_k7_domain_registry_extension_v59 as previous
from acfqp import construction_k7_domain_registry_extension_v60 as subject


def test_v60_domains_are_fresh():
    assert len(subject.K7_DOMAIN_TAG_EXTENSION_V60) == 9
    assert subject.K7_DOMAIN_TAG_EXTENSION_V60.isdisjoint(previous.K7_DOMAIN_TAG_EXTENSION_V59)
