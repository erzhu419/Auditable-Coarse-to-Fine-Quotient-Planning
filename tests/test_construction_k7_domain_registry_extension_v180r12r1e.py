from acfqp import construction_k7_domain_registry_extension_v180r12r1 as parent
from acfqp import construction_k7_domain_registry_extension_v180r12r1e as domains


def test_v180r12r1e_subrecord_domains_are_disjoint() -> None:
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R1E
    assert set(registry) == {
        "source_receipt",
        "terminal_receipt",
        "shared_receipt",
        "receipt_set",
    }
    assert len(set(registry.values())) == len(registry)
    assert set(registry.values()).isdisjoint(
        parent.K7_DOMAIN_TAG_EXTENSION_V180R12R1
    )
