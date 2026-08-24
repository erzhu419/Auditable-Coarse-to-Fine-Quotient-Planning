from acfqp.open_world_compiled_model_v181 import (
    CompiledCoordinateV181,
    CompiledWorldModelV181,
)
from acfqp.open_world_compiled_model_v181r5 import CompiledWorldModelV181R5
from acfqp.open_world_rank_decreasing_planner_v181r5 import (
    RankDecreasingPlannerSessionV181R5,
    certify_rank_decreasing_action_v181r5,
)


def _procrastination_model() -> CompiledWorldModelV181R5:
    coordinate = CompiledCoordinateV181(
        0,
        (
            "SELECT",
            ("EQ", ("A", 0), ("K", 0)),
            ("S", 0),
            ("K", 0),
        ),
        True,
        (0,),
        None,
        (("A", 0), ("S", 0)),
        5,
        1,
        False,
    )
    runtime = CompiledWorldModelV181(
        1,
        1,
        (coordinate,),
        ("EQ", ("S", 0), ("K", 0)),
        3,
        1,
        (("S", 0),),
        ((0,),),
        (),
        0,
        2,
        0,
        "a" * 64,
    )
    return CompiledWorldModelV181R5(
        runtime,
        "a" * 64,
        (),
        0,
        2,
        0,
        (2,),
    )


def test_v181r5_selects_the_strictly_rank_decreasing_action() -> None:
    model = _procrastination_model()
    certificate = certify_rank_decreasing_action_v181r5(
        model,
        state=(1,),
        legal_actions=((0,), (1,)),
        horizon=2,
    )
    assert certificate.certified is True
    assert certificate.selected_action == (1,)
    assert certificate.terminal_distance_rank == 1
    assert certificate.selected_successor_rank_upper_bound == 0
    assert certificate.strict_rank_decrease_proved is True
    assert certificate.persistent_model_bound_rank_cache_used is True
    assert certificate.to_document()["persistent_model_bound_rank_cache_used"] is True
    assert all(
        model.terminal(successor)
        for successor in model.predict_support((1,), certificate.selected_action)
    )


def test_v181r5_reuses_exact_rank_subproblems_for_the_same_model() -> None:
    session = RankDecreasingPlannerSessionV181R5(
        _procrastination_model(),
        legal_actions=((0,), (1,)),
        horizon=2,
    )
    first = session.certify((1,))
    cached_count = session.cached_subproblem_count
    second = session.certify((1,))
    assert first.selected_action == second.selected_action == (1,)
    assert cached_count > 0
    assert session.cached_subproblem_count == cached_count
    assert second.planning_compute_events == 1
