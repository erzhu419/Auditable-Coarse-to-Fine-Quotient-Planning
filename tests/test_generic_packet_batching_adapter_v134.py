from fractions import Fraction

from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY,
    build_packet_batching_adapter_v134,
    packet_batching_config_v134,
)


def test_v134_packet_batching_is_a_fresh_opaque_stochastic_schema():
    adapter = build_packet_batching_adapter_v134(1_034_101, packet_batching_config_v134())
    assert adapter.family == FAMILY
    assert len(adapter.encode(adapter.initial())) == 12
    assert len(adapter.catalogue[0].fields) == 7
    state = adapter.initial()
    action = adapter.actions(state)[0]
    outcomes = adapter.kernel.step(state, action)
    assert len(outcomes) == 2
    assert sum((row.probability for row in outcomes), Fraction()) == 1
    assert len({row.next_state.delay for row in outcomes}) == 2


def test_v134_adapter_permutations_change_with_seed():
    config = packet_batching_config_v134()
    left = build_packet_batching_adapter_v134(1_034_101, config)
    right = build_packet_batching_adapter_v134(1_034_102, config)
    assert left.encode(left.initial()) != right.encode(right.initial())
    assert left.catalogue[0].fields != right.catalogue[0].fields
