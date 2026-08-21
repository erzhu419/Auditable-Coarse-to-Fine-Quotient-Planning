from pathlib import Path
import hashlib

from acfqp.auto_calibrated_archive_dictionary_v135 import (
    DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    derive_auto_calibrated_archive_dictionary_v135,
    freeze_auto_calibrated_archive_dictionary_v135,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v116_cross_epoch_program_branch_campaign.json",
    "v117_dependency_derived_program_branch_campaign.json",
    "v118_fourth_family_inventory_campaign.json",
    "v119_source_unseen_residual_campaign.json",
)


def _sources():
    return tuple((ROOT / name).read_bytes() for name in SOURCE_FILES)


def test_v135_source_only_objective_recovers_robust_three_factor_dictionary():
    document = derive_auto_calibrated_archive_dictionary_v135(_sources())
    assert document["support_thresholds_supplied_by_caller"] is False
    assert document["selected_minimum_distinct_artifact_support"] == 3
    assert document["selected_minimum_distinct_schema_pair_support"] == 2
    assert document["selected_template_count"] == 3
    assert document["selected_summed_weakest_leave_one_prefix_gain_bits"] == 4891
    assert document["target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None


def test_v135_frozen_dictionary_bytes_when_registered():
    raw = freeze_auto_calibrated_archive_dictionary_v135(_sources())
    document = loads_canonical_json(raw)
    if DICTIONARY_ID != "0" * 64:
        assert document["dictionary_id"] == DICTIONARY_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
