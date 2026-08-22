from acfqp.construction_k7_plan_mode_margin_independent_verifier_v157 import (
    _config,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import (
    build_quaternary_relation_workflow_adapter_v153,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
)
from acfqp.paid_path_prefix_query_classifier_core_v161 import (
    build_paid_path_prefix_trace_v161,
    evaluate_progressive_raw_prefix_expression_v160,
    feature_trace_v161,
    synthesize_progressive_raw_prefix_classifier_v160,
)


def test_v161_paid_path_prefix_derives_stable_classifier_without_sibling_tax():
    config = _config()
    modular_config = modular_routing_config_v128()
    labelled = []
    for builder, seeds, current_config, label in (
        (
            build_quaternary_relation_workflow_adapter_v153,
            range(1_047_811, 1_047_815),
            config,
            True,
        ),
        (
            build_relation_fanout_routing_adapter_v154,
            range(1_047_821, 1_047_825),
            config,
            False,
        ),
        (
            build_modular_routing_adapter_v128,
            range(1_048_101, 1_048_105),
            modular_config,
            False,
        ),
    ):
        for seed in seeds:
            trace = build_paid_path_prefix_trace_v161(
                builder(seed, current_config)
            )
            assert trace["path_first_generator_continuation_retained"] is True
            labelled.append((feature_trace_v161(trace), label))
    expression, _mdl, evaluated, separating = (
        synthesize_progressive_raw_prefix_classifier_v160(labelled)
    )
    assert expression["stable_prefix_observation_count"] == 7
    assert evaluated > 0
    assert separating > 0
    for trace, label in labelled:
        decision, _count = evaluate_progressive_raw_prefix_expression_v160(
            expression,
            trace[6],
            prefix_observation_count=7,
        )
        assert (decision == "RELATION_COVERAGE") is label
