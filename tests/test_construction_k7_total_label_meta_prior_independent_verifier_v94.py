import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_total_label_meta_prior_independent_verifier_v94 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v94_total_label_meta_prior_campaign.json"
)
VERIFICATION_PATH = Path(
    ".tmp/exact-freeze/v94_total_label_meta_prior_verification.json"
)


def test_v94_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(
        verifier.ConstructionK7TotalLabelMetaPriorIndependentVerifierV94Error
    ):
        verifier.verify_total_label_meta_prior_campaign_bytes_v94(b"{}")


def test_v94_independent_verifier_has_no_producer_core_or_v73_v75_import():
    source = Path(
        "src/acfqp/construction_k7_total_label_meta_prior_independent_verifier_v94.py"
    ).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden = {
        "acfqp.construction_k7_total_label_meta_prior_campaign_v94",
        "acfqp.total_label_meta_prior_campaign_core_v94",
        "acfqp.generic_low_label_residual_applicability_v73",
        "acfqp.generic_preloaded_certificate_receding_engine_v74",
        "acfqp.generic_total_label_residual_transfer_ablation_v75",
    }
    assert imported.isdisjoint(forbidden)


def test_v94_registered_reduction_is_independently_replayed():
    result = verifier.verify_total_label_meta_prior_campaign_bytes_v94(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(result)
    if verifier.VERIFICATION_ID != "0" * 64:
        assert result == VERIFICATION_PATH.read_bytes()
        assert document["verification_id"] == verifier.VERIFICATION_ID
        assert len(result) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(result).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["meta_prior_total_target_labels"] == 18
    assert document["no_prior_total_target_labels"] == 24
    assert document["strict_cold_direct_target_labels"] == 33
    assert document["sample_tax_reduction_verified_on_registered_target_workload"] is True
    assert document["sample_tax_reduction_generalized_beyond_registered_workload"] is False
    assert document[
        "source_meta_prior_only_stop_with_zero_target_predictive_confirmations_observed"
    ] is True
    assert document["official_execution_allowed"] is False


def test_v94_resigned_semantic_attack_is_rejected_before_replay():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    forged = copy.deepcopy(document)
    forged["registered_gate"][
        "meta_prior_total_labels_strictly_better_than_direct_in_aggregate"
    ] = False
    payload = {key: value for key, value in forged.items() if key != "campaign_id"}
    from acfqp import construction_k7_domain_registry_extension_v94 as domains

    forged["campaign_id"] = domains.extension_content_id_v94(
        domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_CAMPAIGN_V94_DOMAIN,
        payload,
    )
    raw = canonical_json_bytes(forged)
    with pytest.raises(
        verifier.ConstructionK7TotalLabelMetaPriorIndependentVerifierV94Error
    ):
        verifier.verify_total_label_meta_prior_campaign_bytes_v94(raw)
