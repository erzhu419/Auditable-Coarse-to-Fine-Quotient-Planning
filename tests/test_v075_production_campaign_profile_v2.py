from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_production_campaign_profile_v2 as profile


def test_exact_v2_profile_freezes_full_parallelism_without_reduction() -> None:
    value = profile.freeze_v075_production_campaign_profile_v2()
    document = value.to_document()

    assert type(value) is profile.V075ProductionCampaignProfileV2
    assert document["logical_occurrence_count"] == 15
    assert document["max_workers"] == 15
    assert (
        document["executor"]
        == "THREAD_POOL_OVER_ISOLATED_OCCURRENCE_IPC"
    )
    assert document["parallelism_axis"] == "LOGICAL_OCCURRENCE_ONLY"
    assert document["one_fresh_ipc_child_per_occurrence"] is True
    assert document["intra_occurrence_parallelism_allowed"] is False
    assert document["result_order"] == "IMMUTABLE_SCIENTIFIC_ORDER"
    assert document["scientific_ordinals"] == list(range(15))
    assert document["transport_ordinals"] == list(range(1, 16))
    assert document["per_occurrence_algorithm_changed"] is False
    assert document["accuracy_reduction_allowed"] is False
    assert document["statistical_threshold_reduction_allowed"] is False
    assert document["draw_cap_reduction_allowed"] is False
    assert document["evidence_omission_allowed"] is False
    assert document["target_execution_opened"] is False
    assert document["target_accessed"] is False
    assert document["official_execution_allowed"] is False
    assert json.loads(value.canonical_bytes) == document


def test_profile_bytes_replay_is_exact_and_unknown_fields_fail() -> None:
    value = profile.freeze_v075_production_campaign_profile_v2()
    assert (
        profile.verify_v075_production_campaign_profile_bytes_v2(
            value.canonical_bytes
        )
        == value
    )

    altered = value.to_document()
    altered["max_workers"] = 14
    with pytest.raises(
        profile.V075ProductionCampaignProfileV2InvariantViolation
    ):
        profile.verify_v075_production_campaign_profile_bytes_v2(
            canonical_json_bytes(altered)
        )

    unknown = value.to_document()
    unknown["caller_override"] = True
    with pytest.raises(
        profile.V075ProductionCampaignProfileV2InvariantViolation
    ):
        profile.verify_v075_production_campaign_profile_bytes_v2(
            canonical_json_bytes(unknown)
        )


def test_profile_is_factory_only_and_immutable() -> None:
    with pytest.raises(
        profile.V075ProductionCampaignProfileV2InvariantViolation
    ):
        profile.V075ProductionCampaignProfileV2(object())

    value = profile.freeze_v075_production_campaign_profile_v2()
    with pytest.raises(FrozenInstanceError):
        value._profile_id = "0" * 64  # type: ignore[misc]


def test_profile_leaf_has_no_downstream_v075_imports() -> None:
    source = Path(profile.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    assert imported == {
        "__future__",
        "dataclasses",
        "hashlib",
        "typing",
        "acfqp.phase3e_ids",
    }
    assert all(
        not name.startswith("acfqp.v075_")
        for name in imported
    )
