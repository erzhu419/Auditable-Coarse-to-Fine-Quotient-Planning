from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)


def test_v144_maintenance_adapter_is_opaque_and_seeded():
    adapter = build_maintenance_cascade_adapter_v144(
        1_044_001, maintenance_cascade_config_v144()
    )
    state = adapter.initial()
    actions = adapter.actions(state)
    assert adapter.family == FAMILY
    assert actions
    assert len(adapter.encode(state)) == 10
    assert all(len(action.fields) == 6 for action in adapter.catalogue)
    outcome, tape = adapter.select_outcome(
        state, adapter.action_key(actions[0]), 0, 0
    )
    assert len(tape) == 64
    assert outcome.next_state != state
    assert adapter.kernel.rules[adapter.action_key(actions[0])].source_zone == 0


def test_v144_adapter_does_not_publish_generation_witness():
    adapter = build_maintenance_cascade_adapter_v144(
        1_044_002, maintenance_cascade_config_v144()
    )
    assert not hasattr(adapter, "generation_witness")
    assert not hasattr(adapter, "robust_task_path")
