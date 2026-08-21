import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_post_dependency_independent_verifier_v97 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(".tmp/exact-freeze/v97_post_dependency_campaign.json")


def test_v97_independent_verifier_rederives_dependency_and_joint_gate():
    document = verifier.verify_post_dependency_campaign_bytes_v97(
        CAMPAIGN_PATH.read_bytes()
    )
    assert document["verification_status"] == (
        "REGISTERED_POST_DEPENDENCY_JOINT_SUCCESSOR_VERIFIED"
    )
    accounting = document["verified_accounting"]
    assert accounting["meta_prior_lifetime_target_labels"] == 210
    assert accounting["no_structure_prior_lifetime_target_labels"] == 210
    assert accounting["strict_cold_direct_lifetime_target_labels"] == 387
    assert accounting["fresh_post_dependency_candidate_count"] == 2
    assert accounting["post_dependency_abstract_plan_receipt_count"] == 48
    assert document[
        "structural_prior_sample_tax_advantage_over_same_synthesizer_verified"
    ] is False


def test_v97_frozen_verification_is_exact_and_producer_free():
    raw = verifier.freeze_post_dependency_verification_v97(
        CAMPAIGN_PATH.read_bytes()
    )
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert loads_canonical_json(raw)["verification_id"] == verifier.VERIFICATION_ID
    tree = ast.parse(Path(verifier.__file__).read_text())
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        forbidden in module
        for module in imports
        for forbidden in (
            "post_dependency_campaign_v97",
            "post_dependency_campaign_core_v97",
            "generic_post_dependency_residual_v97",
            "generic_persistent_post_dependency_sequence_v97",
            "generic_multi_residual_certificate_planner_v26",
        )
    )


def test_v97_independent_derivation_rejects_resigned_dependency_binding():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    forged = copy.deepcopy(document)
    sequence = forged["target_occurrences"][1]["meta_prior_persistent_sequence"]
    dependency = sequence["retained_post_dependency_acquisition"][
        "retrospective_post_dependency_candidates"
    ][0]
    dependency["driver_post_column"] += 1
    payload = {
        key: value for key, value in dependency.items() if key != "candidate_id"
    }
    dependency["candidate_id"] = verifier._generic_id(  # noqa: SLF001
        verifier._DEPENDENCY_CANDIDATE_DOMAIN, payload  # noqa: SLF001
    )
    with pytest.raises(
        verifier.ConstructionK7PostDependencyIndependentVerifierV97Error
    ):
        verifier._verify_campaign_document(forged)  # noqa: SLF001


def test_v97_independent_verifier_rejects_nonexact_bytes():
    with pytest.raises(
        verifier.ConstructionK7PostDependencyIndependentVerifierV97Error
    ):
        verifier.verify_post_dependency_campaign_bytes_v97(
            CAMPAIGN_PATH.read_bytes() + b"\n"
        )
