from pathlib import Path
import ast
from functools import lru_cache
import hashlib

import pytest

from acfqp.construction_k7_certified_planner_abstention_independent_verifier_v150 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_certified_planner_abstention_verification_v150,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / ".tmp/exact-freeze"
MODULE = ROOT / "src/acfqp/construction_k7_certified_planner_abstention_independent_verifier_v150.py"


@lru_cache(maxsize=1)
def _freeze():
    return freeze_certified_planner_abstention_verification_v150(
        (FROZEN / "v150_certified_planner_abstention_campaign.json").read_bytes(),
        (FROZEN / "v150_certified_planner_abstention_preregistration.json").read_bytes(),
        (FROZEN / "v149_cross_domain_relational_bank_preregistration.json").read_bytes(),
        (FROZEN / "v149_cross_domain_relational_bank_failure.json").read_bytes(),
    )


def test_v150_verifier_has_no_v150_producer_or_core_import():
    forbidden = {
        "acfqp.construction_k7_certified_planner_abstention_campaign_v150",
        "acfqp.cross_domain_relational_factor_bank_campaign_core_v150",
        "acfqp.certified_planner_abstention_sequence_v150",
        "acfqp.cross_domain_relational_factor_bank_campaign_core_v149",
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


def test_v150_producer_free_verification_reconstructs_cross_domain_claim():
    document = loads_canonical_json(_freeze())
    assert document[
        "producer_free_anonymous_binding_and_relational_instantiation_reconstruction"
    ] is True
    assert document["producer_free_abstract_plan_support_reconstruction"] is True
    assert document[
        "registered_cross_domain_sample_efficiency_improvement_independently_verified"
    ] is True
    assert document["verified_accounting"][
        "acquisition_labels_avoided_by_anonymous_relational_prior"
    ] == 51
    assert all(
        value > 0 for value in document["verified_family_aggregate_reductions"].values()
    )
    assert document["complete_world_model_claimed"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v150_verifier_rejects_resigned_campaign_semantic_tamper():
    raw = (FROZEN / "v150_certified_planner_abstention_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    document["registered_gate"]["passed"] = False
    with pytest.raises(ValueError):
        freeze_certified_planner_abstention_verification_v150(
            canonical_json_bytes(document),
            (FROZEN / "v150_certified_planner_abstention_preregistration.json").read_bytes(),
            (FROZEN / "v149_cross_domain_relational_bank_preregistration.json").read_bytes(),
            (FROZEN / "v149_cross_domain_relational_bank_failure.json").read_bytes(),
        )


def test_v150_verification_bytes_when_frozen():
    raw = _freeze()
    if VERIFICATION_ID != "0" * 64:
        assert loads_canonical_json(raw)["verification_id"] == VERIFICATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
