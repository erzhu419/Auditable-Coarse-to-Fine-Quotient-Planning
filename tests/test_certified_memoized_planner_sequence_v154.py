from pathlib import Path

from acfqp.certified_memoized_planner_sequence_v154 import (
    run_certified_memoized_planner_sequence_v154,
)
from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    acquire_matched_relation_coverage_arms_v153,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v154_sequence_consumes_memoized_plan_without_safety_upgrade():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_047_503, config)
    arms = acquire_matched_relation_coverage_arms_v153(
        adapter,
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        config,
    )
    arm = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    sequence = run_certified_memoized_planner_sequence_v154(
        adapter,
        arm["candidate"],
        arm["rows"],
        arm["document"]["ground_support_labels"],
        episode_indices=(651, 652),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    assert all(episode["success"] for episode in sequence["episodes"])
    assert sequence["v115_memoized_compiled_program_plan_receipts_consumed"] is True
    assert sequence["memoized_plan_used_only_for_ordering"] is True
    assert sequence["query_local_overlay_used_as_safety_authority"] is False
