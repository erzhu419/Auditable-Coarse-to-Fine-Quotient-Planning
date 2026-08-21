from acfqp import construction_k7_identity_short_circuited_epoch_preregistration_v111 as v111_pre
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_incremental_abstract_successor_sequence_v113 import (
    run_incremental_abstract_successor_sequence_v113,
)
from acfqp.generic_projected_program_memo_sequence_v115 import (
    run_projected_program_memo_sequence_v115,
)


def test_v115_projected_program_memo_preserves_execution_and_reduces_compute():
    config = v111_pre.campaign_config_v111()
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "COUPLED_EXCHANGE", 682_103, config
    )
    acquisition = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = {
        "episode_indices": (221, 222, 223),
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
    }
    memo = run_projected_program_memo_sequence_v115(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    matched = run_incremental_abstract_successor_sequence_v113(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    sequence = memo["program_memoized_base_sequence"]
    assert [row["action_keys"] for row in sequence["episodes"]] == [
        row["action_keys"] for row in matched["episodes"]
    ]
    assert [row["abstract_execution_receipts"] for row in sequence["episodes"]] == [
        row["abstract_execution_receipts"] for row in matched["episodes"]
    ]
    assert sequence["all_failed_certificates"] == matched["all_failed_certificates"]
    assert sequence["all_local_distinctions"] == matched["all_local_distinctions"]
    assert sequence["lifetime_target_ground_support_labels"] == matched[
        "lifetime_target_ground_support_labels"
    ]
    assert memo["projected_program_branch_cache_hit_count"] > 0
    assert memo["actual_new_abstract_planning_compute_events"] < matched[
        "actual_new_abstract_planning_compute_events"
    ]
    assert memo["compiled_program_memo_used_as_safety_authority"] is False
