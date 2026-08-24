from pathlib import Path

from acfqp import construction_k7_open_world_preregistration_v181 as prereg


def test_final_preregistration_freezes_implementation_before_reveal() -> None:
    document = prereg.freeze_open_world_preregistration_v181().to_document()
    assert document["manifest_reveal_bytes_embedded"] is False
    assert document["named_target_family_registry_present"] is False
    assert len(document["frozen_implementation_source_facts"]) == 5
    base = Path(prereg.__file__).resolve().parent
    assert all((base / row["filename"]).is_file() for row in document["frozen_implementation_source_facts"])
    assert document["target_denominator"]["total_target_episode_count"] == 72


def test_acquisition_switches_only_the_subprogram_archive() -> None:
    policy = prereg.freeze_open_world_preregistration_v181().to_document()[
        "source_acquisition_policy"
    ]
    assert policy["reads_manifest_program_or_generation_witness"] is False
    assert policy["same_stop_rule_for_both_arms"] is True
    assert policy["prior_arm_only_switch"] == "REUSABLE_SUBPROGRAM_ARCHIVE_AVAILABLE"


def test_preregistration_keeps_open_world_and_official_claims_locked() -> None:
    locks = prereg.freeze_open_world_preregistration_v181().to_document()[
        "claim_locks"
    ]
    assert locks["manifest_reveals_accessed"] is False
    assert locks["target_outcomes_accessed"] is False
    assert locks["implementation_source_frozen"] is True
    assert locks["open_ended_world_model_invention_claimed"] is False
    assert locks["broad_iid_sample_efficiency_claimed"] is False
    assert locks["total_work_dominance_claimed"] is False
    assert locks["official_execution_allowed"] is False
    assert locks["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_retained_final_preregistration_bytes_are_exact() -> None:
    value = prereg.freeze_open_world_preregistration_v181()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181_open_world_preregistration.json"
    )
    assert path.read_bytes() == value.canonical_bytes
