import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_source_unseen_residual_independent_verifier_v119 as verifier


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v119_source_unseen_residual_campaign.json"
VERIFICATION = ROOT / ".tmp/exact-freeze/v119_source_unseen_residual_verification.json"


def test_v119_verifier_does_not_import_v119_producer_or_execution_modules():
    tree = ast.parse(Path(verifier.__file__).read_text())
    forbidden = (
        "source_unseen_residual_campaign_v119",
        "source_unseen_residual_campaign_core_v119",
        "source_unseen_residual_preregistration_v119",
        "generic_dual_budget_adapter_v119",
        "source_unseen_partial_acquisition_v119",
        "generic_genesis_authorized_program_branch_sequence_v119",
        "domains.stochastic_dual_budget_composition",
    )
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_v119_independent_replay_verifies_partial_pipeline_and_accounting():
    document = verifier.verify_source_unseen_residual_campaign_bytes_v119(
        CAMPAIGN.read_bytes()
    )
    assert document["registered_gate_independently_verified"] is True
    assert document["verified_accounting"]["partial_prior_acquisition_labels"] == 94
    assert document["verified_accounting"]["certificate_local_labels"] == 88
    assert document["verified_accounting"][
        "planning_compute_events_avoided_against_uncached"
    ] == 3152
    assert document["strict_complete_model_required_for_planning"] is False
    assert document["sample_efficiency_improvement_claimed"] is False


def test_v119_independent_verifier_rejects_changed_bytes():
    raw = bytearray(CAMPAIGN.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(
        verifier.ConstructionK7SourceUnseenResidualIndependentVerifierV119Error
    ):
        verifier.verify_source_unseen_residual_campaign_bytes_v119(bytes(raw))


def test_v119_independent_semantics_reject_resigned_authority_flip():
    document = verifier.loads_canonical_json(CAMPAIGN.read_bytes())
    row = document["target_occurrences"][0]
    row["strict_complete_model_required_for_planning"] = True
    payload = {key: value for key, value in row.items() if key != "occurrence_id"}
    row["occurrence_id"] = verifier.domains.extension_content_id_v119(
        verifier.domains.CONSTRUCTION_K7_SOURCE_UNSEEN_RESIDUAL_OCCURRENCE_V119_DOMAIN,
        payload,
    )
    with pytest.raises(
        verifier.ConstructionK7SourceUnseenResidualIndependentVerifierV119Error
    ):
        verifier._occurrence(
            row,
            verifier.FAMILY,
            verifier.TARGETS[0][1],
            verifier._v117_namespace(),
        )


@pytest.mark.skipif(
    verifier.VERIFICATION_ID == "0" * 64 or not VERIFICATION.exists(),
    reason="V119 independent verification has not been frozen",
)
def test_v119_exact_independent_verification_is_preserved():
    assert verifier.freeze_source_unseen_residual_verification_v119(
        CAMPAIGN.read_bytes()
    ) == VERIFICATION.read_bytes()
