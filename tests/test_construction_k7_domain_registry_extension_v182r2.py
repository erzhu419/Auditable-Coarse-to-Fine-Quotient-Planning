from acfqp import construction_k7_domain_registry_extension_v182 as v182
from acfqp import construction_k7_domain_registry_extension_v182r1 as v182r1
from acfqp import construction_k7_domain_registry_extension_v182r2 as v182r2


def test_v182r2_domains_are_complete_and_additive() -> None:
    assert len(v182r2.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182R2) == 10
    assert len(v182r2.K7_DOMAIN_TAG_EXTENSION_V182R2) == 10
    assert v182r2.K7_DOMAIN_TAG_EXTENSION_V182R2.isdisjoint(
        v182.K7_DOMAIN_TAG_EXTENSION_V182
    )
    assert v182r2.K7_DOMAIN_TAG_EXTENSION_V182R2.isdisjoint(
        v182r1.K7_DOMAIN_TAG_EXTENSION_V182R1
    )


def test_v182r2_content_ids_are_domain_separated() -> None:
    payload = {"schema": "acfqp.v182r2.domain-separation-test"}
    ids = {
        v182r2.extension_content_id_v182r2(domain, payload)
        for domain in v182r2.K7_DOMAIN_TAG_EXTENSION_V182R2
    }
    assert len(ids) == len(v182r2.K7_DOMAIN_TAG_EXTENSION_V182R2)
