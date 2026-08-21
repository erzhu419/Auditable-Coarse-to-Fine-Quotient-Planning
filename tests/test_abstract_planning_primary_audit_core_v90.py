from pathlib import Path

from acfqp.abstract_planning_primary_audit_core_v90 import (
    build_abstract_planning_primary_audit_document_v90,
)
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v90_replays_every_v89_abstract_action_before_ground_certificate():
    campaign = loads_canonical_json(
        Path(
            ".tmp/exact-freeze/v89_permutation_matched_sample_tax_campaign.json"
        ).read_bytes()
    )
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    result = build_abstract_planning_primary_audit_document_v90(
        campaign,
        "fixture-preregistration",
        "6dd9d5c1dab579ef7e0192bc64d486b82468e56a28d1d7a92595505c77dc8f39",
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        maximum_abstract_depth=12,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=32,
    )
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"]["proposal_mismatch_count"] == 0
    assert result["registered_gate"]["non_proposed_ground_action_query_count"] == 0
    assert result["registered_gate"]["audited_exact_transition_state_count"] == 264
    assert result["multi_step_planning_primarily_in_abstract_model_verified"] is True
    assert result["complete_world_model_synthesized"] is False
