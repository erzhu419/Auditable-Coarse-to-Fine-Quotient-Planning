import os

import pytest

from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)
from acfqp.generic_overlay_residual_factor_compiler_v18 import (
    compile_overlay_residual_factor_library_v18,
    replay_overlay_residual_factor_library_v18,
)


def _occurrence(name, state_order, action_order, base, delta):
    rows = []
    for index, status_delta in enumerate((0, 10)):
        pre = [77, base, 9001]
        action = [91, delta]
        post = [77, base + delta + 1, 9001 + status_delta]
        raw_pre = [0] * 3
        raw_post = [0] * 3
        raw_action = [0] * 2
        for canonical, raw in enumerate(state_order):
            raw_pre[raw] = pre[canonical]
            raw_post[raw] = post[canonical]
        for canonical, raw in enumerate(action_order):
            raw_action[raw] = action[canonical]
        rows.append(
            {
                "occurrence": index,
                "transition_index": index,
                "pre_vector": raw_pre,
                "legal_action_keys_before": [0],
                "selected_action": {"action_key": 0, "anonymous_fields": raw_action},
                "post_vector": raw_post,
                "legal_action_keys_after": [] if status_delta else [0],
                "terminal_acceptance_after": True if status_delta else None,
                "outcome_tape_sha256": None,
            }
        )
    return {
        "layout": {
            "state_canonical_to_raw": state_order,
            "action_canonical_to_raw": action_order,
        },
        "unknown_residual_target_columns": [1, 2],
        "raw_transition_rows": rows,
        "opaque_occurrence_label": name,
    }


def test_v18_discovers_shared_residual_subprograms_across_permuted_occurrences():
    occurrences = {
        "O0": _occurrence("ignored-a", [0, 1, 2], [0, 1], 4, 2),
        "O1": _occurrence("ignored-b", [2, 0, 1], [1, 0], 13, 5),
        "O2": _occurrence("ignored-c", [1, 2, 0], [0, 1], 29, 3),
    }
    library = compile_overlay_residual_factor_library_v18(occurrences)
    assert library["all_observed_residual_targets_covered"] is True
    assert library["residual_target_count"] == 6
    assert len(library["compiled_subprograms"]) == 2
    assert library["family_names_available_to_compiler"] is False
    assert library["semantic_state_or_action_names_available_to_compiler"] is False
    assert library["ground_fact_transfer_across_occurrences_claimed"] is False
    assert library["future_transition_prediction_authority_present"] is False
    replay = replay_overlay_residual_factor_library_v18(library, occurrences)
    assert replay["exact_on_frozen_overlay_rows"] is True
    assert replay["raw_transition_assignment_checks"] == 12


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_RESIDUAL_COMPILER") != "1",
    reason="explicit three-family development replay",
)
def test_v18_real_three_family_overlays_yield_honest_partial_residual_library():
    config = pre.campaign_config_v59()
    factor_library = pre.previous.previous.FACTOR_LIBRARY
    occurrences = {}
    for index, (family, seed) in enumerate(
        (
            ("BALANCED_BATCH_REFINEMENT", 590_541),
            ("COUPLED_EXCHANGE", 590_542),
            ("MAINTENANCE_CASCADE", 590_543),
        )
    ):
        adapter = campaign.predecessor.predecessor.prior_ground._adapter(
            family, seed, config
        )
        acquired = campaign.acquire_matched_true_bit_models_v59(
            adapter, factor_library, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        episode = run_certificate_guided_partial_episode_v16(
            adapter,
            acquired["candidate"],
            acquired["rows"],
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        candidate = acquired["candidate"].public_document
        occurrences[f"O{index}"] = {
            "layout": candidate["layout"],
            "unknown_residual_target_columns": candidate[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": episode["raw_local_transition_rows"],
        }
    library = compile_overlay_residual_factor_library_v18(occurrences)
    assert library["all_observed_residual_targets_covered"] is False
    assert len(library["covered_residual_targets"]) == 3
    assert len(library["uncovered_residual_targets"]) == 3
    assert len(library["compiled_subprograms"]) == 2
    assert all(
        row["source_occurrence_support_count"] >= 2
        for row in library["compiled_subprograms"]
    )
    replay = replay_overlay_residual_factor_library_v18(library, occurrences)
    assert replay["exact_on_frozen_overlay_rows"] is True
    assert replay["future_transition_prediction_authority_present"] is False
