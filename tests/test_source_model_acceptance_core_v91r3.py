from acfqp import source_model_acceptance_core_v91r3 as core


def test_v91r3_accepts_complete_singleton_without_inventing_uncertainty(monkeypatch):
    model = {
        "joint_successor_version_space_model_id": "m" * 64,
        "residual_version_spaces": [
            {
                "batch_exact_candidate_count": 1,
                "batch_exact_candidate_frontier": [{}],
            }
        ],
        "every_batch_exact_residual_expression_retained": True,
    }
    monkeypatch.setattr(
        core, "verify_joint_successor_version_space_model_v42", lambda value: value
    )
    predecessor = {
        "schema": "acfqp.prior_only_occurrence_source_campaign.v91r2",
        "campaign_id": "c" * 64,
        "registered_gate": {
            "compiler_ready_heldout_validated": True,
            "joint_successor_model_compiled": True,
            "every_batch_exact_residual_expression_retained": True,
            "multiple_residual_proposals_jointly_compiled": False,
            "passed": False,
        },
        "reusable_joint_successor_version_space_model": model,
        "target_execution_performed": False,
    }
    result = core.build_source_model_acceptance_document_v91r3(
        predecessor,
        preregistration_id="p" * 64,
        v91r2_verification_id="v" * 64,
    )
    assert result["corrected_gate"]["passed"] is True
    assert result["observed_version_space_is_singleton"] is True
    assert result["synthetic_or_duplicate_uncertainty_inserted"] is False
    assert result["new_source_or_target_outcomes_executed"] is False
