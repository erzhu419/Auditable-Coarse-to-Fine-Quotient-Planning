from acfqp import construction_k7_domain_registry_extension_v180r12 as old_domains
from acfqp import construction_k7_domain_registry_extension_v180r12r1 as domains


def test_v180r12r1_domains_are_additive_and_disjoint() -> None:
    registered = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R1
    assert set(registered) == {
        "aggregation_protocol",
        "execution_authorization",
        "terminal_bundle",
        "verification",
        "failure",
    }
    assert len(set(registered.values())) == len(registered)
    assert set(registered.values()).isdisjoint(
        old_domains.K7_DOMAIN_TAG_EXTENSION_V180R12
    )
