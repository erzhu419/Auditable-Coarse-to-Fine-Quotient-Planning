from pathlib import Path

from acfqp.construction_k7_plan_mode_margin_independent_verifier_v157 import (
    _config,
)
from acfqp.construction_k7_progressive_raw_prefix_classifier_receipt_freeze_v160 import (
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160,
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
from acfqp.progressive_raw_prefix_acquisition_operator_v160 import (
    prepare_progressive_raw_prefix_query_v160,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v160_paid_raw_prefix_selects_expected_source_query_policies():
    classifier = verify_frozen_progressive_raw_prefix_classifier_receipt_v160(
        (
            ROOT
            / ".tmp/exact-freeze/v160_progressive_raw_prefix_classifier_receipt.json"
        ).read_bytes()
    )
    config = _config()
    modular_config = modular_routing_config_v128()
    for builder, seed, current_config, decision in (
        (
            build_quaternary_relation_workflow_adapter_v153,
            1_047_811,
            config,
            "RELATION_COVERAGE",
        ),
        (
            build_relation_fanout_routing_adapter_v154,
            1_047_821,
            config,
            "PATH_FIRST_SAFE_FALLBACK",
        ),
        (
            build_modular_routing_adapter_v128,
            1_048_101,
            modular_config,
            "PATH_FIRST_SAFE_FALLBACK",
        ),
    ):
        prepared = prepare_progressive_raw_prefix_query_v160(
            builder(seed, current_config), classifier["selected_expression"]
        )
        assert prepared["decision_trace"][0]["decision"] == "CONTINUE"
        assert prepared["query_policy_decision"] == decision
        assert len(prepared["prefix_batches"]) == 2
