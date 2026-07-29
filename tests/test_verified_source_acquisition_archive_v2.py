from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
from types import SimpleNamespace

import pytest

from acfqp import observation_support_campaign_v1 as campaign
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import verified_source_acquisition_archive_v2 as archive


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _mass(
    destination_id: str,
    lower: Fraction,
    upper: Fraction,
) -> robust.IntervalDestinationMassV1:
    return robust.IntervalDestinationMassV1(
        destination_id,
        lower,
        upper,
    )


def _source_models():
    context_id = _id("source-context")
    root_state = _id("root-state")
    child_state = _id("child-state")
    root_cell = _id("root-cell")
    child_cell = _id("child-cell")
    root_action = _id("root-ground-action")
    child_action = _id("child-ground-action")
    root_semantic = _id("root-semantic-action")
    child_semantic = _id("child-semantic-action")
    active_destination = _id("active-destination")
    failure_destination = _id("failure-destination")
    success_destination = _id("success-destination")
    other_destination = _id("other-destination")
    destinations = tuple(
        sorted(
            (
                robust.RegisteredDestinationV1(
                    active_destination,
                    robust.DestinationCategory.ACTIVE_STATE,
                    child_state,
                ),
                robust.RegisteredDestinationV1(
                    failure_destination,
                    robust.DestinationCategory.FAILURE,
                ),
                robust.RegisteredDestinationV1(
                    success_destination,
                    robust.DestinationCategory.SUCCESS_TERMINAL,
                ),
                robust.RegisteredDestinationV1(
                    other_destination,
                    robust.DestinationCategory.OTHER,
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    catalogues = tuple(
        sorted(
            (
                robust.StateActionCatalogueV1(
                    root_state,
                    root_cell,
                    (
                        robust.CatalogueActionV1(
                            root_action,
                            root_semantic,
                        ),
                    ),
                ),
                robust.StateActionCatalogueV1(
                    child_state,
                    child_cell,
                    (
                        robust.CatalogueActionV1(
                            child_action,
                            child_semantic,
                        ),
                    ),
                ),
            ),
            key=lambda item: item.state_id,
        )
    )
    concretizers = tuple(
        sorted(
            (
                robust.DistinctActionConcretizerEntryV1(
                    root_cell,
                    root_state,
                    root_semantic,
                    (root_action,),
                ),
                robust.DistinctActionConcretizerEntryV1(
                    child_cell,
                    child_state,
                    child_semantic,
                    (child_action,),
                ),
            ),
            key=lambda item: item.concretizer_entry_id,
        )
    )

    def build(tight: bool) -> robust.PartialSupportIntervalModelV1:
        if tight:
            child_masses = (
                _mass(
                    failure_destination,
                    Fraction(1, 20),
                    Fraction(1, 10),
                ),
                _mass(
                    other_destination,
                    Fraction(0),
                    Fraction(1, 20),
                ),
                _mass(
                    success_destination,
                    Fraction(17, 20),
                    Fraction(19, 20),
                ),
            )
            root_masses = (
                _mass(
                    active_destination,
                    Fraction(9, 10),
                    Fraction(19, 20),
                ),
                _mass(
                    failure_destination,
                    Fraction(0),
                    Fraction(1, 20),
                ),
                _mass(
                    other_destination,
                    Fraction(0),
                    Fraction(1, 20),
                ),
            )
        else:
            child_masses = (
                _mass(
                    failure_destination,
                    Fraction(1, 10),
                    Fraction(1, 4),
                ),
                _mass(
                    other_destination,
                    Fraction(0),
                    Fraction(1, 5),
                ),
                _mass(
                    success_destination,
                    Fraction(11, 20),
                    Fraction(9, 10),
                ),
            )
            root_masses = (
                _mass(
                    active_destination,
                    Fraction(3, 4),
                    Fraction(9, 10),
                ),
                _mass(
                    failure_destination,
                    Fraction(0),
                    Fraction(1, 10),
                ),
                _mass(
                    other_destination,
                    Fraction(0),
                    Fraction(3, 20),
                ),
            )
        rows = (
            robust.IntervalSimplexRowV1(
                child_state,
                1,
                child_action,
                Fraction(1, 5),
                Fraction(1, 5),
                other_destination,
                tuple(sorted(child_masses, key=lambda item: item.destination_id)),
            ),
            robust.IntervalSimplexRowV1(
                root_state,
                2,
                root_action,
                Fraction(3, 10),
                Fraction(3, 10),
                other_destination,
                tuple(sorted(root_masses, key=lambda item: item.destination_id)),
            ),
        )
        return robust.build_partial_support_model_v1(
            context_id=context_id,
            root_state_id=root_state,
            catalogues=catalogues,
            destinations=destinations,
            rows=rows,
            concretizer_entries=concretizers,
        )

    threshold = robust.RobustThresholdProfileV1(
        context_id,
        Fraction(1, 5),
        Fraction(1),
    )
    before = build(False)
    after = build(True)
    before_audit = robust.solve_quotient_robust_h2_v1(before, threshold)
    after_audit = robust.solve_quotient_robust_h2_v1(after, threshold)
    assert not before_audit.certified
    assert before_audit.failed_frontier is not None
    return before, after, before_audit, after_audit, threshold


def _fake_execution(
    *,
    checkpoint: int,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    execution_id: str,
) -> campaign.CheckpointExecutionV1:
    value = object.__new__(campaign.CheckpointExecutionV1)
    object.__setattr__(value, "checkpoint", checkpoint)
    object.__setattr__(
        value,
        "bridge",
        SimpleNamespace(quotient_model=model),
    )
    object.__setattr__(value, "threshold", threshold)
    object.__setattr__(value, "quotient_considered", True)
    object.__setattr__(value, "quotient_base_audit", audit)
    # The class is slotted.  The monkeypatched property used by these focused
    # tests derives this same identity from the registered checkpoint.
    assert execution_id == _id(f"execution:{checkpoint}")
    return value


def _fake_prefix_proof(
    before_checkpoint: int = 2_048,
    after_checkpoint: int = 4_096,
) -> archive.RawPrefixExtensionProofV2:
    incremental = after_checkpoint - before_checkpoint
    return archive.RawPrefixExtensionProofV2(
        _id("binding"),
        _id("support-epoch"),
        _id("before-partial-row"),
        _id("after-partial-row"),
        _id("before-physical"),
        _id("after-physical"),
        _id("discovery-digest"),
        _id("before-validation-digest"),
        _id("after-validation-digest"),
        _id("suffix-digest"),
        before_checkpoint,
        after_checkpoint,
        incremental,
        incremental + 3,
        3,
    )


def test_independent_fraction_recurrence_matches_production_audit() -> None:
    before, after, before_audit, after_audit, threshold = _source_models()
    before_metrics = archive.independent_fixed_policy_metrics_v2(
        model=before,
        audit=before_audit,
        threshold=threshold,
    )
    after_metrics = archive.independent_fixed_policy_metrics_v2(
        model=after,
        audit=after_audit,
        threshold=threshold,
    )
    assert before_metrics.reward_lower == before_audit.root_reward_lower
    assert before_metrics.failure_upper == before_audit.root_failure_upper
    assert (
        before_metrics.unrestricted_reward_upper
        == before_audit.unrestricted_reward_upper
    )
    assert (
        before_metrics.normalized_regret_upper
        == before_audit.normalized_regret_upper
    )
    assert after_metrics.reward_lower == after_audit.root_reward_lower
    assert after_metrics.failure_upper == after_audit.root_failure_upper
    assert all(
        type(value) is Fraction
        for value in (
            before_metrics.certificate_slack,
            after_metrics.certificate_slack,
        )
    )


def test_pair_derivation_uses_chronology_and_not_caller_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before, after, before_audit, after_audit, threshold = _source_models()
    monkeypatch.setattr(
        campaign.CheckpointExecutionV1,
        "execution_id",
        property(lambda self: _id(f"execution:{self.checkpoint}")),
    )
    monkeypatch.setattr(
        archive,
        "_physical_row_for_planner_row",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        archive,
        "_raw_prefix_extension",
        lambda *_args, **_kwargs: _fake_prefix_proof(),
    )
    first = _fake_execution(
        checkpoint=2_048,
        model=before,
        audit=before_audit,
        threshold=threshold,
        execution_id=_id("execution:2048"),
    )
    second = _fake_execution(
        checkpoint=4_096,
        model=after,
        audit=after_audit,
        threshold=threshold,
        execution_id=_id("execution:4096"),
    )
    pair, trials = archive._derive_pair(
        source_context_id=before.context_id,
        source_context_key="opaque_graph_w5_v0",
        before=first,
        after=second,
    )
    assert (pair.before_checkpoint, pair.after_checkpoint) == (2_048, 4_096)
    assert pair.trial_ids == tuple(item.trial_id for item in trials)
    assert len(trials) == len(
        before_audit.failed_frontier.other_positive_row_ids
    )
    assert all(
        item.gain_per_draw
        == item.slack_gain / (4_096 - 2_048)
        for item in trials
    )
    assert all(
        item.local_snapshot.before_model_id == before.model_id
        and item.local_snapshot.after_model_id == after.model_id
        for item in trials
    )
    parameters = inspect.signature(
        archive.freeze_verified_source_acquisition_archive_v2
    ).parameters
    assert tuple(parameters) == ("source_campaign", "source_verification")
    assert not {
        "gain",
        "score",
        "pairs",
        "features",
        "trials",
    } & set(parameters)


def test_portable_feature_excludes_identity_and_probability_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before, after, before_audit, after_audit, threshold = _source_models()
    monkeypatch.setattr(
        campaign.CheckpointExecutionV1,
        "execution_id",
        property(lambda self: _id(f"execution:{self.checkpoint}")),
    )
    monkeypatch.setattr(
        archive,
        "_physical_row_for_planner_row",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        archive,
        "_raw_prefix_extension",
        lambda *_args, **_kwargs: _fake_prefix_proof(),
    )
    first = _fake_execution(
        checkpoint=2_048,
        model=before,
        audit=before_audit,
        threshold=threshold,
        execution_id=_id("execution:2048"),
    )
    second = _fake_execution(
        checkpoint=4_096,
        model=after,
        audit=after_audit,
        threshold=threshold,
        execution_id=_id("execution:4096"),
    )
    _, trials = archive._derive_pair(
        source_context_id=before.context_id,
        source_context_key="opaque_graph_w5_v0",
        before=first,
        after=second,
    )
    feature_document = trials[0].portable_feature.to_document()
    snapshot_document = trials[0].local_snapshot.to_document()
    encoded_feature = repr(feature_document)
    assert before.context_id not in encoded_feature
    assert trials[0].local_snapshot.before_row_id not in encoded_feature
    assert "lower" not in feature_document
    assert "upper" not in feature_document
    assert "probability" not in feature_document
    assert "known_support_count_bin" not in feature_document
    assert "before_mass_intervals" in snapshot_document
    assert "after_mass_intervals" in snapshot_document
    assert "raw_prefix_extension_proof_id" in snapshot_document
    assert snapshot_document["portable_feature_key"] == (
        trials[0].portable_feature.feature_key
    )
    before_frontier_row = {
        item.row_id: item for item in before.rows
    }[before_audit.failed_frontier.other_positive_row_ids[0]]
    after_row = {
        item.row_key: item for item in after.rows
    }[before_frontier_row.row_key]
    assert archive._portable_feature(
        model=before,
        audit=before_audit,
        row=before_frontier_row,
    ).feature_key == archive._portable_feature(
        model=after,
        audit=after_audit,
        row=after_row,
    ).feature_key


def _feature(label: str) -> archive.PortableAcquisitionCoreFeatureV2:
    if label == "one":
        action_bin = "1"
        categories = {
            robust.DestinationCategory.SUCCESS_TERMINAL.value,
        }
    elif label == "two":
        action_bin = "2"
        categories = {
            robust.DestinationCategory.FAILURE.value,
            robust.DestinationCategory.SUCCESS_TERMINAL.value,
        }
    else:
        action_bin = "3_PLUS"
        categories = {
            robust.DestinationCategory.ACTIVE_STATE.value,
            robust.DestinationCategory.SUCCESS_TERMINAL.value,
        }
    return archive.PortableAcquisitionCoreFeatureV2(
        "ROOT",
        robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT.value,
        action_bin,
        "1",
        tuple(sorted(categories)),
    )


def _trial(
    *,
    context: str,
    feature: archive.PortableAcquisitionCoreFeatureV2,
    gain: Fraction,
    suffix: str,
) -> archive.VerifiedSourceLocalTrialV2:
    context_id = _id(context)
    destination_id = _id("destination")
    mass = archive.IdentityBoundMassIntervalV2(
        destination_id,
        robust.DestinationCategory.SUCCESS_TERMINAL,
        Fraction(1),
        Fraction(1),
    )
    snapshot = archive.IdentityBoundLocalSnapshotV2(
        context_id,
        _id(f"before-execution:{suffix}"),
        _id(f"after-execution:{suffix}"),
        _id(f"before-model:{suffix}"),
        _id(f"after-model:{suffix}"),
        _id(f"before-audit:{suffix}"),
        _id(f"after-audit:{suffix}"),
        _id(f"threshold:{suffix}"),
        2_048,
        4_096,
        _id(f"before-row:{suffix}"),
        _id(f"after-row:{suffix}"),
        _id(f"state:{suffix}"),
        _id(f"action:{suffix}"),
        2,
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
        (mass,),
        (mass,),
        _fake_prefix_proof(),
        2_048,
        feature.feature_key,
    )
    before = archive.IndependentFixedPolicyMetricsV2(
        Fraction(0),
        Fraction(1, 2),
        Fraction(0),
        Fraction(0),
        Fraction(-1, 2),
    )
    after = archive.IndependentFixedPolicyMetricsV2(
        Fraction(0),
        Fraction(1, 2) - gain,
        Fraction(0),
        Fraction(0),
        Fraction(-1, 2) + gain,
    )
    return archive.VerifiedSourceLocalTrialV2(
        context_id,
        feature,
        snapshot,
        before,
        after,
        gain,
        gain / 2_048,
    )


def test_nonrectangular_consensus_abstains_locally_not_globally() -> None:
    shared = _feature("one")
    local_only = _feature("two")
    second_local_only = _feature("three")
    trials = tuple(
        sorted(
            (
                _trial(
                    context="context-a",
                    feature=shared,
                    gain=Fraction(1, 4),
                    suffix="a-shared",
                ),
                _trial(
                    context="context-a",
                    feature=local_only,
                    gain=Fraction(1, 8),
                    suffix="a-local",
                ),
                _trial(
                    context="context-b",
                    feature=shared,
                    gain=Fraction(1, 4),
                    suffix="b-shared",
                ),
                _trial(
                    context="context-b",
                    feature=second_local_only,
                    gain=Fraction(1, 8),
                    suffix="b-local",
                ),
            ),
            key=lambda item: item.trial_id,
        )
    )
    aggregates, consensus = archive._derive_nonrectangular_consensus(trials)
    assert len(aggregates) == 4
    by_feature = {item.feature_key: item for item in consensus}
    assert (
        by_feature[shared.feature_key].disposition
        is archive.FeatureConsensusDispositionV2.APPLIED
    )
    assert (
        by_feature[local_only.feature_key].disposition
        is archive.FeatureConsensusDispositionV2
        .INSUFFICIENT_CONTEXTS
    )
    assert (
        by_feature[local_only.feature_key].multiplier
        == archive.NEUTRAL_PRIOR_MULTIPLIER
    )
    assert by_feature[shared.feature_key].source_context_ids == tuple(
        sorted((_id("context-a"), _id("context-b")))
    )


def test_degenerate_or_nonpositive_feature_abstains_neutrally() -> None:
    shared = _feature("one")
    comparison = _feature("two")
    zero_trials = tuple(
        sorted(
            (
                _trial(
                    context=context,
                    feature=feature,
                    gain=gain,
                    suffix=f"{context}:{feature.feature_key}",
                )
                for context in ("context-a", "context-b")
                for feature, gain in (
                    (shared, Fraction(0)),
                    (comparison, Fraction(1, 8)),
                )
            ),
            key=lambda item: item.trial_id,
        )
    )
    _, zero_consensus = archive._derive_nonrectangular_consensus(
        zero_trials
    )
    zero_by_feature = {
        item.feature_key: item for item in zero_consensus
    }
    assert (
        zero_by_feature[shared.feature_key].disposition
        is archive.FeatureConsensusDispositionV2
        .NONPOSITIVE_SOURCE_GAIN
    )
    assert (
        zero_by_feature[shared.feature_key].multiplier
        == archive.NEUTRAL_PRIOR_MULTIPLIER
    )

    tied_trials = tuple(
        sorted(
            (
                _trial(
                    context=context,
                    feature=feature,
                    gain=Fraction(1, 8),
                    suffix=f"tie:{context}:{feature.feature_key}",
                )
                for context in ("context-c", "context-d")
                for feature in (shared, comparison)
            ),
            key=lambda item: item.trial_id,
        )
    )
    _, tied_consensus = archive._derive_nonrectangular_consensus(
        tied_trials
    )
    assert all(
        item.disposition
        is archive.FeatureConsensusDispositionV2
        .DEGENERATE_CONTEXT_RANKING
        and item.multiplier == archive.NEUTRAL_PRIOR_MULTIPLIER
        for item in tied_consensus
    )


def test_raw_prefix_extension_reconciliation_fails_closed() -> None:
    proof = _fake_prefix_proof()
    with pytest.raises(
        archive.VerifiedSourceAcquisitionArchiveInvariantViolation,
        match="does not reconcile",
    ):
        replace(
            proof,
            incremental_accepted_draws=proof.incremental_accepted_draws - 1,
        )


def test_forged_audit_metric_fails_independent_recurrence() -> None:
    before, _, before_audit, _, threshold = _source_models()
    forged = replace(
        before_audit,
        root_failure_upper=before_audit.root_failure_upper
        - Fraction(1, 100),
    )
    with pytest.raises(
        archive.VerifiedSourceAcquisitionArchiveInvariantViolation,
        match="independent exact recurrence",
    ):
        archive._verify_audit_arithmetic(before, forged, threshold)


def test_roll_forward_rejects_structural_drift() -> None:
    before, after, _, _, _ = _source_models()
    drifted = replace(after, context_id=_id("different-context"))
    with pytest.raises(
        archive.VerifiedSourceAcquisitionArchiveInvariantViolation,
        match="structural semantics",
    ):
        archive._structurally_compatible_models(before, drifted)
