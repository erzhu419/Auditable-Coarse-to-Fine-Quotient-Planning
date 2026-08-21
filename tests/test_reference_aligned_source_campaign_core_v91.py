import copy

from acfqp import reference_aligned_source_campaign_core_v91 as core


class _ImmediateExecutor:
    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def map(self, function, arguments):
        return [function(row) for row in arguments]


def _fake_member(args):
    seed = args[1]
    episode = {
        "success": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "local_ground_support_labels": 2,
        "execution_steps": 3,
        "partial_planning_compute_events": 5,
        "relational_abstract_support_branch_evaluations": 7,
    }
    return {
        "schema": "acfqp.reference_aligned_source_member.v91",
        "member_id": f"{seed:064x}",
        "source_seed": seed,
        "common_partial_acquisition": {"ground_support_labels": 11},
        "source_evidence": {"fixture": seed},
        "action_catalogue": [{"action_key": 0, "anonymous_fields": [1]}],
        "source_complete_episode": {"predecessor_v30_episode": episode},
        "partial_candidate": object(),
    }


def test_v91_core_aggregates_reference_aligned_joint_model(monkeypatch):
    monkeypatch.setattr(core, "ProcessPoolExecutor", _ImmediateExecutor)
    monkeypatch.setattr(core, "_member", _fake_member)
    monkeypatch.setattr(
        core,
        "pool_reference_aligned_source_evidence_v65",
        lambda members, **_kwargs: {
            "source_member_count": 2,
            "reference_member_id": members[0]["member_id"],
            "source_alignment_receipts": [
                {"graph_edit_score": 0},
                {"graph_edit_score": 2},
            ],
            "canonical_source_pool": {
                "pooled_raw_transition_row_count": 17,
            },
            "every_original_source_evidence_replayed_before_alignment": True,
            "every_source_member_retained_exactly_once": True,
        },
    )
    acquisition = {
        "compiler_ready_acquisition": {
            "status": "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
            "stopped_physical_ground_support_labels": 9,
            "full_query_stream_ground_support_labels": 12,
            "terminal_candidate_derivation_compute_events": 13,
            "compiler_readiness_compute_events": 17,
        }
    }
    monkeypatch.setattr(
        core,
        "run_relation_covering_compiler_ready_acquisition_v52",
        lambda *_args, **_kwargs: copy.deepcopy(acquisition),
    )
    monkeypatch.setattr(
        core,
        "compile_compiler_ready_model_v52",
        lambda *_args: {
            "every_batch_exact_residual_expression_retained": True,
            "multiple_residual_proposals_jointly_compiled": True,
            "version_space_selection_compute_events": 19,
        },
    )
    config = {
        "source_family": "ANONYMOUS_FIXTURE",
        "source_pool_seeds": (1, 2),
        "source_worker_count": 2,
        "required_source_member_count": 2,
        "generic_domains": {"layout": "unused"},
        "maximum_terminal_program_candidates_to_try": 8,
        "prequential_confidence_denominator": 64,
        "offline_library_labels": 23,
    }
    result = core.build_reference_aligned_source_campaign_document_v91(
        config,
        "a" * 64,
        "b" * 64,
        {},
        {},
        {},
        29,
    )
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"][
        "multiple_residual_proposals_jointly_compiled"
    ] is True
    assert result["registered_gate"][
        "finite_observation_color_mismatch_overcome_by_raw_reference_alignment"
    ] is True
    assert result["accounting"]["source_common_partial_labels"] == 22
    assert result["accounting"]["source_certificate_local_labels"] == 4
    assert result["accounting"]["target_labels"] == 0
    assert result["official_scalar_cost"] is None
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
