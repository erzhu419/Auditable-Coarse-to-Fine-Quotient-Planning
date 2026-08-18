from acfqp import construction_k7_domain_registry_extension_v58 as previous
from acfqp import construction_k7_domain_registry_extension_v58r1 as subject


def test_v58r1_domains_are_additive_and_content_addressed():
    assert len(subject.K7_DOMAIN_TAG_EXTENSION_V58R1) == 8
    assert subject.K7_DOMAIN_TAG_EXTENSION_V58R1.isdisjoint(
        previous.K7_DOMAIN_TAG_EXTENSION_V58
    )
    domain = subject.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_CAMPAIGN_V58R1_DOMAIN
    assert subject.extension_content_id_v58r1(domain, {"x": 1}) == (
        subject.extension_content_id_v58r1(domain, {"x": 1})
    )
