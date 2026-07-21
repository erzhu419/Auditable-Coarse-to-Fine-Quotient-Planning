from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    OUTPUT_BYTES,
    PEAK_MOUNTED_BYTES,
    PEAK_WORKING_BYTES,
    PROCESS_LAUNCHES,
    READ_BYTES,
    SHARED_AXES,
    STAGED_BYTES,
    AccountingV1Error,
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ProjectionTermV1,
    ReconciliationProofV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
    derive_comparison_vector_v1,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.phase3e_ids import (
    COMPARISON_PROFILE_DOMAIN,
    COMPARISON_VECTOR_DOMAIN,
    COUNTER_RECORD_DOMAIN,
    COUNTER_REGISTRY_DOMAIN,
    NATIVE_ZERO_ATTESTATION_DOMAIN,
    RECONCILIATION_PROOF_DOMAIN,
    WORK_VECTOR_DOMAIN,
    content_id,
)


def _values(**overrides: int) -> tuple[object, dict[str, int]]:
    registry = official_counter_registry_v1()
    values = {path: 0 for path in registry.required_paths}
    for path, value in overrides.items():
        normalized = path.replace("__", ".")
        assert normalized in values
        values[normalized] = value
    return registry, values


def _vector(
    route: RouteKindEnum,
    *,
    subject: str = "subject-1",
    optional: dict[str, int] | None = None,
    **overrides: int,
) -> tuple[object, WorkVectorV1]:
    registry, values = _values(**overrides)
    values.update(optional or {})
    records = explicit_records_v1(
        registry,
        values,
        recorder_id="trusted-recorder-v1",
        include_optional=bool(optional),
    )
    return registry, registry.materialize(
        subject_id=subject,
        route_kind=route,
        records=records,
    )


def test_official_registry_freezes_all_fq11_leaves_and_metadata() -> None:
    registry = official_counter_registry_v1()
    registry.validate_official_catalogue()

    assert len(registry.operational_leaves) == 34
    assert len(registry.leaves) == 49
    assert {
        registry.by_path["evaluation.semantic_integrity_checks"].lane,
        registry.by_path["evaluation.semantic_protocol_checks"].lane,
    } == {LaneEnum.EVALUATION}
    assert set(registry.required_paths) == {
        leaf.path for leaf in registry.operational_leaves
    } | {
        "process.exit_failures",
        "process.exit_successes",
        "route.attempts",
        "route.failures",
        "route.successes",
        "solver.attempts",
        "solver.failures",
        "solver.successes",
    }
    assert CounterRegistryV1.from_dict(registry.to_dict()) == registry
    assert registry.registry_id == content_id(
        COUNTER_REGISTRY_DOMAIN, registry._payload()
    )

    ground = registry.by_path["local.materialization_ground_steps"]
    assert (
        ground.semantics_id,
        ground.owner,
        ground.unit,
        ground.lane,
        ground.scope,
        ground.reducer,
        ground.comparison_axis,
    ) == (
        "ground-transition-call-v1",
        "slice_materializer",
        "calls",
        LaneEnum.OPERATIONAL,
        "transaction",
        ReducerEnum.SUM,
        KERNEL_TRANSITION_CALLS,
    )
    assert registry.by_path["integrity.bytes_hashed"].lane is LaneEnum.DIAGNOSTIC
    assert registry.by_path["branch.evaluations"].lane is LaneEnum.DERIVED_ONLY
    assert registry.by_path["model.serialized_bytes"].comparison_axis is None


def test_native_zero_is_explicit_observed_work_not_a_missing_default() -> None:
    registry, values = _values()
    missing = dict(values)
    del missing["local.causal_candidate_evaluations"]
    with pytest.raises(AccountingV1Error, match="missing explicit required"):
        explicit_records_v1(
            registry, missing, recorder_id="trusted-recorder-v1"
        )

    complete_records = explicit_records_v1(
        registry, values, recorder_id="trusted-recorder-v1"
    )
    with pytest.raises(AccountingV1Error, match="missing required counter records"):
        registry.materialize(
            subject_id="direct-missing-attack",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=complete_records[1:],
        )

    records = list(
        complete_records
    )
    index = next(
        index
        for index, row in enumerate(records)
        if row.path == "local.causal_candidate_evaluations"
    )
    records[index] = replace(records[index], observed=False)
    with pytest.raises(AccountingV1Error, match="unobserved"):
        registry.materialize(
            subject_id="subject-1",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=tuple(records),
        )

    _, vector = _vector(RouteKindEnum.LOCAL_ATTEMPT)
    attestation = NativeZeroAttestationV1.derive(vector, registry)
    assert set(attestation.zero_paths) == set(registry.required_paths)
    assert set(attestation.recorder_ids) == {"trusted-recorder-v1"}
    assert NativeZeroAttestationV1.from_dict(attestation.to_dict()) == attestation
    assert attestation.native_zero_attestation_id == content_id(
        NATIVE_ZERO_ATTESTATION_DOMAIN, attestation._payload()
    )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("semantics_id", "wrong-semantics-v1"),
        ("owner", "wrong_owner"),
        ("unit", "wrong_unit"),
        ("lane", LaneEnum.EVALUATION),
        ("scope", "wrong_scope"),
        ("reducer", ReducerEnum.MAX),
    ],
)
def test_wrong_counter_record_metadata_fails_closed(field: str, bad_value: object) -> None:
    registry, values = _values()
    records = list(
        explicit_records_v1(
            registry, values, recorder_id="trusted-recorder-v1"
        )
    )
    records[0] = replace(records[0], **{field: bad_value})
    with pytest.raises(AccountingV1Error, match="metadata mismatch"):
        registry.materialize(
            subject_id="subject-1",
            route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            records=tuple(records),
        )


def test_unknown_counter_path_and_registry_metadata_tampering_fail() -> None:
    registry, values = _values()
    with pytest.raises(AccountingV1Error, match="unknown counter paths"):
        explicit_records_v1(
            registry,
            {**values, "unknown.hidden_work": 4},
            recorder_id="trusted-recorder-v1",
        )

    document = registry.to_dict()
    document["leaves"][0]["scope"] = "forged_scope"
    document["counter_registry_id"] = content_id(
        COUNTER_REGISTRY_DOMAIN,
        {
            key: value
            for key, value in document.items()
            if key != "counter_registry_id"
        },
    )
    with pytest.raises(AccountingV1Error, match="catalogue metadata mismatch"):
        CounterRegistryV1.from_dict(document)


def test_route_families_require_native_zero_and_failed_local_fallback_stay_separate() -> None:
    registry, local = _vector(
        RouteKindEnum.LOCAL_ATTEMPT,
        subject="local-failed",
        local__causal_candidate_evaluations=4,
        local__materialization_ground_steps=2,
    )
    _, fallback = _vector(
        RouteKindEnum.DIRECT_FALLBACK,
        subject="fallback-after-local",
        fallback__states_expanded=3,
        fallback__ground_steps=5,
    )

    assert local.work_vector_id != fallback.work_vector_id
    assert local.value("fallback.ground_steps") == 0
    assert fallback.value("local.materialization_ground_steps") == 0
    assert local.value("local.materialization_ground_steps") == 2
    assert fallback.value("fallback.ground_steps") == 5

    mixed_values = dict(local.values)
    mixed_values["fallback.ground_steps"] = 1
    mixed_records = explicit_records_v1(
        registry, mixed_values, recorder_id="trusted-recorder-v1"
    )
    with pytest.raises(AccountingV1Error, match="exclusivity violation"):
        registry.materialize(
            subject_id="forged-combined-route",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=mixed_records,
        )


def test_abstract_and_rebuild_route_stage_coverage_is_fail_closed() -> None:
    registry, abstract = _vector(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        common__abstract_bellman_backups=7,
    )
    assert abstract.value("local.causal_candidate_evaluations") == 0
    assert abstract.value("fallback.states_expanded") == 0
    assert abstract.value("rebuild.ground_steps") == 0

    _, failed_prefix = _vector(
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        subject="failed-abstract-prefix",
        common__abstract_bellman_backups=4,
        common__abstract_audit_obligations=1,
        local__causal_candidate_evaluations=4,
    )
    assert failed_prefix.value("local.causal_candidate_evaluations") == 4
    assert failed_prefix.value("fallback.states_expanded") == 0
    assert failed_prefix.value("rebuild.ground_steps") == 0

    failed_prefix_values = dict(failed_prefix.values)
    failed_prefix_values["local.materialization_ground_steps"] = 1
    with pytest.raises(AccountingV1Error, match="exclusivity violation"):
        registry.materialize(
            subject_id="failed-prefix-with-route-execution",
            route_kind=RouteKindEnum.ABSTRACT_FAILED_PREFIX,
            records=explicit_records_v1(
                registry,
                failed_prefix_values,
                recorder_id="trusted-recorder-v1",
            ),
        )

    _, rebuild = _vector(
        RouteKindEnum.REBUILD,
        subject="rebuild-1",
        rebuild__ground_steps=2,
        rebuild__partition_candidate_evaluations=3,
        io__output_bytes=500,
    )
    assert rebuild.value("rebuild.ground_steps") == 2
    assert rebuild.value("local.materialization_ground_steps") == 0

    bad = dict(rebuild.values)
    bad["common.protocol_checks"] = 1
    with pytest.raises(AccountingV1Error, match="exclusivity violation"):
        registry.materialize(
            subject_id="bad-rebuild",
            route_kind=RouteKindEnum.REBUILD,
            records=explicit_records_v1(
                registry, bad, recorder_id="trusted-recorder-v1"
            ),
        )


def test_reconciliation_and_output_byte_subsets_are_replayed() -> None:
    optional = {
        "route.attempts": 1,
        "route.successes": 0,
        "route.failures": 1,
        "solver.attempts": 1,
        "solver.successes": 0,
        "solver.failures": 1,
        "process.exit_successes": 1,
        "process.exit_failures": 0,
        "model.serialized_bytes": 60,
        "epoch.serialized_bytes": 100,
        "capability.serialized_bytes": 40,
    }
    registry, vector = _vector(
        RouteKindEnum.LOCAL_ATTEMPT,
        optional=optional,
        process__launches=1,
        io__output_bytes=100,
    )
    proof = ReconciliationProofV1.derive(vector, registry)
    assert proof.equations == (
        "process_launches_equals_exit_successes_plus_failures",
        "route_attempts_equals_successes_plus_failures",
        "solver_attempts_equals_successes_plus_failures",
    )
    assert proof.output_byte_subset_paths == (
        "capability.serialized_bytes",
        "epoch.serialized_bytes",
        "model.serialized_bytes",
    )
    assert ReconciliationProofV1.from_dict(proof.to_dict()) == proof
    assert proof.reconciliation_proof_id == content_id(
        RECONCILIATION_PROOF_DOMAIN, proof._payload()
    )

    values = dict(vector.values)
    values["route.failures"] = 0
    with pytest.raises(AccountingV1Error, match="reconciliation failed"):
        registry.materialize(
            subject_id="bad-reconciliation",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=explicit_records_v1(
                registry,
                values,
                recorder_id="trusted-recorder-v1",
                include_optional=True,
            ),
        )

    values = dict(vector.values)
    del values["solver.failures"]
    with pytest.raises(AccountingV1Error, match="missing explicit required"):
        registry.materialize(
            subject_id="partial-reconciliation",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=explicit_records_v1(
                registry,
                values,
                recorder_id="trusted-recorder-v1",
                include_optional=True,
            ),
        )

    values = dict(vector.values)
    values["model.serialized_bytes"] = 101
    with pytest.raises(AccountingV1Error, match="cannot exceed io.output_bytes"):
        registry.materialize(
            subject_id="double-count-attack",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=explicit_records_v1(
                registry,
                values,
                recorder_id="trusted-recorder-v1",
                include_optional=True,
            ),
        )


def test_shared_profile_has_exact_eight_axes_and_complete_projection() -> None:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    profile.validate(registry)

    assert tuple(axis.name for axis in profile.axes) == SHARED_AXES
    assert len(profile.terms) == len(registry.operational_leaves)
    assert {term.source_leaf for term in profile.terms} == {
        leaf.path for leaf in registry.operational_leaves
    }
    assert all(term.coefficient == 1 for term in profile.terms)
    assert all(term.source_lane is LaneEnum.OPERATIONAL for term in profile.terms)
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    assert reducers[PEAK_MOUNTED_BYTES] is ReducerEnum.MAX
    assert reducers[PEAK_WORKING_BYTES] is ReducerEnum.MAX
    assert all(
        reducers[axis] is ReducerEnum.SUM
        for axis in set(SHARED_AXES) - {PEAK_MOUNTED_BYTES, PEAK_WORKING_BYTES}
    )
    assert profile.comparison_profile_id == content_id(
        COMPARISON_PROFILE_DOMAIN, profile._payload()
    )
    assert ComparisonProfileV1.from_dict(profile.to_dict(), registry) == profile


def test_projection_recomputes_sum_and_peak_axes_without_byte_double_charge() -> None:
    optional = {
        "model.serialized_bytes": 700,
        "epoch.serialized_bytes": 900,
        "integrity.bytes_hashed": 10000,
        "branch.evaluations": 0,
    }
    registry, vector = _vector(
        RouteKindEnum.LOCAL_ATTEMPT,
        optional=optional,
        common__abstract_bellman_backups=2,
        common__integrity_checks=3,
        local__causal_candidate_evaluations=4,
        local__materialization_ground_steps=5,
        local__postaudit_ground_steps=7,
        process__launches=1,
        process__exit_successes=1,
        io__read_bytes=11,
        io__staged_bytes=13,
        io__output_bytes=1000,
        io__mounted_bytes_peak=17,
        memory__working_bytes_peak=19,
    )
    profile = official_comparison_profile_v1(registry)
    actual = derive_comparison_vector_v1(vector, registry, profile)

    assert actual.value(KERNEL_TRANSITION_CALLS) == 12
    assert actual.value(NONKERNEL_COMPUTE_EVENTS) == 9
    assert actual.value(PROCESS_LAUNCHES) == 1
    assert actual.value(READ_BYTES) == 11
    assert actual.value(STAGED_BYTES) == 13
    assert actual.value(OUTPUT_BYTES) == 1000
    assert actual.value(PEAK_MOUNTED_BYTES) == 17
    assert actual.value(PEAK_WORKING_BYTES) == 19
    assert actual.value(OUTPUT_BYTES) != 1000 + 700 + 900
    assert ComparisonVectorV1.from_dict(actual.to_dict()) == actual


def test_generic_branch_volume_must_be_reclassified_before_accounting() -> None:
    registry, values = _values()
    values["branch.evaluations"] = 1
    with pytest.raises(AccountingV1Error, match="must be reclassified"):
        registry.materialize(
            subject_id="generic-branch-attack",
            route_kind=RouteKindEnum.LOCAL_ATTEMPT,
            records=explicit_records_v1(
                registry,
                values,
                recorder_id="trusted-recorder-v1",
                include_optional=True,
            ),
        )


def test_projection_rejects_missing_duplicate_wrong_and_nonoperational_terms() -> None:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    terms = profile.terms

    missing = replace(profile, terms=terms[1:])
    with pytest.raises(AccountingV1Error, match="projection coverage mismatch"):
        missing.validate(registry)

    with pytest.raises(AccountingV1Error, match="project only once"):
        replace(profile, terms=tuple(sorted(terms + (terms[0],), key=lambda term: term.source_leaf)))

    index = next(
        index
        for index, term in enumerate(terms)
        if term.source_leaf == "common.abstract_bellman_backups"
    )
    cases = (
        replace(terms[index], coefficient=2),
        replace(terms[index], source_lane=LaneEnum.EVALUATION),
        replace(terms[index], source_semantics_id="wrong-semantics-v1"),
        replace(terms[index], target_axis=KERNEL_TRANSITION_CALLS),
        replace(terms[index], reducer=ReducerEnum.MAX),
    )
    for forged_term in cases:
        forged_terms = list(terms)
        forged_terms[index] = forged_term
        forged = replace(profile, terms=tuple(forged_terms))
        with pytest.raises(AccountingV1Error):
            forged.validate(registry)

    diagnostic = registry.by_path["integrity.bytes_hashed"]
    injected = ProjectionTermV1(
        diagnostic.path,
        READ_BYTES,
        1,
        diagnostic.lane,
        diagnostic.semantics_id,
        ReducerEnum.SUM,
    )
    forged = replace(
        profile,
        terms=tuple(sorted(terms + (injected,), key=lambda term: term.source_leaf)),
    )
    with pytest.raises(AccountingV1Error, match="projection coverage mismatch"):
        forged.validate(registry)


def test_artifact_roundtrip_rejects_record_and_vector_tampering() -> None:
    registry, vector = _vector(
        RouteKindEnum.DIRECT_FALLBACK,
        fallback__states_expanded=2,
        fallback__actions_evaluated=3,
    )
    assert WorkVectorV1.from_dict(vector.to_dict(), registry) == vector
    assert CounterRecordV1.from_dict(vector.records[0].to_dict()) == vector.records[0]
    assert vector.work_vector_id == content_id(WORK_VECTOR_DOMAIN, vector._payload())
    assert vector.records[0].record_id == content_id(
        COUNTER_RECORD_DOMAIN, vector.records[0]._payload()
    )

    record_doc = vector.records[0].to_dict()
    record_doc["value"] = 100
    with pytest.raises(AccountingV1Error, match="content ID mismatch"):
        CounterRecordV1.from_dict(record_doc)

    vector_doc = copy.deepcopy(vector.to_dict())
    vector_doc["records"][0]["value"] = 100
    with pytest.raises(AccountingV1Error):
        WorkVectorV1.from_dict(vector_doc, registry)


def test_comparison_vector_uses_the_central_registered_domain() -> None:
    registry, vector = _vector(RouteKindEnum.DIRECT_FALLBACK)
    actual = derive_comparison_vector_v1(
        vector, registry, official_comparison_profile_v1(registry)
    )
    assert actual.comparison_vector_id == content_id(
        COMPARISON_VECTOR_DOMAIN, actual._payload()
    )


def test_infeasible_fallback_and_failed_paths_keep_full_native_work() -> None:
    registry, fallback = _vector(
        RouteKindEnum.DIRECT_FALLBACK,
        subject="infeasible-fallback-proof",
        fallback__states_expanded=11,
        fallback__actions_evaluated=23,
        fallback__ground_steps=31,
        fallback__outcome_rows=37,
        fallback__bellman_backups=41,
        common__protocol_checks=1,
        control__cap_checks=2,
        io__output_bytes=97,
    )
    registry.validate_vector(fallback)
    assert fallback.value("fallback.ground_steps") == 31
    assert fallback.value("fallback.bellman_backups") == 41
    assert fallback.value("io.output_bytes") == 97


def test_float_bool_and_missing_fields_cannot_masquerade_as_exact_counts() -> None:
    registry, values = _values()
    values["common.protocol_checks"] = True
    with pytest.raises(AccountingV1Error, match="nonnegative exact integer"):
        explicit_records_v1(
            registry, values, recorder_id="trusted-recorder-v1"
        )

    document = official_comparison_profile_v1(registry).to_dict()
    del document["terms"]
    with pytest.raises(AccountingV1Error, match="field set mismatch"):
        ComparisonProfileV1.from_dict(document, registry)
