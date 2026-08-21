from acfqp import prior_only_occurrence_source_campaign_core_v91r2 as core


def test_v91r2_member_uses_no_strict_complete_model_arm(monkeypatch):
    adapter = type(
        "Adapter",
        (),
        {"catalogue": (), "family": "X", "seed": 1},
    )()
    monkeypatch.setattr(
        core.v59.predecessor.predecessor.prior_ground,
        "_adapter",
        lambda *_args: adapter,
    )
    candidate = object()
    monkeypatch.setattr(
        core,
        "acquire_prior_only_partial_candidate_v67",
        lambda *_args, **_kwargs: {
            "document": {
                "strict_no_prior_arm_executed": False,
                "ground_support_labels": 3,
            },
            "candidate": candidate,
            "rows": (),
        },
    )
    monkeypatch.setattr(
        core,
        "run_source_complete_relational_world_model_episode_v31",
        lambda *_args, **_kwargs: {
            "terminal_program_source_evidence": {},
        },
    )
    config = {
        "source_partial_acquisition_maximum_ground_labels": 160,
        "global_alpha_denominator": 64,
        "minimum_reusable_factor_count": 3,
        "generic_domains": {"layout": "layout"},
        "source_episode_index": 0,
        "maximum_abstract_depth": 2,
        "maximum_execution_steps": 3,
        "residual_confidence_denominator": 64,
        "maximum_terminal_program_candidates_to_try": 8,
        "maximum_relational_support_branch_evaluations": 100,
        "relational_support_feasible_beam_width": 2,
    }
    result = core._member(("X", 1, {}, {}, config))  # noqa: SLF001
    assert result["partial_candidate"] is candidate
    assert result["strict_no_prior_arm_executed_for_source_member"] is False
    assert result["sample_tax_comparison_claimed_for_source_member"] is False
