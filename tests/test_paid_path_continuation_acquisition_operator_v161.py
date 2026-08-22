from pathlib import Path

from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
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
from acfqp.paid_path_continuation_acquisition_operator_v161 import (
    acquire_matched_paid_path_continuation_arms_v161,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v161_source_fallbacks_are_exact_and_positive_switch_saves_labels():
    bank = (FREEZE / "v146_anonymous_relational_factor_bank.json").read_bytes()
    verification = (
        FREEZE / "v146_anonymous_relational_factor_bank_verification.json"
    ).read_bytes()
    classifier = (
        FREEZE / "v161_paid_path_prefix_classifier_receipt.json"
    ).read_bytes()
    config = _config()
    modular_config = modular_routing_config_v128()
    modular_config["families"]["STOCHASTIC_MODULAR_ROUTING_HELD_OUT"][
        "maximum_acquisition_labels"
    ] = 2_048
    for builder, seed, current_config, positive in (
        (build_quaternary_relation_workflow_adapter_v153, 1_047_811, config, True),
        (build_relation_fanout_routing_adapter_v154, 1_047_821, config, False),
        (build_modular_routing_adapter_v128, 1_048_101, modular_config, False),
    ):
        adapter = builder(seed, current_config)
        arms = acquire_matched_paid_path_continuation_arms_v161(
            adapter, bank, verification, classifier, current_config
        )
        legacy = acquire_matched_anonymous_relational_factor_bank_arms_v148(
            adapter, bank, verification, current_config
        )
        for name in arms:
            document = arms[name]["document"]
            source = legacy[name]["document"]
            if positive:
                assert document["query_policy_decision"] == "RELATION_COVERAGE"
            else:
                assert document["query_policy_decision"] == "PATH_FIRST_SAFE_FALLBACK"
                assert document["source_v148_acquisition_id"] == source["acquisition_id"]
                assert document["ground_support_labels"] == source["ground_support_labels"]
                assert document["raw_transition_sha256"] == source["raw_transition_sha256"]
        if positive:
            assert (
                arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"][
                    "ground_support_labels"
                ]
                < legacy["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"][
                    "ground_support_labels"
                ]
            )
