from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import hashlib
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp import observation_support_campaign_v1 as campaign
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp import verified_source_acquisition_archive_v2 as archive
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as independent,
)
from acfqp.phase3e_ids import canonical_json_bytes
from tests.test_verified_source_acquisition_archive_v2 import _source_models


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _unsafe_clone(value: Any, **changes: Any) -> Any:
    cloned = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            cloned,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return cloned


def _physical_row(
    *,
    context_key: str,
    semantic_row_key: tuple[str, int, str],
    checkpoint: int,
    planner_row_id: str,
    discovery_ids: tuple[str, ...],
    validation_ids: tuple[str, ...],
) -> acquisition.GraphPartialSupportRowV1:
    semantic_label = ":".join(map(str, semantic_row_key))
    binding_id = _id(f"binding:{context_key}:{semantic_label}")
    support_epoch_id = _id(
        f"support-epoch:{context_key}:{semantic_label}"
    )
    rejection_count = checkpoint // 2_048
    counters = acquisition.GraphPartialSupportCountersV1(
        1,
        acquisition.DISCOVERY_DRAW_COUNT,
        0,
        checkpoint,
        acquisition.DISCOVERY_DRAW_COUNT + checkpoint,
        acquisition.DISCOVERY_DRAW_COUNT,
        0,
        0,
        0,
        checkpoint + rejection_count,
        rejection_count,
        (
            acquisition.DISCOVERY_DRAW_COUNT
            + checkpoint
            + rejection_count
        ),
        rejection_count,
    )
    value = object.__new__(acquisition.GraphPartialSupportRowV1)
    object.__setattr__(
        value,
        "binding",
        SimpleNamespace(row_id=binding_id),
    )
    object.__setattr__(
        value,
        "support_epoch",
        SimpleNamespace(
            support_epoch_id=support_epoch_id,
            support_epoch_index=1,
        ),
    )
    object.__setattr__(
        value,
        "confidence_authority",
        SimpleNamespace(
            authority_id=_id(
                f"authority:{context_key}:{semantic_label}:{checkpoint}"
            )
        ),
    )
    object.__setattr__(
        value,
        "initial_discovery_observation_ids",
        discovery_ids,
    )
    object.__setattr__(value, "prior_validation_observation_ids", ())
    object.__setattr__(
        value,
        "current_validation_observation_ids",
        validation_ids[:checkpoint],
    )
    object.__setattr__(value, "counters", counters)
    object.__setattr__(
        value,
        "_partial_row_id",
        _id(
            f"partial:{context_key}:{semantic_label}:{checkpoint}:"
            f"{planner_row_id}"
        ),
    )
    object.__setattr__(
        value,
        "_physical_evidence_id",
        _id(
            f"physical:{context_key}:{semantic_label}:{checkpoint}:"
            f"{planner_row_id}"
        ),
    )
    return value


def _execution(
    *,
    context: observer.PublicGraphContextV1,
    checkpoint: int,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    raw_registry: dict[
        tuple[str, tuple[str, int, str]],
        tuple[tuple[str, ...], tuple[str, ...]],
    ],
) -> campaign.CheckpointExecutionV1:
    physical_rows = []
    projections = []
    assert audit.failed_frontier is not None
    row_by_id = {item.row_id: item for item in model.rows}
    for planner_row_id in audit.failed_frontier.other_positive_row_ids:
        planner_row = row_by_id[planner_row_id]
        registry_key = (context.context_key, planner_row.row_key)
        discovery_ids, validation_ids = raw_registry[registry_key]
        physical = _physical_row(
            context_key=context.context_key,
            semantic_row_key=planner_row.row_key,
            checkpoint=checkpoint,
            planner_row_id=planner_row.row_id,
            discovery_ids=discovery_ids,
            validation_ids=validation_ids,
        )
        physical_rows.append(physical)
        projections.append(
            SimpleNamespace(
                planner_row=planner_row,
                partial_row_id=physical.partial_row_id,
                confidence_authority_id=(
                    physical.confidence_authority.authority_id
                ),
                support_epoch_id=(
                    physical.support_epoch.support_epoch_id
                ),
            )
        )
    value = object.__new__(campaign.CheckpointExecutionV1)
    object.__setattr__(value, "checkpoint", checkpoint)
    object.__setattr__(
        value,
        "closure",
        SimpleNamespace(
            context=context,
            all_rows=tuple(physical_rows),
        ),
    )
    object.__setattr__(
        value,
        "bridge",
        SimpleNamespace(
            quotient_model=model,
            row_projections=tuple(projections),
        ),
    )
    object.__setattr__(value, "threshold", threshold)
    object.__setattr__(value, "quotient_considered", True)
    object.__setattr__(value, "quotient_base_audit", audit)
    return value


@pytest.fixture(scope="module")
def miniature_source_archive():
    patcher = pytest.MonkeyPatch()
    source_campaign_id = _id("synthetic-v0068-campaign")
    source_verification_id = _id("synthetic-v0068-verification")
    patcher.setattr(
        campaign.ObservationSupportCampaignV1,
        "campaign_id",
        property(lambda _self: source_campaign_id),
    )
    patcher.setattr(
        campaign.ObservationSupportCampaignVerificationV1,
        "verification_id",
        property(lambda _self: source_verification_id),
    )
    patcher.setattr(
        campaign.CheckpointExecutionV1,
        "execution_id",
        property(
            lambda self: _id(
                "execution:"
                f"{self.closure.context.context_key}:{self.checkpoint}"
            )
        ),
    )
    base_before, base_after, _, _, _ = _source_models()
    contexts = {
        item.context_key: item
        for item in observer.registered_public_graph_contexts_v1()
    }
    context_results = []
    raw_registry: dict[
        tuple[str, tuple[str, int, str]],
        tuple[tuple[str, ...], tuple[str, ...]],
    ] = {}
    for context_key in campaign.REGISTERED_CONTEXT_ORDER:
        context = contexts[context_key]
        before_model = replace(
            base_before,
            context_id=context.context_id,
        )
        after_model = replace(
            base_after,
            context_id=context.context_id,
        )
        threshold = robust.RobustThresholdProfileV1(
            context.context_id,
            Fraction(1, 5),
            Fraction(1),
        )
        before_audit = robust.solve_quotient_robust_h2_v1(
            before_model,
            threshold,
        )
        after_audit = robust.solve_quotient_robust_h2_v1(
            after_model,
            threshold,
        )
        assert not before_audit.certified
        assert not after_audit.certified
        semantic_keys = {
            row.row_key
            for model, audit in (
                (before_model, before_audit),
                (after_model, after_audit),
            )
            for row in model.rows
            if (
                audit.failed_frontier is not None
                and row.row_id
                in audit.failed_frontier.other_positive_row_ids
            )
        }
        for semantic_key in semantic_keys:
            label = ":".join(map(str, semantic_key))
            discovery = tuple(
                _id(f"discovery:{context_key}:{label}:{index}")
                for index in range(acquisition.DISCOVERY_DRAW_COUNT)
            )
            validation = tuple(
                _id(f"validation:{context_key}:{label}:{index}")
                for index in range(max(campaign.REGISTERED_CHECKPOINTS))
            )
            raw_registry[(context_key, semantic_key)] = (
                discovery,
                validation,
            )
        executions = tuple(
            _execution(
                context=context,
                checkpoint=checkpoint,
                model=(
                    before_model if checkpoint == 2_048 else after_model
                ),
                audit=(
                    before_audit if checkpoint == 2_048 else after_audit
                ),
                threshold=threshold,
                raw_registry=raw_registry,
            )
            for checkpoint in campaign.REGISTERED_CHECKPOINTS
        )
        context_result = object.__new__(campaign.ContextCampaignResultV1)
        object.__setattr__(context_result, "context", context)
        object.__setattr__(context_result, "executions", executions)
        context_results.append(context_result)
    source_campaign = object.__new__(campaign.ObservationSupportCampaignV1)
    object.__setattr__(
        source_campaign,
        "context_results",
        tuple(context_results),
    )
    replayed_rows = tuple(
        sorted(
            {
                row.partial_row_id
                for result in context_results
                for execution in result.executions
                for row in execution.closure.all_rows
            }
        )
    )
    role_manifest = SimpleNamespace(
        campaign_id=source_campaign_id,
        bindings=tuple(
            SimpleNamespace(
                artifact_role="RAW_PARTIAL_SUPPORT_ROW_REPLAY",
                artifact_id=row_id,
            )
            for row_id in replayed_rows
        ),
    )
    source_verification = object.__new__(
        campaign.ObservationSupportCampaignVerificationV1
    )
    for field, value in (
        ("campaign_id", source_campaign_id),
        ("replayed_campaign_id", source_campaign_id),
        ("replayed_row_ids", replayed_rows),
        (
            "replayed_row_verification_ids",
            tuple(
                sorted(_id(f"row-verification:{row_id}") for row_id in replayed_rows)
            ),
        ),
        ("family_verification_id", _id("family-verification")),
        ("role_manifest", role_manifest),
        ("same_implementation_full_replay", True),
        ("independent_implementation_claimed", False),
        ("exact_iid_implementation_claimed", False),
        ("formal_exact_iid_plan_certificate", False),
        ("valid", True),
    ):
        object.__setattr__(source_verification, field, value)
    claimed = archive.freeze_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    yield source_campaign, source_verification, claimed
    patcher.undo()


def _verify(fixture, claimed=None):
    source_campaign, source_verification, baseline = fixture
    return independent.verify_source_acquisition_archive_independently_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
        claimed=baseline if claimed is None else claimed,
    )


def _replace_trial_graph(
    baseline: archive.VerifiedSourceAcquisitionArchiveV2,
    old: archive.VerifiedSourceLocalTrialV2,
    new: archive.VerifiedSourceLocalTrialV2,
) -> archive.VerifiedSourceAcquisitionArchiveV2:
    trials = tuple(
        sorted(
            (new if item is old else item for item in baseline.trials),
            key=lambda item: item.trial_id,
        )
    )
    pairs = tuple(
        sorted(
            (
                _unsafe_clone(
                    pair,
                    trial_ids=tuple(
                        sorted(
                            new.trial_id if item == old.trial_id else item
                            for item in pair.trial_ids
                        )
                    ),
                )
                for pair in baseline.adjacent_pairs
            ),
            key=lambda item: item.pair_id,
        )
    )
    aggregates, consensus = archive._derive_nonrectangular_consensus(trials)
    return _unsafe_clone(
        baseline,
        adjacent_pairs=pairs,
        trials=trials,
        context_feature_aggregates=aggregates,
        consensus=consensus,
    )


def test_independent_verifier_accepts_archive_without_production_replay(
    miniature_source_archive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("production archive helper was called")

    for name in (
        "freeze_verified_source_acquisition_archive_v2",
        "verify_verified_source_acquisition_archive_v2",
        "_derive_pair",
        "_derive_nonrectangular_consensus",
        "independent_fixed_policy_metrics_v2",
    ):
        monkeypatch.setattr(archive, name, forbidden)
    result = _verify(miniature_source_archive)
    assert result.valid
    assert result.registered_adjacent_pair_count == 7
    assert result.independent_archive_transform_verified
    assert result.independent_source_campaign_verifier_claimed is False
    assert result.source_campaign_verification_boundary == (
        independent.SOURCE_CAMPAIGN_VERIFICATION_BOUNDARY
    )
    assert result.archive_id == result.independently_recomputed_archive_id
    assert result.archive_id == miniature_source_archive[2].archive_id
    assert result.archive_document_digest == hashlib.sha256(
        b"acfqp:v072-independent-archive-document:v2\x00"
        + canonical_json_bytes(miniature_source_archive[2].to_document())
    ).hexdigest()


def test_coherently_resigned_trial_score_is_rejected(
    miniature_source_archive,
) -> None:
    baseline = miniature_source_archive[2]
    old = next(item for item in baseline.trials if item.slack_gain > 0)
    increment = Fraction(1, 10_000)
    new_roll_forward = replace(
        old.roll_forward_metrics,
        certificate_slack=(
            old.roll_forward_metrics.certificate_slack + increment
        ),
    )
    new_gain = old.slack_gain + increment
    new = replace(
        old,
        roll_forward_metrics=new_roll_forward,
        slack_gain=new_gain,
        gain_per_draw=new_gain / old.local_snapshot.incremental_draws,
    )
    forged = _replace_trial_graph(baseline, old, new)
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="roll-forward trial metrics|gain",
    ):
        _verify(miniature_source_archive, forged)


def test_coherently_resigned_pair_and_archive_ids_are_rejected(
    miniature_source_archive,
) -> None:
    baseline = miniature_source_archive[2]
    first_pair = baseline.adjacent_pairs[0]
    changed_pair = _unsafe_clone(
        first_pair,
        before_execution_id=_id("coherently-resigned-before-execution"),
    )
    changed_pairs = tuple(
        sorted(
            (
                changed_pair if item is first_pair else item
                for item in baseline.adjacent_pairs
            ),
            key=lambda item: item.pair_id,
        )
    )
    forged_pair = _unsafe_clone(baseline, adjacent_pairs=changed_pairs)
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="before_execution_id",
    ):
        _verify(miniature_source_archive, forged_pair)

    forged_archive = _unsafe_clone(
        baseline,
        source_family_id=_id("coherently-resigned-source-family"),
        source_training_split_id=_id(
            "coherently-resigned-source-training-split"
        ),
    )
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="family/training split",
    ):
        _verify(miniature_source_archive, forged_archive)


@pytest.mark.parametrize("mode", ("missing", "extra"))
def test_missing_or_extra_registered_pair_is_rejected(
    miniature_source_archive,
    mode: str,
) -> None:
    baseline = miniature_source_archive[2]
    pairs = (
        baseline.adjacent_pairs[:-1]
        if mode == "missing"
        else (*baseline.adjacent_pairs, baseline.adjacent_pairs[0])
    )
    forged = _unsafe_clone(baseline, adjacent_pairs=tuple(pairs))
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="pair",
    ):
        _verify(miniature_source_archive, forged)


def test_raw_prefix_swap_and_portable_feature_leakage_are_rejected(
    miniature_source_archive,
) -> None:
    baseline = miniature_source_archive[2]
    old = baseline.trials[0]
    proof = old.local_snapshot.raw_prefix_extension
    changed_proof = _unsafe_clone(
        proof,
        before_validation_ids_digest=proof.after_validation_ids_digest,
        after_validation_ids_digest=proof.before_validation_ids_digest,
    )
    changed_snapshot = replace(
        old.local_snapshot,
        raw_prefix_extension=changed_proof,
    )
    changed_trial = replace(old, local_snapshot=changed_snapshot)
    raw_forged = _replace_trial_graph(baseline, old, changed_trial)
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="raw-prefix",
    ):
        _verify(miniature_source_archive, raw_forged)

    leaked_feature = _unsafe_clone(
        old.portable_feature,
        stage_role=old.source_context_id,
    )
    leaked_snapshot = _unsafe_clone(
        old.local_snapshot,
        portable_feature_key=leaked_feature.feature_key,
    )
    leaked_trial = _unsafe_clone(
        old,
        portable_feature=leaked_feature,
        local_snapshot=leaked_snapshot,
    )
    leakage_forged = _replace_trial_graph(baseline, old, leaked_trial)
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="portable feature",
    ):
        _verify(miniature_source_archive, leakage_forged)


def _forged_consensus_from_aggregates(
    aggregates: tuple[archive.SourceContextFeatureAggregateV2, ...],
) -> tuple[archive.NonrectangularFeatureConsensusV2, ...]:
    grouped: dict[str, list[archive.SourceContextFeatureAggregateV2]] = {}
    for item in aggregates:
        grouped.setdefault(item.feature_key, []).append(item)
    results = []
    for feature_key, values in grouped.items():
        ordered = sorted(values, key=lambda item: item.source_context_id)
        ranks = [item.normalized_midrank for item in ordered]
        mean_rank = sum(ranks, Fraction(0)) / len(ranks)
        worst_rank = min(ranks)
        disagreement = mean_rank - worst_rank
        mean_gain = sum(
            (item.mean_gain_per_draw for item in ordered),
            Fraction(0),
        ) / len(ordered)
        any_degenerate = any(
            item.context_ranking_degenerate for item in ordered
        )
        disposition = (
            archive.FeatureConsensusDispositionV2
            .DEGENERATE_CONTEXT_RANKING
            if any_degenerate
            else (
                archive.FeatureConsensusDispositionV2
                .NONPOSITIVE_SOURCE_GAIN
                if mean_gain <= 0
                else (
                    archive.FeatureConsensusDispositionV2.HIGH_DISAGREEMENT
                    if disagreement > archive.MAX_MIDRANK_DISAGREEMENT
                    else archive.FeatureConsensusDispositionV2.APPLIED
                )
            )
        )
        multiplier = (
            archive.MIN_PRIOR_MULTIPLIER
            + (
                archive.MAX_PRIOR_MULTIPLIER
                - archive.MIN_PRIOR_MULTIPLIER
            )
            * mean_rank
            if disposition
            is archive.FeatureConsensusDispositionV2.APPLIED
            else archive.NEUTRAL_PRIOR_MULTIPLIER
        )
        results.append(
            archive.NonrectangularFeatureConsensusV2(
                feature_key,
                tuple(item.source_context_id for item in ordered),
                tuple(sorted(item.aggregate_id for item in ordered)),
                mean_gain,
                mean_rank,
                worst_rank,
                disagreement,
                any_degenerate,
                disposition,
                multiplier,
            )
        )
    return tuple(sorted(results, key=lambda item: item.consensus_id))


def test_context_transposed_ranks_and_resigned_consensus_are_rejected(
    miniature_source_archive,
) -> None:
    baseline = miniature_source_archive[2]
    context_id = baseline.context_feature_aggregates[0].source_context_id
    in_context = [
        item
        for item in baseline.context_feature_aggregates
        if item.source_context_id == context_id
    ]
    assert len(in_context) >= 2
    first, second = in_context[:2]
    forged_aggregates = tuple(
        sorted(
            (
                _unsafe_clone(
                    item,
                    normalized_midrank=(
                        second.normalized_midrank
                        if item is first
                        else (
                            first.normalized_midrank
                            if item is second
                            else item.normalized_midrank
                        )
                    ),
                )
                for item in baseline.context_feature_aggregates
            ),
            key=lambda item: item.aggregate_id,
        )
    )
    forged_consensus = _forged_consensus_from_aggregates(
        forged_aggregates
    )
    forged = _unsafe_clone(
        baseline,
        context_feature_aggregates=forged_aggregates,
        consensus=forged_consensus,
    )
    with pytest.raises(
        independent.IndependentSourceArchiveVerificationViolation,
        match="ranks/midranks|consensus",
    ):
        _verify(miniature_source_archive, forged)
