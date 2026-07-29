"""Independent replay of the V0-073 anytime adaptive development control.

The verifier reconstructs every target prefix, anytime checkpoint, confidence
row, robust audit, proposal decision, raw block slice, stopping event, draw
charge, and content identity.  It does not call the production control
builder, prefix/epoch constructors, decision preparer, or arm runner.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import math
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import sequential_bernoulli_acquisition_v1 as sequential
from acfqp import v073_certificate_boundary_voi_v1 as voi
from acfqp import (
    v073_certificate_boundary_voi_independent_verifier_v1
    as voi_independent,
)
from acfqp import v073_anytime_adaptive_acquisition_v1 as adaptive


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v073_anytime_adaptive_acquisition_independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    "acfqp:v073-anytime-adaptive-independent-attestation:v1"
)
DOMAINS = {
    "stream": "acfqp:v073-development-shared-target-row-stream:v1",
    "schedule": "acfqp:v073-anytime-block-schedule-profile:v1",
    "prefix": "acfqp:v073-target-row-prefix-checkpoint:v1",
    "epoch": "acfqp:v073-anytime-adaptive-model-epoch:v1",
    "decision": "acfqp:v073-pre-materialization-voi-decision:v1",
    "block": "acfqp:v073-executed-anytime-target-block:v1",
    "run": "acfqp:v073-anytime-adaptive-arm-run:v1",
    "control": "acfqp:v073-anytime-three-arm-control:v1",
}


class V073AnytimeAdaptiveIndependentVerificationFailure(ValueError):
    """The claimed adaptive control differs from exact independent replay."""


def _fail(message: str) -> None:
    raise V073AnytimeAdaptiveIndependentVerificationFailure(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V073AnytimeAdaptiveIndependentVerificationFailure(
            str(error)
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + body
    ).hexdigest()


def _id(role: str, payload: Mapping[str, Any]) -> str:
    return _hash(DOMAINS[role], payload)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V073AnytimeAdaptiveIndependentVerificationFailure(
            f"{field_name} is not one canonical content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("independent adaptive replay encountered inexact arithmetic")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _pack(values: tuple[bool, ...]) -> bytes:
    output = bytearray(math.ceil(len(values) / 8))
    for index, value in enumerate(values):
        if type(value) is not bool:
            _fail("shared raw target stream contains non-boolean data")
        if value:
            output[index // 8] |= 1 << (index % 8)
    return bytes(output)


def _stream_payload(
    stream: adaptive.DevelopmentSharedTargetRowStreamV1,
) -> dict[str, Any]:
    if (
        type(stream) is not adaptive.DevelopmentSharedTargetRowStreamV1
        or stream.remaining_horizon not in (1, 2)
        or len(stream.outcomes)
        != adaptive.INITIAL_DRAWS_PER_ROW + adaptive.BLOCK_SIZE
        or stream.initial_draw_count != adaptive.INITIAL_DRAWS_PER_ROW
        or stream.source_inputs != ()
        or stream.registered_target_evidence is not False
    ):
        _fail("shared target stream shape or evidence scope changed")
    packed = _pack(stream.outcomes)
    return {
        "schema": "acfqp.v073_development_shared_target_row_stream.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "context_id": stream.context_id,
        "remaining_horizon": stream.remaining_horizon,
        "outcome_count": len(stream.outcomes),
        "initial_draw_count": stream.initial_draw_count,
        "packed_outcomes_sha256": hashlib.sha256(packed).hexdigest(),
        "packed_outcomes_byte_count": len(packed),
        "source_inputs": [],
        "development_only": True,
        "registered_target_evidence": False,
    }


def _verify_schedule(
    schedule: adaptive.DevelopmentAnytimeBlockScheduleProfileV1,
) -> None:
    if (
        type(schedule)
        is not adaptive.DevelopmentAnytimeBlockScheduleProfileV1
        or type(schedule.sequential_profile)
        is not sequential.SequentialBernoulliProfileV1
        or schedule.family_alpha != Fraction(1, 100)
        or schedule.row_alpha != Fraction(1, 200)
        or schedule.row_obligation_count != 2
        or schedule.row_alpha * schedule.row_obligation_count
        != schedule.family_alpha
        or schedule.sequential_profile.confidence_alpha
        != schedule.row_alpha
        or schedule.sequential_profile.checkpoints != (128, 130)
        or schedule.sequential_profile.target_half_width
        != Fraction(1, 1000)
        or schedule.sequential_profile.boundary_grid_bits != 16
        or schedule.initial_draws_per_row != 128
        or schedule.block_size != 2
        or schedule.max_executed_blocks != 2
        or schedule.max_blocks_per_row != 1
        or schedule.confidence_accounting
        != (
            "ROW_FAMILY_ALPHA_PREALLOCATION_AND_ONE_ALPHA_VILLE_"
            "TIME_UNIFORM_NO_CHECKPOINT_SPENDING"
        )
        or schedule.stopping_rule
        != (
            "STOP_AT_FIRST_POSTBLOCK_ROBUST_PLAN_CERTIFICATE_"
            "ELSE_HARD_CAP"
        )
    ):
        _fail("shared anytime/alpha-spending schedule differs from replay")
    payload = {
        "schema": "acfqp.v073_anytime_block_schedule_profile.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "sequential_profile_id": schedule.sequential_profile.profile_id,
        "family_alpha": _fdoc(schedule.family_alpha),
        "row_alpha": _fdoc(schedule.row_alpha),
        "row_obligation_count": schedule.row_obligation_count,
        "initial_draws_per_row": schedule.initial_draws_per_row,
        "block_size": schedule.block_size,
        "max_executed_blocks": schedule.max_executed_blocks,
        "max_blocks_per_row": schedule.max_blocks_per_row,
        "confidence_accounting": schedule.confidence_accounting,
        "stopping_rule": schedule.stopping_rule,
        "unexecuted_blocks_charge_zero_draws": True,
    }
    if schedule.schedule_profile_id != _id("schedule", payload):
        _fail("schedule profile content identity does not replay")


def _expected_prefix(
    *,
    stream: adaptive.DevelopmentSharedTargetRowStreamV1,
    draw_count: int,
    schedule: adaptive.DevelopmentAnytimeBlockScheduleProfileV1,
) -> tuple[
    sequential.AnytimeBernoulliCheckpointV1,
    str,
    str,
    int,
]:
    raw = stream.outcomes[:draw_count]
    success_count = sum(raw)
    checkpoint = sequential.build_anytime_bernoulli_checkpoint_v1(
        draw_count,
        success_count,
        schedule.sequential_profile,
    )
    raw_hash = hashlib.sha256(_pack(raw)).hexdigest()
    payload = {
        "schema": "acfqp.v073_target_row_prefix_checkpoint.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "stream_id": stream.stream_id,
        "remaining_horizon": stream.remaining_horizon,
        "prefix_draw_count": draw_count,
        "success_count": success_count,
        "raw_prefix_sha256": raw_hash,
        "checkpoint": checkpoint.to_document(),
        "source_inputs": [],
        "target_local_counts_only": True,
    }
    return checkpoint, raw_hash, _id("prefix", payload), success_count


def _verify_prefix(
    claimed: adaptive.DevelopmentTargetRowPrefixV1,
    stream: adaptive.DevelopmentSharedTargetRowStreamV1,
    schedule: adaptive.DevelopmentAnytimeBlockScheduleProfileV1,
) -> None:
    if type(claimed) is not adaptive.DevelopmentTargetRowPrefixV1:
        _fail("row prefix has a noncanonical concrete type")
    checkpoint, raw_hash, prefix_id, successes = _expected_prefix(
        stream=stream,
        draw_count=claimed.prefix_draw_count,
        schedule=schedule,
    )
    if (
        claimed.stream_id != stream.stream_id
        or claimed.remaining_horizon != stream.remaining_horizon
        or claimed.success_count != successes
        or claimed.raw_prefix_sha256 != raw_hash
        or claimed.checkpoint != checkpoint
        or claimed.source_inputs != ()
        or claimed.prefix_id != prefix_id
    ):
        _fail("row prefix/checkpoint fails raw target replay")


def _rebuild_model_and_audit(
    *,
    prefixes: tuple[adaptive.DevelopmentTargetRowPrefixV1, ...],
    template: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustPlanAuditV1,
]:
    by_horizon = {item.remaining_horizon: item for item in prefixes}
    rows = []
    for row in template.rows:
        checkpoint = by_horizon[row.remaining_horizon].checkpoint
        rows.append(
            replace(
                row,
                masses=tuple(
                    robust.IntervalDestinationMassV1(
                        mass.destination_id,
                        (
                            1 - checkpoint.upper_probability
                            if mass.destination_id
                            == row.other_destination_id
                            else checkpoint.lower_probability
                        ),
                        (
                            1 - checkpoint.lower_probability
                            if mass.destination_id
                            == row.other_destination_id
                            else checkpoint.upper_probability
                        ),
                    )
                    for mass in row.masses
                ),
            )
        )
    model = robust.build_partial_support_model_v1(
        context_id=template.context_id,
        root_state_id=template.root_state_id,
        catalogues=template.catalogues,
        destinations=template.destinations,
        rows=rows,
        concretizer_entries=template.concretizer_entries,
    )
    audit = robust.solve_ground_direct_robust_h2_v1(model, threshold)
    robust.verify_robust_plan_audit_v1(model, threshold, audit)
    return model, audit


def _verify_epoch(
    *,
    claimed: adaptive.DevelopmentAnytimeAdaptiveEpochV1,
    expected_index: int,
    stream_by_horizon: Mapping[
        int, adaptive.DevelopmentSharedTargetRowStreamV1
    ],
    schedule: adaptive.DevelopmentAnytimeBlockScheduleProfileV1,
    template: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> None:
    if (
        type(claimed)
        is not adaptive.DevelopmentAnytimeAdaptiveEpochV1
        or claimed.epoch_index != expected_index
        or tuple(item.remaining_horizon for item in claimed.row_prefixes)
        != (1, 2)
        or claimed.source_inputs != ()
    ):
        _fail("adaptive epoch structure or source boundary changed")
    for prefix in claimed.row_prefixes:
        _verify_prefix(
            prefix,
            stream_by_horizon[prefix.remaining_horizon],
            schedule,
        )
    model, audit = _rebuild_model_and_audit(
        prefixes=claimed.row_prefixes,
        template=template,
        threshold=threshold,
    )
    if claimed.model != model or claimed.audit != audit:
        _fail("confidence model or robust audit differs from prefix replay")
    if audit.status is robust.RobustAuditStatus.CERTIFIED:
        if claimed.proof_dag is not None or claimed.row_evidence != ():
            _fail("certified epoch retained failed-proof acquisition evidence")
    else:
        if (
            type(claimed.proof_dag)
            is not voi.DevelopmentFailedProofDAGV1
            or len(claimed.row_evidence) != 2
        ):
            _fail("failed epoch lacks its proof DAG or row evidence")
        # This is the independently implemented V0-073 DAG verifier, not the
        # production DAG freezer.
        try:
            voi_independent._verify_dag(
                model, threshold, audit, claimed.proof_dag
            )
        except (
            voi_independent
            .V073CertificateBoundaryVOIIndependentVerificationFailure
        ) as error:
            raise V073AnytimeAdaptiveIndependentVerificationFailure(
                str(error)
            ) from error
        prefix_by_horizon = {
            item.remaining_horizon: item for item in claimed.row_prefixes
        }
        evidence_by_row = {
            item.row_id: item for item in claimed.row_evidence
        }
        if set(evidence_by_row) != {item.row_id for item in model.rows}:
            _fail("epoch evidence does not cover exactly the current rows")
        for row in model.rows:
            prefix = prefix_by_horizon[row.remaining_horizon]
            evidence = evidence_by_row[row.row_id]
            destinations = tuple(item.destination_id for item in row.masses)
            expected_counts = tuple(
                (
                    prefix.prefix_draw_count - prefix.success_count
                    if destination == row.other_destination_id
                    else prefix.success_count
                )
                for destination in destinations
            )
            if (
                evidence.context_id != model.context_id
                or evidence.model_id != model.model_id
                or evidence.row_id != row.row_id
                or evidence.evidence_epoch_id != prefix.prefix_id
                or evidence.destination_ids != destinations
                or evidence.counts != expected_counts
                or evidence.other_destination_id
                != row.other_destination_id
                or evidence.future_child_support_enumerated is not False
                or evidence.unobserved_outcomes_aggregated_into_other
                is not True
            ):
                _fail("current row evidence differs from raw prefix counts")
    payload = {
        "schema": "acfqp.v073_anytime_adaptive_model_epoch.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "epoch_index": expected_index,
        "row_prefix_ids": [
            item.prefix_id for item in claimed.row_prefixes
        ],
        "model_id": model.model_id,
        "audit_id": audit.audit_id,
        "audit_status": audit.status.value,
        "proof_dag_id": (
            None if claimed.proof_dag is None else claimed.proof_dag.dag_id
        ),
        "row_evidence_ids": [
            item.evidence_id for item in claimed.row_evidence
        ],
        "source_inputs": [],
        "confidence_authority": sequential.METHOD_ID,
    }
    if claimed.epoch_id != _id("epoch", payload):
        _fail("adaptive epoch content identity does not replay")


def _decision_payload(
    decision: adaptive.DevelopmentPreMaterializationDecisionV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v073_pre_materialization_voi_decision.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "arm": decision.arm.value,
        "round_index": decision.round_index,
        "pre_epoch_id": decision.pre_epoch_id,
        "proof_dag_id": decision.proof_dag_id,
        "eligible_horizons": list(decision.eligible_horizons),
        "exhausted_horizons": list(decision.exhausted_horizons),
        "selected_horizon": decision.selected_horizon,
        "selected_row_id": decision.selected_row_id,
        "selected_candidate_id": decision.selected_candidate_id,
        "voi_result_id": (
            None
            if decision.voi_result is None
            else decision.voi_result.result_id
        ),
        "source_prior_id": decision.source_prior_id,
        "selection_rule": (
            "FIRST_FIXED_HORIZON_WITH_REMAINING_BLOCK_BUDGET"
            if decision.arm
            is adaptive.DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2
            else (
                "FIRST_VOI_RANKED_CANDIDATE_WITH_REMAINING_"
                "BLOCK_BUDGET"
            )
        ),
        "access_events": list(decision.access_events),
        "target_reads_before_freeze": 0,
        "future_outcome_fields_used": [],
        "decision_frozen_before_materialization": True,
    }


def _verify_decision(
    *,
    claimed: adaptive.DevelopmentPreMaterializationDecisionV1,
    arm: adaptive.DevelopmentAnytimeArmV1,
    round_index: int,
    pre_epoch: adaptive.DevelopmentAnytimeAdaptiveEpochV1,
    exhausted: tuple[int, ...],
    source_trials: tuple[voi.DevelopmentSourceVOITrialV1, ...],
    source_prior: voi.DevelopmentSourceVOIPriorV1,
    threshold: robust.RobustThresholdProfileV1,
) -> int:
    if (
        type(claimed)
        is not adaptive.DevelopmentPreMaterializationDecisionV1
        or claimed.arm is not arm
        or claimed.round_index != round_index
        or pre_epoch.proof_dag is None
        or claimed.pre_epoch_id != pre_epoch.epoch_id
        or claimed.proof_dag_id != pre_epoch.proof_dag.dag_id
        or claimed.exhausted_horizons != tuple(sorted(exhausted))
        or claimed.eligible_horizons
        != tuple(item for item in (1, 2) if item not in exhausted)
        or claimed.target_reads_before_freeze != 0
        or claimed.future_outcome_fields_used != ()
    ):
        _fail("decision chronology, budget, or proof-DAG binding is stale")
    row_by_horizon = {
        item.remaining_horizon: item for item in pre_epoch.model.rows
    }
    replayed_fantasies = 0
    if arm is adaptive.DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2:
        expected_horizon = next(
            item for item in (1, 2) if item in claimed.eligible_horizons
        )
        if (
            claimed.voi_result is not None
            or claimed.selected_candidate_id is not None
            or claimed.source_prior_id is not None
            or claimed.access_events != adaptive.FIXED_DECISION_EVENTS
        ):
            _fail("fixed decision contains VOI/source/future inputs")
    else:
        if (
            type(claimed.voi_result)
            is not voi.DevelopmentCertificateBoundaryVOIResultV1
            or claimed.access_events != adaptive.VOI_DECISION_EVENTS
        ):
            _fail("VOI decision lacks its replayable pre-model result")
        if arm is adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI:
            if (
                claimed.voi_result.arm
                is not voi.DevelopmentVOIArmV1.NO_PRIOR
                or claimed.source_prior_id is not None
            ):
                _fail("target-only decision contains source evidence")
            try:
                attestation = (
                    voi_independent
                    .verify_v073_certificate_boundary_voi_result_v1(
                    result=claimed.voi_result,
                    model=pre_epoch.model,
                    threshold=threshold,
                    failed_audit=pre_epoch.audit,
                    proof_dag=pre_epoch.proof_dag,
                    row_evidence=pre_epoch.row_evidence,
                    )
                )
            except (
                voi_independent
                .V073CertificateBoundaryVOIIndependentVerificationFailure
            ) as error:
                raise V073AnytimeAdaptiveIndependentVerificationFailure(
                    str(error)
                ) from error
        else:
            if claimed.source_prior_id != source_prior.prior_id:
                _fail("source decision prior identity is missing or stale")
            try:
                attestation = (
                    voi_independent
                    .verify_v073_certificate_boundary_voi_result_v1(
                    result=claimed.voi_result,
                    model=pre_epoch.model,
                    threshold=threshold,
                    failed_audit=pre_epoch.audit,
                    proof_dag=pre_epoch.proof_dag,
                    row_evidence=pre_epoch.row_evidence,
                    source_trials=source_trials,
                    source_prior=source_prior,
                    )
                )
            except (
                voi_independent
                .V073CertificateBoundaryVOIIndependentVerificationFailure
            ) as error:
                raise V073AnytimeAdaptiveIndependentVerificationFailure(
                    str(error)
                ) from error
        replayed_fantasies = attestation.replayed_fantasy_count
        base_by_candidate = {
            item.candidate.candidate_id: item
            for item in claimed.voi_result.base_vois
        }
        expected_candidate = next(
            candidate_id
            for candidate_id
            in claimed.voi_result.schedule.ordered_candidate_ids
            if base_by_candidate[
                candidate_id
            ].candidate.remaining_horizon in claimed.eligible_horizons
        )
        expected_horizon = base_by_candidate[
            expected_candidate
        ].candidate.remaining_horizon
        if claimed.selected_candidate_id != expected_candidate:
            _fail("decision differs from first eligible exact VOI candidate")
    if (
        claimed.selected_horizon != expected_horizon
        or claimed.selected_row_id
        != row_by_horizon[expected_horizon].row_id
        or claimed.decision_id != _id(
            "decision", _decision_payload(claimed)
        )
    ):
        _fail("selected row or decision identity does not replay")
    return replayed_fantasies


def _block_payload(
    block: adaptive.DevelopmentExecutedAnytimeBlockV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v073_executed_anytime_target_block.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "decision_id": block.decision.decision_id,
        "pre_epoch_id": block.pre_epoch_id,
        "post_epoch_id": block.post_epoch_id,
        "stream_id": block.stream_id,
        "slice_start": block.slice_start,
        "slice_end": block.slice_end,
        "accepted_draws": block.accepted_draws,
        "accepted_successes": block.accepted_successes,
        "raw_slice_sha256": block.raw_slice_sha256,
        "stop_reason": block.stop_reason.value,
        "access_events": list(block.access_events),
        "decision_frozen_event_index": block.access_events.index(
            "DECISION_FROZEN"
        ),
        "first_target_read_event_index": block.access_events.index(
            "SELECTED_RAW_SUFFIX_READ"
        ),
        "unexecuted_draws_charged": 0,
    }


def _run_payload(
    run: adaptive.DevelopmentAnytimeAdaptiveArmRunV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v073_anytime_adaptive_arm_run.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "arm": run.arm.value,
        "schedule_profile_id": run.schedule_profile_id,
        "stream_ids": list(run.stream_ids),
        "threshold_profile_id": run.threshold_profile_id,
        "epoch_ids": [item.epoch_id for item in run.epochs],
        "decision_ids": [item.decision_id for item in run.decisions],
        "block_ids": [item.block_id for item in run.blocks],
        "source_prior_id": run.source_prior_id,
        "terminal_code": run.terminal_code.value,
        "common_initial_accepted_draws": (
            run.common_initial_accepted_draws
        ),
        "incremental_accepted_draws": run.incremental_accepted_draws,
        "total_accepted_draws": run.total_accepted_draws,
        "executed_block_count": len(run.blocks),
        "unexecuted_blocks_charged_draws": 0,
        "same_raw_stream_contract": True,
        "source_enters_counts_or_cs": False,
        "source_enters_fantasy_or_certificate": False,
        "registered_execution_allowed": False,
        "sample_saving_claimed": False,
        "sample_efficiency_gate_status": "NOT_RUN",
    }


def _verify_run(
    *,
    run: adaptive.DevelopmentAnytimeAdaptiveArmRunV1,
    streams: tuple[adaptive.DevelopmentSharedTargetRowStreamV1, ...],
    schedule: adaptive.DevelopmentAnytimeBlockScheduleProfileV1,
    template: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    source_trials: tuple[voi.DevelopmentSourceVOITrialV1, ...],
    source_prior: voi.DevelopmentSourceVOIPriorV1,
) -> tuple[int, int, int]:
    if (
        type(run) is not adaptive.DevelopmentAnytimeAdaptiveArmRunV1
        or len(run.blocks) not in (1, 2)
        or len(run.decisions) != len(run.blocks)
        or len(run.epochs) != len(run.blocks) + 1
        or run.schedule_profile_id != schedule.schedule_profile_id
        or run.stream_ids
        != tuple(sorted(item.stream_id for item in streams))
        or run.threshold_profile_id != threshold.threshold_profile_id
        or run.unexecuted_blocks_charged_draws != 0
        or run.registered_execution_allowed is not False
        or run.sample_saving_claimed is not False
        or run.sample_efficiency_gate_status != "NOT_RUN"
        or run.common_initial_accepted_draws
        != adaptive.COMMON_INITIAL_ACCEPTED_DRAWS
    ):
        _fail("arm run shape, shared contract, or Gate lock changed")
    if run.arm is adaptive.DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI:
        if run.source_prior_id != source_prior.prior_id:
            _fail("source run prior identity differs")
    elif run.source_prior_id is not None:
        _fail("non-source run binds source prior")
    stream_by_horizon = {
        item.remaining_horizon: item for item in streams
    }
    exhausted: tuple[int, ...] = ()
    fantasy_count = 0
    for index, epoch in enumerate(run.epochs):
        _verify_epoch(
            claimed=epoch,
            expected_index=index,
            stream_by_horizon=stream_by_horizon,
            schedule=schedule,
            template=template,
            threshold=threshold,
        )
    for index, (decision, block) in enumerate(
        zip(run.decisions, run.blocks, strict=True),
        start=1,
    ):
        pre = run.epochs[index - 1]
        post = run.epochs[index]
        fantasy_count += _verify_decision(
            claimed=decision,
            arm=run.arm,
            round_index=index,
            pre_epoch=pre,
            exhausted=exhausted,
            source_trials=source_trials,
            source_prior=source_prior,
            threshold=threshold,
        )
        stream = stream_by_horizon[decision.selected_horizon]
        prior_prefix = {
            item.remaining_horizon: item for item in pre.row_prefixes
        }[decision.selected_horizon]
        start = prior_prefix.prefix_draw_count
        end = start + adaptive.BLOCK_SIZE
        raw = stream.outcomes[start:end]
        expected_reason = (
            adaptive.DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK
            if post.audit.status is robust.RobustAuditStatus.CERTIFIED
            else adaptive.DevelopmentBlockStopReasonV1.CONTINUE_FAILED_PROOF
        )
        if (
            type(block)
            is not adaptive.DevelopmentExecutedAnytimeBlockV1
            or block.decision != decision
            or block.pre_epoch_id != pre.epoch_id
            or block.post_epoch_id != post.epoch_id
            or block.stream_id != stream.stream_id
            or block.slice_start != start
            or block.slice_end != end
            or block.accepted_draws != adaptive.BLOCK_SIZE
            or block.accepted_successes != sum(raw)
            or block.raw_slice_sha256
            != hashlib.sha256(_pack(raw)).hexdigest()
            or block.stop_reason is not expected_reason
            or block.access_events
            != decision.access_events + adaptive.POST_DECISION_EVENTS
            or block.access_events.index("DECISION_FROZEN")
            >= block.access_events.index("SELECTED_RAW_SUFFIX_READ")
            or block.unexecuted_draws_charged != 0
            or block.block_id != _id("block", _block_payload(block))
        ):
            _fail("executed block, early-stop chronology, or raw slice changed")
        post_prefix = {
            item.remaining_horizon: item for item in post.row_prefixes
        }
        for horizon in (1, 2):
            expected_count = (
                end
                if horizon == decision.selected_horizon
                else {
                    item.remaining_horizon: item
                    for item in pre.row_prefixes
                }[horizon].prefix_draw_count
            )
            if post_prefix[horizon].prefix_draw_count != expected_count:
                _fail("unselected row consumed or omitted target draws")
        exhausted = tuple(sorted((*exhausted, decision.selected_horizon)))
        if expected_reason is (
            adaptive.DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK
        ) and index != len(run.blocks):
            _fail("run continued after its first robust certificate")
    expected_terminal = (
        adaptive.DevelopmentRunTerminalCodeV1.PLAN_CERTIFIED
        if run.epochs[-1].audit.status is robust.RobustAuditStatus.CERTIFIED
        else (
            adaptive.DevelopmentRunTerminalCodeV1
            .BLOCK_BUDGET_EXHAUSTED_NONCERTIFICATE
        )
    )
    expected_incremental_draws = adaptive.BLOCK_SIZE * len(run.blocks)
    expected_total_draws = (
        adaptive.COMMON_INITIAL_ACCEPTED_DRAWS
        + expected_incremental_draws
    )
    if (
        run.terminal_code is not expected_terminal
        or run.incremental_accepted_draws != expected_incremental_draws
        or run.total_accepted_draws != expected_total_draws
        or run.run_id != _id("run", _run_payload(run))
    ):
        _fail("terminal stopping reason or accepted-draw total changed")
    return fantasy_count, expected_incremental_draws, expected_total_draws


@dataclass(frozen=True, slots=True)
class V073AnytimeAdaptiveIndependentAttestationV1:
    control_id: str
    run_ids: tuple[str, ...]
    replayed_block_count: int
    replayed_common_initial_accepted_draws: int
    replayed_incremental_accepted_draws: int
    replayed_total_accepted_draws: int
    replayed_voi_fantasy_count: int
    unexecuted_draws_verified_zero_charge: int
    shared_raw_stream_replay_passed: bool
    shared_confidence_contract_passed: bool
    decision_before_materialization_passed: bool
    earliest_certificate_stop_passed: bool
    source_proposal_only_passed: bool
    controller_stream_accounting_independently_reimplemented: bool
    planner_replay_boundary: str
    planner_algorithm_independence_claimed: bool
    registered_execution_allowed: bool = False
    sample_saving_claimed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        _cid(self.control_id, "adaptive attestation control")
        if (
            tuple(sorted(set(self.run_ids))) != self.run_ids
            or len(self.run_ids) != 3
            or self.replayed_block_count != 5
            or self.replayed_common_initial_accepted_draws != 768
            or self.replayed_incremental_accepted_draws != 10
            or self.replayed_total_accepted_draws != 778
            or self.replayed_voi_fantasy_count <= 0
            or self.unexecuted_draws_verified_zero_charge != 2
            or self.shared_raw_stream_replay_passed is not True
            or self.shared_confidence_contract_passed is not True
            or self.decision_before_materialization_passed is not True
            or self.earliest_certificate_stop_passed is not True
            or self.source_proposal_only_passed is not True
            or self.controller_stream_accounting_independently_reimplemented
            is not True
            or self.planner_replay_boundary
            != adaptive.PLANNER_REPLAY_BOUNDARY
            or self.planner_algorithm_independence_claimed is not False
            or self.registered_execution_allowed is not False
            or self.sample_saving_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            _fail("adaptive independent attestation is incomplete")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v073_anytime_adaptive_independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verification_profile": VERIFICATION_PROFILE,
            "control_id": self.control_id,
            "run_ids": list(self.run_ids),
            "replayed_block_count": self.replayed_block_count,
            "replayed_common_initial_accepted_draws": (
                self.replayed_common_initial_accepted_draws
            ),
            "replayed_incremental_accepted_draws": (
                self.replayed_incremental_accepted_draws
            ),
            "replayed_total_accepted_draws": (
                self.replayed_total_accepted_draws
            ),
            "replayed_voi_fantasy_count": (
                self.replayed_voi_fantasy_count
            ),
            "unexecuted_draws_verified_zero_charge": (
                self.unexecuted_draws_verified_zero_charge
            ),
            "shared_raw_stream_replay_passed": True,
            "shared_confidence_contract_passed": True,
            "decision_before_materialization_passed": True,
            "earliest_certificate_stop_passed": True,
            "source_proposal_only_passed": True,
            "controller_stream_accounting_independently_reimplemented": True,
            "planner_replay_boundary": adaptive.PLANNER_REPLAY_BOUNDARY,
            "planner_algorithm_independence_claimed": False,
            "registered_execution_allowed": False,
            "sample_saving_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def attestation_id(self) -> str:
        return _hash(VERIFICATION_DOMAIN, self._payload())


def verify_v073_anytime_three_arm_control_v1(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> V073AnytimeAdaptiveIndependentAttestationV1:
    """Independently replay the complete three-arm adaptive control."""

    if (
        type(control) is not adaptive.DevelopmentAnytimeThreeArmControlV1
        or type(control.structural_template_model)
        is not robust.PartialSupportIntervalModelV1
        or type(control.threshold) is not robust.RobustThresholdProfileV1
        or control.threshold.context_id
        != control.structural_template_model.context_id
        or control.threshold.risk_tolerance != adaptive.RISK_TOLERANCE
        or control.registered_execution_allowed is not False
        or control.registered_target_evidence is not False
        or control.sample_saving_claimed is not False
        or control.sample_efficiency_gate_status != "NOT_RUN"
        or control.independent_verifier_scope
        != adaptive.INDEPENDENT_VERIFIER_SCOPE
        or control.planner_replay_boundary
        != adaptive.PLANNER_REPLAY_BOUNDARY
        or control.planner_algorithm_independence_claimed is not False
    ):
        _fail("control type, threshold, or locked claim boundary changed")
    _verify_schedule(control.schedule_profile)
    if (
        type(control.streams) is not tuple
        or tuple(item.remaining_horizon for item in control.streams) != (1, 2)
    ):
        _fail("control does not contain exactly the two shared row streams")
    for stream in control.streams:
        payload = _stream_payload(stream)
        if (
            stream.context_id
            != control.structural_template_model.context_id
            or stream.stream_id != _id("stream", payload)
        ):
            _fail("shared raw target stream identity does not replay")
    expected_arms = tuple(adaptive.DevelopmentAnytimeArmV1)
    if tuple(item.arm for item in control.runs) != expected_arms:
        _fail("three-arm order or coverage changed")
    total_fantasies = 0
    total_incremental_draws = 0
    total_all_draws = 0
    for run in control.runs:
        fantasies, incremental_draws, all_draws = _verify_run(
            run=run,
            streams=control.streams,
            schedule=control.schedule_profile,
            template=control.structural_template_model,
            threshold=control.threshold,
            source_trials=control.source_trials,
            source_prior=control.source_prior,
        )
        total_fantasies += fantasies
        total_incremental_draws += incremental_draws
        total_all_draws += all_draws
    expected_incremental_draw_result = (
        (adaptive.DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2.value, 4),
        (adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI.value, 2),
        (adaptive.DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI.value, 4),
    )
    expected_total_draw_result = (
        (adaptive.DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2.value, 260),
        (adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI.value, 258),
        (adaptive.DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI.value, 260),
    )
    if (
        control.incremental_accepted_draw_result
        != expected_incremental_draw_result
        or tuple(
            (item.arm.value, item.incremental_accepted_draws)
            for item in control.runs
        )
        != expected_incremental_draw_result
        or control.total_accepted_draw_result
        != expected_total_draw_result
        or tuple(
            (item.arm.value, item.total_accepted_draws)
            for item in control.runs
        )
        != expected_total_draw_result
        or control.runs[0].epochs[0] != control.runs[1].epochs[0]
        or control.runs[0].epochs[0] != control.runs[2].epochs[0]
        or control.runs[0].epochs[-1] != control.runs[2].epochs[-1]
        or control.runs[0].decisions[0].selected_horizon != 1
        or control.runs[1].decisions[0].selected_horizon != 2
        or control.runs[2].decisions[0].selected_horizon != 1
    ):
        _fail("shared-stream matched result or development draw totals changed")
    payload = {
        "schema": "acfqp.v073_anytime_three_arm_control.v1",
        "schema_version": adaptive.SCHEMA_VERSION,
        "proposed_contract_version": adaptive.PROPOSED_CONTRACT_VERSION,
        "profile_key": adaptive.PROFILE_KEY,
        "structural_template_model_id": (
            control.structural_template_model.model_id
        ),
        "stream_ids": [item.stream_id for item in control.streams],
        "schedule_profile_id": (
            control.schedule_profile.schedule_profile_id
        ),
        "threshold_profile_id": control.threshold.threshold_profile_id,
        "source_trial_ids": [
            item.trial_id for item in control.source_trials
        ],
        "source_prior_id": control.source_prior.prior_id,
        "run_ids": [item.run_id for item in control.runs],
        "common_initial_accepted_draws_per_arm": (
            adaptive.COMMON_INITIAL_ACCEPTED_DRAWS
        ),
        "incremental_accepted_draw_result": [
            {"arm": arm, "accepted_draws": draws}
            for arm, draws in expected_incremental_draw_result
        ],
        "total_accepted_draw_result": [
            {"arm": arm, "accepted_draws": draws}
            for arm, draws in expected_total_draw_result
        ],
        "shared_raw_streams": True,
        "shared_confidence_contract": True,
        "source_enters_only_proposal_rank": True,
        "unexecuted_blocks_charge_zero_draws": True,
        "development_only": True,
        "registered_execution_allowed": False,
        "registered_target_evidence": False,
        "sample_saving_claimed": False,
        "sample_efficiency_gate_status": "NOT_RUN",
        "independent_verifier_scope": adaptive.INDEPENDENT_VERIFIER_SCOPE,
        "planner_replay_boundary": adaptive.PLANNER_REPLAY_BOUNDARY,
        "planner_algorithm_independence_claimed": False,
    }
    if control.control_id != _id("control", payload):
        _fail("three-arm control content identity does not replay")
    return V073AnytimeAdaptiveIndependentAttestationV1(
        control_id=control.control_id,
        run_ids=tuple(sorted(item.run_id for item in control.runs)),
        replayed_block_count=sum(len(item.blocks) for item in control.runs),
        replayed_common_initial_accepted_draws=(
            adaptive.COMMON_INITIAL_ACCEPTED_DRAWS * len(control.runs)
        ),
        replayed_incremental_accepted_draws=total_incremental_draws,
        replayed_total_accepted_draws=total_all_draws,
        replayed_voi_fantasy_count=total_fantasies,
        unexecuted_draws_verified_zero_charge=2,
        shared_raw_stream_replay_passed=True,
        shared_confidence_contract_passed=True,
        decision_before_materialization_passed=True,
        earliest_certificate_stop_passed=True,
        source_proposal_only_passed=True,
        controller_stream_accounting_independently_reimplemented=True,
        planner_replay_boundary=adaptive.PLANNER_REPLAY_BOUNDARY,
        planner_algorithm_independence_claimed=False,
    )


__all__ = [
    "verify_v073_anytime_three_arm_control_v1",
    "V073AnytimeAdaptiveIndependentAttestationV1",
    "V073AnytimeAdaptiveIndependentVerificationFailure",
]
