from pathlib import Path
import ast
from functools import lru_cache
import hashlib

from acfqp.construction_k7_anonymous_relational_factor_bank_independent_verifier_v148 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_anonymous_relational_factor_bank_verification_v148,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / ".tmp/exact-freeze"
MODULE = ROOT / "src/acfqp/construction_k7_anonymous_relational_factor_bank_independent_verifier_v148.py"


@lru_cache(maxsize=1)
def _freeze():
    return freeze_anonymous_relational_factor_bank_verification_v148(
        (FROZEN / "v148_anonymous_relational_factor_bank_campaign.json").read_bytes(),
        (FROZEN / "v148_anonymous_relational_factor_bank_preregistration.json").read_bytes(),
        (FROZEN / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (FROZEN / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
    )


def test_v148_verifier_has_no_v148_producer_import():
    forbidden = {
        "acfqp.construction_k7_anonymous_relational_factor_bank_campaign_v148",
        "acfqp.anonymous_relational_factor_bank_planning_campaign_core_v148",
        "acfqp.anonymous_relational_factor_bank_acquisition_v148",
        "acfqp.anonymous_relational_template_instantiator_v147",
    }
    imported = set()
    for node in ast.walk(ast.parse(MODULE.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not imported & forbidden


def test_v148_producer_free_verification_reconstructs_registered_claim():
    raw = _freeze()
    document = loads_canonical_json(raw)
    assert document[
        "producer_free_anonymous_constant_relation_and_coordinate_binding_reconstruction"
    ] is True
    assert document["producer_free_matched_candidate_and_stop_reconstruction"] is True
    assert document["producer_free_abstract_plan_support_reconstruction"] is True
    assert document[
        "registered_workload_sample_efficiency_improvement_independently_verified"
    ] is True
    assert document["verified_accounting"][
        "acquisition_labels_avoided_by_anonymous_relational_prior"
    ] == 48
    assert document["complete_world_model_claimed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v148_verification_bytes_when_frozen():
    raw = _freeze()
    if VERIFICATION_ID != "0" * 64:
        assert loads_canonical_json(raw)["verification_id"] == VERIFICATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
