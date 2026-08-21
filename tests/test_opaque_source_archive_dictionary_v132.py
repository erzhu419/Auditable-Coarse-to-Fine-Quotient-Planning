from pathlib import Path
import hashlib

from acfqp.opaque_source_archive_dictionary_v132 import (
    DICTIONARY_ID,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    derive_opaque_source_archive_dictionary_v132,
    freeze_opaque_source_archive_dictionary_v132,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"
SOURCE_FILES = (
    "v116_cross_epoch_program_branch_campaign.json",
    "v117_dependency_derived_program_branch_campaign.json",
    "v118_fourth_family_inventory_campaign.json",
    "v119_source_unseen_residual_campaign.json",
)


def _source(files=SOURCE_FILES):
    return tuple((ROOT / name).read_bytes() for name in files)


def test_v132_opaque_archive_has_no_fixed_alias_or_cardinality_dependency():
    four = derive_opaque_source_archive_dictionary_v132(reversed(_source()))
    five = derive_opaque_source_archive_dictionary_v132(
        _source(("v115_projected_program_memo_campaign.json", *SOURCE_FILES))
    )
    four_signatures = [row["signature_sha256"] for row in four["selected_subprograms"]]
    five_signatures = [row["signature_sha256"] for row in five["selected_subprograms"]]
    assert four["source_archive_cardinality"] == 4
    assert five["source_archive_cardinality"] == 5
    assert four_signatures == five_signatures
    assert len(four_signatures) == 3
    assert four["source_aliases_or_version_names_consumed"] is False
    assert four["fixed_source_archive_cardinality_required_by_synthesizer"] is False
    assert all(
        holdout["eligible"]
        for row in four["support_and_leave_one_artifact_evidence"]
        if row["selected"]
        for holdout in row["leave_one_artifact_reconstructions"]
    )
    assert four["official_scalar_cost"] is None
    assert four["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v132_frozen_dictionary_bytes():
    raw = freeze_opaque_source_archive_dictionary_v132(_source())
    document = loads_canonical_json(raw)
    assert document["dictionary_id"] != "0" * 64
    if DICTIONARY_ID != "0" * 64:
        assert document["dictionary_id"] == DICTIONARY_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
