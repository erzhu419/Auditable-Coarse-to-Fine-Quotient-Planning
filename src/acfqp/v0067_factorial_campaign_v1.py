"""Real V0-067 factorial campaign and separate semantic replay verifier.

This module is the only positive-claim authority for the V0-067 graph Gate.
It constructs all sixteen registered cells from registered real typed
authorities, checks
the paired raw prefixes across fixed/sequential arms, preserves deduplicated
registered-native-authority versus factorial-comparison accounting, and
separately rebuilds every adapter and Gate result.  The replay deliberately
does not claim implementation independence.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import functools
import hashlib
from typing import Any, Mapping

import acfqp.anytime_variable_graph_runner_v1 as anytime
import acfqp.factorial_sample_efficiency_gate_v1 as gate
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
import acfqp.v0066_graph_acquisition_metaprior_v1 as source_meta
import acfqp.variable_graph_direct_fixed_v1 as direct_fixed
import acfqp.variable_graph_direct_sequential_v1 as direct_sequential
import acfqp.variable_order_graph_rapm_v1 as graph


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = gate.CONTRACT_VERSION
PROFILE_KEY = "v0067_real_factorial_campaign_v0"

DOMAIN_TAGS = {
    "pairing": "acfqp:v0067-real-factorial-pairing:v1",
    "counters": "acfqp:v0067-real-factorial-native-counters:v1",
    "campaign": "acfqp:v0067-real-factorial-campaign:v1",
    "verification": "acfqp:v0067-real-factorial-verification:v1",
}


class V0067FactorialCampaignInvariantViolation(ValueError):
    """The real factorial campaign, pairing, or replay is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V0067FactorialCampaignInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V0067FactorialCampaignInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _flags_are_prefix(
    prefix: bytes,
    prefix_word_count: int,
    full: bytes,
) -> bool:
    if (
        type(prefix) is not bytes
        or type(full) is not bytes
        or type(prefix_word_count) is not int
        or prefix_word_count <= 0
        or len(prefix) > len(full)
    ):
        return False
    complete_bytes, trailing_bits = divmod(prefix_word_count, 8)
    if prefix[:complete_bytes] != full[:complete_bytes]:
        return False
    if trailing_bits == 0:
        return len(prefix) == complete_bytes
    mask = (1 << trailing_bits) - 1
    return (
        len(prefix) == complete_bytes + 1
        and (prefix[complete_bytes] & mask)
        == (full[complete_bytes] & mask)
        and prefix[complete_bytes] & ~mask == 0
    )


def _row_key(row: Any) -> tuple[str, tuple[int, int, int]]:
    return row.catalogue.catalogue_id, row.action


@dataclass(frozen=True, slots=True)
class V0067PairedPrefixVerificationV1:
    fixed_quotient_campaign_id: str
    anytime_result_ids: tuple[str, ...]
    direct_fixed_result_ids: tuple[str, ...]
    direct_sequential_result_ids: tuple[str, ...]
    quotient_rows_verified: int
    quotient_prefix_draws_verified: int
    direct_rows_verified: int
    direct_prefix_draws_verified: int
    quotient_seed_and_raw_prefix_match: bool
    direct_seed_and_raw_prefix_match: bool

    def __post_init__(self) -> None:
        _cid(
            self.fixed_quotient_campaign_id,
            "pairing fixed quotient campaign",
        )
        for values, field, expected in (
            (self.anytime_result_ids, "pairing anytime results", 3),
            (self.direct_fixed_result_ids, "pairing direct fixed results", 2),
            (
                self.direct_sequential_result_ids,
                "pairing direct sequential results",
                2,
            ),
        ):
            if (
                values != tuple(sorted(set(values)))
                or len(values) != expected
            ):
                raise V0067FactorialCampaignInvariantViolation(
                    f"{field} are incomplete"
                )
            for item in values:
                _cid(item, field)
        if (
            self.quotient_rows_verified != 142
            or self.quotient_prefix_draws_verified != 1_409_024
            or self.direct_rows_verified != 90
            or self.direct_prefix_draws_verified != 737_280
            or self.quotient_seed_and_raw_prefix_match is not True
            or self.direct_seed_and_raw_prefix_match is not True
        ):
            raise V0067FactorialCampaignInvariantViolation(
                "fixed/sequential raw paired-prefix verification failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_paired_prefix_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "fixed_quotient_campaign_id": (
                self.fixed_quotient_campaign_id
            ),
            "anytime_result_ids": list(self.anytime_result_ids),
            "direct_fixed_result_ids": list(
                self.direct_fixed_result_ids
            ),
            "direct_sequential_result_ids": list(
                self.direct_sequential_result_ids
            ),
            "quotient_rows_verified": self.quotient_rows_verified,
            "quotient_prefix_draws_verified": (
                self.quotient_prefix_draws_verified
            ),
            "direct_rows_verified": self.direct_rows_verified,
            "direct_prefix_draws_verified": (
                self.direct_prefix_draws_verified
            ),
            "quotient_seed_and_raw_prefix_match": True,
            "direct_seed_and_raw_prefix_match": True,
        }

    @property
    def pairing_verification_id(self) -> str:
        return _content_id("pairing", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "pairing_verification_id": self.pairing_verification_id,
        }


def verify_v0067_paired_prefixes_v1(
    fixed_campaign: graph.VariableOrderGraphCampaignV1,
    anytime_results: tuple[anytime.AnytimeVariableGraphResultV1, ...],
    direct_fixed_results: tuple[direct_fixed.DirectFixedResultV1, ...],
    direct_sequential_results: tuple[
        direct_sequential.DirectSequentialResultV1,
        ...,
    ],
) -> V0067PairedPrefixVerificationV1:
    """Compare raw fixed streams with the actually consumed prefixes."""

    if (
        type(fixed_campaign) is not graph.VariableOrderGraphCampaignV1
        or tuple(item.context for item in fixed_campaign.results)
        != graph.registered_variable_order_contexts_v1()
        or type(anytime_results) is not tuple
        or tuple(item.context for item in anytime_results)
        != graph.registered_variable_order_contexts_v1()
        or type(direct_fixed_results) is not tuple
        or tuple(item.context for item in direct_fixed_results)
        != graph.registered_variable_order_contexts_v1()[:2]
        or type(direct_sequential_results) is not tuple
        or tuple(item.context for item in direct_sequential_results)
        != graph.registered_variable_order_contexts_v1()[:2]
    ):
        raise V0067FactorialCampaignInvariantViolation(
            "paired-prefix inputs are not the registered real families"
        )

    quotient_rows = 0
    quotient_draws = 0
    for fixed_result, sequential_result in zip(
        fixed_campaign.results,
        anytime_results,
    ):
        fixed_rows = {
            _row_key(row): row
            for row in (
                fixed_result.evidence.root_rows
                + fixed_result.evidence.continuation_rows
            )
        }
        sequential_rows = (
            sequential_result.final_evidence.root_rows
            + sequential_result.final_evidence.continuation_rows
        )
        if set(fixed_rows) != {_row_key(row) for row in sequential_rows}:
            raise V0067FactorialCampaignInvariantViolation(
                "quotient fixed/sequential row support is not identical"
            )
        for prefix in sequential_rows:
            fixed = fixed_rows[_row_key(prefix)]
            seed = graph._row_seed(
                sequential_result.context,
                prefix.catalogue,
                prefix.action,
            )
            if (
                prefix.paired_seed_id != anytime._seed_id(seed)
                or prefix.atom_descriptors != fixed.atom_descriptors
                or prefix.packed_ordinals
                != fixed.packed_ordinals[: len(prefix.packed_ordinals)]
                or not _flags_are_prefix(
                    prefix.packed_rejection_flags,
                    prefix.random_word_count,
                    fixed.packed_rejection_flags,
                )
            ):
                raise V0067FactorialCampaignInvariantViolation(
                    "quotient raw paired prefix differs from fixed stream"
                )
            quotient_rows += 1
            quotient_draws += prefix.sample_count

    direct_rows = 0
    direct_draws = 0
    for fixed_result, sequential_result in zip(
        direct_fixed_results,
        direct_sequential_results,
    ):
        fixed_rows = {_row_key(row): row for row in fixed_result.rows}
        if set(fixed_rows) != {
            _row_key(row) for row in sequential_result.rows
        }:
            raise V0067FactorialCampaignInvariantViolation(
                "direct fixed/sequential row support is not identical"
            )
        for prefix in sequential_result.rows:
            fixed = fixed_rows[_row_key(prefix)]
            stream_id = direct_fixed.paired_stream_identity_v1(
                prefix.context_id,
                prefix.catalogue.catalogue_id,
                prefix.action,
                prefix.paired_v0066_seed,
            )
            if (
                stream_id != fixed.paired_stream_id
                or prefix.atom_descriptors != fixed.atom_descriptors
                or prefix.packed_ordinals
                != fixed.packed_ordinals[: len(prefix.packed_ordinals)]
                or not _flags_are_prefix(
                    prefix.packed_rejection_flags,
                    prefix.random_word_count,
                    fixed.packed_rejection_flags,
                )
            ):
                raise V0067FactorialCampaignInvariantViolation(
                    "direct raw paired prefix differs from fixed stream"
                )
            direct_rows += 1
            direct_draws += prefix.draw_count

    return V0067PairedPrefixVerificationV1(
        fixed_campaign.campaign_id,
        tuple(sorted(item.result_id for item in anytime_results)),
        tuple(sorted(item.result_id for item in direct_fixed_results)),
        tuple(
            sorted(item.result_id for item in direct_sequential_results)
        ),
        quotient_rows,
        quotient_draws,
        direct_rows,
        direct_draws,
        True,
        True,
    )


@dataclass(frozen=True, slots=True)
class V0067NativeCounterSummaryV1:
    source_proxy_comparison_draws: int
    source_proxy_physical_unique_draws: int
    source_proxy_comparison_exact_queries: int
    source_proxy_physical_unique_exact_queries: int
    sunk_source_provenance_exact_queries: int
    deduplicated_registered_native_target_acquisition_draws: int
    factorial_comparison_target_acquisition_draws: int
    deduplicated_registered_native_target_support_queries: int
    factorial_comparison_target_support_queries: int
    deduplicated_registered_native_target_fallback_queries: int
    factorial_comparison_target_fallback_queries: int
    deduplicated_registered_native_evaluation_exact_queries: int
    factorial_comparison_evaluation_exact_queries: int
    target_deduplication_semantics: str = (
        "DEDUPLICATED_REGISTERED_REAL_NATIVE_AUTHORITIES_"
        "NOT_PHYSICAL_CRN_BYTES"
    )
    source_project_cost_complete: bool = False
    heterogeneous_work_scalarized: bool = False
    counter_completeness_claimed: bool = False
    counter_completeness_gate_status: str = (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )

    def __post_init__(self) -> None:
        expected = (
            (self.source_proxy_comparison_draws, 5_451_776),
            (self.source_proxy_physical_unique_draws, 5_242_880),
            (self.source_proxy_comparison_exact_queries, 80),
            (self.source_proxy_physical_unique_exact_queries, 40),
            (self.sunk_source_provenance_exact_queries, 120),
            (
                self.deduplicated_registered_native_target_acquisition_draws,
                32_555_008,
            ),
            (
                self.factorial_comparison_target_acquisition_draws,
                52_576_256,
            ),
            (
                self.deduplicated_registered_native_target_support_queries,
                464,
            ),
            (self.factorial_comparison_target_support_queries, 748),
            (
                self.deduplicated_registered_native_target_fallback_queries,
                120,
            ),
            (self.factorial_comparison_target_fallback_queries, 240),
        )
        if (
            any(value != frozen for value, frozen in expected)
            or type(
                self.deduplicated_registered_native_evaluation_exact_queries
            )
            is not int
            or self.deduplicated_registered_native_evaluation_exact_queries
            <= 0
            or type(self.factorial_comparison_evaluation_exact_queries)
            is not int
            or self.factorial_comparison_evaluation_exact_queries
            < self.deduplicated_registered_native_evaluation_exact_queries
            or self.target_deduplication_semantics
            != (
                "DEDUPLICATED_REGISTERED_REAL_NATIVE_AUTHORITIES_"
                "NOT_PHYSICAL_CRN_BYTES"
            )
            or self.source_project_cost_complete is not False
            or self.heterogeneous_work_scalarized is not False
            or self.counter_completeness_claimed is not False
            or self.counter_completeness_gate_status
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        ):
            raise V0067FactorialCampaignInvariantViolation(
                "real campaign native work was omitted, duplicated, or "
                "scalarized"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_native_counter_summary.v1",
            "schema_version": SCHEMA_VERSION,
            "source_proxy_comparison_draws": (
                self.source_proxy_comparison_draws
            ),
            "source_proxy_physical_unique_draws": (
                self.source_proxy_physical_unique_draws
            ),
            "source_proxy_comparison_exact_queries": (
                self.source_proxy_comparison_exact_queries
            ),
            "source_proxy_physical_unique_exact_queries": (
                self.source_proxy_physical_unique_exact_queries
            ),
            "sunk_source_provenance_exact_queries": (
                self.sunk_source_provenance_exact_queries
            ),
            "deduplicated_registered_native_target_acquisition_draws": (
                self.deduplicated_registered_native_target_acquisition_draws
            ),
            "factorial_comparison_target_acquisition_draws": (
                self.factorial_comparison_target_acquisition_draws
            ),
            "deduplicated_registered_native_target_support_queries": (
                self.deduplicated_registered_native_target_support_queries
            ),
            "factorial_comparison_target_support_queries": (
                self.factorial_comparison_target_support_queries
            ),
            "deduplicated_registered_native_target_fallback_queries": (
                self.deduplicated_registered_native_target_fallback_queries
            ),
            "factorial_comparison_target_fallback_queries": (
                self.factorial_comparison_target_fallback_queries
            ),
            "deduplicated_registered_native_evaluation_exact_queries": (
                self.deduplicated_registered_native_evaluation_exact_queries
            ),
            "factorial_comparison_evaluation_exact_queries": (
                self.factorial_comparison_evaluation_exact_queries
            ),
            "target_deduplication_semantics": (
                self.target_deduplication_semantics
            ),
            "source_project_cost_complete": False,
            "heterogeneous_work_scalarized": False,
            "counter_completeness_claimed": False,
            "counter_completeness_gate_status": (
                self.counter_completeness_gate_status
            ),
        }

    @property
    def counter_summary_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counter_summary_id": self.counter_summary_id,
        }


def _native_counter_summary(
    source_prior: gate.SourcePriorGateEvidenceV1,
    arm_results: tuple[gate.GraphOccurrenceArmResultV1, ...],
) -> V0067NativeCounterSummaryV1:
    unique_arm_ids = {
        gate.NO_PRIOR_FIXED.arm_id,
        gate.NO_PRIOR_SEQUENTIAL.arm_id,
        gate.DIRECT_FIXED.arm_id,
        gate.DIRECT_SEQUENTIAL.arm_id,
    }
    unique = tuple(
        item for item in arm_results if item.arm.arm_id in unique_arm_ids
    )
    return V0067NativeCounterSummaryV1(
        source_prior.offline_source_work.generative_oracle_samples,
        source_prior.physical_unique_proxy_work.generative_oracle_samples,
        source_prior.offline_source_work.exact_kernel_queries,
        source_prior.physical_unique_proxy_work.exact_kernel_queries,
        source_prior.sunk_source_provenance_work.exact_kernel_queries,
        sum(item.work.acquisition_draws for item in unique),
        sum(item.work.acquisition_draws for item in arm_results),
        sum(
            item.work.target_acquisition.exact_kernel_queries
            for item in unique
        ),
        sum(
            item.work.target_acquisition.exact_kernel_queries
            for item in arm_results
        ),
        sum(item.work.fallback.exact_kernel_queries for item in unique),
        sum(
            item.work.fallback.exact_kernel_queries
            for item in arm_results
        ),
        sum(
            item.work.independent_verification.exact_kernel_queries
            for item in unique
        ),
        sum(
            item.work.independent_verification.exact_kernel_queries
            for item in arm_results
        ),
    )


@dataclass(frozen=True, slots=True)
class V0067FactorialCampaignV1:
    source_campaign: source_meta.V0066GraphAcquisitionMetaPriorCampaignV1
    source_verification: (
        source_meta.V0066GraphAcquisitionMetaPriorVerificationV1
    )
    source_prior: gate.SourcePriorGateEvidenceV1
    preregistration: gate.FactorialSampleEfficiencyPreregistrationV1
    fixed_quotient_campaign: graph.VariableOrderGraphCampaignV1
    fixed_quotient_verification: (
        graph.VariableOrderGraphCampaignVerificationV1
    )
    anytime_results: tuple[anytime.AnytimeVariableGraphResultV1, ...]
    anytime_verifications: tuple[
        anytime.AnytimeVariableGraphVerificationV1,
        ...,
    ]
    direct_fixed_results: tuple[direct_fixed.DirectFixedResultV1, ...]
    direct_fixed_verifications: tuple[
        direct_fixed.DirectFixedVerificationV1,
        ...,
    ]
    direct_sequential_results: tuple[
        direct_sequential.DirectSequentialResultV1,
        ...,
    ]
    direct_sequential_verifications: tuple[
        direct_sequential.DirectSequentialVerificationV1,
        ...,
    ]
    arm_results: tuple[gate.GraphOccurrenceArmResultV1, ...]
    pairing_verification: V0067PairedPrefixVerificationV1
    native_counters: V0067NativeCounterSummaryV1
    gate_result: gate.FactorialSampleEfficiencyGateResultV1
    status: str = "REGISTERED_REAL_FACTORIAL_GATE_EVALUATED"
    synthetic_fixture_supports_claim: bool = False
    broad_generalization_claimed: bool = False
    official_execution_allowed: bool = False
    counter_completeness_claimed: bool = False
    counter_completeness_gate_status: str = (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    workload_economics_gate_status: str = (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        if (
            type(self.source_campaign)
            is not source_meta.V0066GraphAcquisitionMetaPriorCampaignV1
            or type(self.source_verification)
            is not source_meta.V0066GraphAcquisitionMetaPriorVerificationV1
            or type(self.source_prior) is not gate.SourcePriorGateEvidenceV1
            or type(self.preregistration)
            is not gate.FactorialSampleEfficiencyPreregistrationV1
            or type(self.fixed_quotient_campaign)
            is not graph.VariableOrderGraphCampaignV1
            or type(self.fixed_quotient_verification)
            is not graph.VariableOrderGraphCampaignVerificationV1
            or type(self.pairing_verification)
            is not V0067PairedPrefixVerificationV1
            or type(self.native_counters)
            is not V0067NativeCounterSummaryV1
            or type(self.gate_result)
            is not gate.FactorialSampleEfficiencyGateResultV1
            or len(self.anytime_results) != 3
            or len(self.anytime_verifications) != 3
            or len(self.direct_fixed_results) != 2
            or len(self.direct_fixed_verifications) != 2
            or len(self.direct_sequential_results) != 2
            or len(self.direct_sequential_verifications) != 2
            or len(self.arm_results) != 16
            or any(
                type(item) is not anytime.AnytimeVariableGraphResultV1
                for item in self.anytime_results
            )
            or any(
                type(item)
                is not anytime.AnytimeVariableGraphVerificationV1
                for item in self.anytime_verifications
            )
            or any(
                result.context.context_id != verification.context_id
                or result.result_id != verification.result_id
                for result, verification in zip(
                    self.anytime_results,
                    self.anytime_verifications,
                )
            )
            or any(
                type(item) is not direct_fixed.DirectFixedResultV1
                for item in self.direct_fixed_results
            )
            or any(
                type(item) is not direct_fixed.DirectFixedVerificationV1
                for item in self.direct_fixed_verifications
            )
            or any(
                result.result_id != verification.result_id
                for result, verification in zip(
                    self.direct_fixed_results,
                    self.direct_fixed_verifications,
                )
            )
            or any(
                type(item) is not direct_sequential.DirectSequentialResultV1
                for item in self.direct_sequential_results
            )
            or any(
                type(item)
                is not direct_sequential.DirectSequentialVerificationV1
                for item in self.direct_sequential_verifications
            )
            or any(
                result.result_id != verification.result_id
                for result, verification in zip(
                    self.direct_sequential_results,
                    self.direct_sequential_verifications,
                )
            )
            or any(
                type(item) is not gate.GraphOccurrenceArmResultV1
                for item in self.arm_results
            )
            or self.source_verification.campaign_id
            != self.source_campaign.campaign_id
            or self.fixed_quotient_verification.campaign_id
            != self.fixed_quotient_campaign.campaign_id
            or self.source_prior.gate_prior_id
            != self.preregistration.source_prior_gate_id
            or self.gate_result.preregistration_id
            != self.preregistration.preregistration_id
            or self.gate_result.source_prior_gate_id
            != self.source_prior.gate_prior_id
            or self.gate_result.result_ids
            != tuple(sorted(item.result_id for item in self.arm_results))
            or self.status != "REGISTERED_REAL_FACTORIAL_GATE_EVALUATED"
            or self.synthetic_fixture_supports_claim is not False
            or self.broad_generalization_claimed is not False
            or self.official_execution_allowed is not False
            or self.counter_completeness_claimed is not False
            or self.counter_completeness_gate_status
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.workload_economics_gate_status
            != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise V0067FactorialCampaignInvariantViolation(
                "real factorial campaign identity or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_real_factorial_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_campaign_id": self.source_campaign.campaign_id,
            "source_verification_id": (
                self.source_verification.verification_id
            ),
            "source_prior_gate_id": self.source_prior.gate_prior_id,
            "preregistration_id": self.preregistration.preregistration_id,
            "fixed_quotient_campaign_id": (
                self.fixed_quotient_campaign.campaign_id
            ),
            "fixed_quotient_verification_id": (
                self.fixed_quotient_verification.verification_id
            ),
            "anytime_result_ids": [
                item.result_id for item in self.anytime_results
            ],
            "anytime_verification_ids": [
                item.verification_id for item in self.anytime_verifications
            ],
            "direct_fixed_result_ids": [
                item.result_id for item in self.direct_fixed_results
            ],
            "direct_fixed_verification_ids": [
                item.verification_id
                for item in self.direct_fixed_verifications
            ],
            "direct_sequential_result_ids": [
                item.result_id for item in self.direct_sequential_results
            ],
            "direct_sequential_verification_ids": [
                item.verification_id
                for item in self.direct_sequential_verifications
            ],
            "arm_result_ids": [
                item.result_id for item in self.arm_results
            ],
            "pairing_verification_id": (
                self.pairing_verification.pairing_verification_id
            ),
            "native_counter_summary_id": (
                self.native_counters.counter_summary_id
            ),
            "gate_result_id": self.gate_result.gate_result_id,
            "status": self.status,
            "synthetic_fixture_supports_claim": False,
            "broad_generalization_claimed": False,
            "official_execution_allowed": False,
            "counter_completeness_claimed": False,
            "counter_completeness_gate_status": (
                self.counter_completeness_gate_status
            ),
            "workload_economics_gate_status": (
                self.workload_economics_gate_status
            ),
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_prior": self.source_prior.to_document(),
            "preregistration": self.preregistration.to_document(),
            "pairing_verification": self.pairing_verification.to_document(),
            "native_counters": self.native_counters.to_document(),
            "gate_result": self.gate_result.to_document(),
            "campaign_id": self.campaign_id,
        }


def _preregistration(
    source_campaign: source_meta.V0066GraphAcquisitionMetaPriorCampaignV1,
    source_prior: gate.SourcePriorGateEvidenceV1,
) -> gate.FactorialSampleEfficiencyPreregistrationV1:
    query_ids = {
        item.context_key: item.query_id
        for item in source_campaign.target_proposals
    }
    return gate.FactorialSampleEfficiencyPreregistrationV1(
        gate.build_registered_graph_occurrences_v1(query_ids, 1),
        gate.REGISTERED_ARMS,
        source_prior.gate_prior_id,
        _content_id(
            "campaign",
            {
                "schema": "acfqp.v0067-real-factorial-claim-scope.v1",
                "claim_scope": gate.REGISTERED_CLAIM_SCOPE,
            },
        ),
        _content_id(
            "campaign",
            {
                "schema": (
                    "acfqp.v0067-real-factorial-confidence-budget.v1"
                ),
                "per_obligation_tail_upper": _fdoc(
                    Fraction(1, 250_000)
                ),
                "joint_tail_upper": _fdoc(Fraction(97, 25_000)),
            },
        ),
    )


def _arm_results(
    preregistration: gate.FactorialSampleEfficiencyPreregistrationV1,
    source_campaign: source_meta.V0066GraphAcquisitionMetaPriorCampaignV1,
    source_prior: gate.SourcePriorGateEvidenceV1,
    fixed_campaign: graph.VariableOrderGraphCampaignV1,
    fixed_verification: graph.VariableOrderGraphCampaignVerificationV1,
    anytime_results: tuple[anytime.AnytimeVariableGraphResultV1, ...],
    anytime_verifications: tuple[
        anytime.AnytimeVariableGraphVerificationV1,
        ...,
    ],
    direct_fixed_results: tuple[direct_fixed.DirectFixedResultV1, ...],
    direct_fixed_verifications: tuple[
        direct_fixed.DirectFixedVerificationV1,
        ...,
    ],
    direct_sequential_results: tuple[
        direct_sequential.DirectSequentialResultV1,
        ...,
    ],
    direct_sequential_verifications: tuple[
        direct_sequential.DirectSequentialVerificationV1,
        ...,
    ],
) -> tuple[gate.GraphOccurrenceArmResultV1, ...]:
    proposal_by_context = {
        item.context_id: item for item in source_campaign.target_proposals
    }
    anytime_by_context = {
        item.context.context_id: (item, verification)
        for item, verification in zip(
            anytime_results,
            anytime_verifications,
        )
    }
    direct_fixed_by_context = {
        item.context.context_id: (item, verification)
        for item, verification in zip(
            direct_fixed_results,
            direct_fixed_verifications,
        )
    }
    direct_sequential_by_context = {
        item.context.context_id: (item, verification)
        for item, verification in zip(
            direct_sequential_results,
            direct_sequential_verifications,
        )
    }
    rows: list[gate.GraphOccurrenceArmResultV1] = []
    for occurrence in preregistration.occurrences:
        proposal = proposal_by_context[occurrence.context_id]
        sequential_result, sequential_verification = anytime_by_context[
            occurrence.context_id
        ]
        rows.extend(
            (
                gate.adapt_v0066_fixed_quotient_result_v1(
                    preregistration,
                    occurrence,
                    fixed_campaign,
                    fixed_verification,
                ),
                gate.adapt_anytime_quotient_result_v1(
                    preregistration,
                    occurrence,
                    sequential_result,
                    sequential_verification,
                ),
                gate.adapt_v0066_fixed_quotient_result_v1(
                    preregistration,
                    occurrence,
                    fixed_campaign,
                    fixed_verification,
                    source_prior=source_prior,
                    target_proposal=proposal,
                ),
                gate.adapt_anytime_quotient_result_v1(
                    preregistration,
                    occurrence,
                    sequential_result,
                    sequential_verification,
                    source_prior=source_prior,
                    target_proposal=proposal,
                ),
            )
        )
        if (
            occurrence.context_key
            != "variable_negative_k6_minus_edge_v0"
        ):
            fixed_result, fixed_result_verification = (
                direct_fixed_by_context[occurrence.context_id]
            )
            direct_result, direct_result_verification = (
                direct_sequential_by_context[occurrence.context_id]
            )
            rows.extend(
                (
                    gate.adapt_direct_fixed_result_v1(
                        preregistration,
                        occurrence,
                        fixed_result,
                        fixed_result_verification,
                    ),
                    gate.adapt_direct_sequential_result_v1(
                        preregistration,
                        occurrence,
                        direct_result,
                        direct_result_verification,
                    ),
                )
            )
    return tuple(rows)


@functools.lru_cache(maxsize=1)
def run_v0067_factorial_campaign_v1() -> V0067FactorialCampaignV1:
    """Run the complete registered-native 4+2 factorial."""

    source_campaign = (
        source_meta.run_v0066_graph_acquisition_metaprior_v1()
    )
    source_verification = (
        source_meta.verify_v0066_graph_acquisition_metaprior_v1(
            source_campaign
        )
    )
    source_prior = gate.build_v0066_source_prior_gate_evidence_v1(
        source_campaign,
        source_verification,
    )
    preregistration = _preregistration(source_campaign, source_prior)

    fixed_campaign = graph.run_variable_order_graph_campaign_v1()
    fixed_verification = graph.verify_variable_order_graph_campaign_v1(
        fixed_campaign
    )
    if (
        fixed_campaign.source_skeleton.skeleton_id
        != source_campaign.source_skeleton.skeleton_id
    ):
        raise V0067FactorialCampaignInvariantViolation(
            "quotient arms did not share the frozen pretrained skeleton"
        )

    contexts = graph.registered_variable_order_contexts_v1()
    anytime_results = tuple(
        anytime.run_anytime_variable_graph_context_v1(
            context,
            fixed_campaign.source_skeleton,
        )
        for context in contexts
    )
    anytime_verifications = tuple(
        anytime.verify_anytime_variable_graph_result_v1(item)
        for item in anytime_results
    )
    direct_fixed_results = tuple(
        direct_fixed.run_direct_fixed_context_v1(context)
        for context in contexts[:2]
    )
    direct_fixed_verifications = tuple(
        direct_fixed.verify_direct_fixed_result_v1(item)
        for item in direct_fixed_results
    )
    direct_sequential_results = tuple(
        direct_sequential.run_direct_sequential_context_v1(context)
        for context in contexts[:2]
    )
    direct_sequential_verifications = tuple(
        direct_sequential.verify_direct_sequential_result_v1(item)
        for item in direct_sequential_results
    )

    arm_results = _arm_results(
        preregistration,
        source_campaign,
        source_prior,
        fixed_campaign,
        fixed_verification,
        anytime_results,
        anytime_verifications,
        direct_fixed_results,
        direct_fixed_verifications,
        direct_sequential_results,
        direct_sequential_verifications,
    )
    pairing = verify_v0067_paired_prefixes_v1(
        fixed_campaign,
        anytime_results,
        direct_fixed_results,
        direct_sequential_results,
    )
    counters = _native_counter_summary(source_prior, arm_results)
    gate_result = gate.evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source_prior,
        arm_results,
    )
    return V0067FactorialCampaignV1(
        source_campaign,
        source_verification,
        source_prior,
        preregistration,
        fixed_campaign,
        fixed_verification,
        anytime_results,
        anytime_verifications,
        direct_fixed_results,
        direct_fixed_verifications,
        direct_sequential_results,
        direct_sequential_verifications,
        arm_results,
        pairing,
        counters,
        gate_result,
    )


@dataclass(frozen=True, slots=True)
class V0067FactorialCampaignVerificationV1:
    campaign_id: str
    source_verification_id: str
    fixed_quotient_verification_id: str
    anytime_verification_ids: tuple[str, ...]
    direct_fixed_verification_ids: tuple[str, ...]
    direct_sequential_verification_ids: tuple[str, ...]
    rebuilt_arm_result_ids: tuple[str, ...]
    rebuilt_pairing_verification_id: str
    rebuilt_counter_summary_id: str
    rebuilt_gate_result_id: str
    all_upstream_authorities_replayed: bool
    all_adapters_rebuilt: bool
    raw_pairing_replayed: bool
    registered_native_subset_accounting_reconciled: bool
    simultaneous_confidence_reconciled: bool
    exact_objective_constraint_replayed: bool
    online_gate_passed: bool
    meta_prior_target_savings_claimed: bool
    source_prior_amortization_status: str
    known_label_conditional_claim_only: bool
    pretrained_quotient_regime_only: bool
    synthetic_fixture_supports_claim: bool = False
    broad_generalization_claimed: bool = False
    official_execution_allowed: bool = False
    independent_implementation_claimed: bool = False
    separate_semantic_replay: bool = True
    native_accounting_scope: str = (
        "REGISTERED_REAL_NATIVE_AUTHORITY_SUBSET_ONLY"
    )
    counter_completeness_claimed: bool = False
    counter_completeness_gate_status: str = (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    workload_economics_gate_status: str = (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        for value, field in (
            (self.campaign_id, "verified campaign"),
            (self.source_verification_id, "verified source"),
            (
                self.fixed_quotient_verification_id,
                "verified fixed quotient",
            ),
            (
                self.rebuilt_pairing_verification_id,
                "rebuilt pairing",
            ),
            (self.rebuilt_counter_summary_id, "rebuilt counters"),
            (self.rebuilt_gate_result_id, "rebuilt Gate"),
        ):
            _cid(value, field)
        for values, field, expected in (
            (
                self.anytime_verification_ids,
                "verified anytime family",
                3,
            ),
            (
                self.direct_fixed_verification_ids,
                "verified direct fixed family",
                2,
            ),
            (
                self.direct_sequential_verification_ids,
                "verified direct sequential family",
                2,
            ),
            (self.rebuilt_arm_result_ids, "rebuilt Gate cells", 16),
        ):
            if (
                values != tuple(sorted(set(values)))
                or len(values) != expected
            ):
                raise V0067FactorialCampaignInvariantViolation(
                    f"{field} are incomplete"
                )
            for item in values:
                _cid(item, field)
        if (
            any(
                item is not True
                for item in (
                    self.all_upstream_authorities_replayed,
                    self.all_adapters_rebuilt,
                    self.raw_pairing_replayed,
                    self.registered_native_subset_accounting_reconciled,
                    self.simultaneous_confidence_reconciled,
                    self.exact_objective_constraint_replayed,
                    self.online_gate_passed,
                    self.known_label_conditional_claim_only,
                    self.pretrained_quotient_regime_only,
                )
            )
            or self.meta_prior_target_savings_claimed is not False
            or self.source_prior_amortization_status != "NOT_ESTABLISHED"
            or self.synthetic_fixture_supports_claim is not False
            or self.broad_generalization_claimed is not False
            or self.official_execution_allowed is not False
            or self.independent_implementation_claimed is not False
            or self.separate_semantic_replay is not True
            or self.native_accounting_scope
            != "REGISTERED_REAL_NATIVE_AUTHORITY_SUBSET_ONLY"
            or self.counter_completeness_claimed is not False
            or self.counter_completeness_gate_status
            != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.workload_economics_gate_status
            != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise V0067FactorialCampaignInvariantViolation(
                "factorial semantic replay exceeded its claim boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_real_factorial_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "source_verification_id": self.source_verification_id,
            "fixed_quotient_verification_id": (
                self.fixed_quotient_verification_id
            ),
            "anytime_verification_ids": list(
                self.anytime_verification_ids
            ),
            "direct_fixed_verification_ids": list(
                self.direct_fixed_verification_ids
            ),
            "direct_sequential_verification_ids": list(
                self.direct_sequential_verification_ids
            ),
            "rebuilt_arm_result_ids": list(self.rebuilt_arm_result_ids),
            "rebuilt_pairing_verification_id": (
                self.rebuilt_pairing_verification_id
            ),
            "rebuilt_counter_summary_id": (
                self.rebuilt_counter_summary_id
            ),
            "rebuilt_gate_result_id": self.rebuilt_gate_result_id,
            "all_upstream_authorities_replayed": True,
            "all_adapters_rebuilt": True,
            "raw_pairing_replayed": True,
            "registered_native_subset_accounting_reconciled": True,
            "simultaneous_confidence_reconciled": True,
            "exact_objective_constraint_replayed": True,
            "online_gate_passed": True,
            "meta_prior_target_savings_claimed": False,
            "source_prior_amortization_status": (
                self.source_prior_amortization_status
            ),
            "known_label_conditional_claim_only": True,
            "pretrained_quotient_regime_only": True,
            "synthetic_fixture_supports_claim": False,
            "broad_generalization_claimed": False,
            "official_execution_allowed": False,
            "independent_implementation_claimed": False,
            "separate_semantic_replay": True,
            "native_accounting_scope": self.native_accounting_scope,
            "counter_completeness_claimed": False,
            "counter_completeness_gate_status": (
                self.counter_completeness_gate_status
            ),
            "workload_economics_gate_status": (
                self.workload_economics_gate_status
            ),
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_v0067_factorial_campaign_v1(
    campaign: V0067FactorialCampaignV1,
) -> V0067FactorialCampaignVerificationV1:
    """Separately replay real authorities and rebuild the final Gate."""

    if type(campaign) is not V0067FactorialCampaignV1:
        raise V0067FactorialCampaignInvariantViolation(
            "factorial verifier rejects runtime substitutions"
        )
    campaign.__post_init__()
    campaign.source_campaign.__post_init__()
    campaign.source_verification.__post_init__()

    source_verification = (
        source_meta.verify_v0066_graph_acquisition_metaprior_v1(
            campaign.source_campaign
        )
    )
    fixed_verification = graph.verify_variable_order_graph_campaign_v1(
        campaign.fixed_quotient_campaign
    )
    anytime_verifications = tuple(
        anytime.verify_anytime_variable_graph_result_v1(item)
        for item in campaign.anytime_results
    )
    direct_fixed_verifications = tuple(
        direct_fixed.verify_direct_fixed_result_v1(item)
        for item in campaign.direct_fixed_results
    )
    direct_sequential_verifications = tuple(
        direct_sequential.verify_direct_sequential_result_v1(item)
        for item in campaign.direct_sequential_results
    )
    if (
        source_verification.verification_id
        != campaign.source_verification.verification_id
        or fixed_verification.verification_id
        != campaign.fixed_quotient_verification.verification_id
        or tuple(item.verification_id for item in anytime_verifications)
        != tuple(
            item.verification_id for item in campaign.anytime_verifications
        )
        or tuple(
            item.verification_id for item in direct_fixed_verifications
        )
        != tuple(
            item.verification_id
            for item in campaign.direct_fixed_verifications
        )
        or tuple(
            item.verification_id
            for item in direct_sequential_verifications
        )
        != tuple(
            item.verification_id
            for item in campaign.direct_sequential_verifications
        )
    ):
        raise V0067FactorialCampaignInvariantViolation(
            "an upstream semantic authority failed independent replay"
        )

    source_prior = gate.build_v0066_source_prior_gate_evidence_v1(
        campaign.source_campaign,
        source_verification,
    )
    preregistration = _preregistration(
        campaign.source_campaign,
        source_prior,
    )
    rebuilt_arm_results = _arm_results(
        preregistration,
        campaign.source_campaign,
        source_prior,
        campaign.fixed_quotient_campaign,
        fixed_verification,
        campaign.anytime_results,
        anytime_verifications,
        campaign.direct_fixed_results,
        direct_fixed_verifications,
        campaign.direct_sequential_results,
        direct_sequential_verifications,
    )
    pairing = verify_v0067_paired_prefixes_v1(
        campaign.fixed_quotient_campaign,
        campaign.anytime_results,
        campaign.direct_fixed_results,
        campaign.direct_sequential_results,
    )
    counters = _native_counter_summary(source_prior, rebuilt_arm_results)
    rebuilt_gate = gate.evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source_prior,
        rebuilt_arm_results,
    )
    if (
        source_prior.gate_prior_id != campaign.source_prior.gate_prior_id
        or preregistration.preregistration_id
        != campaign.preregistration.preregistration_id
        or tuple(item.result_id for item in rebuilt_arm_results)
        != tuple(item.result_id for item in campaign.arm_results)
        or pairing.pairing_verification_id
        != campaign.pairing_verification.pairing_verification_id
        or counters.counter_summary_id
        != campaign.native_counters.counter_summary_id
        or rebuilt_gate.gate_result_id
        != campaign.gate_result.gate_result_id
    ):
        raise V0067FactorialCampaignInvariantViolation(
            "adapter, pairing, counter, or Gate replay changed identity"
        )
    if (
        source_prior.offline_source_work
        != gate.EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            5_451_776,
            80,
            0,
            0,
        )
        or source_prior.physical_unique_proxy_work
        != gate.EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            5_242_880,
            40,
            0,
            0,
        )
        or source_prior.sunk_source_provenance_work
        != gate.EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            0,
            120,
            0,
            0,
        )
        or rebuilt_gate.confidence_reconciliation.joint_tail_upper
        != Fraction(97, 25_000)
        or rebuilt_gate.confidence_reconciliation.joint_confidence_lower
        != Fraction(24_903, 25_000)
        or rebuilt_gate.meta_prior_target_savings_claimed is not False
        or rebuilt_gate.offline_inclusive_status != "NOT_ESTABLISHED"
        or rebuilt_gate.claim_scope != gate.REGISTERED_CLAIM_SCOPE
        or rebuilt_gate.online_gate_passed is not True
    ):
        raise V0067FactorialCampaignInvariantViolation(
            "source accounting, confidence, or narrow claim failed replay"
        )
    return V0067FactorialCampaignVerificationV1(
        campaign.campaign_id,
        source_verification.verification_id,
        fixed_verification.verification_id,
        tuple(
            sorted(item.verification_id for item in anytime_verifications)
        ),
        tuple(
            sorted(
                item.verification_id
                for item in direct_fixed_verifications
            )
        ),
        tuple(
            sorted(
                item.verification_id
                for item in direct_sequential_verifications
            )
        ),
        tuple(sorted(item.result_id for item in rebuilt_arm_results)),
        pairing.pairing_verification_id,
        counters.counter_summary_id,
        rebuilt_gate.gate_result_id,
        True,
        True,
        True,
        True,
        True,
        True,
        rebuilt_gate.online_gate_passed,
        rebuilt_gate.meta_prior_target_savings_claimed,
        rebuilt_gate.offline_inclusive_status,
        True,
        True,
    )


__all__ = [
    "CONTRACT_VERSION",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V0067FactorialCampaignInvariantViolation",
    "V0067FactorialCampaignV1",
    "V0067FactorialCampaignVerificationV1",
    "V0067NativeCounterSummaryV1",
    "V0067PairedPrefixVerificationV1",
    "run_v0067_factorial_campaign_v1",
    "verify_v0067_factorial_campaign_v1",
    "verify_v0067_paired_prefixes_v1",
]
