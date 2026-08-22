from acfqp.domains.stochastic_relation_keyed_workflow import (
    RelationKeyedWorkflowAction,
    RelationKeyedWorkflowStatus,
)
from acfqp.generic_ternary_relation_workflow_adapter_v152 import (
    build_ternary_relation_workflow_adapter_v152,
    ternary_relation_workflow_config_v152,
)


def test_v152_adapter_hides_three_key_relation_and_preserves_success_path():
    adapter = build_ternary_relation_workflow_adapter_v152(
        1_047_002, ternary_relation_workflow_config_v152()
    )
    assert len(adapter.actions(adapter.initial())) == 3
    assert len({rule.opaque_mode for rule in adapter.kernel.rules}) == 3
    assert all(rule.mode_increment not in action.fields for rule, action in zip(adapter.kernel.rules, adapter.catalogue))
    state = adapter.initial()
    while state.status is RelationKeyedWorkflowStatus.ACTIVE:
        key = next(
            index
            for index, rule in enumerate(adapter.kernel.rules)
            if rule.source_stage == state.stage and rule.mode_increment == 3
        )
        state = adapter.kernel.step(state, RelationKeyedWorkflowAction(key))[0].next_state
    assert state.status is RelationKeyedWorkflowStatus.SUCCESS
