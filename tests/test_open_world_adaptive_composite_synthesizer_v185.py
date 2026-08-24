from acfqp.open_world_adaptive_composite_synthesizer_v185 import (
    synthesize_adaptive_composite_scalar_v185,
)
from acfqp.open_world_universal_machine_v182 import MachineSynthesisRowV182


def test_v185_semantic_search_discovers_nested_rule_without_named_pattern() -> None:
    rows = tuple(
        MachineSynthesisRowV182(
            (x, y),
            (arrival,),
            max(x + arrival - y, 0),
        )
        for x, y, arrival in (
            (0, 0, 0),
            (0, 1, 1),
            (1, 0, 1),
            (1, 2, 0),
            (2, 1, 0),
            (2, 2, 1),
            (3, 0, 0),
            (3, 2, 1),
        )
    )
    result = synthesize_adaptive_composite_scalar_v185(
        rows,
        macro_library=None,
        maximum_macro_candidate_evaluations=0,
        maximum_fair_candidate_evaluations=10_000,
        resource_step_cap=64,
        register_count=6,
        maximum_residual_support=1,
    )
    assert result.residual_values == ()
    assert result.fair_fallback_used is True
    assert result.selected_macro_id is None
    assert result.to_document()["new_low_level_primitive_opcode_invented"] is False
