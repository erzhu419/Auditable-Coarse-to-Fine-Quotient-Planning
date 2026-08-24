from __future__ import annotations

from pathlib import Path

from acfqp.open_world_machine_compiled_model_v182 import (
    RawMachineTransitionV182,
    compile_machine_world_model_v182,
)
from acfqp.open_world_machine_planner_v182 import MachinePlannerSessionV182


ROOT = Path(__file__).resolve().parents[1]


def _rows() -> tuple[RawMachineTransitionV182, ...]:
    rows = []
    query = 0
    for countdown in range(5):
        for action in range(2):
            for residual in range(2):
                successor = (max(0, countdown - 1), action + 1, residual)
                rows.append(
                    RawMachineTransitionV182.observe(
                        occurrence_index=182001,
                        query_index=query,
                        state=(countdown, 0, 0),
                        action=(action,),
                        successor=successor,
                        terminal=successor[0] == 0,
                    )
                )
                query += 1
    return tuple(rows)


def _model():
    return compile_machine_world_model_v182(
        _rows(),
        maximum_enumeration_events_per_scalar=5_000,
        maximum_instruction_count=3,
        maximum_execution_steps=16,
        maximum_residual_support=2,
    )


def test_v182_compiler_discovers_layout_factors_programs_and_partial_support() -> None:
    model = _model()
    assert model.state_width == 3
    assert model.action_width == 1
    assert all(model.covers(row) for row in _rows())
    assert model.coordinates[0].synthesis.exact_on_all_rows is True
    assert model.coordinates[0].synthesis.read_dependencies == (("S", 0),)
    assert model.coordinates[1].synthesis.exact_on_all_rows is True
    assert model.coordinates[1].synthesis.read_dependencies == (("A", 0),)
    assert model.coordinates[2].synthesis.exact_on_all_rows is False
    assert model.coordinates[2].synthesis.residual_values == (0, 1)
    assert model.terminal_synthesis.exact_on_all_rows is True
    assert model.terminal_synthesis.read_dependencies == (("S", 0),)
    assert model.factor_boundaries == ((0,), (1,), (2,))
    document = model.to_document()
    assert document["layout_names_supplied"] is False
    assert document["domain_family_supplied"] is False
    assert document["finite_candidate_program_catalog_used"] is False


def test_v182_planner_consumes_only_compiled_model_and_reuses_rank_cache() -> None:
    model = _model()
    session = MachinePlannerSessionV182(
        model,
        legal_actions=((0,), (1,)),
        horizon=4,
    )
    first = session.certify((3, 0, 0))
    second = session.certify((3, 0, 0))
    assert first.certified is True
    assert first.terminal_distance_rank == 3
    assert first.selected_successor_rank_upper_bound == 2
    assert first.to_document()["ground_transition_argument_present"] is False
    assert second.certified is True
    assert second.persistent_cache_hit_count > 0
    assert session.cached_subproblem_count > 0


def test_v182_unseen_support_requires_a_local_distinction() -> None:
    model = _model()
    unseen = RawMachineTransitionV182.observe(
        occurrence_index=182002,
        query_index=0,
        state=(2, 0, 0),
        action=(0,),
        successor=(1, 1, 2),
        terminal=False,
    )
    assert model.covers(unseen) is False


def test_v182_compiler_and_planner_have_no_named_domain_adapter() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src" / "acfqp" / "open_world_machine_compiled_model_v182.py",
            ROOT / "src" / "acfqp" / "open_world_machine_planner_v182.py",
        )
    )
    assert "LMB" not in source
    assert "2048" not in source
    assert "MANIFEST_DOCUMENTS" not in source
    assert "transition_oracle" not in source
