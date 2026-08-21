import json
from pathlib import Path


def test_v102_family_aggregation_explains_v101_failure_without_erasing_it():
    document = json.loads(Path(".tmp/exact-freeze/v101_abstract_execution_utilization_campaign.json").read_bytes())
    balanced = [row for row in document["target_occurrences"] if row["target_family"] == "BALANCED_BATCH_REFINEMENT"]
    disagreements = sum(row["frozen_v100_sequence_wide_observation"]["sequence_wide_path_coverage"]["persistent_sequence_disagreement_abstention_count"] for row in balanced)
    accepts = sum(row["frozen_v100_sequence_wide_observation"]["sequence_wide_path_coverage"]["persistent_sequence_accept_count"] for row in balanced)
    assert disagreements > 0 and accepts > 0
    assert any(row["registered_gate"]["passed"] is False for row in balanced)
