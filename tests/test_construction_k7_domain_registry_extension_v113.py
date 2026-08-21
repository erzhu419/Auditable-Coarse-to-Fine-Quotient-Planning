from acfqp import construction_k7_domain_registry_extension_v112 as previous
from acfqp import construction_k7_domain_registry_extension_v113 as domains


def test_v113_domains_are_additive_and_content_addressed():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V113) == 8
    assert domains.K7_DOMAIN_TAG_EXTENSION_V113.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V112
    )
    domain = (
        domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_UPDATE_V113_DOMAIN
    )
    assert domains.extension_content_id_v113(domain, {"delta": 1}) == (
        domains.extension_content_id_v113(domain, {"delta": 1})
    )
    assert domains.extension_content_id_v113(domain, {"delta": 1}) != (
        domains.extension_content_id_v113(domain, {"delta": 2})
    )
