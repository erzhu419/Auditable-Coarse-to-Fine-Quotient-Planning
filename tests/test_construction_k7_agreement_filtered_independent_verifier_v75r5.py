import ast
import os
from pathlib import Path

import pytest

from acfqp.construction_k7_agreement_filtered_independent_verifier_v75r5 import (
    ConstructionK7AgreementFilteredIndependentVerifierV75R5Error,
    verify_agreement_filtered_campaign_bytes_v75r5,
)
from acfqp.phase3e_ids import loads_canonical_json


def test_v75r5_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(ConstructionK7AgreementFilteredIndependentVerifierV75R5Error):
        verify_agreement_filtered_campaign_bytes_v75r5(b"{}")


def test_v75r5_independent_verifier_import_surface_excludes_producer_algorithms():
    path = Path(
        "src/acfqp/construction_k7_agreement_filtered_independent_verifier_v75r5.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "construction_k7_agreement_filtered_campaign_v75r5",
        "agreement_filtered_priority_campaign_core_v75r5",
        "generic_portable_certificate_query_priority_v44",
        "generic_structural_rank_query_prior_v46",
        "generic_abstract_agreement_query_filter_v47",
    )
    assert not any(any(name in row for name in forbidden) for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_REUSABLE_V75R5") != "1",
    reason="explicit producer-free V75r5 reconstruction",
)
def test_v75r5_independent_verifier_reconstructs_frozen_campaign():
    from acfqp.construction_k7_agreement_filtered_campaign_v75r5 import (
        run_agreement_filtered_campaign_v75r5,
    )

    campaign = run_agreement_filtered_campaign_v75r5()
    verification = loads_canonical_json(
        verify_agreement_filtered_campaign_bytes_v75r5(campaign.canonical_bytes)
    )
    assert verification["target_certificate_episode_traces_replayed"] == 16
    assert verification["target_labels_by_arm"][
        "AGREEMENT_FILTERED_STRUCTURAL_RANK_AND_MODEL"
    ] == 138
    assert verification["operator_controls_priority_sample_tax_verified"] is True
    assert verification["filtered_matches_model_only_verified"] is True
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
