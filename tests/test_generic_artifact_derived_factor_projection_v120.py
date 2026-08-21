from pathlib import Path

import pytest

from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
    verify_artifact_factor_projection_v120,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v120_derives_three_generic_templates_from_frozen_artifacts():
    library = derive_artifact_factor_projection_v120(_sources())
    replay = verify_artifact_factor_projection_v120(library, _sources())
    expressions = {
        str(row["normalized_expression"])
        for row in library["derived_subprograms"]
    }
    assert len(library["derived_subprograms"]) == 3
    assert str(["S", "SELF"]) in expressions
    assert str(["A", 0]) in expressions
    assert str(
        ["E07", ["S", "SELF"], ["E05", ["S", "SELF"], ["A", 0]]]
    ) in expressions
    assert replay["exact_artifact_reconstruction"] is True
    assert library["hand_written_factor_template_count"] == 0
    assert library["target_slot_inventory_supplied"] is False


def test_v120_derivation_rejects_changed_source_campaign_bytes():
    sources = _sources()
    changed = bytearray(sources["V118"])
    changed[len(changed) // 2] ^= 1
    sources["V118"] = bytes(changed)
    with pytest.raises(Exception):
        derive_artifact_factor_projection_v120(sources)
