from __future__ import annotations

from pathlib import Path

from acfqp import construction_k7_open_world_execution_preregistration_v181r2 as prereg


def test_v181r2_execution_is_frozen_before_fresh_target_queries() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r2().to_document()
    assert document["target_oracle_query_count"] == 0
    assert document["target_outcomes_accessed"] is False
    assert document["runner_frozen_before_target_outcome_access"] is True
    assert document["resource_cap_increased_relative_to_v181r1"] is False
    assert document["target_episode_denominator"] == 72


def test_v181r2_preregistration_rehashes_every_runner_source() -> None:
    document = prereg.freeze_open_world_execution_preregistration_v181r2().to_document()
    base = Path(prereg.__file__).resolve().parent
    assert len(document["frozen_source_facts"]) == len(prereg.SOURCE_FILENAMES)
    for row in document["frozen_source_facts"]:
        raw = (base / row["filename"]).read_bytes()
        import hashlib

        assert row["byte_count"] == len(raw)
        assert row["sha256"] == hashlib.sha256(raw).hexdigest()
    assert document["durable_checkpoint_after_every_acquisition_block"] is True
    assert document["official_execution_allowed"] is False
