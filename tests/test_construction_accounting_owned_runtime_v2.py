from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib

from acfqp import construction_accounting_owned_runtime_v1 as hook_v1
from acfqp import construction_accounting_owned_runtime_v2 as runtime_v2
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import h2_graph_transition_engine_v1 as engine
from acfqp.relational_graph_core_v1 import GraphTopologyV1


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:owned-causal-promotion-runtime-test:v2\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _kernel() -> engine.H2GraphKernelV1:
    return engine.H2GraphKernelV1(
        topology=GraphTopologyV1(
            4,
            ((0, 1), (0, 2), (1, 3), (2, 3)),
        ),
        rank_cap=6,
        horizon=2,
        spawn_law=((1, Fraction(99, 100)), (2, Fraction(1, 100))),
    )


def test_exact_12_instance_plan_materializes_stage_local_vectors() -> None:
    with runtime_v2.activate_owned_causal_promotion_accounting_v2(
        occurrence_id=_id("complete")
    ) as session:
        for index, stage in enumerate(
            runtime_v2.CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
        ):
            runtime_v2.enter_owned_causal_promotion_stage_v2(stage)
            if (
                stage
                is registry_v6.ConstructionStageKindV6
                .OPEN_INCREMENTAL_ACQUISITION
                and index == 4
            ):
                stream = engine.DeterministicH2GraphStreamV1(
                    kernel=_kernel(),
                    state=engine.H2GraphStateV1((1, 1, 2, 0)),
                    action=engine.H2GraphActionV1(0, 1, 0),
                    remaining_horizon=2,
                    seed=17,
                )
                for _ in range(25):
                    stream.draw()
            runtime_v2.exit_owned_causal_promotion_stage_v2(
                stage,
                output_bindings=((f"stage-{index}", _id(f"output-{index}")),),
            )
        result = runtime_v2.complete_owned_causal_promotion_occurrence_v2()

    assert result is not None
    assert session.is_terminal is True
    assert len(result.recorded_stages) == 12
    assert len(result.recorded_stages[0].work_vector.records) == 202
    assert all(
        len(row.work_vector.records) == 202
        for row in result.recorded_stages
    )
    assert Counter(
        row.stage_start.stage_kind.value for row in result.recorded_stages
    ) == {
        "PREOPEN_COMMON_PREFIX": 1,
        "INITIAL_ACQUISITION": 1,
        "INITIAL_MODEL_BUILD": 1,
        "FAILED_ABSTRACT_PREFIX": 1,
        "OPEN_INCREMENTAL_ACQUISITION": 3,
        "OPEN_CHECKPOINT_REPLANNING": 4,
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION": 1,
    }
    first_open = result.recorded_stages[4].work_vector.values
    assert first_open["acquisition.incremental_engine_ground_draws"] == 25
    assert first_open["acquisition.incremental_engine_random_word_calls"] >= 25
    assert len(result.recorded_stages[4].operation_events) == len(
        {
            event.operation_site_id
            for event in result.recorded_stages[4].operation_events
        }
    )
    assert result.to_document()["occurrence_work_vector_issued"] is False
    assert result.to_document()["shared_resource_fixed_point_complete"] is False


def test_inactive_successor_stage_gateway_is_noop() -> None:
    assert runtime_v2.owned_causal_promotion_accounting_active_v2() is False
    assert runtime_v2.enter_owned_causal_promotion_stage_v2(object()) is None
    assert runtime_v2.exit_owned_causal_promotion_stage_v2(object()) is None
    assert runtime_v2.complete_owned_causal_promotion_occurrence_v2() is None
    assert hook_v1.owned_accounting_active_v1() is False
