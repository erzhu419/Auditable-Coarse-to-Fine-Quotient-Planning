from acfqp import construction_k7_domain_registry_extension_v180r8 as v180r8
from acfqp import construction_k7_domain_registry_extension_v180r9 as v180r9


def test_v180r9_domains_are_additive_and_complete() -> None:
    assert len(v180r9.K7_DOMAIN_TAG_EXTENSION_V180R9) == 8
    assert v180r9.K7_DOMAIN_TAG_EXTENSION_V180R9.isdisjoint(
        v180r8.K7_DOMAIN_TAG_EXTENSION_V180R8
    )


def test_v180r9_domain_separation() -> None:
    payload = {"schema": "acfqp.v180r9.domain-test"}
    assert len(
        {
            v180r9.extension_content_id_v180r9(domain, payload)
            for domain in v180r9.K7_DOMAIN_TAG_EXTENSION_V180R9
        }
    ) == 8
