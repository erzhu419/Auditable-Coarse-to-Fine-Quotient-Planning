from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.generic_action_applicability_compiler_v58 import (
    applicable_action_keys_v58,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4


def test_v58_applicability_program_filters_anonymous_actions_by_state():
    program = load_action_applicability_model_v87()[
        "action_applicability_program"
    ]
    state = (0, 17, 8, 9001, 3, 14)
    actions = (
        FlatRawActionV4(6, (17, 1, 6, 1, 3)),
        FlatRawActionV4(8, (17, 1, 5, 1, 4)),
    )
    assert applicable_action_keys_v58(program, state, actions) == (6,)
