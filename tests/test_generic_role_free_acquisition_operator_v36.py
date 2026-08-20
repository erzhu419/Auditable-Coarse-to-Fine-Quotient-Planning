import copy

from acfqp.generic_role_free_acquisition_operator_v36 import (
    PRESERVED_V36_DEVELOPMENT_FAILURE,
    schedule_role_free_acquisition_queries_v36,
)


def _row(pre, post, key, terminal):
    return {
        "pre_vector": pre,
        "post_vector": post,
        "selected_action": {"action_key": key, "anonymous_fields": [key, -key]},
        "legal_action_keys_after": [] if terminal is not None else [0],
        "terminal_acceptance_after": terminal,
        "outcome_tape_sha256": None,
    }


def _evidence():
    return {
        "layout": {"state_canonical_to_raw": [0, 1, 2]},
        "unknown_residual_target_columns": [2],
        "raw_transition_rows": [
            _row([8, 1, 4], [9, 2, 4], 0, None),
            _row([3, 3, 4], [4, 4, 9], 1, True),
            _row([5, 2, 4], [6, 3, 4], 2, None),
        ],
    }


def test_v36_schedule_is_invariant_to_every_outcome_witness_field():
    library = {
        "template_library_id": "a" * 64,
        "role_free_template_count": 1,
    }
    original = schedule_role_free_acquisition_queries_v36(
        _evidence(), role_free_template_library=library
    )
    changed = copy.deepcopy(_evidence())
    for row in changed["raw_transition_rows"]:
        row["post_vector"] = [value + 100 for value in row["post_vector"]]
        row["legal_action_keys_after"] = [99]
        row["terminal_acceptance_after"] = None
        row["outcome_tape_sha256"] = "f" * 64
    replay = schedule_role_free_acquisition_queries_v36(
        changed, role_free_template_library=library
    )
    assert [row["query_projection"] for row in original["schedule"]] == [
        row["query_projection"] for row in replay["schedule"]
    ]
    assert original["query_source_projection_sha256"] == replay[
        "query_source_projection_sha256"
    ]
    assert original["terminal_acceptance_label_accessed"] is False
    assert original["heuristic_operator_not_safety_authority"] is True


def test_v36_prior_moves_anonymous_boundary_query_before_hash_control():
    library = {
        "template_library_id": "a" * 64,
        "role_free_template_count": 1,
    }
    prior = schedule_role_free_acquisition_queries_v36(
        _evidence(), role_free_template_library=library
    )
    assert prior["schedule"][0]["query_projection"]["pre_vector"][:2] == [3, 3]
    strict = schedule_role_free_acquisition_queries_v36(
        _evidence(), role_free_template_library=None
    )
    assert strict["query_count"] == prior["query_count"]


def test_v36_preserves_the_overeager_prior_failure_as_a_noncertificate():
    failure = PRESERVED_V36_DEVELOPMENT_FAILURE
    assert failure["prior_status"].endswith("FAILED_NONCERTIFICATE")
    assert failure["prior_stop_labels"] == 9
    assert failure["strict_stop_labels"] == 13
    assert failure["registered_scientific_result"] is False
    assert failure["safety_authority"] is False
