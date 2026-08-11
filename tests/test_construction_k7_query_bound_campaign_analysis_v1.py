from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_campaign_analysis_v1 as subject
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.accounting_v1 import ReducerEnum, SHARED_AXES
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-campaign-analysis-test:v1\x00" + label.encode()
    ).hexdigest()


def test_public_surface_and_domains_freeze_retrospective_boundary() -> None:
    assert set(subject.__all__) == {
        "ANALYSIS_MODE",
        "ConstructionK7QueryBoundCampaignAnalysisV1Error",
        "MAX_EXPLICIT_PERMUTATIONS",
        "QueryBoundCampaignAnalysisSpecV1",
        "QueryBoundCampaignAnalysisV1",
        "QueryBoundCampaignOccurrenceRowV1",
        "QueryBoundCampaignVectorPrefixV1",
        "analyze_query_bound_campaign_bundles_v1",
        "freeze_query_bound_campaign_analysis_spec_v1",
        "verify_query_bound_campaign_analysis_v1",
    }
    assert subject.ANALYSIS_MODE == "RETROSPECTIVE_ACCOUNTING_ONLY_NOT_PREREGISTERED"
    assert {
        subject.SPEC_DOMAIN,
        subject.ROW_DOMAIN,
        subject.PREFIX_DOMAIN,
        subject.ANALYSIS_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_analysis_spec_rejects_singletons_duplicates_and_incomplete_enumeration() -> None:
    first = "1" * 64
    second = "2" * 64
    spec = subject.freeze_query_bound_campaign_analysis_spec_v1(
        ordered_occurrence_ids=(first, second), permutation_cap=2
    )
    document = spec.to_document()
    assert document["campaign_preregistration_present"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["scalar_gate_status"] == "NOT_RUN"
    with pytest.raises(subject.ConstructionK7QueryBoundCampaignAnalysisV1Error):
        subject.freeze_query_bound_campaign_analysis_spec_v1(
            ordered_occurrence_ids=(first,), permutation_cap=1
        )
    with pytest.raises(subject.ConstructionK7QueryBoundCampaignAnalysisV1Error):
        subject.freeze_query_bound_campaign_analysis_spec_v1(
            ordered_occurrence_ids=(first, first), permutation_cap=2
        )
    with pytest.raises(subject.ConstructionK7QueryBoundCampaignAnalysisV1Error):
        subject.freeze_query_bound_campaign_analysis_spec_v1(
            ordered_occurrence_ids=(first, second), permutation_cap=1
        )


def test_campaign_result_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundCampaignAnalysisV1Error):
        subject.verify_query_bound_campaign_analysis_v1(
            object(),  # type: ignore[arg-type]
            spec=object(),  # type: ignore[arg-type]
            bundle_directories=(),
        )


def test_analysis_does_not_rebaseline_a_tampered_frozen_spec() -> None:
    spec = subject.freeze_query_bound_campaign_analysis_spec_v1(
        ordered_occurrence_ids=("1" * 64, "2" * 64),
        permutation_cap=2,
    )
    object.__setattr__(spec, "ordered_occurrence_ids", ("2" * 64, "1" * 64))
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignAnalysisV1Error,
        match="changed after issuance",
    ):
        subject.analyze_query_bound_campaign_bundles_v1(
            spec,
            bundle_directories=(),
        )


def test_prefix_mechanics_use_sum_for_traffic_and_max_for_capacity() -> None:
    occurrence_ids = (_id("occurrence-1"), _id("occurrence-2"))
    spec = subject.freeze_query_bound_campaign_analysis_spec_v1(
        ordered_occurrence_ids=occurrence_ids,
        permutation_cap=2,
    )
    common = {
        "campaign_analysis_spec_id": spec.spec_id,
        "runtime_preparation_id": _id("runtime-preparation"),
        "runtime_tree_id": _id("runtime-tree"),
        "source_closure_id": _id("source-closure"),
        "source_trace_sha256": _id("source-trace"),
        "build_epoch_envelope_sha256": _id("build-epoch"),
        "output_bytes": 1,
        "role_digests": tuple(
            (role, _id(f"role-{role}")) for role in bundle_v1.ROLE_ORDER
        ),
    }
    rows = tuple(
        subject.QueryBoundCampaignOccurrenceRowV1(
            subject._ROW_ISSUER,
            common["campaign_analysis_spec_id"],
            index,
            occurrence_id,
            _id(f"verification-{index}"),
            _id(f"trace-{index}"),
            _id(f"measurement-{index}"),
            _id(f"receipt-set-{index}"),
            common["runtime_preparation_id"],
            common["runtime_tree_id"],
            common["source_closure_id"],
            common["source_trace_sha256"],
            common["build_epoch_envelope_sha256"],
            tuple(_id(f"work-{index}-{offset}") for offset in range(3)),
            tuple(_id(f"comparison-{index}-{offset}") for offset in range(3)),
            tuple(_id(f"proof-{index}-{offset}") for offset in range(3)),
            tuple((axis, index * 10 + offset) for offset, axis in enumerate(SHARED_AXES)),
            common["output_bytes"],
            common["role_digests"],
        )
        for index, occurrence_id in enumerate(occurrence_ids, start=1)
    )
    prefixes = subject._prefixes(spec, rows)
    final_rows = tuple(row for row in prefixes if row.prefix_length == 2)
    assert len(prefixes) == 4
    assert len(final_rows) == 2
    assert final_rows[0].values == final_rows[1].values
    profile = registry_v6.official_comparison_profile_v6(
        registry_v6.official_counter_registry_v6()
    )
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    first = dict(rows[0].aggregate_values)
    second = dict(rows[1].aggregate_values)
    expected = tuple(
        (
            axis,
            first[axis] + second[axis]
            if reducers[axis] is ReducerEnum.SUM
            else max(first[axis], second[axis]),
        )
        for axis in SHARED_AXES
    )
    assert final_rows[0].values == expected


@pytest.fixture(scope="module")
def real_campaign_analysis():
    supplied = os.environ.get("ACFQP_QUERY_BOUND_CAMPAIGN_BUNDLES")
    if not supplied:
        pytest.skip("set ACFQP_QUERY_BOUND_CAMPAIGN_BUNDLES to two bundle directories")
    directories = tuple(Path(value) for value in supplied.split(os.pathsep) if value)
    if len(directories) < 2:
        pytest.fail("campaign analysis requires at least two bundle directories")
    verifications = tuple(
        bundle_v1.verify_query_bound_complete_bundle_directory_v1(directory)
        for directory in directories
    )
    spec = subject.freeze_query_bound_campaign_analysis_spec_v1(
        ordered_occurrence_ids=tuple(row.occurrence_id for row in verifications),
        permutation_cap=subject.MAX_EXPLICIT_PERMUTATIONS,
    )
    result = subject.analyze_query_bound_campaign_bundles_v1(
        spec,
        bundle_directories=directories,
    )
    return result, spec, directories


def test_real_multioccurrence_analysis_closes_vector_prefixes_only(
    real_campaign_analysis,
) -> None:
    result, spec, directories = real_campaign_analysis
    verified = subject.verify_query_bound_campaign_analysis_v1(
        result,
        spec=spec,
        bundle_directories=directories,
    )
    count = len(spec.ordered_occurrence_ids)
    document = verified.to_document()
    assert len(verified.rows) == count
    assert len(verified.prefixes) == document["enumerated_order_count"] * count
    assert all(tuple(axis for axis, _value in row.values) == SHARED_AXES for row in verified.prefixes)
    assert document["all_occurrence_accounting_bundles_independently_replayed"] is True
    assert document["scientific_planner_recomputed_by_campaign"] is False
    assert document["source_bytes_embedded_or_externally_anchored"] is False
    assert document["accounting_campaign_analysis_only"] is True
    assert document["campaign_preregistration_present"] is False
    assert document["scientific_campaign_closure_issued"] is False
    assert document["certificate_coverage_gate_status"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_real_analysis_rejects_duplicate_bundle_substitution(
    real_campaign_analysis,
) -> None:
    _result, spec, directories = real_campaign_analysis
    attacked = (directories[0], directories[0], *directories[2:])
    with pytest.raises(subject.ConstructionK7QueryBoundCampaignAnalysisV1Error):
        subject.analyze_query_bound_campaign_bundles_v1(
            spec,
            bundle_directories=attacked,
        )
