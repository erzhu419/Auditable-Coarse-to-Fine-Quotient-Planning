import os

import pytest

from acfqp.generic_adaptive_residual_factor_acquisition_v19 import (
    acquire_adaptive_residual_factor_v19,
    replay_adaptive_residual_factor_v19,
)


def _rows():
    result = []
    for query in range(20):
        pre = [query, 10 + query]
        action = [2]
        for branch in (0, 1):
            result.append(
                {
                    "occurrence": 0,
                    "transition_index": len(result),
                    "pre_vector": pre,
                    "legal_action_keys_before": [0],
                    "selected_action": {"action_key": query, "anonymous_fields": action},
                    "post_vector": [query, 13 + query if branch else 10 + query],
                    "legal_action_keys_after": [0],
                    "terminal_acceptance_after": None,
                    "outcome_tape_sha256": None,
                }
            )
    return result


def test_v19_same_synthesizer_prior_reduces_synthetic_labels():
    evidence = {
        "layout": {
            "state_canonical_to_raw": [0, 1],
            "action_canonical_to_raw": [0],
        },
        "unknown_residual_target_columns": [1],
        "raw_transition_rows": _rows(),
    }
    library = {
        "residual_factor_library_id": "f" * 64,
        "compiled_subprograms": [
            {
                "normalized_expression": [
                    "R04",
                    ["R00"],
                    ["R03", ["R03", ["R00"], ["R01"]], ["R02"]],
                ]
            }
        ],
    }
    prior = acquire_adaptive_residual_factor_v19(evidence, prior_library=library)
    strict = acquire_adaptive_residual_factor_v19(evidence, prior_library=None)
    assert prior["ground_support_labels"] < strict["ground_support_labels"]
    assert prior["same_generic_synthesizer_and_stop_rule"] is True
    assert strict["same_generic_synthesizer_and_stop_rule"] is True
    assert prior["proposal_only_not_safety_authority"] is True
    assert replay_adaptive_residual_factor_v19(prior, evidence)[
        "exact_support_on_full_frozen_query_stream"
    ] is True


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_RESIDUAL_ACQUISITION") != "1",
    reason="explicit three-family development acquisition",
)
def test_v19_real_development_occurrences_close_without_frontier_fallback():
    from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
    )
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )

    config = pre.campaign_config_v59()
    factor_library = pre.previous.previous.FACTOR_LIBRARY
    residual_library = freeze_residual_factor_library_v62().to_document()[
        "compiled_library"
    ]
    reductions = []
    for family, seed in (
        ("BALANCED_BATCH_REFINEMENT", 590_641),
        ("COUPLED_EXCHANGE", 590_642),
        ("MAINTENANCE_CASCADE", 590_643),
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
        document = acquired["candidate"].public_document
        evidence = {
            "layout": document["layout"],
            "unknown_residual_target_columns": document[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": episode["raw_local_transition_rows"],
        }
        prior = acquire_adaptive_residual_factor_v19(
            evidence, prior_library=residual_library
        )
        strict = acquire_adaptive_residual_factor_v19(evidence, prior_library=None)
        assert prior["reachable_frontier_exhaustion_consumed"] is False
        assert strict["reachable_frontier_exhaustion_consumed"] is False
        reductions.append(strict["ground_support_labels"] - prior["ground_support_labels"])
        prior_replay = replay_adaptive_residual_factor_v19(prior, evidence)
        strict_replay = replay_adaptive_residual_factor_v19(strict, evidence)
        assert prior_replay["future_transition_prediction_authority_present"] is False
        assert strict_replay["future_transition_prediction_authority_present"] is False
        assert prior_replay["supported_raw_transition_count"] > 0
        assert strict_replay["supported_raw_transition_count"] > 0
    assert all(value > 0 for value in reductions)
