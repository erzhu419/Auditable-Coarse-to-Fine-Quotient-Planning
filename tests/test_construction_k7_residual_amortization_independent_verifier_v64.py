import ast
import copy
import os

import pytest

from acfqp import construction_k7_domain_registry_extension_v64 as domains
from acfqp.construction_k7_residual_amortization_campaign_v64 import (
    run_residual_amortization_campaign_v64,
)
from acfqp.construction_k7_residual_amortization_independent_verifier_v64 import (
    verify_residual_amortization_campaign_bytes_v64,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


pytestmark = pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_V64") != "1",
    reason="explicit frozen V64 campaign bytes",
)


def test_v64_independent_verifier_reconstructs_observed_amortization():
    campaign = run_residual_amortization_campaign_v64()
    result = loads_canonical_json(
        verify_residual_amortization_campaign_bytes_v64(campaign.canonical_bytes)
    )
    assert result["status"] == "PRODUCER_FREE_RESIDUAL_PRIOR_AMORTIZATION_VERIFIED"
    assert result["occurrence_count"] == 72
    assert result["observed_lifetime_label_saving_after_offline_tax"] >= 0
    assert result["official_execution_allowed"] is False


def test_v64_independent_verifier_rejects_resigned_lifetime_attack():
    document = run_residual_amortization_campaign_v64().to_document()
    forged = copy.deepcopy(document)
    forged["observed_lifetime_label_saving"] += 1
    payload = {key: value for key, value in forged.items() if key != "campaign_id"}
    forged["campaign_id"] = domains.extension_content_id_v64(
        domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_CAMPAIGN_V64_DOMAIN,
        payload,
    )
    with pytest.raises(Exception):
        verify_residual_amortization_campaign_bytes_v64(canonical_json_bytes(forged))


def test_v64_independent_verifier_has_no_producer_or_core_import():
    module = __import__(
        "acfqp.construction_k7_residual_amortization_independent_verifier_v64",
        fromlist=["x"],
    )
    tree = ast.parse(open(module.__file__, encoding="utf-8").read())
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert all("amortization_campaign_v64" not in name for name in imported)
    assert all("amortization_campaign_core_v64" not in name for name in imported)
