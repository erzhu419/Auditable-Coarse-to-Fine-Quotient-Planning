from fractions import Fraction

from acfqp.domains.stochastic_reservoir_dispatch import (
    ReservoirDispatchStatus,
    generate_stochastic_reservoir_dispatch,
)
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY,
    build_reservoir_dispatch_adapter_v171,
    reservoir_dispatch_config_v171,
)


def test_v171_reservoir_kernel_has_robust_success_path_and_stochastic_support():
    kernel, evidence = generate_stochastic_reservoir_dispatch(
        basin_count=8, seed=1_059_799
    )
    state = kernel.initial_distribution()[0][1]
    for key in evidence.robust_conduit_path:
        outcomes = kernel.step(state, kernel.actions(state)[
            tuple(action.conduit for action in kernel.actions(state)).index(key)
        ])
        assert sum((row.probability for row in outcomes), Fraction()) == 1
        state = max(outcomes, key=lambda row: row.next_state.stress).next_state
    assert state.status is ReservoirDispatchStatus.SUCCESS


def test_v171_adapter_is_opaque_permuted_and_deterministic():
    config = reservoir_dispatch_config_v171()
    left = build_reservoir_dispatch_adapter_v171(1_059_799, config)
    right = build_reservoir_dispatch_adapter_v171(1_059_799, config)
    assert left.family == FAMILY
    assert left.catalogue == right.catalogue
    assert left.encode(left.initial()) == right.encode(right.initial())
    assert len(left.encode(left.initial())) == 13
    assert all(len(action.fields) == 8 for action in left.catalogue)
