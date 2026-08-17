from __future__ import annotations

from collections import deque
import inspect
import random

from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementStatus,
    generate_stochastic_batch_refinement,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
)


_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
    "cross_schema_subprograms": [
        {
            "signature_sha256": "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "source_schema_pairs": [[4, 3], [7, 5]],
        },
        {
            "signature_sha256": "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "source_schema_pairs": [[4, 3], [7, 5]],
        },
        {
            "signature_sha256": "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
            "source_schema_pairs": [[4, 3], [7, 5]],
        },
    ],
}


def _batch_occurrence(occurrence: int, seed: int):
    kernel, _witness = generate_stochastic_batch_refinement(
        stage_count=6, unit_base=3, seed=seed
    )
    state_order = list(range(9))
    action_order = list(range(5))
    random.Random(seed ^ 12_345).shuffle(state_order)
    random.Random(seed ^ 67_890).shuffle(action_order)
    catalogue = []
    for key, rule in enumerate(kernel.rules):
        semantic = (
            rule.source_stage,
            rule.anonymous_advance_class,
            rule.unit_increment,
            rule.risk_increment,
            1,
        )
        catalogue.append(
            FlatRawActionV4(key, tuple(semantic[index] for index in action_order))
        )
    token = {
        BatchRefinementStatus.ACTIVE: 9_001,
        BatchRefinementStatus.FAILURE: 9_007,
        BatchRefinementStatus.SUCCESS: 9_011,
    }

    def encode(state):
        semantic = (
            state.stage,
            state.units,
            state.risk,
            state.checksum,
            token[state.status],
            kernel.checksum_modulus,
            kernel.risk_capacity,
            kernel.target_units,
            kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    queue = deque([kernel.initial_distribution()[0][1]])
    seen = set(queue)
    rows = []
    while queue:
        state = queue.popleft()
        legal = kernel.actions(state)
        for action in legal:
            for outcome in kernel.step(state, action):
                successor = outcome.next_state
                legal_after = kernel.actions(successor)
                rows.append(
                    FlatRawTransitionV4(
                        occurrence,
                        len(rows),
                        encode(state),
                        tuple(item.rule for item in legal),
                        catalogue[action.rule],
                        encode(successor),
                        tuple(item.rule for item in legal_after),
                        None
                        if legal_after
                        else successor.status is BatchRefinementStatus.SUCCESS,
                    )
                )
                if (
                    successor.status is BatchRefinementStatus.ACTIVE
                    and successor not in seen
                ):
                    seen.add(successor)
                    queue.append(successor)
    return tuple(rows), tuple(catalogue)


def _ood_occurrence():
    catalogue = tuple(
        FlatRawActionV4(index, (bit, 1))
        for index, bit in enumerate((1, 2, 4))
    )
    tokens = {"A": 9_001, "F": 9_007, "S": 9_011}
    rows = []
    queue = deque([0])
    seen = {0}
    while queue:
        mask = queue.popleft()
        legal = (0, 1, 2)
        for key, bit in enumerate((1, 2, 4)):
            successor = mask | bit
            status = "F" if successor & 4 else "S" if successor == 3 else "A"
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    (mask, tokens["A"], 3, 4, 1),
                    legal,
                    catalogue[key],
                    (successor, tokens[status], 3, 4, 1),
                    () if status != "A" else legal,
                    None if status == "A" else status == "S",
                )
            )
            if status == "A" and successor not in seen:
                seen.add(successor)
                queue.append(successor)
    return tuple(rows), catalogue


def _synthesize(rows, catalogues):
    return synthesize_joint_factor_residual_world_model_v9(
        rows,
        catalogues,
        _LIBRARY,
        layout_domain=CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
        program_domain=CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
        support_domain=CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
        factor_domain=CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
        result_domain=CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
        minimum_reusable_factor_count=3,
    )


def test_joint_synthesis_has_no_scaffold_or_slot_input_and_discovers_both_classes():
    parameters = inspect.signature(
        synthesize_joint_factor_residual_world_model_v9
    ).parameters
    assert "scaffold_program" not in parameters
    assert "target_program" not in parameters
    assert "factor_slots" not in parameters
    rows = {}
    catalogues = {}
    for occurrence, seed in enumerate((549_101, 549_102, 549_103)):
        rows[occurrence], catalogues[occurrence] = _batch_occurrence(
            occurrence, seed
        )
    result = _synthesize(rows, catalogues)
    assert result["transfer_admitted"] is True
    assert result["factorable_reusable_count"] >= 3
    assert result["residual_schema_bound_count"] >= 1
    assert result["complete_target_program_synthesized_from_raw_observations"] is True
    assert result["v51_target_program_consumed"] is False
    assert result["shared_residual_scaffold_consumed"] is False
    assert result["predeclared_reusable_factor_slots_consumed"] is False
    assert result["caller_selected_target_columns"] == []


def test_incompatible_bitmask_domain_is_fully_synthesized_but_not_transferred():
    rows, catalogue = _ood_occurrence()
    result = _synthesize({0: rows}, {0: catalogue})
    assert result["status"] == "JOINT_PROGRAM_DISCOVERED_STRICT_OOD_NO_TRANSFER"
    assert result["transfer_admitted"] is False
    assert result["factorable_reusable_count"] == 2
    assert any(
        row["normalized_expression"][0] == "E13"
        for row in result["assignment_classifications"]
        if isinstance(row["normalized_expression"], list)
    )
