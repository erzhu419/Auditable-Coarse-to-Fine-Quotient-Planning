from __future__ import annotations

from acfqp import construction_k7_open_world_machine_protocol_v182 as protocol


def test_v182_protocol_is_outcome_free_and_locks_claim_boundaries() -> None:
    frozen = protocol.freeze_open_world_machine_protocol_v182()
    document = frozen.to_document()
    assert document["protocol_id"] == frozen.protocol_id
    assert document["manifest_commitments"] == list(
        protocol.MANIFEST_COMMITMENTS_V182
    )
    assert len(document["manifest_commitments"]) == 3
    assert document["source_and_target_manifest_preimages_revealed"] is False
    assert document["source_or_target_transition_outcomes_accessed"] is False
    assert document["finite_candidate_program_catalog_used"] is False
    assert document["named_domain_family_used"] is False
    assert document["named_layout_used"] is False
    assert document["search_resource_bounded_per_occurrence"] is True
    assert document["broad_iid_sample_efficiency_claimed"] is False
    assert document["arbitrary_domain_transfer_claimed"] is False
    assert document["total_work_dominance_claimed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False


def test_v182_protocol_pins_only_generic_machine_sources() -> None:
    document = protocol.freeze_open_world_machine_protocol_v182().to_document()
    paths = [row["relative_path"] for row in document["source_facts"]]
    assert len(paths) == len(set(paths)) == 6
    assert all("v182" in path or path.endswith("phase3e_ids.py") for path in paths)
    assert not any("manifest_reveal" in path or "campaign" in path for path in paths)
