import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r2 as parent
from acfqp import construction_k7_domain_registry_extension_v180r12r2e as domains


def test_v180r12r2e_subrecord_domains_are_exact_and_disjoint() -> None:
    registry = domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R2E
    assert set(registry) == {
        "source_receipt",
        "route_component_chain_receipt",
        "terminal_receipt",
        "terminal_shared_receipt",
        "terminal_receipt_set",
        "v180r7r1_construction_axis_receipt",
        "campaign_counter_record",
        "campaign_receipt_set",
        "campaign_work_vector",
        "campaign_comparison_vector",
        "campaign_projection_proof",
        "campaign_native_zero_attestation",
        "campaign_accounting_chain",
        "campaign_structural_boundary",
    }
    assert len(registry) == len(set(registry.values())) == 14
    assert all(tag.endswith(":v180r12r2e") for tag in registry.values())
    assert set(registry.values()).isdisjoint(
        parent.K7_DOMAIN_TAG_EXTENSION_V180R12R2
    )


def test_v180r12r2e_rejects_parent_domains() -> None:
    with pytest.raises(ValueError, match="absent from V180r12r2e"):
        domains.extension_content_id_v180r12r2e(
            parent.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
            {"producer": True},
        )
