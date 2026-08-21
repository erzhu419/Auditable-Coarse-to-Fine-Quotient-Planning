from pathlib import Path
import ast
import hashlib

import pytest

from acfqp.construction_k7_fair_unified_factor_prior_ablation_independent_verifier_v129r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_fair_unified_factor_prior_ablation_verification_v129r1,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    names = {
        "v128_campaign": "v128_third_family_owned_sequence_campaign.json",
        "v128_verification": "v128_third_family_owned_sequence_verification.json",
        "v127_campaign": "v127_owned_sequence_cross_family_campaign.json",
        "v127_verification": "v127_owned_sequence_cross_family_verification.json",
        "v126_campaign": "v126_standalone_generic_owned_campaign.json",
        "v126_verification": "v126_standalone_generic_owned_verification.json",
        "v125_campaign": "v125_standalone_generic_model_campaign.json",
        "v125_verification": "v125_standalone_generic_model_verification.json",
        "v124_campaign": "v124_cross_family_generic_compiler_campaign.json",
        "v124_verification": "v124_cross_family_generic_compiler_verification.json",
        "v123r1_campaign": "v123r1_generic_quotient_compiler_campaign.json",
        "v123r1_verification": "v123r1_generic_quotient_compiler_verification.json",
        "v122_campaign": "v122_generic_factor_planner_campaign.json",
        "v122_verification": "v122_generic_factor_planner_verification.json",
        "failed_v123": "v123_generic_quotient_compiler_failure.json",
        "v121r1_campaign": "v121r1_generic_subprogram_campaign.json",
        "v121_failed_campaign": "v121_generic_artifact_subprogram_campaign.json",
        "v121r1_verification": "v121r1_generic_subprogram_verification.json",
        "failed_v129": "v129_unified_factor_prior_ablation_failure.json",
    }
    return (
        (ROOT / "v129r1_fair_unified_factor_prior_ablation_campaign.json").read_bytes(),
        {key: (ROOT / name).read_bytes() for key, name in names.items()},
        source,
    )


def test_v129r1_producer_free_rebuilds_acquisition_models_receipts_and_plans():
    raw = freeze_fair_unified_factor_prior_ablation_verification_v129r1(*_inputs())
    document = loads_canonical_json(raw)
    assert document[
        "registered_workload_sample_efficiency_improvement_independently_verified"
    ] is True
    assert document["producer_free_fair_path_first_batch_reconstruction"] is True
    assert document["producer_free_per_label_candidate_and_stop_reconstruction"] is True
    assert sum(row["labels_avoided"] for row in document["verified_occurrences"]) == 17
    assert sum(
        arm["model_epoch_count"]
        for row in document["verified_occurrences"]
        for arm in (row["factor_prior_sequence"], row["strict_no_prior_sequence"])
    ) == 72
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v129r1_verifier_import_surface_excludes_v129r1_producers():
    path = (
        Path(__file__).resolve().parents[1]
        / "src/acfqp/construction_k7_fair_unified_factor_prior_ablation_independent_verifier_v129r1.py"
    )
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = (
        "construction_k7_fair_unified_factor_prior_ablation_campaign_v129r1",
        "fair_unified_factor_prior_ablation_campaign_core_v129r1",
        "fair_unified_factor_prior_ablation_acquisition_v129r1",
        "standalone_generic_owned_sequence_v126",
    )
    assert not any(
        name.endswith(suffix) for name in imported for suffix in forbidden
    )


@pytest.mark.skipif(VERIFICATION_ID == "0" * 64, reason="V129r1 verification is not frozen")
def test_v129r1_frozen_verification_bytes():
    raw = (
        ROOT / "v129r1_fair_unified_factor_prior_ablation_verification.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
