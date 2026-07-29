"""Independent exact replay for the V0-073 development VOI slice.

This verifier intentionally does not call the production scorer, source-prior
builder, proof-DAG freezer, candidate derivation, KT helpers, fantasy-model
helper, or base-VOI helper.  It reconstructs their arithmetic and identities
from the typed inputs, then replays the existing audited H=2 robust planner for
every proposal-only fantasy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import math
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v073_certificate_boundary_voi_v1 as voi


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v073_certificate_boundary_voi_independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    "acfqp:v073-independent-voi-attestation:v1"
)

# Literal copies are deliberate: changing a production domain without changing
# this verifier must break replay.
DOMAINS = {
    "portable_feature": "acfqp:v073-portable-voi-feature:v1",
    "source_trial": "acfqp:v073-source-voi-trial:v1",
    "source_entry": "acfqp:v073-source-voi-prior-entry:v1",
    "source_prior": "acfqp:v073-source-voi-prior:v1",
    "dag_risk": "acfqp:v073-failed-proof-risk-node:v1",
    "dag_regret": "acfqp:v073-failed-proof-regret-node:v1",
    "dag_root": "acfqp:v073-failed-proof-gap-node:v1",
    "dag": "acfqp:v073-failed-proof-dag:v1",
    "candidate": "acfqp:v073-certificate-boundary-voi-candidate:v1",
    "fantasy": "acfqp:v073-kt-proof-gap-fantasy:v1",
    "base": "acfqp:v073-target-only-base-voi:v1",
    "arm_score": "acfqp:v073-proposal-only-arm-voi-score:v1",
    "schedule": "acfqp:v073-voi-candidate-schedule:v1",
    "result": "acfqp:v073-development-voi-result:v1",
    "control": "acfqp:v073-development-voi-opportunity-control:v1",
}


class V073CertificateBoundaryVOIIndependentVerificationFailure(ValueError):
    """The submitted development bundle differs from independent replay."""


def _fail(message: str) -> None:
    raise V073CertificateBoundaryVOIIndependentVerificationFailure(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V073CertificateBoundaryVOIIndependentVerificationFailure(
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
        raise V073CertificateBoundaryVOIIndependentVerificationFailure(
            f"{field_name} is not one canonical SHA-256 ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("independent replay encountered inexact arithmetic")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _proof_gap(
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    return max(
        Fraction(0),
        audit.root_failure_upper - threshold.risk_tolerance,
        audit.normalized_regret_upper
        - threshold.normalized_regret_tolerance,
    )


def _portable_feature(
    remaining_horizon: int,
    category: robust.SelectedRowCategory,
) -> str:
    return _id(
        "portable_feature",
        {
            "schema": "acfqp.v073_portable_voi_feature.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "remaining_horizon": remaining_horizon,
            "selected_row_category": category.value,
            "context_id_absent": True,
            "row_id_absent": True,
            "sample_count_absent": True,
            "probability_absent": True,
            "target_role_absent": True,
        },
    )


def _trial_payload(
    trial: voi.DevelopmentSourceVOITrialV1,
) -> dict[str, Any]:
    if (
        type(trial) is not voi.DevelopmentSourceVOITrialV1
        or trial.target_context_id is not None
        or trial.target_model_id is not None
        or trial.target_audit_id is not None
        or trial.target_outcome_used is not False
        or type(trial.source_utility) is not Fraction
    ):
        _fail("source trial contains target evidence")
    _cid(trial.source_context_id, "source context")
    _cid(trial.feature_key, "source feature")
    return {
        "schema": "acfqp.v073_source_voi_trial.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "source_context_id": trial.source_context_id,
        "feature_key": trial.feature_key,
        "source_utility": _fdoc(trial.source_utility),
        "target_context_id": None,
        "target_model_id": None,
        "target_audit_id": None,
        "target_outcome_used": False,
        "proposal_only": True,
    }


def _midranks(values: Mapping[str, Fraction]) -> dict[str, Fraction]:
    ordered = sorted(values, key=lambda key: (values[key], key))
    if len(ordered) < 2:
        _fail("source context has fewer than two features")
    output: dict[str, Fraction] = {}
    for key in ordered:
        tied_positions = tuple(
            index
            for index, candidate in enumerate(ordered)
            if values[candidate] == values[key]
        )
        output[key] = (
            sum((Fraction(index) for index in tied_positions), Fraction(0))
            / len(tied_positions)
            / (len(ordered) - 1)
        )
    return output


def _verify_source_prior(
    trials: tuple[voi.DevelopmentSourceVOITrialV1, ...],
    prior: voi.DevelopmentSourceVOIPriorV1,
    target_context_id: str,
) -> dict[str, Fraction]:
    if (
        type(trials) is not tuple
        or type(prior) is not voi.DevelopmentSourceVOIPriorV1
        or len(trials) < 4
    ):
        _fail("source prior inputs have noncanonical types")
    trial_ids = {}
    pair_trials = {}
    by_context: dict[str, dict[str, Fraction]] = {}
    for trial in trials:
        payload = _trial_payload(trial)
        trial_id = _id("source_trial", payload)
        if trial.trial_id != trial_id or trial_id in trial_ids:
            _fail("source trial identity does not replay")
        trial_ids[trial_id] = trial
        pair = trial.source_context_id, trial.feature_key
        if pair in pair_trials:
            _fail("duplicated source context/feature trial")
        pair_trials[pair] = trial_id
        by_context.setdefault(trial.source_context_id, {})[
            trial.feature_key
        ] = trial.source_utility
    contexts = tuple(sorted(by_context))
    features = tuple(
        sorted({feature for values in by_context.values() for feature in values})
    )
    if (
        len(contexts) < 2
        or len(features) < 2
        or target_context_id in contexts
        or any(tuple(sorted(values)) != features for values in by_context.values())
    ):
        _fail("source/target disjoint rectangular coverage does not replay")
    ranks = {
        context: _midranks(by_context[context]) for context in contexts
    }
    expected_entries = {}
    q_by_feature = {}
    for feature in features:
        feature_ranks = tuple(ranks[context][feature] for context in contexts)
        q = sum(feature_ranks, Fraction(0)) / len(feature_ranks)
        trial_refs = tuple(
            sorted(pair_trials[(context, feature)] for context in contexts)
        )
        payload = {
            "schema": "acfqp.v073_source_voi_prior_entry.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "feature_key": feature,
            "q": _fdoc(q),
            "worst_midrank": _fdoc(min(feature_ranks)),
            "source_context_count": len(contexts),
            "source_trial_ids": list(trial_refs),
            "may_certify": False,
        }
        expected_entries[feature] = (
            q,
            min(feature_ranks),
            trial_refs,
            _id("source_entry", payload),
        )
        q_by_feature[feature] = q
    actual_entries = {entry.feature_key: entry for entry in prior.entries}
    if set(actual_entries) != set(expected_entries):
        _fail("source prior feature set differs from replay")
    for feature, (q, worst, refs, entry_id) in expected_entries.items():
        entry = actual_entries[feature]
        if (
            type(entry) is not voi.DevelopmentSourceVOIPriorEntryV1
            or entry.q != q
            or entry.worst_midrank != worst
            or entry.source_context_count != len(contexts)
            or entry.source_trial_ids != refs
            or entry.entry_id != entry_id
        ):
            _fail("source prior entry differs from exact midrank replay")
    source_trial_ids = tuple(sorted(trial_ids))
    payload = {
        "schema": "acfqp.v073_source_voi_prior.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "source_context_ids": list(contexts),
        "source_trial_ids": list(source_trial_ids),
        "entry_ids": [
            expected_entries[feature][3] for feature in features
        ],
        "target_context_ids": [],
        "target_quantities_used": [],
        "may_certify": False,
        "may_narrow_confidence": False,
    }
    if (
        prior.source_context_ids != contexts
        or prior.source_trial_ids != source_trial_ids
        or prior.target_context_ids != ()
        or prior.may_certify is not False
        or prior.may_narrow_confidence is not False
        or prior.prior_id != _id("source_prior", payload)
    ):
        _fail("source prior identity or authority differs from replay")
    return q_by_feature


def _verify_dag(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    audit: robust.RobustPlanAuditV1,
    dag: voi.DevelopmentFailedProofDAGV1,
) -> Fraction:
    if (
        type(dag) is not voi.DevelopmentFailedProofDAGV1
        or audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
    ):
        _fail("failed-proof DAG lacks one failed audit")
    robust.verify_robust_plan_audit_v1(model, threshold, audit)
    risk_id = _id(
        "dag_risk",
        {
            "schema": "acfqp.v073_failed_proof_risk_node.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "model_id": model.model_id,
            "audit_id": audit.audit_id,
            "selected_row_bound_ids": [
                item.row_bound_id for item in audit.selected_row_bounds
            ],
            "root_failure_upper": _fdoc(audit.root_failure_upper),
            "risk_tolerance": _fdoc(threshold.risk_tolerance),
            "source_prior_inputs": [],
        },
    )
    regret_id = _id(
        "dag_regret",
        {
            "schema": "acfqp.v073_failed_proof_regret_node.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "model_id": model.model_id,
            "audit_id": audit.audit_id,
            "selected_row_bound_ids": [
                item.row_bound_id for item in audit.selected_row_bounds
            ],
            "normalized_regret_upper": _fdoc(
                audit.normalized_regret_upper
            ),
            "normalized_regret_tolerance": _fdoc(
                threshold.normalized_regret_tolerance
            ),
            "source_prior_inputs": [],
        },
    )
    gap = _proof_gap(audit, threshold)
    gap_id = _id(
        "dag_root",
        {
            "schema": "acfqp.v073_failed_proof_gap_node.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "ordered_parent_ids": [risk_id, regret_id],
            "current_proof_gap": _fdoc(gap),
            "source_prior_inputs": [],
        },
    )
    payload = {
        "schema": "acfqp.v073_failed_proof_dag.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "model_id": model.model_id,
        "threshold_profile_id": threshold.threshold_profile_id,
        "audit_id": audit.audit_id,
        "frontier_id": audit.failed_frontier.frontier_id,
        "selected_row_ids": list(audit.failed_frontier.selected_row_ids),
        "risk_node_id": risk_id,
        "regret_node_id": regret_id,
        "gap_node_id": gap_id,
        "current_proof_gap": _fdoc(gap),
        "source_prior_inputs": [],
    }
    if (
        gap <= 0
        or dag.model_id != model.model_id
        or dag.threshold_profile_id != threshold.threshold_profile_id
        or dag.audit_id != audit.audit_id
        or dag.frontier_id != audit.failed_frontier.frontier_id
        or dag.selected_row_ids != audit.failed_frontier.selected_row_ids
        or dag.risk_node_id != risk_id
        or dag.regret_node_id != regret_id
        or dag.gap_node_id != gap_id
        or dag.current_proof_gap != gap
        or dag.dag_id != _id("dag", payload)
    ):
        _fail("failed-proof DAG is stale or transplanted")
    return gap


def _compositions(total: int, width: int) -> tuple[tuple[int, ...], ...]:
    if width == 1:
        return ((total,),)
    return tuple(
        (first, *suffix)
        for first in range(total + 1)
        for suffix in _compositions(total - first, width - 1)
    )


def _rising(start: Fraction, count: int) -> Fraction:
    product = Fraction(1)
    for offset in range(count):
        product *= start + offset
    return product


def _kt_probability(
    current: tuple[int, ...],
    additional: tuple[int, ...],
) -> Fraction:
    block = sum(additional)
    result = Fraction(math.factorial(block))
    for value in additional:
        result /= math.factorial(value)
    for count, value in zip(current, additional):
        result *= _rising(Fraction(count) + Fraction(1, 2), value)
    return result / _rising(
        Fraction(sum(current)) + Fraction(len(current), 2),
        block,
    )


def _point_model(
    model: robust.PartialSupportIntervalModelV1,
    row_id: str,
    destination_ids: tuple[str, ...],
    masses: tuple[Fraction, ...],
) -> robust.PartialSupportIntervalModelV1:
    rows = {row.row_id: row for row in model.rows}
    row = rows.get(row_id)
    if (
        row is None
        or tuple(item.destination_id for item in row.masses)
        != destination_ids
    ):
        _fail("fantasy support differs from current row support")
    point_row = replace(
        row,
        masses=tuple(
            robust.IntervalDestinationMassV1(destination, mass, mass)
            for destination, mass in zip(destination_ids, masses)
        ),
    )
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=tuple(
            point_row if item.row_id == row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )


def _solve(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> robust.RobustPlanAuditV1:
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        return robust.solve_ground_direct_robust_h2_v1(model, threshold)
    return robust.solve_quotient_robust_h2_v1(model, threshold)


def _candidate_payload(
    *,
    row: robust.IntervalSimplexRowV1,
    provenance: robust.SelectedRowProvenanceV1,
    evidence: voi.CurrentRowCountEvidenceV1,
) -> tuple[dict[str, Any], str]:
    feature = _portable_feature(row.remaining_horizon, provenance.category)
    payload = {
        "schema": "acfqp.v073_certificate_boundary_voi_candidate.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "row_id": row.row_id,
        "state_id": row.state_id,
        "action_id": row.action_id,
        "remaining_horizon": row.remaining_horizon,
        "selected_row_category": provenance.category.value,
        "feature_key": feature,
        "row_evidence_id": evidence.evidence_id,
        "other_destination_id": row.other_destination_id,
        "derived_from_failed_frontier": True,
        "future_child_support_enumerated": False,
    }
    return payload, _id("candidate", payload)


def _fantasy_payload(
    *,
    candidate_id: str,
    evidence: voi.CurrentRowCountEvidenceV1,
    block_size: int,
    additional: tuple[int, ...],
    probability: Fraction,
    point_masses: tuple[Fraction, ...],
    fantasy_model: robust.PartialSupportIntervalModelV1,
    fantasy_audit: robust.RobustPlanAuditV1,
    gap_after: Fraction,
    reduction: Fraction,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v073_kt_proof_gap_fantasy.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "row_evidence_id": evidence.evidence_id,
        "next_block_size": block_size,
        "destination_ids": list(evidence.destination_ids),
        "additional_counts": list(additional),
        "predictive_probability": _fdoc(probability),
        "posterior_predictive_masses": [
            _fdoc(value) for value in point_masses
        ],
        "fantasy_model_id": fantasy_model.model_id,
        "fantasy_audit_id": fantasy_audit.audit_id,
        "proof_gap_after": _fdoc(gap_after),
        "proof_gap_reduction": _fdoc(reduction),
        "would_certify_in_proposal_fantasy": (
            fantasy_audit.status is robust.RobustAuditStatus.CERTIFIED
            and gap_after == 0
        ),
        "other_destination_id": evidence.other_destination_id,
        "unknown_child_destination_ids": [],
        "source_prior_inputs": [],
        "certificate_authority": False,
    }


def _verify_result(
    *,
    result: voi.DevelopmentCertificateBoundaryVOIResultV1,
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    audit: robust.RobustPlanAuditV1,
    dag: voi.DevelopmentFailedProofDAGV1,
    evidence_tuple: tuple[voi.CurrentRowCountEvidenceV1, ...],
    q_by_feature: Mapping[str, Fraction],
    source_prior_id: str | None,
) -> int:
    if (
        type(result) is not voi.DevelopmentCertificateBoundaryVOIResultV1
        or audit.failed_frontier is None
        or result.context_id != model.context_id
        or result.model_id != model.model_id
        or result.threshold_profile_id != threshold.threshold_profile_id
        or result.failed_audit_id != audit.audit_id
        or result.proof_dag_id != dag.dag_id
        or result.row_evidence_ids
        != tuple(sorted(item.evidence_id for item in evidence_tuple))
        or result.source_prior_id != source_prior_id
        or any(
            value != 0
            for value in (
                result.target_observer_calls,
                result.target_draws,
                result.kernel_calls,
                result.materializer_calls,
            )
        )
        or result.registered_target_evidence is not False
        or result.sample_saving_claimed is not False
        or result.sample_efficiency_gate_status != "NOT_RUN"
    ):
        _fail("result identity, access log, or locked Gate is invalid")
    if (
        result.arm is voi.DevelopmentVOIArmV1.NO_PRIOR
        and source_prior_id is not None
    ) or (
        result.arm is voi.DevelopmentVOIArmV1.SOURCE_META_PRIOR
        and source_prior_id is None
    ):
        _fail("result arm/source binding is invalid")

    rows = {item.row_id: item for item in model.rows}
    provenance = {item.row_id: item for item in audit.selected_row_provenance}
    evidence_by_row = {item.row_id: item for item in evidence_tuple}
    if (
        len(evidence_by_row) != len(evidence_tuple)
        or tuple(sorted(evidence_by_row))
        != audit.failed_frontier.other_positive_row_ids
    ):
        _fail("row evidence is not exactly the OTHER-positive frontier")
    actual_base = {
        item.candidate.row_id: item for item in result.base_vois
    }
    if set(actual_base) != set(evidence_by_row):
        _fail("base VOI candidate rows differ from failed frontier")

    expected_base_ids = {}
    expected_candidate_ids = {}
    base_values = {}
    fantasy_count = 0
    for row_id in audit.failed_frontier.other_positive_row_ids:
        row = rows[row_id]
        row_provenance = provenance[row_id]
        evidence = evidence_by_row[row_id]
        destination_ids = tuple(item.destination_id for item in row.masses)
        if (
            type(evidence) is not voi.CurrentRowCountEvidenceV1
            or evidence.context_id != model.context_id
            or evidence.model_id != model.model_id
            or evidence.destination_ids != destination_ids
            or evidence.other_destination_id != row.other_destination_id
            or evidence.future_child_support_enumerated is not False
            or evidence.unobserved_outcomes_aggregated_into_other is not True
        ):
            _fail("row count evidence leaks support or mismatches model")
        candidate_payload, candidate_id = _candidate_payload(
            row=row,
            provenance=row_provenance,
            evidence=evidence,
        )
        base = actual_base[row_id]
        candidate = base.candidate
        if (
            type(candidate) is not voi.DevelopmentVOICandidateV1
            or candidate.candidate_id != candidate_id
            or candidate.row_id != row.row_id
            or candidate.state_id != row.state_id
            or candidate.action_id != row.action_id
            or candidate.remaining_horizon != row.remaining_horizon
            or candidate.selected_row_category != row_provenance.category
            or candidate.feature_key
            != candidate_payload["feature_key"]
            or candidate.row_evidence_id != evidence.evidence_id
            or candidate.other_destination_id != row.other_destination_id
        ):
            _fail("candidate differs from exact frontier derivation")
        expected_candidate_ids[row_id] = candidate_id
        actual_fantasies = {
            item.additional_counts: item for item in base.fantasies
        }
        compositions = _compositions(
            result.next_block_size, len(destination_ids)
        )
        if set(actual_fantasies) != set(compositions):
            _fail("fantasy count composition coverage is incomplete")
        expected_fantasy_ids = []
        expected_reduction = Fraction(0)
        cert_probability = Fraction(0)
        probability_sum = Fraction(0)
        for additional in compositions:
            fantasy_count += 1
            probability = _kt_probability(evidence.counts, additional)
            denominator = (
                sum(evidence.counts)
                + result.next_block_size
                + Fraction(len(evidence.counts), 2)
            )
            point_masses = tuple(
                (count + extra + Fraction(1, 2)) / denominator
                for count, extra in zip(evidence.counts, additional)
            )
            fantasy_model = _point_model(
                model, row_id, destination_ids, point_masses
            )
            fantasy_audit = _solve(
                fantasy_model, threshold, audit.solver_kind
            )
            robust.verify_robust_plan_audit_v1(
                fantasy_model, threshold, fantasy_audit
            )
            gap_after = _proof_gap(fantasy_audit, threshold)
            reduction = max(
                Fraction(0), dag.current_proof_gap - gap_after
            )
            payload = _fantasy_payload(
                candidate_id=candidate_id,
                evidence=evidence,
                block_size=result.next_block_size,
                additional=additional,
                probability=probability,
                point_masses=point_masses,
                fantasy_model=fantasy_model,
                fantasy_audit=fantasy_audit,
                gap_after=gap_after,
                reduction=reduction,
            )
            expected_id = _id("fantasy", payload)
            fantasy = actual_fantasies[additional]
            if (
                type(fantasy) is not voi.DevelopmentKTFantasyV1
                or fantasy.fantasy_id != expected_id
                or fantasy.candidate_id != candidate_id
                or fantasy.row_evidence_id != evidence.evidence_id
                or fantasy.next_block_size != result.next_block_size
                or fantasy.destination_ids != destination_ids
                or fantasy.predictive_probability != probability
                or fantasy.posterior_predictive_masses != point_masses
                or fantasy.fantasy_model_id != fantasy_model.model_id
                or fantasy.fantasy_audit_id != fantasy_audit.audit_id
                or fantasy.proof_gap_after != gap_after
                or fantasy.proof_gap_reduction != reduction
                or fantasy.would_certify_in_proposal_fantasy
                != payload["would_certify_in_proposal_fantasy"]
                or fantasy.other_destination_id
                != evidence.other_destination_id
                or fantasy.unknown_child_destination_ids != ()
                or fantasy.source_prior_inputs != ()
                or fantasy.certificate_authority is not False
            ):
                _fail("fantasy differs from independent KT/planner replay")
            expected_fantasy_ids.append(expected_id)
            probability_sum += probability
            expected_reduction += probability * reduction
            if payload["would_certify_in_proposal_fantasy"]:
                cert_probability += probability
        if probability_sum != 1:
            _fail("independent KT fantasy law is not normalized")
        expected_fantasy_ids.sort()
        base_payload = {
            "schema": "acfqp.v073_target_only_base_voi.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "proof_dag_id": dag.dag_id,
            "next_block_size": result.next_block_size,
            "fantasy_ids": expected_fantasy_ids,
            "current_proof_gap": _fdoc(dag.current_proof_gap),
            "expected_gap_reduction": _fdoc(expected_reduction),
            "base_voi_per_draw": _fdoc(
                expected_reduction / result.next_block_size
            ),
            "certifying_fantasy_probability": _fdoc(cert_probability),
            "predictive_kind": "JEFFREYS_KT_DIRICHLET_MULTINOMIAL",
            "source_prior_inputs": [],
            "certificate_authority": False,
        }
        base_id = _id("base", base_payload)
        if (
            base.base_voi_id != base_id
            or tuple(item.fantasy_id for item in base.fantasies)
            != tuple(expected_fantasy_ids)
            or base.proof_dag_id != dag.dag_id
            or base.next_block_size != result.next_block_size
            or base.current_proof_gap != dag.current_proof_gap
            or base.expected_gap_reduction != expected_reduction
            or base.base_voi_per_draw
            != expected_reduction / result.next_block_size
            or base.certifying_fantasy_probability != cert_probability
            or base.predictive_kind
            != "JEFFREYS_KT_DIRICHLET_MULTINOMIAL"
            or base.source_prior_inputs != ()
            or base.certificate_authority is not False
        ):
            _fail("base VOI differs from exact target-only replay")
        expected_base_ids[row_id] = base_id
        base_values[row_id] = (
            candidate_payload["feature_key"],
            expected_reduction / result.next_block_size,
        )

    if tuple(item.base_voi_id for item in result.base_vois) != tuple(
        sorted(expected_base_ids.values())
    ):
        _fail("base VOI ordering or identity is noncanonical")

    score_by_candidate = {
        item.candidate_id: item for item in result.arm_scores
    }
    if set(score_by_candidate) != set(expected_candidate_ids.values()):
        _fail("arm scores do not cover the exact candidate set")
    expected_score_ids = []
    sortable = []
    for row_id, candidate_id in expected_candidate_ids.items():
        feature, base_value = base_values[row_id]
        if result.arm is voi.DevelopmentVOIArmV1.NO_PRIOR:
            q = None
            multiplier = Fraction(1)
            bound_prior_id = None
        else:
            if feature not in q_by_feature:
                _fail("source prior lacks a portable target feature")
            q = q_by_feature[feature]
            multiplier = Fraction(1, 2) + Fraction(3, 2) * q
            bound_prior_id = source_prior_id
        score = base_value * multiplier
        payload = {
            "schema": "acfqp.v073_proposal_only_arm_voi_score.v1",
            "schema_version": voi.SCHEMA_VERSION,
            "arm": result.arm.value,
            "base_voi_id": expected_base_ids[row_id],
            "candidate_id": candidate_id,
            "feature_key": feature,
            "base_voi_per_draw": _fdoc(base_value),
            "multiplier": _fdoc(multiplier),
            "score": _fdoc(score),
            "source_q": None if q is None else _fdoc(q),
            "source_prior_id": bound_prior_id,
            "source_enters_base_voi": False,
            "source_enters_fantasy_model": False,
            "source_enters_certificate": False,
            "proposal_only": True,
            "certificate_authority": False,
        }
        score_id = _id("arm_score", payload)
        actual = score_by_candidate[candidate_id]
        if (
            type(actual) is not voi.DevelopmentVOIArmScoreV1
            or actual.arm is not result.arm
            or actual.arm_score_id != score_id
            or actual.base_voi_id != expected_base_ids[row_id]
            or actual.feature_key != feature
            or actual.base_voi_per_draw != base_value
            or actual.multiplier != multiplier
            or actual.score != score
            or actual.source_q != q
            or actual.source_prior_id != bound_prior_id
            or actual.proposal_only is not True
            or actual.certificate_authority is not False
        ):
            _fail("arm score differs from post-base proposal weighting")
        expected_score_ids.append(score_id)
        sortable.append(
            (
                score,
                base_value,
                rows[row_id].remaining_horizon,
                candidate_id,
            )
        )
    expected_candidates = tuple(
        item[3]
        for item in sorted(
            sortable,
            key=lambda item: (
                -item[0],
                -item[1],
                result.next_block_size,
                -item[2],
                item[3],
            ),
        )
    )
    schedule_payload = {
        "schema": "acfqp.v073_voi_candidate_schedule.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "arm": result.arm.value,
        "ordered_arm_score_ids": sorted(expected_score_ids),
        "ordered_candidate_ids": list(expected_candidates),
        "selected_candidate_id": expected_candidates[0],
        "ordering_rule": (
            "-score,-base_voi_per_draw,next_block_size,"
            "-remaining_horizon,candidate_id"
        ),
        "authorization_emitted": False,
        "target_access_permitted": False,
    }
    schedule = result.schedule
    if (
        type(schedule) is not voi.DevelopmentVOIScheduleV1
        or schedule.arm is not result.arm
        or schedule.ordered_arm_score_ids
        != tuple(sorted(expected_score_ids))
        or schedule.ordered_candidate_ids != expected_candidates
        or schedule.selected_candidate_id != expected_candidates[0]
        or schedule.schedule_id != _id("schedule", schedule_payload)
    ):
        _fail("schedule differs from exact arm-score ordering")
    if tuple(item.arm_score_id for item in result.arm_scores) != tuple(
        sorted(expected_score_ids)
    ):
        _fail("arm-score ordering is noncanonical")
    result_payload = {
        "schema": "acfqp.v073_development_voi_result.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "proposed_contract_version": voi.PROPOSED_CONTRACT_VERSION,
        "profile_key": voi.PROFILE_KEY,
        "arm": result.arm.value,
        "context_id": model.context_id,
        "model_id": model.model_id,
        "threshold_profile_id": threshold.threshold_profile_id,
        "failed_audit_id": audit.audit_id,
        "proof_dag_id": dag.dag_id,
        "row_evidence_ids": list(result.row_evidence_ids),
        "base_voi_ids": sorted(expected_base_ids.values()),
        "arm_score_ids": sorted(expected_score_ids),
        "schedule_id": schedule.schedule_id,
        "source_prior_id": source_prior_id,
        "next_block_size": result.next_block_size,
        "target_observer_calls": 0,
        "target_draws": 0,
        "kernel_calls": 0,
        "materializer_calls": 0,
        "registered_target_evidence": False,
        "registered_execution_allowed": False,
        "sample_saving_claimed": False,
        "sample_efficiency_gate_status": "NOT_RUN",
    }
    if result.result_id != _id("result", result_payload):
        _fail("result content identity does not replay")
    return fantasy_count


@dataclass(frozen=True, slots=True)
class V073CertificateBoundaryVOIIndependentAttestationV1:
    control_id: str
    no_prior_result_id: str
    source_result_id: str
    replayed_fantasy_count: int
    source_target_disjoint: bool
    exact_kt_replayed: bool
    exact_robust_planner_replayed: bool
    source_enters_only_final_multiplier: bool
    registered_execution_allowed: bool = False
    registered_target_observations: int = 0
    sample_saving_claimed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        for value, name in (
            (self.control_id, "attested control"),
            (self.no_prior_result_id, "attested no-prior result"),
            (self.source_result_id, "attested source result"),
        ):
            _cid(value, name)
        if (
            type(self.replayed_fantasy_count) is not int
            or self.replayed_fantasy_count <= 0
            or self.source_target_disjoint is not True
            or self.exact_kt_replayed is not True
            or self.exact_robust_planner_replayed is not True
            or self.source_enters_only_final_multiplier is not True
            or self.registered_execution_allowed is not False
            or self.registered_target_observations != 0
            or self.sample_saving_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            _fail("independent attestation overclaims or is incomplete")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v073_certificate_boundary_voi_"
                "independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "verification_profile": VERIFICATION_PROFILE,
            "control_id": self.control_id,
            "no_prior_result_id": self.no_prior_result_id,
            "source_result_id": self.source_result_id,
            "replayed_fantasy_count": self.replayed_fantasy_count,
            "source_target_disjoint": True,
            "exact_kt_replayed": True,
            "exact_robust_planner_replayed": True,
            "source_enters_only_final_multiplier": True,
            "registered_execution_allowed": False,
            "registered_target_observations": 0,
            "sample_saving_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def attestation_id(self) -> str:
        return _hash(VERIFICATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class V073CertificateBoundaryVOIResultIndependentAttestationV1:
    """Independent replay of one arbitrary typed development scorer result."""

    result_id: str
    model_id: str
    audit_id: str
    proof_dag_id: str
    replayed_fantasy_count: int
    source_prior_id: str | None
    exact_replay_passed: bool = True
    registered_execution_allowed: bool = False
    registered_target_observations: int = 0
    sample_saving_claimed: bool = False

    def __post_init__(self) -> None:
        for value, name in (
            (self.result_id, "result attestation result"),
            (self.model_id, "result attestation model"),
            (self.audit_id, "result attestation audit"),
            (self.proof_dag_id, "result attestation DAG"),
        ):
            _cid(value, name)
        if self.source_prior_id is not None:
            _cid(self.source_prior_id, "result attestation source prior")
        if (
            type(self.replayed_fantasy_count) is not int
            or self.replayed_fantasy_count <= 0
            or self.exact_replay_passed is not True
            or self.registered_execution_allowed is not False
            or self.registered_target_observations != 0
            or self.sample_saving_claimed is not False
        ):
            _fail("single-result independent attestation is incomplete")


def verify_v073_certificate_boundary_voi_result_v1(
    *,
    result: voi.DevelopmentCertificateBoundaryVOIResultV1,
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    failed_audit: robust.RobustPlanAuditV1,
    proof_dag: voi.DevelopmentFailedProofDAGV1,
    row_evidence: tuple[voi.CurrentRowCountEvidenceV1, ...],
    source_trials: tuple[voi.DevelopmentSourceVOITrialV1, ...] = (),
    source_prior: voi.DevelopmentSourceVOIPriorV1 | None = None,
) -> V073CertificateBoundaryVOIResultIndependentAttestationV1:
    """Replay one scorer result without using any production scoring helper."""

    gap = _verify_dag(model, threshold, failed_audit, proof_dag)
    if gap != proof_dag.current_proof_gap:
        _fail("single-result proof gap differs from its exact DAG")
    if result.arm is voi.DevelopmentVOIArmV1.NO_PRIOR:
        if source_trials != () or source_prior is not None:
            _fail("NO_PRIOR result verification received source evidence")
        q_by_feature: Mapping[str, Fraction] = {}
        source_prior_id = None
    else:
        if (
            type(source_trials) is not tuple
            or type(source_prior) is not voi.DevelopmentSourceVOIPriorV1
        ):
            _fail("source result verification lacks typed source evidence")
        q_by_feature = _verify_source_prior(
            source_trials,
            source_prior,
            model.context_id,
        )
        source_prior_id = source_prior.prior_id
    count = _verify_result(
        result=result,
        model=model,
        threshold=threshold,
        audit=failed_audit,
        dag=proof_dag,
        evidence_tuple=row_evidence,
        q_by_feature=q_by_feature,
        source_prior_id=source_prior_id,
    )
    return V073CertificateBoundaryVOIResultIndependentAttestationV1(
        result_id=result.result_id,
        model_id=model.model_id,
        audit_id=failed_audit.audit_id,
        proof_dag_id=proof_dag.dag_id,
        replayed_fantasy_count=count,
        source_prior_id=source_prior_id,
    )


def verify_v073_certificate_boundary_voi_control_v1(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> V073CertificateBoundaryVOIIndependentAttestationV1:
    """Independently replay every source and target-only proposal quantity."""

    if type(control) is not voi.DevelopmentVOIOpportunityControlV1:
        _fail("control has a noncanonical concrete type")
    model = control.target_model
    threshold = control.threshold
    audit = control.failed_audit
    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(audit) is not robust.RobustPlanAuditV1
        or control.registered_execution_allowed is not False
        or control.registered_target_evidence is not False
        or control.sample_saving_claimed is not False
        or control.sample_efficiency_gate_status != "NOT_RUN"
    ):
        _fail("control types or registered locks are invalid")
    gap = _verify_dag(model, threshold, audit, control.proof_dag)
    if gap != control.proof_dag.current_proof_gap:
        _fail("current proof gap differs from DAG")
    q_by_feature = _verify_source_prior(
        control.source_trials,
        control.source_prior,
        model.context_id,
    )
    no_prior_fantasies = _verify_result(
        result=control.no_prior_result,
        model=model,
        threshold=threshold,
        audit=audit,
        dag=control.proof_dag,
        evidence_tuple=control.row_evidence,
        q_by_feature={},
        source_prior_id=None,
    )
    source_fantasies = _verify_result(
        result=control.source_result,
        model=model,
        threshold=threshold,
        audit=audit,
        dag=control.proof_dag,
        evidence_tuple=control.row_evidence,
        q_by_feature=q_by_feature,
        source_prior_id=control.source_prior.prior_id,
    )
    if (
        control.no_prior_result.base_vois
        != control.source_result.base_vois
        or control.no_prior_result.schedule.selected_candidate_id
        == control.source_result.schedule.selected_candidate_id
        or no_prior_fantasies != source_fantasies
    ):
        _fail("fixture lacks source-free base identity or divergent ranking")
    base_by_candidate = {
        base.candidate.candidate_id: base
        for base in control.no_prior_result.base_vois
    }
    no_prior_selected = base_by_candidate[
        control.no_prior_result.schedule.selected_candidate_id
    ]
    source_selected = base_by_candidate[
        control.source_result.schedule.selected_candidate_id
    ]
    if (
        no_prior_selected.certifying_fantasy_probability
        == source_selected.certifying_fantasy_probability
        or max(
            item.certifying_fantasy_probability
            for item in base_by_candidate.values()
        )
        <= 0
    ):
        _fail("fixture lacks divergent one-block stopping opportunity")
    control_payload = {
        "schema": "acfqp.v073_development_voi_opportunity_control.v1",
        "schema_version": voi.SCHEMA_VERSION,
        "proposed_contract_version": voi.PROPOSED_CONTRACT_VERSION,
        "profile_key": voi.PROFILE_KEY,
        "source_trial_ids": [
            item.trial_id for item in control.source_trials
        ],
        "source_prior_id": control.source_prior.prior_id,
        "target_context_id": model.context_id,
        "target_model_id": model.model_id,
        "threshold_profile_id": threshold.threshold_profile_id,
        "failed_audit_id": audit.audit_id,
        "proof_dag_id": control.proof_dag.dag_id,
        "row_evidence_ids": [
            item.evidence_id for item in control.row_evidence
        ],
        "no_prior_result_id": control.no_prior_result.result_id,
        "source_result_id": control.source_result.result_id,
        "next_block_size": control.next_block_size,
        "selected_candidates_differ": True,
        "one_block_stopping_opportunity_differs": True,
        "registered_execution_allowed": False,
        "registered_target_evidence": False,
        "sample_saving_claimed": False,
        "sample_efficiency_gate_status": "NOT_RUN",
    }
    if control.control_id != _id("control", control_payload):
        _fail("control content identity does not replay")
    return V073CertificateBoundaryVOIIndependentAttestationV1(
        control_id=control.control_id,
        no_prior_result_id=control.no_prior_result.result_id,
        source_result_id=control.source_result.result_id,
        replayed_fantasy_count=no_prior_fantasies + source_fantasies,
        source_target_disjoint=True,
        exact_kt_replayed=True,
        exact_robust_planner_replayed=True,
        source_enters_only_final_multiplier=True,
    )


__all__ = [
    "verify_v073_certificate_boundary_voi_control_v1",
    "verify_v073_certificate_boundary_voi_result_v1",
    "V073CertificateBoundaryVOIIndependentAttestationV1",
    "V073CertificateBoundaryVOIResultIndependentAttestationV1",
    "V073CertificateBoundaryVOIIndependentVerificationFailure",
]
