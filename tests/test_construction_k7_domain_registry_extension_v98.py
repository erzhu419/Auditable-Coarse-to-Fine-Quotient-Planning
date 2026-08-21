from acfqp import construction_k7_domain_registry_extension_v97 as previous
from acfqp import construction_k7_domain_registry_extension_v98 as current


def test_v98_domains_are_unique_and_additive():
    assert len(current.K7_DOMAIN_TAG_EXTENSION_V98) == 4
    assert current.K7_DOMAIN_TAG_EXTENSION_V98.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V97
    )
    domain = current.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_CAMPAIGN_V98_DOMAIN
    assert current.extension_content_id_v98(domain, {"x": 1}) == current.extension_content_id_v98(
        domain, {"x": 1}
    )

