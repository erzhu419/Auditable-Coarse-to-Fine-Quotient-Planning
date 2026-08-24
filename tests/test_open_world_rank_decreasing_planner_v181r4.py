from acfqp.open_world_compiled_model_v181 import (
    CompiledCoordinateV181,
    CompiledWorldModelV181,
)
from acfqp.open_world_compiled_model_v181r3 import (
    CompiledWorldModelV181R3,
    certify_receding_action_v181r3,
)
from acfqp.open_world_rank_decreasing_planner_v181r4 import (
    certify_rank_decreasing_action_v181r4,
)


def _procrastination_model() -> CompiledWorldModelV181R3:
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
    return CompiledWorldModelV181R3(
        runtime,
        "a" * 64,
        (),
        0,
        2,
        0,
        (2,),
    )


def test_v181r3_first_winning_action_can_procrastinate() -> None:
    certificate = certify_receding_action_v181r3(
        _procrastination_model(),
        state=(1,),
        legal_actions=((0,), (1,)),
        horizon=2,
    )
    assert certificate.certified is True
    assert certificate.selected_action == (0,)
    assert _procrastination_model().predict_support((1,), certificate.selected_action) == ((1,),)


def test_v181r4_selects_the_strictly_rank_decreasing_action() -> None:
    model = _procrastination_model()
    certificate = certify_rank_decreasing_action_v181r4(
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
    assert all(
        model.terminal(successor)
        for successor in model.predict_support((1,), certificate.selected_action)
    )
