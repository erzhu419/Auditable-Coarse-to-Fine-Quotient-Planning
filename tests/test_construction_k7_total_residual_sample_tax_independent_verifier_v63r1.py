import ast
import copy
import os

import pytest

from acfqp import construction_k7_domain_registry_extension_v63r1 as domains
from acfqp.construction_k7_total_residual_sample_tax_campaign_v63r1 import (
    run_total_residual_sample_tax_campaign_v63r1,
)
from acfqp.construction_k7_total_residual_sample_tax_independent_verifier_v63r1 import (
    verify_total_residual_sample_tax_campaign_bytes_v63r1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


pytestmark = pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V63R1") != "1",
    reason="explicit frozen V63r1 campaign bytes",
)


def test_v63r1_independent_verifier_reconstructs_all_matched_acquisitions():
    campaign = run_total_residual_sample_tax_campaign_v63r1()
    result = loads_canonical_json(
        verify_total_residual_sample_tax_campaign_bytes_v63r1(
            campaign.canonical_bytes
        )
    )
    assert result["status"] == "PRODUCER_FREE_TOTAL_RESIDUAL_SAMPLE_TAX_VERIFIED"
    assert result["occurrence_count"] == 12
    assert result["target_residual_label_reduction"] > 0
    assert result["official_execution_allowed"] is False


def test_v63r1_independent_verifier_rejects_resigned_accounting_attack():
    document = run_total_residual_sample_tax_campaign_v63r1().to_document()
    forged = copy.deepcopy(document)
    forged["accounting"]["prior_residual_acquisition_target_labels"] += 1
    payload = {key: value for key, value in forged.items() if key != "campaign_id"}
    forged["campaign_id"] = domains.extension_content_id_v63r1(
        domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63R1_DOMAIN,
        payload,
    )
    with pytest.raises(Exception):
        verify_total_residual_sample_tax_campaign_bytes_v63r1(
            canonical_json_bytes(forged)
        )


def test_v63r1_independent_verifier_does_not_import_producer_or_core():
    module = __import__(
        "acfqp.construction_k7_total_residual_sample_tax_independent_verifier_v63r1",
        fromlist=["x"],
    )
    tree = ast.parse(open(module.__file__, encoding="utf-8").read())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert all("campaign_v63r1" not in name for name in imported)
    assert all("campaign_core_v63r1" not in name for name in imported)
