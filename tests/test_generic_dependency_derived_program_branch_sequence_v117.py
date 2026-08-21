from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp import construction_k7_projected_program_memo_preregistration_v115 as v115_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_cross_epoch_program_branch_sequence_v116 import (
    run_cross_epoch_program_branch_sequence_v116,
)
from acfqp.generic_dependency_derived_program_branch_sequence_v117 import (
    derive_program_branch_dependency_receipt_v117,
    program_branch_cache_retention_decision_v117,
    run_dependency_derived_program_branch_sequence_v117,
)


def _case():
    config = v115_pre.campaign_config_v115()
    factor_library = (
        v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "BALANCED_BATCH_REFINEMENT", 1_028_101, config
    )
    acquisition = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    return config, adapter, acquisition


def test_v117_dependency_receipt_rejects_changed_action_catalogue():
    _config, adapter, acquisition = _case()
    receipt = derive_program_branch_dependency_receipt_v117(
        acquisition["candidate"], adapter.catalogue
    )
    first = adapter.catalogue[0]
    changed = (
        FlatRawActionV4(first.key, (first.fields[0] + 1, *first.fields[1:])),
        *adapter.catalogue[1:],
    )
    changed_receipt = derive_program_branch_dependency_receipt_v117(
        acquisition["candidate"], changed
    )
    same = program_branch_cache_retention_decision_v117(receipt, receipt)
    different = program_branch_cache_retention_decision_v117(
        receipt, changed_receipt
    )
    assert same["retain_program_branch_cache"] is True
    assert same["invalidate_program_branch_cache"] is False
    assert different["retain_program_branch_cache"] is False
    assert different["invalidate_program_branch_cache"] is True


def test_v117_dependency_derived_retention_preserves_v116_sequence_exactly():
    config, adapter, acquisition = _case()
    common = {
        "episode_indices": (251, 252, 253),
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
    }
    derived = run_dependency_derived_program_branch_sequence_v117(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    matched = run_cross_epoch_program_branch_sequence_v116(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    assert derived["dependency_derived_program_branch_base_sequence"] == matched[
        "cross_epoch_program_branch_base_sequence"
    ]
    assert derived["actual_new_abstract_planning_compute_events"] == matched[
        "actual_new_abstract_planning_compute_events"
    ]
    assert derived["compiled_model_cache_or_receipt_used_as_safety_authority"] is False
