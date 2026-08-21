from acfqp import construction_k7_domain_registry_extension_v98 as previous
from acfqp import construction_k7_domain_registry_extension_v99 as current


def test_v99_domains_are_unique_and_additive():
    assert len(current.K7_DOMAIN_TAG_EXTENSION_V99) == 4
    assert current.K7_DOMAIN_TAG_EXTENSION_V99.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V98
    )

