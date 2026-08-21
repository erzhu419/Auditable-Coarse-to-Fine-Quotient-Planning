from pathlib import Path
import hashlib

import pytest

from acfqp.occurrence_factor_bank_v139 import (
    BANK_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_occurrence_factor_bank_v139,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v134_packet_batching_transfer_campaign.json",
    "v136_auto_calibrated_archive_planning_campaign.json",
    "v138_heterogeneous_cohort_planning_campaign.json",
)


def _sources():
    return tuple((ROOT / name).read_bytes() for name in SOURCE_FILES)


@pytest.fixture(scope="module")
def frozen():
    raw = freeze_occurrence_factor_bank_v139(_sources())
    return raw, loads_canonical_json(raw)


def test_v139_decodes_robust_candidates_at_occurrence_granularity(frozen):
    _raw, document = frozen
    assert document["source_occurrence_archive_cardinality"] == 12
    assert document["selected_minimum_distinct_occurrence_support"] == 7
    assert document["selected_template_count"] == 5
    assert document["selected_cross_schema_template_count"] == 5
    assert document["selected_structural_schema_pair_template_count"] == 0
    assert document["robust_candidate_schema_decoded"] is True
    assert document["occurrence_support_not_campaign_container_support"] is True
    assert document["semantic_family_names_used_for_selection"] is False
    assert document["new_target_occurrences_accessed"] is False
    assert document["new_target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None


@pytest.mark.skipif(BANK_ID == "0" * 64, reason="V139 bank not frozen")
def test_v139_frozen_bank_bytes_when_registered():
    raw = (ROOT / "v139_occurrence_factor_bank.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["bank_id"] == BANK_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
