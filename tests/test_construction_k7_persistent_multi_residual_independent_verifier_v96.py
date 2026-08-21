import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_persistent_multi_residual_independent_verifier_v96 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json"
)


def _resign(document):
    for occurrence in document["target_occurrences"]:
        for key in (
            "meta_prior_persistent_sequence",
            "no_prior_persistent_sequence",
        ):
            sequence = occurrence[key]
            payload = {
                name: value for name, value in sequence.items() if name != "sequence_id"
            }
            sequence["sequence_id"] = verifier._generic_id(  # noqa: SLF001
                verifier._SEQUENCE_DOMAIN, payload  # noqa: SLF001
            )
        payload = {
            name: value
            for name, value in occurrence.items()
            if name != "occurrence_id"
        }
        occurrence["occurrence_id"] = verifier.domains.extension_content_id_v96(
            verifier.domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_OCCURRENCE_V96_DOMAIN,
            payload,
        )
    payload = {
        name: value for name, value in document.items() if name != "campaign_id"
    }
    document["campaign_id"] = verifier.domains.extension_content_id_v96(
        verifier.domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_CAMPAIGN_V96_DOMAIN,
        payload,
    )


def test_v96_independent_verifier_preserves_registered_failure():
    document = verifier.verify_persistent_multi_residual_campaign_bytes_v96(
        CAMPAIGN_PATH.read_bytes()
    )
    assert document["verification_status"] == (
        "REGISTERED_PERSISTENT_MULTI_RESIDUAL_GATE_FAILURE_VERIFIED"
    )
    assert document["verified_failure"]["meta_prior_lifetime_target_labels"] == 96
    assert document["verified_failure"]["strict_cold_direct_lifetime_target_labels"] == 174
    assert document["persistent_joint_residual_integration_verified"] is False


def test_v96_verification_is_producer_free_and_exact():
    raw = verifier.freeze_persistent_multi_residual_verification_v96(
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
            "persistent_multi_residual_campaign_v96",
            "persistent_multi_residual_campaign_core_v96",
            "generic_persistent_multi_residual_sequence_v96",
            "generic_multi_residual_certificate_planner_v26",
        )
    )


def test_v96_independent_semantics_reject_resigned_joint_claim():
    forged = copy.deepcopy(loads_canonical_json(CAMPAIGN_PATH.read_bytes()))
    forged["target_occurrences"][0]["meta_prior_persistent_sequence"][
        "retained_joint_proposal_count"
    ] = 2
    _resign(forged)
    with pytest.raises(
        verifier.ConstructionK7PersistentMultiResidualIndependentVerifierV96Error
    ):
        verifier._verify_campaign_document(forged)  # noqa: SLF001


def test_v96_independent_verifier_rejects_nonexact_bytes():
    with pytest.raises(
        verifier.ConstructionK7PersistentMultiResidualIndependentVerifierV96Error
    ):
        verifier.verify_persistent_multi_residual_campaign_bytes_v96(
            CAMPAIGN_PATH.read_bytes() + b"\n"
        )
