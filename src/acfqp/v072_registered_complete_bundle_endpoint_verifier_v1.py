"""Independent complete-bundle endpoint authority for registered V0-072.

The endpoint accepts no caller-supplied status, count, endpoint, terminal, or
sample claim.  A bundle can be minted only from the exact fifteen-occurrence
production objects after the complete reconciliation has been independently
replayed.  Verification repeats that replay and then derives the two frozen
sample endpoints from native occurrence work.

The positive result is deliberately narrow: it is evidence only for the
registered V0-072 family and its conditional idealized-IID interpretation.
It is not broad sample-efficiency, workload-economics, or project-completion
evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_campaign_reconciliation_v1 as reconciliation
from acfqp import (
    v072_registered_campaign_reconciliation_independent_verifier_v1
    as reconciliation_independent,
)
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import v072_registered_incremental_epoch_materializer_v1 as incremental
from acfqp import v072_registered_matched_direct_runtime_v1 as direct
from acfqp import v072_registered_operational_terminal_authority_v1 as terminal
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_complete_bundle_endpoint_verifier_v1"
REGISTERED_BUNDLE_MINTING_ENABLED = True
REGISTERED_ENDPOINT_STATUS = (
    "IMPLEMENTED_REQUIRES_INTERNALLY_MINTED_COMPLETE_REGISTERED_BUNDLE"
)
REGISTERED_OBSERVATIONS_GENERATED = 0
LOGICAL_OCCURRENCE_DENOMINATOR = 15
REGISTERED_CONTEXT_COUNT = 3

REGISTERED_ENDPOINT_PASS = "REGISTERED_V072_SAMPLE_ENDPOINTS_PASS"
REGISTERED_ENDPOINT_FAIL = "REGISTERED_V072_SAMPLE_ENDPOINTS_FAIL"

_ADAPTIVE_ROUTE_TERMINAL_CODES = {
    "CONDITIONAL_PLAN_CERTIFICATE",
    "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE",
    "NO_POSITIVE_GAIN_NONCERTIFICATE",
    "INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE",
    "TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE",
}
_DIRECT_ROUTE_TERMINAL_CODES = {
    "CONDITIONAL_PLAN_CERTIFICATE",
    prereg.DIRECT_CHECKPOINT_CAP_TERMINAL_CODE,
    "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE",
}

DOMAIN_TAGS = {
    "bundle": "acfqp:v072-registered-complete-campaign-bundle:v1",
    "verification": (
        "acfqp:v072-registered-complete-bundle-endpoint-verification:v1"
    ),
    "readiness": (
        "acfqp:v072-registered-complete-bundle-verifier-readiness:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("registered endpoint content domains must be unique")


class V072RegisteredCompleteBundleVerificationFailure(ValueError):
    """A registered complete-bundle claim is foreign, partial, or stale."""


class RegisteredCompleteBundleEndpointLockedV1(RuntimeError):
    """Compatibility name retained for callers of the former lock skeleton."""


def _fail(message: str) -> None:
    raise V072RegisteredCompleteBundleVerificationFailure(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredCompleteBundleVerificationFailure(
            f"registered endpoint content replay failed: {error}"
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredCompleteBundleVerificationFailure(
            f"{field_name} is not one canonical content ID"
        ) from error


def _route_result_id(value: Any) -> str:
    if type(value) is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
        return value.verified_result_id
    if type(value) is direct.RegisteredMatchedDirectOccurrenceResultV1:
        return value.result_id
    _fail("complete bundle contains a foreign route result")


def _terminal_authority_id(value: Any) -> str | None:
    if value is None:
        return None
    if type(value) is not terminal.RegisteredOperationalTerminalAuthorityResultV1:
        _fail("complete bundle contains a foreign terminal authority")
    return value.authority_result_id


def _evaluation_id(value: Any) -> str | None:
    if value is None:
        return None
    if type(value) is not evaluator.RegisteredIndependentExactGroundEvaluationResultV1:
        _fail("complete bundle contains a foreign exact evaluation")
    return value.result_id


RouteResultV1 = (
    adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    | direct.RegisteredMatchedDirectOccurrenceResultV1
)


@dataclass(frozen=True, slots=True)
class _ReplayedOccurrenceEndpointFactV1:
    """Small nonauthoritative fact used after complete independent replay."""

    occurrence_id: str
    occurrence_record_id: str
    context_id: str
    context_key: str
    context_ordinal: int
    arm: str
    arm_ordinal: int
    occurrence_ordinal: int
    terminal_class: str
    terminal_code: str
    online_draws: int
    exact_evaluation_pass: bool

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "endpoint occurrence"),
            (self.occurrence_record_id, "endpoint occurrence record"),
            (self.context_id, "endpoint context"),
        ):
            _cid(value, label)
        if (
            self.arm not in prereg.ARM_ORDER
            or self.arm_ordinal != prereg.ARM_ORDER.index(self.arm)
            or self.context_ordinal not in range(REGISTERED_CONTEXT_COUNT)
            or self.occurrence_ordinal
            != self.context_ordinal * len(prereg.ARM_ORDER) + self.arm_ordinal
            or type(self.context_key) is not str
            or not self.context_key
            or self.terminal_class
            not in ("PLAN_CERTIFICATE", "ATTEMPT_CLOSURE_NONCERTIFICATE")
            or self.terminal_code not in prereg.TERMINAL_CODES
            or self.terminal_code
            not in (
                _DIRECT_ROUTE_TERMINAL_CODES
                if self.arm == "MATCHED_DIRECT_GROUND"
                else _ADAPTIVE_ROUTE_TERMINAL_CODES
            )
            or (
                self.terminal_class == "PLAN_CERTIFICATE"
            )
            != (self.terminal_code == "CONDITIONAL_PLAN_CERTIFICATE")
            or type(self.online_draws) is not int
            or self.online_draws <= 0
            or type(self.exact_evaluation_pass) is not bool
            or self.exact_evaluation_pass
            != (self.terminal_class == "PLAN_CERTIFICATE")
        ):
            _fail("replayed occurrence endpoint fact is malformed")


@dataclass(frozen=True, slots=True)
class _DerivedRegisteredEndpointSummaryV1:
    arm_online_draws: tuple[tuple[str, int], ...]
    arm_plan_certificate_counts: tuple[tuple[str, int], ...]
    arm_noncertificate_counts: tuple[tuple[str, int], ...]
    terminal_code_counts: tuple[tuple[str, int], ...]
    target_online_draws: int
    source_exact_valid_context_count: int
    source_required_context_count: int
    wrong_control_certificate_count: int
    ood_control_certificate_count: int
    source_coverage_noninferior_to_no_prior: bool
    source_coverage_noninferior_to_matched_direct: bool
    primary_operator_endpoint_pass: bool
    matched_sample_tax_endpoint_pass: bool
    no_protocol_or_integrity_failure: bool

    def __post_init__(self) -> None:
        arms = tuple(name for name, _value in self.arm_online_draws)
        if (
            arms != prereg.ARM_ORDER
            or tuple(name for name, _value in self.arm_plan_certificate_counts)
            != prereg.ARM_ORDER
            or tuple(name for name, _value in self.arm_noncertificate_counts)
            != prereg.ARM_ORDER
            or tuple(name for name, _value in self.terminal_code_counts)
            != prereg.TERMINAL_CODES
            or any(
                type(value) is not int or value < 0
                for _name, value in (
                    *self.arm_online_draws,
                    *self.arm_plan_certificate_counts,
                    *self.arm_noncertificate_counts,
                    *self.terminal_code_counts,
                )
            )
            or any(
                certificates + noncertificates != REGISTERED_CONTEXT_COUNT
                for (
                    (_arm_a, certificates),
                    (_arm_b, noncertificates),
                ) in zip(
                    self.arm_plan_certificate_counts,
                    self.arm_noncertificate_counts,
                    strict=True,
                )
            )
            or self.target_online_draws
            != sum(value for _arm, value in self.arm_online_draws)
            or self.source_required_context_count != REGISTERED_CONTEXT_COUNT
            or self.source_exact_valid_context_count
            != dict(self.arm_plan_certificate_counts)[
                "SOURCE_CONSENSUS_PRIOR"
            ]
            or self.wrong_control_certificate_count
            != dict(self.arm_plan_certificate_counts)[
                "WRONG_CONSENSUS_PRIOR"
            ]
            or self.ood_control_certificate_count
            != dict(self.arm_plan_certificate_counts)["OOD_ABSTENTION"]
        ):
            _fail("derived registered endpoint summary does not reconcile")


def _derive_registered_endpoint_summary_v1(
    facts: tuple[_ReplayedOccurrenceEndpointFactV1, ...],
) -> _DerivedRegisteredEndpointSummaryV1:
    """Derive every count/comparison; no caller count enters this function."""

    if (
        type(facts) is not tuple
        or len(facts) != LOGICAL_OCCURRENCE_DENOMINATOR
        or any(type(item) is not _ReplayedOccurrenceEndpointFactV1 for item in facts)
        or tuple(item.occurrence_ordinal for item in facts)
        != tuple(range(LOGICAL_OCCURRENCE_DENOMINATOR))
        or len({item.occurrence_id for item in facts})
        != LOGICAL_OCCURRENCE_DENOMINATOR
        or len({item.occurrence_record_id for item in facts})
        != LOGICAL_OCCURRENCE_DENOMINATOR
    ):
        _fail("endpoint facts omitted, reordered, duplicated, or replaced an occurrence")
    contexts = prereg.registered_heldout_public_contexts_v2()
    if tuple(
        (
            item.context_id,
            item.context_key,
            item.context_ordinal,
            item.arm,
            item.arm_ordinal,
        )
        for item in facts
    ) != tuple(
        (
            context.context_id,
            context.context_key,
            context_ordinal,
            arm,
            arm_ordinal,
        )
        for context_ordinal, context in enumerate(contexts)
        for arm_ordinal, arm in enumerate(prereg.ARM_ORDER)
    ):
        _fail("endpoint context-major registered schedule differs")

    by_arm = {
        arm: tuple(item for item in facts if item.arm == arm)
        for arm in prereg.ARM_ORDER
    }
    arm_draws = tuple(
        (arm, sum(item.online_draws for item in by_arm[arm]))
        for arm in prereg.ARM_ORDER
    )
    arm_certificates = tuple(
        (
            arm,
            sum(
                item.terminal_class == "PLAN_CERTIFICATE"
                and item.exact_evaluation_pass
                for item in by_arm[arm]
            ),
        )
        for arm in prereg.ARM_ORDER
    )
    arm_noncertificates = tuple(
        (
            arm,
            sum(
                item.terminal_class == "ATTEMPT_CLOSURE_NONCERTIFICATE"
                for item in by_arm[arm]
            ),
        )
        for arm in prereg.ARM_ORDER
    )
    terminal_counts = tuple(
        (
            code,
            sum(item.terminal_code == code for item in facts),
        )
        for code in prereg.TERMINAL_CODES
    )
    certificates = dict(arm_certificates)
    draws = dict(arm_draws)
    source_contextwise_no_prior = all(
        source.exact_evaluation_pass >= no_prior.exact_evaluation_pass
        for source, no_prior in zip(
            by_arm["SOURCE_CONSENSUS_PRIOR"],
            by_arm["NO_PRIOR"],
            strict=True,
        )
    )
    source_contextwise_direct = all(
        source.exact_evaluation_pass >= matched_direct.exact_evaluation_pass
        for source, matched_direct in zip(
            by_arm["SOURCE_CONSENSUS_PRIOR"],
            by_arm["MATCHED_DIRECT_GROUND"],
            strict=True,
        )
    )
    return _DerivedRegisteredEndpointSummaryV1(
        arm_draws,
        arm_certificates,
        arm_noncertificates,
        terminal_counts,
        sum(item.online_draws for item in facts),
        certificates["SOURCE_CONSENSUS_PRIOR"],
        REGISTERED_CONTEXT_COUNT,
        certificates["WRONG_CONSENSUS_PRIOR"],
        certificates["OOD_ABSTENTION"],
        source_contextwise_no_prior,
        source_contextwise_direct,
        draws["SOURCE_CONSENSUS_PRIOR"] < draws["NO_PRIOR"],
        (
            draws["SOURCE_CONSENSUS_PRIOR"]
            <= draws["MATCHED_DIRECT_GROUND"]
        ),
        not any(
            item.terminal_code in ("PROTOCOL_FAILURE", "INTEGRITY_FAILURE")
            for item in facts
        ),
    )


def _adaptive_acquisition_history(
    value: adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
) -> tuple[Any, ...]:
    final_epoch = value.execution.epochs[-1]
    if type(final_epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
        return final_epoch.acquisitions
    if type(final_epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
        return final_epoch.acquisition_history
    _fail("adaptive endpoint result has a foreign final epoch")


def _target_evidence_identity_sets(
    route_results: tuple[RouteResultV1, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    adaptive_values = tuple(
        entry.observation.observation_id
        for result in route_results
        if type(result) is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
        for acquisition in _adaptive_acquisition_history(result)
        for entry in acquisition.transcript.entries
    )
    direct_values: list[str] = []
    for result in route_results:
        if type(result) is not direct.RegisteredMatchedDirectOccurrenceResultV1:
            continue
        checkpoint = result.checkpoint_records[-1].inventory_checkpoint
        validation_ids = tuple(
            observation_id
            for prefix in checkpoint.row_prefixes
            for observation_id in prefix.acquisition_validation_observation_ids
        )
        if (
            len(validation_ids)
            != result.physical_row_count * result.stopped_checkpoint
            or len(set(validation_ids)) != len(validation_ids)
        ):
            _fail("direct final inventory omits or reuses raw observations")
        # The final inventory retains every validation observation ID.  Its
        # separately replayed discovery prefix and physical-evidence IDs bind
        # the 64 discovery observations per row without exposing a second
        # caller-provided inventory.
        direct_values.extend(validation_ids)
        direct_values.extend(
            prefix.discovery_transcript_id
            for prefix in checkpoint.row_prefixes
        )
        direct_values.extend(
            row.physical_evidence_id for row in checkpoint.row_evidence
        )
    direct_tuple = tuple(direct_values)
    if (
        not adaptive_values
        or not direct_tuple
        or len(adaptive_values) != len(set(adaptive_values))
        or len(direct_tuple) != len(set(direct_tuple))
        or set(adaptive_values) & set(direct_tuple)
    ):
        _fail("target evidence identity was reused across route occurrences")
    return adaptive_values, direct_tuple


def _source_target_evidence_disjoint_v1(
    *,
    source_raw_ids: tuple[str, ...],
    adaptive_target_ids: tuple[str, ...],
    direct_target_ids: tuple[str, ...],
) -> bool:
    """Compare all retained route-native target IDs to the source raw union."""

    if (
        type(source_raw_ids) is not tuple
        or type(adaptive_target_ids) is not tuple
        or type(direct_target_ids) is not tuple
        or not source_raw_ids
        or not adaptive_target_ids
        or not direct_target_ids
    ):
        _fail("source/target identity lanes are missing")
    for value in (
        *source_raw_ids,
        *adaptive_target_ids,
        *direct_target_ids,
    ):
        _cid(value, "source/target physical evidence")
    target = (*adaptive_target_ids, *direct_target_ids)
    if len(target) != len(set(target)):
        _fail("adaptive/direct target evidence identity was reused")
    if set(source_raw_ids) & set(target):
        _fail("source evidence identity was reused by a target route")
    return True


def _crn_prefix_map(
    value: adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
) -> dict[tuple[str, str, int], tuple[str, int, int, int]]:
    output: dict[tuple[str, str, int], tuple[str, int, int, int]] = {}
    for acquisition in _adaptive_acquisition_history(value):
        for entry in acquisition.transcript.entries:
            observation = entry.observation
            raw = observation.raw_commitment
            key = (
                observation.raw_word_pairing_group_id,
                observation.lane.value,
                observation.accepted_draw_index,
            )
            fact = (
                raw.raw_digest,
                raw.random_word_start_index,
                raw.random_word_count,
                raw.rejection_count,
            )
            if key in output and output[key] != fact:
                _fail("one arm-free CRN key has conflicting raw commitments")
            output[key] = fact
    if not output:
        _fail("adaptive result has no target CRN commitments")
    return output


def _candidate_semantic_signature(value: Any) -> tuple[Any, ...]:
    return (
        value.portable_feature_key,
        value.boundary_depth,
        value.causal_weight.numerator,
        value.causal_weight.denominator,
        value.sound_cover,
        value.cap_eligible,
        value.draw_upper,
        tuple(item.action for item in value.new_child_rows),
    )


def _neutral_schedule_signature(
    value: adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
) -> tuple[Any, ...]:
    output = []
    for closure in value.execution.selector_closures:
        claim = closure.claim
        by_id = {
            item.candidate_id: _candidate_semantic_signature(item)
            for item in claim.candidates
        }
        output.append(
            (
                claim.round_index,
                tuple(sorted(by_id.values())),
                tuple(
                    by_id[item]
                    for item in claim.decision.ordered_eligible_candidate_ids
                ),
                claim.decision.outcome.value,
                (
                    None
                    if claim.decision.selected_candidate_id is None
                    else by_id[claim.decision.selected_candidate_id]
                ),
                claim.decision.remaining_draw_cap,
            )
        )
    return tuple(output)


def _neutral_control_checks(
    route_results: tuple[RouteResultV1, ...],
) -> tuple[bool, bool]:
    by_context_arm = {
        (
            result.execution.occurrence_plan.template.context_id,
            result.execution.occurrence_plan.template.arm,
        ): result
        for result in route_results
        if type(result) is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    }
    schedule_match = True
    crn_match = True
    for context in prereg.registered_heldout_public_contexts_v2():
        neutral = by_context_arm.get((context.context_id, "NO_PRIOR"))
        ood = by_context_arm.get((context.context_id, "OOD_ABSTENTION"))
        if neutral is None or ood is None:
            _fail("neutral/OOD adaptive controls are missing")
        schedule_match = schedule_match and (
            neutral.execution.status is ood.execution.status
            and _neutral_schedule_signature(neutral)
            == _neutral_schedule_signature(ood)
        )
        crn_match = crn_match and (
            _crn_prefix_map(neutral) == _crn_prefix_map(ood)
        )
    return schedule_match, crn_match


_BUNDLE_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredCampaignCompleteBundleV1:
    """Exact internal bundle; its fields are evidence, never endpoint inputs."""

    _minting_capability: object
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1
    execution_plan: consumer.RegisteredCampaignExecutionPlanV1
    source_reconstruction_replay: source_recipe.SourceReconstructionReplayV1 | None = None
    route_results: tuple[RouteResultV1, ...] = ()
    operational_terminal_authorities: tuple[
        terminal.RegisteredOperationalTerminalAuthorityResultV1 | None, ...
    ] = ()
    exact_evaluations: tuple[
        evaluator.RegisteredIndependentExactGroundEvaluationResultV1 | None,
        ...,
    ] = ()
    reconciliation: reconciliation.RegisteredCampaignReconciliationV1 | None = None
    reconciliation_attestation: (
        reconciliation_independent
        .RegisteredCampaignReconciliationIndependentVerificationV1
        | None
    ) = None
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._minting_capability is not _BUNDLE_MINTING_SENTINEL
            or REGISTERED_BUNDLE_MINTING_ENABLED is not True
            or type(self.authority_chain)
            is not consumer.RegisteredCampaignAuthorityChainV1
            or type(self.execution_plan)
            is not consumer.RegisteredCampaignExecutionPlanV1
            or self.execution_plan.authority_chain_id
            != self.authority_chain.chain_id
            or type(self.source_reconstruction_replay)
            is not source_recipe.SourceReconstructionReplayV1
            or any(
                type(values) is not tuple
                or len(values) != LOGICAL_OCCURRENCE_DENOMINATOR
                for values in (
                    self.route_results,
                    self.operational_terminal_authorities,
                    self.exact_evaluations,
                )
            )
            or type(self.reconciliation)
            is not reconciliation.RegisteredCampaignReconciliationV1
            or type(self.reconciliation_attestation)
            is not (
                reconciliation_independent
                .RegisteredCampaignReconciliationIndependentVerificationV1
            )
            or self.reconciliation.execution_plan != self.execution_plan
            or tuple(
                item.route_result for item in self.reconciliation.occurrences
            )
            != self.route_results
            or tuple(
                item.operational_terminal_authority
                for item in self.reconciliation.occurrences
            )
            != self.operational_terminal_authorities
            or tuple(
                item.exact_evaluation for item in self.reconciliation.occurrences
            )
            != self.exact_evaluations
            or self.reconciliation_attestation.reconciliation_id
            != self.reconciliation.reconciliation_id
        ):
            _fail(
                "complete bundle lacks the internal fully reconciled "
                "fifteen-occurrence minting capability"
            )
        object.__setattr__(
            self,
            "_bundle_id",
            _hash("bundle", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_complete_campaign_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain.chain_id,
            "execution_plan_id": self.execution_plan.plan_id,
            "source_reconstruction_recipe_id": (
                self.source_reconstruction_replay.recipe_id
            ),
            "route_result_ids": [
                _route_result_id(item) for item in self.route_results
            ],
            "operational_terminal_authority_result_ids": [
                _terminal_authority_id(item)
                for item in self.operational_terminal_authorities
            ],
            "exact_evaluation_result_ids": [
                _evaluation_id(item) for item in self.exact_evaluations
            ],
            "reconciliation_id": self.reconciliation.reconciliation_id,
            "reconciliation_verification_id": (
                self.reconciliation_attestation.verification_id
            ),
            "logical_occurrence_denominator": 15,
            "caller_endpoint_status_count_terminal_accepted": False,
            "all_occurrences_retained": True,
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation": self.reconciliation.to_document(),
            "reconciliation_attestation": (
                self.reconciliation_attestation.to_document()
            ),
            "bundle_id": self.bundle_id,
        }


_VERIFICATION_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredCompleteBundleEndpointVerificationV1:
    _minting_capability: object
    bundle_id: str
    authority_chain_id: str
    execution_plan_id: str
    reconciliation_id: str
    reconciliation_verification_id: str
    occurrence_record_ids: tuple[str, ...]
    logical_occurrence_denominator: int
    source_offline_unique_draws: int
    target_online_draws: int
    target_replay_draws: int
    arm_online_draws: tuple[tuple[str, int], ...]
    arm_plan_certificate_counts: tuple[tuple[str, int], ...]
    arm_noncertificate_counts: tuple[tuple[str, int], ...]
    terminal_code_counts: tuple[tuple[str, int], ...]
    source_exact_valid_context_count: int
    source_required_context_count: int
    wrong_control_certificate_count: int
    ood_control_certificate_count: int
    source_coverage_noninferior_to_no_prior: bool
    source_coverage_noninferior_to_matched_direct: bool
    no_prior_ood_arm_free_schedule_match: bool
    no_prior_ood_crn_prefix_match: bool
    source_target_evidence_disjoint: bool
    primary_operator_endpoint_pass: bool
    matched_sample_tax_endpoint_pass: bool
    correctness_prerequisites_pass: bool
    registered_v072_endpoints_pass: bool
    verification_result: str
    sample_efficiency_gate_status: str
    broad_sample_efficiency_claimed: bool = False
    total_objective_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate_status: str = "NOT_RUN"
    counter_completeness_gate_status: str = "NOT_RUN"
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.bundle_id, "endpoint bundle"),
            (self.authority_chain_id, "endpoint authority chain"),
            (self.execution_plan_id, "endpoint execution plan"),
            (self.reconciliation_id, "endpoint reconciliation"),
            (
                self.reconciliation_verification_id,
                "endpoint reconciliation verification",
            ),
            *((value, "endpoint occurrence") for value in self.occurrence_record_ids),
        ):
            _cid(value, label)
        passed = self.registered_v072_endpoints_pass
        arm_names = tuple(name for name, _value in self.arm_online_draws)
        certificate_names = tuple(
            name for name, _value in self.arm_plan_certificate_counts
        )
        noncertificate_names = tuple(
            name for name, _value in self.arm_noncertificate_counts
        )
        terminal_names = tuple(
            name for name, _value in self.terminal_code_counts
        )
        draws = dict(self.arm_online_draws)
        certificates = dict(self.arm_plan_certificate_counts)
        noncertificates = dict(self.arm_noncertificate_counts)
        expected_correctness_if_claimed = all(
            (
                self.source_exact_valid_context_count
                == self.source_required_context_count,
                self.wrong_control_certificate_count == 0,
                self.ood_control_certificate_count == 0,
                self.source_coverage_noninferior_to_no_prior,
                self.source_coverage_noninferior_to_matched_direct,
                self.no_prior_ood_arm_free_schedule_match,
                self.no_prior_ood_crn_prefix_match,
                self.source_target_evidence_disjoint,
            )
        )
        if (
            self._minting_capability is not _VERIFICATION_SENTINEL
            or len(self.occurrence_record_ids) != LOGICAL_OCCURRENCE_DENOMINATOR
            or len(set(self.occurrence_record_ids))
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or self.logical_occurrence_denominator
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or type(self.source_offline_unique_draws) is not int
            or self.source_offline_unique_draws <= 0
            or type(self.target_online_draws) is not int
            or self.target_online_draws <= 0
            or type(self.target_replay_draws) is not int
            or self.target_replay_draws <= 0
            or arm_names != prereg.ARM_ORDER
            or certificate_names != prereg.ARM_ORDER
            or noncertificate_names != prereg.ARM_ORDER
            or terminal_names != prereg.TERMINAL_CODES
            or any(
                type(value) is not int or value < 0
                for _name, value in (
                    *self.arm_online_draws,
                    *self.arm_plan_certificate_counts,
                    *self.arm_noncertificate_counts,
                    *self.terminal_code_counts,
                )
            )
            or self.target_online_draws
            != sum(value for _arm, value in self.arm_online_draws)
            or sum(value for _code, value in self.terminal_code_counts)
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or any(
                certificates[arm] + noncertificates[arm]
                != REGISTERED_CONTEXT_COUNT
                for arm in prereg.ARM_ORDER
            )
            or self.source_required_context_count != REGISTERED_CONTEXT_COUNT
            or self.source_exact_valid_context_count
            != certificates["SOURCE_CONSENSUS_PRIOR"]
            or self.wrong_control_certificate_count
            != certificates["WRONG_CONSENSUS_PRIOR"]
            or self.ood_control_certificate_count
            != certificates["OOD_ABSTENTION"]
            or self.primary_operator_endpoint_pass
            != (
                draws["SOURCE_CONSENSUS_PRIOR"]
                < draws["NO_PRIOR"]
            )
            or self.matched_sample_tax_endpoint_pass
            != (
                draws["SOURCE_CONSENSUS_PRIOR"]
                <= draws["MATCHED_DIRECT_GROUND"]
            )
            or (
                self.correctness_prerequisites_pass
                and not expected_correctness_if_claimed
            )
            or passed
            != (
                self.correctness_prerequisites_pass
                and self.primary_operator_endpoint_pass
                and self.matched_sample_tax_endpoint_pass
            )
            or type(passed) is not bool
            or self.verification_result
            != (REGISTERED_ENDPOINT_PASS if passed else REGISTERED_ENDPOINT_FAIL)
            or self.sample_efficiency_gate_status
            != (
                "PASSED_REGISTERED_V072_ENDPOINTS_ONLY"
                if passed
                else "FAILED_REGISTERED_V072_ENDPOINTS"
            )
            or any(
                (
                    self.broad_sample_efficiency_claimed,
                    self.total_objective_claimed,
                    self.official_execution_allowed,
                    self.official_scalar_cost is not None,
                    self.official_N_break_even is not None,
                    self.workload_economics_gate_status != "NOT_RUN",
                    self.counter_completeness_gate_status != "NOT_RUN",
                )
            )
        ):
            _fail("registered endpoint verification overstates or miscounts evidence")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_complete_bundle_endpoint_"
                "verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                name: (
                    [list(item) for item in value]
                    if name
                    in (
                        "arm_online_draws",
                        "arm_plan_certificate_counts",
                        "arm_noncertificate_counts",
                        "terminal_code_counts",
                    )
                    else (
                        list(value)
                        if name == "occurrence_record_ids"
                        else value
                    )
                )
                for name, value in (
                    (
                        field_name,
                        getattr(self, field_name),
                    )
                    for field_name in self.__dataclass_fields__
                    if field_name
                    not in ("_minting_capability", "_verification_id")
                )
            },
            "source_offline_in_target_online_draws": False,
            "target_replay_in_online_draws": False,
            "exact_evaluation_in_operational_draws": False,
            "crn_draw_discount": 0,
            "caller_endpoint_status_count_terminal_accepted": False,
            "conditional_on_idealized_iid_transition_model": True,
            "formal_exact_iid_implementation_claimed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class RegisteredCompleteBundleVerifierReadinessV1:
    consumer_readiness_id: str
    bundle_minting_enabled: bool = True
    registered_bundle_available: bool = False
    registered_endpoint_verification_allowed: bool = True
    registered_observations_generated: int = 0
    caller_endpoint_argument_allowed: bool = False
    caller_status_argument_allowed: bool = False
    caller_count_argument_allowed: bool = False

    def __post_init__(self) -> None:
        _cid(self.consumer_readiness_id, "consumer readiness")
        if (
            self.bundle_minting_enabled is not True
            or self.registered_bundle_available is not False
            or self.registered_endpoint_verification_allowed is not True
            or self.registered_observations_generated != 0
            or self.caller_endpoint_argument_allowed
            or self.caller_status_argument_allowed
            or self.caller_count_argument_allowed
        ):
            _fail("registered endpoint readiness overstates current evidence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_complete_bundle_"
                "verifier_readiness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "registered_endpoint_status": REGISTERED_ENDPOINT_STATUS,
            "consumer_readiness_id": self.consumer_readiness_id,
            "bundle_minting_enabled": True,
            "registered_bundle_available": False,
            "registered_endpoint_verification_allowed": True,
            "registered_observations_generated": 0,
            "caller_endpoint_argument_allowed": False,
            "caller_status_argument_allowed": False,
            "caller_count_argument_allowed": False,
            "display_status_is_evidence": False,
            "complete_independent_replay_required": True,
        }

    @property
    def readiness_id(self) -> str:
        return _hash("readiness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "readiness_id": self.readiness_id}


def inspect_registered_complete_bundle_verifier_readiness_v1(
) -> RegisteredCompleteBundleVerifierReadinessV1:
    readiness = consumer.inspect_registered_campaign_consumer_readiness_v1()
    return RegisteredCompleteBundleVerifierReadinessV1(readiness.readiness_id)


def _verify_explicit_bundle_inputs(
    *,
    authority_chain: Any,
    execution_plan: Any,
    source_reconstruction_replay: Any,
    route_results: Any,
    operational_terminal_authorities: Any,
    exact_evaluations: Any,
    claimed_reconciliation: Any,
    claimed_attestation: Any,
) -> reconciliation_independent.RegisteredCampaignReconciliationIndependentVerificationV1:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(execution_plan)
        is not consumer.RegisteredCampaignExecutionPlanV1
        or type(source_reconstruction_replay)
        is not source_recipe.SourceReconstructionReplayV1
        or type(claimed_reconciliation)
        is not reconciliation.RegisteredCampaignReconciliationV1
        or type(claimed_attestation)
        is not (
            reconciliation_independent
            .RegisteredCampaignReconciliationIndependentVerificationV1
        )
        or any(
            type(values) is not tuple
            or len(values) != LOGICAL_OCCURRENCE_DENOMINATOR
            for values in (
                route_results,
                operational_terminal_authorities,
                exact_evaluations,
            )
        )
    ):
        _fail("complete bundle inputs have a foreign or incomplete exact type")
    try:
        consumer.verify_registered_campaign_authority_chain_v1(authority_chain)
    except (ValueError, RuntimeError, KeyError, TypeError) as error:
        raise V072RegisteredCompleteBundleVerificationFailure(
            "complete bundle authority chain replay failed"
        ) from error
    expected_plan = consumer.RegisteredCampaignExecutionPlanV1(
        authority_chain.chain_id,
        tuple(
            consumer.RegisteredOccurrenceExecutionPlanV1(
                authority_chain.chain_id,
                template,
            )
            for template in consumer.registered_occurrence_templates_v1()
        ),
    )
    if (
        execution_plan != expected_plan
        or claimed_reconciliation.execution_plan != expected_plan
        or tuple(item.route_result for item in claimed_reconciliation.occurrences)
        != route_results
        or tuple(
            item.operational_terminal_authority
            for item in claimed_reconciliation.occurrences
        )
        != operational_terminal_authorities
        or tuple(
            item.exact_evaluation
            for item in claimed_reconciliation.occurrences
        )
        != exact_evaluations
    ):
        _fail("complete bundle skipped, reordered, or substituted evidence")
    try:
        replayed = (
            reconciliation_independent
            .verify_registered_v072_campaign_reconciliation_independently_v1(
                authority_chain=authority_chain,
                execution_plan=execution_plan,
                source_reconstruction_replay=source_reconstruction_replay,
                claimed=claimed_reconciliation,
            )
        )
    except (ValueError, RuntimeError, KeyError, TypeError, AssertionError) as error:
        raise V072RegisteredCompleteBundleVerificationFailure(
            "complete bundle independent reconciliation replay failed"
        ) from error
    if replayed != claimed_attestation:
        _fail("stored reconciliation attestation is stale or caller-forged")
    return replayed


def mint_registered_v072_complete_bundle_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    execution_plan: consumer.RegisteredCampaignExecutionPlanV1,
    source_reconstruction_replay: source_recipe.SourceReconstructionReplayV1,
    route_results: tuple[RouteResultV1, ...],
    operational_terminal_authorities: tuple[
        terminal.RegisteredOperationalTerminalAuthorityResultV1 | None, ...
    ],
    exact_evaluations: tuple[
        evaluator.RegisteredIndependentExactGroundEvaluationResultV1 | None,
        ...,
    ],
    reconciliation: reconciliation.RegisteredCampaignReconciliationV1,
    reconciliation_attestation: (
        reconciliation_independent
        .RegisteredCampaignReconciliationIndependentVerificationV1
    ),
) -> RegisteredCampaignCompleteBundleV1:
    """Mint only after a fresh independent replay of all fifteen occurrences."""

    _verify_explicit_bundle_inputs(
        authority_chain=authority_chain,
        execution_plan=execution_plan,
        source_reconstruction_replay=source_reconstruction_replay,
        route_results=route_results,
        operational_terminal_authorities=operational_terminal_authorities,
        exact_evaluations=exact_evaluations,
        claimed_reconciliation=reconciliation,
        claimed_attestation=reconciliation_attestation,
    )
    return RegisteredCampaignCompleteBundleV1(
        _BUNDLE_MINTING_SENTINEL,
        authority_chain,
        execution_plan,
        source_reconstruction_replay,
        route_results,
        operational_terminal_authorities,
        exact_evaluations,
        reconciliation,
        reconciliation_attestation,
    )


def _replayed_endpoint_facts(
    bundle: RegisteredCampaignCompleteBundleV1,
) -> tuple[_ReplayedOccurrenceEndpointFactV1, ...]:
    return tuple(
        _ReplayedOccurrenceEndpointFactV1(
            occurrence.occurrence_plan.occurrence_id,
            occurrence.occurrence_record_id,
            occurrence.occurrence_plan.template.context_id,
            occurrence.occurrence_plan.template.context_key,
            occurrence.occurrence_plan.template.context_ordinal,
            occurrence.occurrence_plan.template.arm,
            occurrence.occurrence_plan.template.arm_ordinal,
            occurrence.occurrence_plan.template.occurrence_ordinal,
            occurrence.terminal_class.value,
            occurrence.terminal_code,
            occurrence.work.online_acquisition_draws,
            (
                occurrence.exact_evaluation is not None
                and occurrence.exact_evaluation.status
                is (
                    evaluator.RegisteredExactGroundEvaluationStatusV1
                    .CERTIFICATE_METRICS_PASS
                )
                and occurrence.exact_evaluation.certificate_metrics_pass
            ),
        )
        for occurrence in bundle.reconciliation.occurrences
    )


def verify_registered_v072_complete_bundle_v1(
    *,
    bundle: Any,
) -> RegisteredCompleteBundleEndpointVerificationV1:
    """Replay one internal bundle and derive the registered sample endpoints."""

    if type(bundle) is not RegisteredCampaignCompleteBundleV1:
        _fail(
            "registered endpoint requires one exact internally minted "
            "complete bundle; caller endpoint/status/count strings are not evidence"
        )
    replayed_attestation = _verify_explicit_bundle_inputs(
        authority_chain=bundle.authority_chain,
        execution_plan=bundle.execution_plan,
        source_reconstruction_replay=bundle.source_reconstruction_replay,
        route_results=bundle.route_results,
        operational_terminal_authorities=(
            bundle.operational_terminal_authorities
        ),
        exact_evaluations=bundle.exact_evaluations,
        claimed_reconciliation=bundle.reconciliation,
        claimed_attestation=bundle.reconciliation_attestation,
    )
    facts = _replayed_endpoint_facts(bundle)
    summary = _derive_registered_endpoint_summary_v1(facts)
    schedule_match, crn_match = _neutral_control_checks(bundle.route_results)
    adaptive_target_ids, direct_target_ids = _target_evidence_identity_sets(
        bundle.route_results
    )
    source_target_disjoint = _source_target_evidence_disjoint_v1(
        source_raw_ids=(
            bundle.reconciliation.source_offline
            .physical_raw_observation_ids
        ),
        adaptive_target_ids=adaptive_target_ids,
        direct_target_ids=direct_target_ids,
    )

    source_positive = (
        summary.source_exact_valid_context_count
        == summary.source_required_context_count
    )
    zero_negative_control_certificates = (
        summary.wrong_control_certificate_count == 0
        and summary.ood_control_certificate_count == 0
    )
    correctness = all(
        (
            summary.no_protocol_or_integrity_failure,
            source_positive,
            zero_negative_control_certificates,
            summary.source_coverage_noninferior_to_no_prior,
            summary.source_coverage_noninferior_to_matched_direct,
            schedule_match,
            crn_match,
            source_target_disjoint,
        )
    )
    passed = (
        correctness
        and summary.primary_operator_endpoint_pass
        and summary.matched_sample_tax_endpoint_pass
    )
    totals = bundle.reconciliation.campaign_totals
    return RegisteredCompleteBundleEndpointVerificationV1(
        _VERIFICATION_SENTINEL,
        bundle.bundle_id,
        bundle.authority_chain.chain_id,
        bundle.execution_plan.plan_id,
        bundle.reconciliation.reconciliation_id,
        replayed_attestation.verification_id,
        tuple(
            item.occurrence_record_id
            for item in bundle.reconciliation.occurrences
        ),
        LOGICAL_OCCURRENCE_DENOMINATOR,
        bundle.reconciliation.source_offline.unique_physical_raw_draws,
        summary.target_online_draws,
        totals.target_replay_draws,
        summary.arm_online_draws,
        summary.arm_plan_certificate_counts,
        summary.arm_noncertificate_counts,
        summary.terminal_code_counts,
        summary.source_exact_valid_context_count,
        summary.source_required_context_count,
        summary.wrong_control_certificate_count,
        summary.ood_control_certificate_count,
        summary.source_coverage_noninferior_to_no_prior,
        summary.source_coverage_noninferior_to_matched_direct,
        schedule_match,
        crn_match,
        source_target_disjoint,
        summary.primary_operator_endpoint_pass,
        summary.matched_sample_tax_endpoint_pass,
        correctness,
        passed,
        REGISTERED_ENDPOINT_PASS if passed else REGISTERED_ENDPOINT_FAIL,
        (
            "PASSED_REGISTERED_V072_ENDPOINTS_ONLY"
            if passed
            else "FAILED_REGISTERED_V072_ENDPOINTS"
        ),
    )


__all__ = [
    "LOGICAL_OCCURRENCE_DENOMINATOR",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_BUNDLE_MINTING_ENABLED",
    "REGISTERED_ENDPOINT_STATUS",
    "REGISTERED_OBSERVATIONS_GENERATED",
    "RegisteredCampaignCompleteBundleV1",
    "RegisteredCompleteBundleEndpointLockedV1",
    "RegisteredCompleteBundleEndpointVerificationV1",
    "RegisteredCompleteBundleVerifierReadinessV1",
    "SCHEMA_VERSION",
    "V072RegisteredCompleteBundleVerificationFailure",
    "inspect_registered_complete_bundle_verifier_readiness_v1",
    "mint_registered_v072_complete_bundle_v1",
    "verify_registered_v072_complete_bundle_v1",
]
