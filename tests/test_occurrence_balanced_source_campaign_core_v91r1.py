from acfqp import occurrence_balanced_source_campaign_core_v91r1 as core


class _Executor:
    def __init__(self, max_workers):
        assert max_workers == 2

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def map(self, function, rows):
        return [function(row) for row in rows]


def _member(seed):
    episode = {
        "success": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "local_ground_support_labels": 2,
        "execution_steps": 1,
        "partial_planning_compute_events": 3,
        "relational_abstract_support_branch_evaluations": 4,
    }
    return {
        "schema": "acfqp.occurrence_balanced_source_member.v91r1",
        "member_id": str(seed) * 64,
        "common_partial_acquisition": {"ground_support_labels": 5},
        "source_evidence": {},
        "action_catalogue": [],
        "source_complete_episode": {"predecessor_v30_episode": episode},
        "partial_candidate": object(),
    }


def test_v91r1_core_aggregates_occurrence_balanced_joint_model(monkeypatch):
    monkeypatch.setattr(core, "ProcessPoolExecutor", _Executor)
    monkeypatch.setattr(core, "_member", lambda row: _member(row[1]))
    monkeypatch.setattr(
        core,
        "pool_reference_aligned_source_evidence_v65",
        lambda *_args, **_kwargs: {
            "source_member_count": 2,
            "reference_member_id": str(1) * 64,
            "every_original_source_evidence_replayed_before_alignment": True,
            "every_source_member_retained_exactly_once": True,
            "source_alignment_receipts": [
                {"graph_edit_score": 0},
                {"graph_edit_score": 1},
            ],
            "canonical_source_pool": {
                "pooled_raw_transition_row_count": 9,
            },
        },
    )
    monkeypatch.setattr(
        core,
        "run_occurrence_balanced_compiler_ready_acquisition_v66",
        lambda *_args, **_kwargs: {
            "query_schedule": {
                "query_count": 8,
                "occurrence_signature_bucket_count": 2,
                "outcome_tape_accessed_by_ranking": False,
            },
            "compiler_ready_acquisition": {
                "status": "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
                "stopped_physical_ground_support_labels": 6,
                "full_query_stream_ground_support_labels": 8,
                "terminal_candidate_derivation_compute_events": 10,
                "compiler_readiness_compute_events": 11,
                "retired_failed_proposal_count": 1,
            },
        },
    )
    monkeypatch.setattr(
        core,
        "compile_occurrence_balanced_model_v66",
        lambda *_args, **_kwargs: {
            "every_batch_exact_residual_expression_retained": True,
            "multiple_residual_proposals_jointly_compiled": True,
            "version_space_selection_compute_events": 12,
        },
    )
    config = {
        "source_family": "ANONYMOUS",
        "source_pool_seeds": (1, 2),
        "source_worker_count": 2,
        "required_source_member_count": 2,
        "generic_domains": {"layout": "layout"},
        "maximum_terminal_program_candidates_to_try": 8,
        "prequential_confidence_denominator": 4096,
        "offline_library_labels": 7,
    }
    result = core.build_occurrence_balanced_source_campaign_document_v91r1(
        config,
        "a" * 64,
        "b" * 64,
        "c" * 64,
        {},
        {},
        {},
        13,
    )
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"]["failed_candidate_retirement_count"] == 1
    assert result["target_execution_performed"] is False
    assert result["official_scalar_cost"] is None
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
