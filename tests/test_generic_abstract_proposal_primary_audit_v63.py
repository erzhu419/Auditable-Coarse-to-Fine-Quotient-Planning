from pathlib import Path

from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.generic_abstract_proposal_primary_audit_v63 import (
    audit_abstract_proposal_primary_v63,
)
from acfqp.generic_portable_coordinate_aligned_inputs_v64 import (
    reconstruct_coordinate_aligned_planning_inputs_v64,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v63_audits_v89_ground_work_as_proposal_only_certification():
    campaign = loads_canonical_json(
        Path(
            ".tmp/exact-freeze/v89_permutation_matched_sample_tax_campaign.json"
        ).read_bytes()
    )
    occurrence = campaign["target_occurrences"][0]
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    model = projected["projected_disagreement_successor_model"]
    program = applicability["action_applicability_program"]
    candidate, _rows, catalogue = reconstruct_coordinate_aligned_planning_inputs_v64(
        model,
        occurrence["coordinate_alignment"],
        occurrence["target_common_partial_acquisition"]["candidate"],
        occurrence["target_common_partial_raw_transition_rows"],
        occurrence["target_common_partial_action_catalogue"],
    )
    episode = occurrence["matched_ablation"]["arms"][
        "APPLICABILITY_CONDITIONED_WORLD_MODEL"
    ]
    audit = audit_abstract_proposal_primary_v63(
        episode,
        model,
        program,
        candidate,
        catalogue,
        maximum_abstract_depth=12,
        maximum_abstract_support_branch_evaluations=1_000_000,
        abstract_support_feasible_beam_width=32,
    )
    assert audit[
        "every_exactly_certified_action_was_abstractly_proposed_first"
    ] is True
    assert audit["non_proposed_alternative_action_query_count"] == 0
    assert audit[
        "ground_queries_used_only_to_certify_abstractly_proposed_policy"
    ] is True
    assert audit["abstract_model_used_as_safety_authority"] is False
