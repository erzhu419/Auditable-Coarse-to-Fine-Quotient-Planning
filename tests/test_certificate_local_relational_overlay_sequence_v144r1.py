from functools import lru_cache
from pathlib import Path

from acfqp.certificate_local_relational_overlay_sequence_v144r1 import (
    _advance,
    _full_rebuild,
    _initialize,
)
from acfqp.construction_k7_occurrence_factor_bank_update_independent_verifier_v141 import (
    FROZEN_BANK_ID,
)
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.fifth_family_factor_bank_transfer_acquisition_v144 import (
    _validated_projection,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)
from acfqp.generic_relational_factor_execution_projection_v144 import (
    compile_relational_factor_execution_projection_v144,
)
from acfqp.phase3e_ids import loads_canonical_json
from acfqp.robust_factor_dictionary_acquisition_v131r2 import (
    synthesize_robust_dictionary_factor_candidate_v131r2,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@lru_cache(maxsize=1)
def _fixture():
    config = maintenance_cascade_config_v144()
    adapter = build_maintenance_cascade_adapter_v144(1_044_003, config)
    batches = tuple(fair_witness_blind_path_first_stream_v129r1(adapter))
    rows = tuple(row for batch in batches[:72] for row in batch)
    dictionary = loads_canonical_json(
        (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes()
    )
    verification = loads_canonical_json(
        (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes()
    )
    assert dictionary["bank_id"] == FROZEN_BANK_ID
    source, _compute = synthesize_robust_dictionary_factor_candidate_v131r2(
        rows,
        adapter.catalogue,
        _validated_projection(dictionary, verification),
        support_label_count=72,
        factor_prior_enabled=False,
        layout_domain=config["generic_domains"]["layout"],
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
    )
    candidate = compile_relational_factor_execution_projection_v144(
        source, rows, adapter.catalogue
    )
    return adapter, candidate, rows


def test_v144r1_program_mismatch_becomes_exact_local_overlay():
    adapter, candidate, rows = _fixture()
    state, bootstrap = _initialize(candidate, rows, adapter.catalogue)
    original = rows[-1]
    raw_target = candidate.layout.state_canonical_to_raw[
        candidate.assignments[0]["target_column"]
    ]
    post = list(original.post)
    post[raw_target] += 997
    mismatch = FlatRawTransitionV4(
        original.occurrence,
        original.index + 10_000,
        original.pre,
        original.legal_before,
        original.action,
        tuple(post),
        original.legal_after,
        original.terminal_acceptance_after,
        original.outcome_tape_sha256,
    )
    next_state, update = _advance(
        state, candidate, (mismatch,), adapter.catalogue
    )
    match = _full_rebuild(
        next_state,
        candidate,
        (*rows, mismatch),
        adapter.catalogue,
        update_receipt=update,
    )
    assert bootstrap["query_local_overlay_row_count"] == 0
    assert update["delta_query_local_exact_overlay_row_count"] == 1
    assert update["source_partial_program_mutated"] is False
    assert next_state.model["query_local_exact_overlay_edge_count"] == 1
    assert next_state.model["compiled_factor_program_checked_each_abstract_edge"] is False
    assert match["query_local_overlay_inventory_exactly_equal_full_rebuild"] is True
    assert match["model_used_as_safety_authority"] is False
