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
from acfqp.progressive_raw_prefix_query_classifier_core_v160 import (
    ANONYMOUS_RAW_DELTA_FEATURE_WIDTH_V160,
    build_progressive_raw_prefix_trace_v160,
    evaluate_progressive_raw_prefix_expression_v160,
    synthesize_progressive_raw_prefix_classifier_v160,
)


def _feature_trace(document):
    return tuple(
        tuple(tuple(row) for row in prefix["anonymous_raw_delta_feature_rows"])
        for prefix in document["prefixes"]
    )


def test_v160_generic_raw_prefix_grammar_separates_three_source_dynamics():
    config = _config()
    modular_config = modular_routing_config_v128()
    labelled = []
    documents = []
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
            document = build_progressive_raw_prefix_trace_v160(
                builder(seed, current_config)
            )
            documents.append(document)
            labelled.append((_feature_trace(document), label))
    expression, mdl, evaluated, separating = (
        synthesize_progressive_raw_prefix_classifier_v160(labelled)
    )
    assert expression["stable_prefix_observation_count"] == 2
    assert evaluated > 0
    assert separating > 0
    assert mdl
    for (trace, label), document in zip(labelled, documents):
        assert document["full_initial_action_frontier_required_for_decision"] is False
        assert all(
            len(row) == ANONYMOUS_RAW_DELTA_FEATURE_WIDTH_V160
            for prefix in trace
            for row in prefix
        )
        assert (
            evaluate_progressive_raw_prefix_expression_v160(
                expression,
                trace[0],
                prefix_observation_count=1,
            )[0]
            == "CONTINUE"
        )
        decision, _count = evaluate_progressive_raw_prefix_expression_v160(
            expression,
            trace[1],
            prefix_observation_count=2,
        )
        assert (decision == "RELATION_COVERAGE") is label
