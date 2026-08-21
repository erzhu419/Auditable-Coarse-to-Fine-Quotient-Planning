from acfqp import construction_k7_domain_registry_extension_v113 as previous
from acfqp import construction_k7_domain_registry_extension_v114 as domains


def test_v114_domains_are_additive():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V114) == 4
    assert domains.K7_DOMAIN_TAG_EXTENSION_V114.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V113
    )
