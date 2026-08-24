from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v180 as v180
from acfqp import construction_k7_domain_registry_extension_v181 as v181
from acfqp import construction_k7_open_world_protocol_contract_v181 as protocol


def test_v181_domains_are_additive_and_unique() -> None:
    assert len(v181.K7_DOMAIN_TAG_EXTENSION_V181) == 9
    assert len(v181.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V181) == 9
    assert v181.K7_DOMAIN_TAG_EXTENSION_V181.isdisjoint(
        v180.K7_DOMAIN_TAG_EXTENSION_V180
    )


def test_protocol_removes_finite_candidate_and_named_family_inputs() -> None:
    document = protocol.freeze_open_world_protocol_contract_v181().to_document()
    invention = document["representation_invention_protocol"]
    hidden = document["hidden_target_protocol"]
    assert invention["named_target_family_registry_present"] is False
    assert invention["finite_candidate_program_catalog_present"] is False
    assert invention["whole_program_templates_present"] is False
    assert invention["program_length_semantic_bound"] is None
    assert hidden["manifest_count"] == 3
    assert hidden["synthesizer_may_not_read_manifest_programs"] is True
    assert hidden["oracle_exposes_only_raw_transition_queries"] is True


def test_protocol_freezes_higher_horizon_iid_and_matched_controls() -> None:
    document = protocol.freeze_open_world_protocol_contract_v181().to_document()
    science = document["scientific_protocol"]
    assert science["minimum_horizon"] == 5
    assert science["honest_partial_dynamics_support_required"] is True
    assert science["minimum_iid_distribution_count"] == 3
    assert science["iid_occurrences_per_distribution"] == 12
    assert science["same_synthesizer_search_and_stop_rule_across_arms"] is True
    assert science["ground_distinction_only_after_certificate_failure"] is True


def test_protocol_is_outcome_free_and_keeps_every_gate_locked() -> None:
    locks = protocol.freeze_open_world_protocol_contract_v181().to_document()[
        "claim_locks"
    ]
    assert locks["v181_manifest_reveals_accessed"] is False
    assert locks["v181_target_outcomes_accessed"] is False
    assert locks["implementation_source_frozen"] is False
    assert locks["open_ended_world_model_invention_claimed"] is False
    assert locks["broad_iid_sample_efficiency_claimed"] is False
    assert locks["total_work_dominance_claimed"] is False
    assert locks["official_execution_allowed"] is False
    assert locks["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert locks["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_retained_protocol_bytes_are_exact() -> None:
    value = protocol.freeze_open_world_protocol_contract_v181()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181_open_world_protocol_contract.json"
    )
    assert path.read_bytes() == value.canonical_bytes
