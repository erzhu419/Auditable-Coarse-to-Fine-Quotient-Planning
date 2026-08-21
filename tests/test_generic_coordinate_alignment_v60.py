import pytest

from acfqp import construction_k7_applicability_target_preregistration_v87 as prior
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.generic_coordinate_alignment_v60 import (
    GenericCoordinateAlignmentV60Error,
    aligned_source_views_v60,
    compile_coordinate_alignment_v60,
)
from acfqp.generic_coordinate_aligned_certificate_planner_v60 import (
    run_coordinate_aligned_applicability_ablation_v60,
)


@pytest.fixture(scope="module")
def aligned_fixture():
    config = prior.campaign_config_v87()
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], 888_881, config
    )
    factor_library = v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    model = load_projected_model_artifact_v86()[
        "projected_disagreement_successor_model"
    ]
    applicability = load_action_applicability_model_v87()[
        "action_applicability_program"
    ]
    alignment = compile_coordinate_alignment_v60(
        model,
        applicability,
        partial["candidate"],
        partial["rows"],
        adapter.catalogue,
    )
    return adapter, partial, model, applicability, alignment


def test_v60_discovers_unique_coordinate_and_action_projection(aligned_fixture):
    _adapter, partial, model, applicability, alignment = aligned_fixture
    assert alignment["source_model_id"] == model[
        "projected_disagreement_successor_model_id"
    ]
    assert alignment["source_applicability_program_id"] == applicability[
        "action_applicability_program_id"
    ]
    assert alignment["target_partial_candidate_id"] == partial["candidate"].public_document[
        "candidate_id"
    ]
    assert sorted(alignment["source_state_to_target_canonical"]) == list(range(6))
    assert sorted(alignment["source_action_to_target_canonical"]) == list(range(5))
    assert alignment["exact_full_model_projection_count"] == 1
    assert alignment["target_episode_outcomes_used"] is False
    assert alignment["alignment_used_as_safety_authority"] is False


def test_v60_aligned_views_replay_all_partial_rows(aligned_fixture):
    adapter, partial, _model, _applicability, alignment = aligned_fixture
    rows, actions = aligned_source_views_v60(
        alignment, partial["candidate"], partial["rows"], adapter.catalogue
    )
    assert len(rows) == len(partial["rows"])
    assert len(actions) == len(adapter.catalogue)
    relation = (
        alignment["target_applicability_state_column"],
        alignment["target_applicability_action_field"],
    )
    assert relation[0] in partial["candidate"].public_document[
        "unknown_residual_target_columns"
    ]


def test_v60_rejects_forged_alignment_identity(aligned_fixture):
    adapter, partial, _model, _applicability, alignment = aligned_fixture
    forged = dict(alignment)
    forged["coordinate_alignment_id"] = "f" * 64
    with pytest.raises(GenericCoordinateAlignmentV60Error):
        aligned_source_views_v60(
            forged, partial["candidate"], partial["rows"], adapter.catalogue
        )


def test_v60_projection_drives_abstract_ordering_but_not_safety(aligned_fixture):
    adapter, partial, model, applicability, alignment = aligned_fixture
    result = run_coordinate_aligned_applicability_ablation_v60(
        adapter,
        partial["candidate"],
        partial["rows"],
        model,
        applicability,
        model_source_episode_index=0,
        episode_index=91,
        maximum_abstract_depth=prior.campaign_config_v87()[
            "maximum_abstract_depth"
        ],
        maximum_execution_steps=prior.campaign_config_v87()[
            "maximum_execution_steps"
        ],
    )
    assert result["coordinate_alignment_id"] == alignment["coordinate_alignment_id"]
    derived = result["arms"]["APPLICABILITY_CONDITIONED_WORLD_MODEL"]
    assert derived["abstract_plan_success_count"] > 0
    assert derived["abstract_plan_abstention_count"] == 0
    assert derived["abstract_model_ordering_accepted_count"] == derived[
        "abstract_plan_success_count"
    ]
    assert result["all_ground_queries_followed_failed_certificates"] is True
    assert result["coordinate_alignment_or_model_used_as_safety_authority"] is False
