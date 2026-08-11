from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_multiquery_campaign_v1 as subject
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.accounting_v1 import SHARED_AXES
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def multiquery_campaign(tmp_path_factory):
    source = source_v1.run_heldout_checkpoint_recertification_v1()
    directory = tmp_path_factory.mktemp("heldout-multiquery") / "campaign"
    original_solve = robust.solve_quotient_robust_h2_v1
    solve_boundaries: list[bool] = []

    def counted_solve(*args, **kwargs):
        solve_boundaries.append(
            (directory / subject.PREREGISTRATION_FILENAME).is_file()
        )
        return original_solve(*args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("fresh multiquery campaign attempted ground access")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(robust, "solve_quotient_robust_h2_v1", counted_solve)
    patcher.setattr(acquisition, "open_graph_partial_support_prefix_v1", forbidden)
    patcher.setattr(observer, "open_target_local_transition_stream_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    patcher.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    try:
        result = subject.run_heldout_multiquery_campaign_v1(
            source,
            occurrence_specs=(
                (_id("heldout-multiquery-occurrence-a-v1"), 5),
                (_id("heldout-multiquery-occurrence-b-v1"), 6),
            ),
            campaign_directory=directory,
        )
        yield result, directory, tuple(solve_boundaries)
    finally:
        patcher.undo()


def test_domains_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7HeldoutMultiqueryCampaignV1Error",
        "EXPECTED_OCCURRENCE_COUNT",
        "HeldoutMultiqueryCampaignClosureV1",
        "HeldoutMultiqueryCampaignFileCommitV1",
        "HeldoutMultiqueryCampaignOccurrenceRowV1",
        "HeldoutMultiqueryCampaignPreregistrationV1",
        "HeldoutMultiqueryCampaignResultV1",
        "LOCAL_DOMAINS",
        "run_heldout_multiquery_campaign_v1",
        "verify_heldout_multiquery_campaign_v1",
    }


def test_query_specs_precede_exactly_two_owner_accounted_planner_calls(
    multiquery_campaign,
) -> None:
    result, directory, solve_boundaries = multiquery_campaign
    preregistration = result.preregistration.to_document()
    assert preregistration["all_query_specs_frozen_before_preregistration"] is True
    assert preregistration["fresh_query_planner_invocations_before_preregistration"] == 0
    assert sum(solve_boundaries) == 2
    assert solve_boundaries[-2:] == (True, True)
    assert (directory / subject.PREREGISTRATION_FILENAME).is_file()
    assert result.closure.to_document()[
        "fresh_owner_accounted_planner_invocation_count"
    ] == 2
    assert result.closure.to_document()[
        "accounting_planner_replay_invocation_count"
    ] == 0


def test_one_query_neutral_model_serves_two_distinct_fresh_occurrences(
    multiquery_campaign,
) -> None:
    result, _directory, _calls = multiquery_campaign
    reuses = tuple(row.reuse_result for row in result.rows)
    assert len({row.query.logical_occurrence_id for row in reuses}) == 2
    assert len({row.query.query_id for row in reuses}) == 2
    assert len({row.plan.plan_id for row in reuses}) == 2
    assert len({row.result_id for row in reuses}) == 2
    assert len({row.query.source_overlay_id for row in reuses}) == 1
    assert len({row.query.quotient_model_id for row in reuses}) == 1
    assert len({row.plan.audit.audit_id for row in reuses}) == 1
    assert all(row.plan.audit.certified for row in reuses)


def test_both_occurrences_have_complete_zero_ground_accounting(
    multiquery_campaign,
) -> None:
    result, directory, _calls = multiquery_campaign
    for index, row in enumerate(result.rows, start=1):
        values = row.occurrence_bundle.work_vector.values
        assert values["common.abstract_audit_obligations"] == 1
        assert values["common.abstract_bellman_backups"] > 0
        assert dict(row.occurrence_bundle.comparison_vector.values)[
            "kernel_transition_calls"
        ] == 0
        assert all(
            value == 0
            for path, value in values.items()
            if path.startswith(("local.", "fallback.", "rebuild."))
        )
        assert len(tuple((directory / f"occurrence-{index:04d}").glob("*.json"))) == 8
        assert row.to_document()["fresh_ground_or_observer_event_count"] == 0
        assert row.to_document()["accounting_planner_replay_invocations"] == 0


def test_two_rows_close_all_denominators_and_vector_sum(
    multiquery_campaign,
) -> None:
    result, _directory, _calls = multiquery_campaign
    closure = result.closure.to_document()
    assert closure["registered_logical_occurrence_count"] == 2
    assert closure["closed_logical_occurrence_count"] == 2
    assert closure["closure_denominator"] == 2
    assert closure["certificate_coverage_denominator"] == 2
    assert closure["future_economics_cost_denominator"] == 2
    assert closure["plan_certificate_count"] == 2
    assert closure["noncertificate_count"] == 0
    expected = tuple(
        (
            axis,
            sum(
                dict(row.occurrence_bundle.comparison_vector.values)[axis]
                for row in result.rows
            ),
        )
        for axis in SHARED_AXES
    )
    assert result.closure.cumulative_comparison_values == expected
    assert result.to_document()["single_query_neutral_overlay_reused"] is True
    assert result.to_document()[
        "fresh_planner_execution_accounted_without_replay"
    ] is True


def test_campaign_files_and_typed_replay_are_complete(
    multiquery_campaign,
) -> None:
    result, directory, _calls = multiquery_campaign
    assert result.result_id == result.to_document()[
        "heldout_multiquery_campaign_result_id"
    ]
    for commit in result.file_commits:
        raw = (directory / commit.filename).read_bytes()
        assert len(raw) == commit.byte_count
        assert hashlib.sha256(raw).hexdigest() == commit.bytes_sha256


def test_closure_vector_mutation_is_rejected(multiquery_campaign) -> None:
    result, _directory, _calls = multiquery_campaign
    original = result.closure.cumulative_comparison_values
    changed = ((original[0][0], original[0][1] + 1), *original[1:])
    try:
        object.__setattr__(result.closure, "cumulative_comparison_values", changed)
        with pytest.raises(subject.ConstructionK7HeldoutMultiqueryCampaignV1Error):
            subject.verify_heldout_multiquery_campaign_v1(result)
    finally:
        object.__setattr__(result.closure, "cumulative_comparison_values", original)
