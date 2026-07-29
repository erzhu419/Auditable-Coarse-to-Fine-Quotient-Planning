"""Independent replay of the V0-072 development source-prior control.

This verifier deliberately does not import or call the campaign's production
raw-tape, proxy, aggregate, or consensus helpers.  All domains, primitive
source tapes, midranks, standard V2 content IDs, and the compact authority ID
are reconstructed here.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
from itertools import combinations
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import verified_source_acquisition_archive_v2 as source_v2


SCHEMA_VERSION = "1.0.0"
SELECTOR_SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v072_five_arm_development_source_prior_independent_verifier_v1"
)

BEFORE_DRAWS = 128
AFTER_DRAWS = 256
SUFFIX_DRAWS = 128

CAMPAIGN_DOMAINS = {
    "source_context": "acfqp:v072-five-arm-dev-source-context:v1",
    "source_raw": "acfqp:v072-five-arm-dev-source-raw-observation:v1",
    "source_trial": "acfqp:v072-five-arm-dev-source-trial:v1",
    "source_archive": "acfqp:v072-five-arm-dev-source-archive:v1",
    "source_authority": "acfqp:v072-five-arm-dev-source-authority:v1",
}
ARCHIVE_DOMAIN_PREFIX = "acfqp:verified-source-acquisition-archive:"
SELECTOR_SOURCE_BINDING_DOMAIN = (
    "acfqp:v072-verified-source-prior-binding:v2"
)
SELECTOR_OOD_DOMAIN = "acfqp:v072-ood-prior-typed-abstention:v2"


class IndependentDevelopmentSourcePriorVerificationFailure(ValueError):
    """Raw source evidence or its derived proposal consensus is invalid."""


def _fail(message: str) -> None:
    raise IndependentDevelopmentSourcePriorVerificationFailure(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentDevelopmentSourcePriorVerificationFailure(
            f"{field_name} is not one canonical SHA-256 ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("independent source arithmetic is not exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _feature_documents() -> tuple[tuple[dict[str, Any], str], ...]:
    destination_categories = tuple(
        item.value
        for item in robust.DestinationCategory
        if item is not robust.DestinationCategory.OTHER
    )

    def subsets(values: tuple[str, ...]) -> Iterable[tuple[str, ...]]:
        for size in range(1, len(values) + 1):
            yield from combinations(values, size)

    stage_categories = {
        "ROOT": (
            robust.SelectedRowCategory.ROOT_SELECTED.value,
            robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT.value,
        ),
        "CONTINUATION": (
            robust.SelectedRowCategory.CONTINUATION_SELECTED.value,
            robust.SelectedRowCategory
            .CONTINUATION_CONCRETIZER_COMPONENT.value,
        ),
    }
    output: list[tuple[dict[str, Any], str]] = []
    for stage, categories in stage_categories.items():
        for category in categories:
            for action_bin in ("1", "2", "3_PLUS"):
                for support_bin in ("1", "2", "3_PLUS"):
                    for destinations in subsets(destination_categories):
                        payload = {
                            "schema": (
                                "acfqp.portable_acquisition_core_feature.v2"
                            ),
                            "schema_version": source_v2.SCHEMA_VERSION,
                            "feature_schema_id": source_v2.FEATURE_SCHEMA_ID,
                            "stage_role": stage,
                            "selected_row_category": category,
                            "catalogue_action_count_bin": action_bin,
                            "concretizer_support_count_bin": support_bin,
                            "destination_category_presence": list(destinations),
                            "ids_stripped": True,
                            "exact_probabilities_absent": True,
                            "exact_counts_absent": True,
                            "vertex_labels_absent": True,
                            "context_identity_absent": True,
                            "observed_support_count_absent": True,
                        }
                        feature_id = _hash(
                            (
                                f"{ARCHIVE_DOMAIN_PREFIX}"
                                "portable-feature:v2"
                            ),
                            payload,
                        )
                        output.append((payload, feature_id))
    return tuple(sorted(output, key=lambda item: item[1]))


def _context_documents() -> tuple[tuple[str, dict[str, Any], str], ...]:
    values = (
        (
            "PATH4_SOURCE",
            ((0, 1), (1, 2), (2, 3)),
            "PERIODIC_FEATURE_DIFFICULTY_LAW_P1_V1",
        ),
        (
            "STAR4_SOURCE",
            ((0, 1), (0, 2), (0, 3)),
            "PERIODIC_FEATURE_DIFFICULTY_LAW_P2_V1",
        ),
    )
    output = []
    for key, edges, law in values:
        payload = {
            "schema": "acfqp.v072_five_arm_dev_source_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": key,
            "topology_edges": [list(item) for item in edges],
            "observation_law": law,
            "source_role": "OFFLINE_DEVELOPMENT_PROPOSAL_ONLY",
            "registered_context": False,
            "target_observations_used": 0,
        }
        output.append(
            (
                key,
                payload,
                _hash(CAMPAIGN_DOMAINS["source_context"], payload),
            )
        )
    return tuple(output)


def _probability_numerator(context_key: str, ordinal: int) -> int:
    difficulty = ordinal % 24
    if context_key == "PATH4_SOURCE":
        return 4 + difficulty
    if context_key == "STAR4_SOURCE":
        return 8 + 2 * difficulty
    _fail("unknown development source context")
    raise AssertionError


def _raw_replay(
    *,
    context_key: str,
    context_id: str,
    feature_id: str,
    ordinal: int,
) -> tuple[int, int, str, str, str]:
    numerator = _probability_numerator(context_key, ordinal)
    rotation = int(feature_id[:8], 16) % 64
    digest = hashlib.sha256()
    before = 0
    after = 0
    first = ""
    last = ""
    for index in range(1, AFTER_DRAWS + 1):
        success = (index - 1 + rotation) % 64 < numerator
        payload = {
            "schema": "acfqp.v072_five_arm_dev_source_raw.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "portable_feature_key": feature_id,
            "sequence_index": index,
            "success": success,
            "source_role": "OFFLINE_DEVELOPMENT_PROPOSAL_ONLY",
            "registered_target_evidence": False,
        }
        commitment = _hash(CAMPAIGN_DOMAINS["source_raw"], payload)
        if not first:
            first = commitment
        last = commitment
        digest.update(bytes.fromhex(commitment))
        after += int(success)
        if index <= BEFORE_DRAWS:
            before += int(success)
    return before, after, first, last, digest.hexdigest()


def _proxy(draws: int, successes: int) -> Fraction:
    return Fraction(successes + 1, draws + 1) / (draws // 64)


def _trial_payload(
    *,
    context_id: str,
    feature_id: str,
    ordinal: int,
    replay: tuple[int, int, str, str, str],
) -> tuple[dict[str, Any], Fraction]:
    before_proxy = _proxy(BEFORE_DRAWS, replay[0])
    after_proxy = _proxy(AFTER_DRAWS, replay[1])
    gain = max(Fraction(0), before_proxy - after_proxy)
    per_draw = gain / SUFFIX_DRAWS
    return (
        {
            "schema": "acfqp.v072_five_arm_dev_source_trial.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": context_id,
            "portable_feature_key": feature_id,
            "feature_ordinal": ordinal,
            "before_draws": BEFORE_DRAWS,
            "after_draws": AFTER_DRAWS,
            "incremental_draws": SUFFIX_DRAWS,
            "before_success_count": replay[0],
            "after_success_count": replay[1],
            "first_raw_commitment_id": replay[2],
            "last_raw_commitment_id": replay[3],
            "ordered_raw_commitment_digest": replay[4],
            "before_uncertainty_proxy": _fdoc(before_proxy),
            "after_uncertainty_proxy": _fdoc(after_proxy),
            "proposal_gain": _fdoc(gain),
            "gain_per_draw": _fdoc(per_draw),
            "raw_tape_replayed": True,
            "ranking_only": True,
            "confidence_interval_claimed": False,
            "certificate_input": False,
            "caller_supplied_gain": False,
            "registered_target_evidence": False,
        },
        per_draw,
    )


def _aggregate_payload(
    *,
    context_id: str,
    feature_id: str,
    trial_id: str,
    mean: Fraction,
    midrank: Fraction,
    degenerate: bool,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.source_context_feature_aggregate.v2",
        "schema_version": source_v2.SCHEMA_VERSION,
        "source_context_id": context_id,
        "feature_key": feature_id,
        "trial_ids": [trial_id],
        "mean_gain_per_draw": _fdoc(mean),
        "normalized_midrank": _fdoc(midrank),
        "context_ranking_degenerate": degenerate,
    }


def _consensus_payload(
    *,
    feature_id: str,
    context_ids: tuple[str, ...],
    aggregate_ids: tuple[str, ...],
    mean_gain: Fraction,
    mean_rank: Fraction,
    worst_rank: Fraction,
    disagreement: Fraction,
    degenerate: bool,
    disposition: source_v2.FeatureConsensusDispositionV2,
    multiplier: Fraction,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.nonrectangular_feature_consensus.v2",
        "schema_version": source_v2.SCHEMA_VERSION,
        "feature_key": feature_id,
        "source_context_ids": list(context_ids),
        "aggregate_ids": list(aggregate_ids),
        "mean_gain_per_draw": _fdoc(mean_gain),
        "mean_midrank": _fdoc(mean_rank),
        "worst_midrank": _fdoc(worst_rank),
        "disagreement": _fdoc(disagreement),
        "any_context_ranking_degenerate": degenerate,
        "disagreement_threshold": _fdoc(
            source_v2.MAX_MIDRANK_DISAGREEMENT
        ),
        "disposition": disposition.value,
        "multiplier": _fdoc(multiplier),
        "missing_feature_behavior": "NEUTRAL_MULTIPLIER",
    }


def verify_development_source_prior_authority_independently_v1(
    claimed: Any,
) -> Any:
    """Recompute every source primitive without production helper calls."""

    from acfqp import v072_five_arm_confirmatory_campaign_v1 as types

    if type(claimed) is not types.DevelopmentSourcePriorAuthorityV1:
        _fail("source-prior claim has a foreign concrete type")
    expected_features = _feature_documents()
    feature_by_id = {feature_id: payload for payload, feature_id in expected_features}
    expected_contexts = _context_documents()
    context_by_id = {
        context_id: (key, payload)
        for key, payload, context_id in expected_contexts
    }
    if (
        len(claimed.contexts) != len(expected_contexts)
        or tuple(item.context_id for item in claimed.contexts)
        != tuple(item[2] for item in expected_contexts)
        or any(
            item.to_document()
            != {**payload, "context_id": context_id}
            for item, (_, payload, context_id) in zip(
                claimed.contexts, expected_contexts
            )
        )
    ):
        _fail("source-context inventory or content identity differs")
    trial_by_key = {
        (
            item.context.context_id,
            item.portable_feature.feature_key,
        ): item
        for item in claimed.trials
    }
    if len(trial_by_key) != len(context_by_id) * len(feature_by_id):
        _fail("source-trial inventory is incomplete or duplicated")

    trial_ids: dict[tuple[str, str], str] = {}
    means: dict[tuple[str, str], Fraction] = {}
    for context_id, (context_key, _) in context_by_id.items():
        for ordinal, (_, feature_id) in enumerate(expected_features):
            trial = trial_by_key.get((context_id, feature_id))
            if trial is None:
                _fail("source trial is missing one context-feature pair")
            feature_document = trial.portable_feature.to_document()
            feature_claim_id = feature_document.pop("feature_key")
            if (
                feature_claim_id != feature_id
                or feature_document != feature_by_id[feature_id]
            ):
                _fail("portable source feature content identity differs")
            replay = _raw_replay(
                context_key=context_key,
                context_id=context_id,
                feature_id=feature_id,
                ordinal=ordinal,
            )
            payload, per_draw = _trial_payload(
                context_id=context_id,
                feature_id=feature_id,
                ordinal=ordinal,
                replay=replay,
            )
            trial_id = _hash(CAMPAIGN_DOMAINS["source_trial"], payload)
            trial_document = trial.to_document()
            claimed_trial_id = trial_document.pop("trial_id")
            trial_document.pop("source_context")
            trial_document.pop("portable_feature")
            if (
                claimed_trial_id != trial_id
                or trial_document != payload
                or trial.before_success_count != replay[0]
                or trial.after_success_count != replay[1]
                or trial.gain_per_draw != per_draw
            ):
                _fail("source raw tape, proxy, or trial identity differs")
            trial_ids[(context_id, feature_id)] = trial_id
            means[(context_id, feature_id)] = per_draw

    midranks: dict[tuple[str, str], Fraction] = {}
    degenerate_by_context: dict[str, bool] = {}
    for context_id in context_by_id:
        ordered = sorted(
            (
                (feature_id, means[(context_id, feature_id)])
                for feature_id in feature_by_id
            ),
            key=lambda item: (item[1], item[0]),
        )
        denominator = len(ordered) - 1
        degenerate_by_context[context_id] = (
            denominator <= 0 or len({item[1] for item in ordered}) <= 1
        )
        cursor = 0
        while cursor < len(ordered):
            end = cursor + 1
            while end < len(ordered) and ordered[end][1] == ordered[cursor][1]:
                end += 1
            rank = Fraction(cursor + end - 1, 2 * denominator)
            for feature_id, _ in ordered[cursor:end]:
                midranks[(context_id, feature_id)] = rank
            cursor = end

    aggregate_by_key = {
        (item.source_context_id, item.feature_key): item
        for item in claimed.context_feature_aggregates
    }
    aggregate_ids: dict[tuple[str, str], str] = {}
    for key, mean in means.items():
        context_id, feature_id = key
        payload = _aggregate_payload(
            context_id=context_id,
            feature_id=feature_id,
            trial_id=trial_ids[key],
            mean=mean,
            midrank=midranks[key],
            degenerate=degenerate_by_context[context_id],
        )
        aggregate_id = _hash(
            f"{ARCHIVE_DOMAIN_PREFIX}context-feature-aggregate:v2",
            payload,
        )
        claimed_aggregate = aggregate_by_key.get(key)
        if claimed_aggregate is None:
            _fail("source aggregate is missing")
        document = claimed_aggregate.to_document()
        claimed_id = document.pop("aggregate_id")
        if claimed_id != aggregate_id or document != payload:
            _fail("source aggregate or midrank identity differs")
        aggregate_ids[key] = aggregate_id

    consensus_by_feature = {
        item.feature_key: item for item in claimed.consensus
    }
    consensus_ids: list[str] = []
    for feature_id in feature_by_id:
        context_ids = tuple(
            sorted(context_id for context_id in context_by_id)
        )
        ranks = tuple(
            midranks[(context_id, feature_id)]
            for context_id in context_ids
        )
        mean_rank = sum(ranks, Fraction(0)) / len(ranks)
        worst_rank = min(ranks)
        disagreement = mean_rank - worst_rank
        mean_gain = sum(
            (
                means[(context_id, feature_id)]
                for context_id in context_ids
            ),
            Fraction(0),
        ) / len(context_ids)
        aggregate_tuple = tuple(
            sorted(
                aggregate_ids[(context_id, feature_id)]
                for context_id in context_ids
            )
        )
        degenerate = any(
            degenerate_by_context[context_id]
            for context_id in context_ids
        )
        disposition = (
            source_v2.FeatureConsensusDispositionV2.APPLIED
            if (
                len(context_ids) >= source_v2.MIN_SOURCE_CONTEXTS_PER_FEATURE
                and not degenerate
                and mean_gain > 0
                and disagreement
                <= source_v2.MAX_MIDRANK_DISAGREEMENT
            )
            else (
                source_v2.FeatureConsensusDispositionV2.HIGH_DISAGREEMENT
                if disagreement
                > source_v2.MAX_MIDRANK_DISAGREEMENT
                else source_v2.FeatureConsensusDispositionV2
                .DEGENERATE_CONTEXT_RANKING
            )
        )
        multiplier = (
            source_v2.MIN_PRIOR_MULTIPLIER
            + (
                source_v2.MAX_PRIOR_MULTIPLIER
                - source_v2.MIN_PRIOR_MULTIPLIER
            )
            * mean_rank
            if disposition
            is source_v2.FeatureConsensusDispositionV2.APPLIED
            else source_v2.NEUTRAL_PRIOR_MULTIPLIER
        )
        payload = _consensus_payload(
            feature_id=feature_id,
            context_ids=context_ids,
            aggregate_ids=aggregate_tuple,
            mean_gain=mean_gain,
            mean_rank=mean_rank,
            worst_rank=worst_rank,
            disagreement=disagreement,
            degenerate=degenerate,
            disposition=disposition,
            multiplier=multiplier,
        )
        consensus_id = _hash(
            f"{ARCHIVE_DOMAIN_PREFIX}feature-consensus:v2",
            payload,
        )
        item = consensus_by_feature.get(feature_id)
        if item is None:
            _fail("source consensus is missing")
        document = item.to_document()
        claimed_id = document.pop("consensus_id")
        if claimed_id != consensus_id or document != payload:
            _fail("source consensus, rank, or multiplier differs")
        consensus_ids.append(consensus_id)

    sorted_trial_ids = sorted(trial_ids.values())
    sorted_aggregate_ids = sorted(aggregate_ids.values())
    sorted_consensus_ids = sorted(consensus_ids)
    archive_payload = {
        "schema": "acfqp.v072_five_arm_dev_source_archive.v1",
        "schema_version": SCHEMA_VERSION,
        "source_context_ids": [
            item[2] for item in expected_contexts
        ],
        "source_trial_ids": sorted_trial_ids,
        "aggregate_ids": sorted_aggregate_ids,
        "consensus_ids": sorted_consensus_ids,
        "source_frozen": True,
        "proposal_only": True,
        "registered_target_evidence": False,
    }
    archive_id = _hash(
        CAMPAIGN_DOMAINS["source_archive"],
        archive_payload,
    )
    binding_payload = {
        "schema": "acfqp.v072_verified_source_prior_binding.v2",
        "schema_version": SELECTOR_SCHEMA_VERSION,
        "archive_id": archive_id,
        "feature_schema_id": source_v2.FEATURE_SCHEMA_ID,
        "consensus_ids": sorted_consensus_ids,
        "source_frozen": True,
        "ranking_only": True,
        "may_certify": False,
    }
    binding_id = _hash(SELECTOR_SOURCE_BINDING_DOMAIN, binding_payload)
    binding_doc = claimed.source_prior_binding.to_document()
    claimed_binding_id = binding_doc.pop("source_prior_binding_id")
    binding_doc.pop("consensus")
    if claimed_binding_id != binding_id or binding_doc != binding_payload:
        _fail("standard source-prior binding content identity differs")
    ood_doc = claimed.ood_abstention.to_document()
    ood_id = ood_doc.pop("abstention_id")
    expected_ood_payload = {
        "schema": "acfqp.v072_ood_prior_typed_abstention.v2",
        "schema_version": SELECTOR_SCHEMA_VERSION,
        "rejected_prior_id": binding_id,
        "rejected_feature_schema_id": (
            claimed.ood_abstention.rejected_feature_schema_id
        ),
        "reason": "SCHEMA_MISMATCH",
        "source_numerical_inputs": [],
        "source_numerical_inputs_absent": True,
        "ranking_multiplier": _fdoc(Fraction(1)),
    }
    if (
        ood_doc != expected_ood_payload
        or ood_id != _hash(SELECTOR_OOD_DOMAIN, expected_ood_payload)
    ):
        _fail("OOD typed abstention identity differs")
    authority_payload = {
        "schema": "acfqp.v072_five_arm_dev_source_authority.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": types.PROPOSED_CONTRACT_VERSION,
        "profile_key": types.PROFILE_KEY,
        "source_context_ids": [item[2] for item in expected_contexts],
        "source_archive_id": archive_id,
        "source_prior_binding_id": binding_id,
        "ood_abstention_id": ood_id,
        "source_trial_count": len(sorted_trial_ids),
        "source_raw_accepted_draws": len(sorted_trial_ids) * AFTER_DRAWS,
        "consensus_count": len(sorted_consensus_ids),
        "source_quantities_are_proposal_only": True,
        "source_quantities_in_certificate_inputs": 0,
        "caller_supplied_gain": False,
        "caller_supplied_rank": False,
        "caller_supplied_multiplier": False,
        "registered_target_evidence": False,
        "sample_efficiency_evidence": False,
    }
    authority_id = _hash(
        CAMPAIGN_DOMAINS["source_authority"],
        authority_payload,
    )
    if (
        claimed.source_archive_id != archive_id
        or claimed.authority_id != authority_id
    ):
        _fail("source archive or compact authority identity differs")
    return types.DevelopmentSourcePriorIndependentAttestationV1(
        authority_id,
        archive_id,
        binding_id,
        len(expected_contexts),
        len(sorted_trial_ids),
        len(sorted_trial_ids) * AFTER_DRAWS,
        len(sorted_consensus_ids),
    )


__all__ = [
    "IndependentDevelopmentSourcePriorVerificationFailure",
    "SCHEMA_VERSION",
    "VERIFICATION_PROFILE",
    "verify_development_source_prior_authority_independently_v1",
]
