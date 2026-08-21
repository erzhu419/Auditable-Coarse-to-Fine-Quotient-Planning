"""Matched acquisition using the independently verified V132 opaque dictionary."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v133 as domains
from acfqp.construction_k7_opaque_source_archive_independent_verifier_v132 import (
    FROZEN_DICTIONARY_ID,
    VERIFICATION_ID as V132_VERIFICATION_ID,
)
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    exact_generic_artifact_factor_replay_v121,
)
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.robust_factor_dictionary_acquisition_v131r2 import (
    robust_dictionary_factor_stop_update_v131r2,
    synthesize_robust_dictionary_factor_candidate_v131r2,
)


class OpaqueArchiveFactorAcquisitionV133Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpaqueArchiveFactorAcquisitionV133Error(message)


def _validated_projection(
    dictionary: Mapping[str, Any], verification: Mapping[str, Any]
) -> Mapping[str, Any]:
    projection = dictionary.get("v15_partial_synthesizer_projection")
    support = dictionary.get("support_and_leave_one_artifact_evidence")
    if (
        dictionary.get("dictionary_id") != FROZEN_DICTIONARY_ID
        or dictionary.get("source_archive_cardinality") != 4
        or dictionary.get("selected_template_count") != 3
        or dictionary.get("target_outcomes_accessed") is not False
        or dictionary.get("fixed_source_campaign_inventory_embedded_in_synthesizer")
        is not False
        or type(projection) is not dict
        or projection.get("source_factor_library_id") != FROZEN_DICTIONARY_ID
        or type(support) is not list
        or not all(
            holdout.get("eligible") is True
            for row in support
            if row.get("selected") is True
            for holdout in row.get("leave_one_artifact_reconstructions", ())
        )
        or verification.get("verification_id") != V132_VERIFICATION_ID
        or verification.get("dictionary_id") != FROZEN_DICTIONARY_ID
        or verification.get("producer_free_dictionary_reconstruction") is not True
        or verification.get(
            "every_selected_template_leave_one_artifact_positive_gain_verified"
        )
        is not True
        or verification.get("target_outcomes_accessed") is not False
    ):
        _fail("V133 V132 dictionary receipt changed")
    return projection


def acquire_matched_opaque_archive_factor_arms_v133(
    adapter: Any,
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _validated_projection(dictionary, dictionary_verification)
    states = {
        enabled: {
            "candidate": None,
            "issued": 0,
            "invalidated": 0,
            "disagreements": 0,
            "epoch": 0,
            "successes": 0,
            "previous": None,
            "history": [],
            "derivation_compute": 0,
            "selected_artifact": 0,
        }
        for enabled in (True, False)
    }
    results: dict[bool, dict[str, Any]] = {}
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    accepting_label = None
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    for labels, batch in enumerate(
        fair_witness_blind_path_first_stream_v129r1(adapter), 1
    ):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        if accepting_label is None and any(
            row.terminal_acceptance_after is True for row in batch
        ):
            accepting_label = labels
        for enabled in (True, False):
            if enabled in results:
                continue
            state = states[enabled]
            candidate = state["candidate"]
            if candidate is not None:
                replay = exact_generic_artifact_factor_replay_v121(
                    candidate, current, adapter.catalogue
                )
                if replay["exact"] is True:
                    state["successes"] += 1
                else:
                    state["previous"] = candidate.public_document["candidate_id"]
                    state["candidate"] = None
                    state["invalidated"] += 1
                    state["epoch"] += 1
                    state["successes"] = 0
            if state["candidate"] is None:
                try:
                    candidate, compute = synthesize_robust_dictionary_factor_candidate_v131r2(
                        current,
                        adapter.catalogue,
                        projection,
                        support_label_count=labels,
                        factor_prior_enabled=enabled,
                        layout_domain=config["generic_domains"]["layout"],
                        minimum_factor_assignment_count=config[
                            "minimum_reusable_factor_count"
                        ],
                    )
                    state["candidate"] = candidate
                    state["issued"] = labels
                    state["derivation_compute"] += compute[
                        "generic_atomic_expression_evaluations"
                    ]
                    state["selected_artifact"] = compute[
                        "artifact_expression_selected_count"
                    ]
                    if (
                        state["previous"] is not None
                        and candidate.public_document["candidate_id"]
                        != state["previous"]
                    ):
                        state["disagreements"] += 1
                except Exception as error:
                    state["history"].append(
                        {
                            "support_label_count": labels,
                            "candidate_available": False,
                            "constructor_error_type": type(error).__name__,
                        }
                    )
                    continue
            candidate = state["candidate"]
            stop = robust_dictionary_factor_stop_update_v131r2(
                candidate,
                current,
                adapter.catalogue,
                factor_prior_enabled=enabled,
                candidate_epoch=state["epoch"],
                invalidated_candidate_count=state["invalidated"],
                post_issuance_exact_prediction_success_count=state["successes"],
                global_alpha_denominator=config["global_alpha_denominator"],
            )
            state["history"].append(
                {
                    "support_label_count": labels,
                    "candidate_available": True,
                    "candidate_id": candidate.public_document["candidate_id"],
                    "stopped_by_shared_rule": stop["stopped"],
                    "accepting_projection_available": accepting_label is not None,
                }
            )
            if stop["stopped"] is not True or accepting_label is None:
                continue
            prefix = tuple(row for selected in batches[:labels] for row in selected)
            payload = {
                "schema": "acfqp.opaque_archive_factor_acquisition_arm.v133",
                "family": adapter.family,
                "seed": adapter.seed,
                "arm": "OPAQUE_ARCHIVE_FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR",
                "factor_prior_enabled": enabled,
                "v132_dictionary_id": FROZEN_DICTIONARY_ID,
                "v132_independent_verification_id": V132_VERIFICATION_ID,
                "verified_dictionary_receipt_consumed_before_target_outcomes": True,
                "fair_witness_blind_path_first_backtracking": True,
                "generation_witness_accessed": False,
                "reachable_frontier_exhaustion_used_as_stopping_input": False,
                "only_arm_switch_is_normalized_factor_prior": True,
                "same_generic_atomic_hypothesis_pool": True,
                "same_candidate_carrier_and_schema": True,
                "same_candidate_replay_function": True,
                "same_stopping_rule_function": True,
                "ground_support_labels": labels,
                "raw_transition_count": len(prefix),
                "raw_transition_sha256": hashlib.sha256(
                    canonical_json_bytes([row.to_document() for row in prefix])
                ).hexdigest(),
                "candidate": dict(candidate.public_document),
                "candidate_issued_at_support_label": state["issued"],
                "invalidated_candidate_count": state["invalidated"],
                "candidate_program_disagreement_count": state["disagreements"],
                "candidate_epoch": state["epoch"],
                "post_issuance_exact_prediction_success_count": state["successes"],
                "first_accepting_observation_label": accepting_label,
                "terminal_stop_update": dict(stop),
                "stopping_history": list(state["history"]),
                "derivation_compute_events": state["derivation_compute"],
                "artifact_expression_selected_count": state["selected_artifact"],
                "sample_labels_and_derivation_compute_separate": True,
                "complete_world_model_claimed": False,
                "planning_authority_present": False,
            }
            results[enabled] = {
                "document": {
                    **payload,
                    "acquisition_id": domains.extension_content_id_v133(
                        domains.CONSTRUCTION_K7_OPAQUE_ARCHIVE_FACTOR_ACQUISITION_V133_DOMAIN,
                        payload,
                    ),
                },
                "candidate": candidate,
                "rows": prefix,
                "batches": tuple(batches[:labels]),
            }
        if len(results) == 2:
            prior, strict = results[True], results[False]
            common = min(len(prior["batches"]), len(strict["batches"]))
            if tuple(
                row for batch in prior["batches"][:common] for row in batch
            ) != tuple(
                row for batch in strict["batches"][:common] for row in batch
            ):
                _fail("V133 matched arms diverged before common stop")
            return {
                "OPAQUE_ARCHIVE_FACTOR_PRIOR_ON": prior,
                "STRICT_NO_PRIOR": strict,
            }
    _fail(
        f"V133 opaque-archive acquisition did not close before cap for "
        f"{adapter.family} seed {adapter.seed}"
    )


__all__ = ("acquire_matched_opaque_archive_factor_arms_v133",)
