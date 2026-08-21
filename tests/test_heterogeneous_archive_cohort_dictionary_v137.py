from pathlib import Path
import hashlib

import pytest

from acfqp.heterogeneous_archive_cohort_dictionary_v137 import (
    DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_heterogeneous_archive_cohort_dictionary_v137,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v116_cross_epoch_program_branch_campaign.json",
    "v117_dependency_derived_program_branch_campaign.json",
    "v118_fourth_family_inventory_campaign.json",
    "v119_source_unseen_residual_campaign.json",
    "v134_packet_batching_transfer_campaign.json",
)


def _sources():
    return tuple((ROOT / name).read_bytes() for name in SOURCE_FILES)


@pytest.fixture(scope="module")
def frozen():
    raw = freeze_heterogeneous_archive_cohort_dictionary_v137(_sources())
    return raw, loads_canonical_json(raw)


def test_v137_records_incompatible_source_and_selects_maximal_coherent_cohort(frozen):
    _raw, document = frozen
    assert document["complete_source_archive_cardinality"] == 5
    assert document["selected_cohort_cardinality"] == 4
    assert len(document["excluded_archive_artifact_sha256s"]) == 1
    assert document["selected_template_count"] > 0
    assert document["maximal_cardinality_then_source_only_gain_selection"] is True
    assert document["incompatible_sources_recorded_not_silently_dropped"] is True
    assert document["source_aliases_or_family_names_used_for_cohort_selection"] is False
    assert document["target_outcomes_accessed"] is False
    assert document["official_scalar_cost"] is None


def test_v137_frozen_dictionary_bytes_when_registered():
    raw = (ROOT / "v137_heterogeneous_archive_cohort_dictionary.json").read_bytes()
    document = loads_canonical_json(raw)
    if DICTIONARY_ID != "0" * 64:
        assert document["dictionary_id"] == DICTIONARY_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
