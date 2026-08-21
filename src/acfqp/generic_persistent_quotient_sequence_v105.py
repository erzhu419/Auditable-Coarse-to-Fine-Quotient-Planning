"""Persistent quotient-model action ordering with exact local certificates."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_actual_quotient_execution_receipt_v105 import (
    build_actual_quotient_execution_receipt_v105,
    verify_actual_quotient_execution_receipt_v105,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    compile_observation_quotient_graph_v105,
    plan_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_receipted_preloaded_certificate_engine_v103 import (
    run_receipted_preloaded_certificate_episode_v103,
)
from acfqp.phase3e_ids import canonical_json_bytes


_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-quotient-sequence:v105\x00"


class GenericPersistentQuotientSequenceV105Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPersistentQuotientSequenceV105Error(message)


def _row(document: Mapping[str, Any]) -> FlatRawTransitionV4:
    selected = document.get("selected_action")
    if type(selected) is not dict:
        _fail("V105 persisted transition action changed")
    return FlatRawTransitionV4(
        document["occurrence"],
        document["transition_index"],
        tuple(document["pre_vector"]),
        tuple(document["legal_action_keys_before"]),
        FlatRawActionV4(
            selected["action_key"], tuple(selected["anonymous_fields"])
        ),
        tuple(document["post_vector"]),
        tuple(document["legal_action_keys_after"]),
        document["terminal_acceptance_after"],
        document.get("outcome_tape_sha256"),
    )


def _deduplicate(
    rows: tuple[FlatRawTransitionV4, ...],
) -> tuple[FlatRawTransitionV4, ...]:
    unique = {}
    for row in rows:
        unique[(row.pre, row.action.key, row.post)] = row
    return tuple(unique[key] for key in sorted(unique))


def _group_count(rows: tuple[FlatRawTransitionV4, ...]) -> int:
    return len({(row.pre, row.action.key) for row in rows})


def _orderer(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[FlatRawTransitionV4, ...],
    model: Mapping[str, Any],
    *,
    maximum_abstract_depth: int,
):
    legal_by_raw = {}
    for row in rows:
        legal_by_raw[row.pre] = row.legal_before
        legal_by_raw[row.post] = row.legal_after

    def order(raw: tuple[int, ...]) -> Mapping[str, Any] | None:
        legal = legal_by_raw.get(raw)
        if not legal:
            return None
        try:
            plan = plan_observation_quotient_graph_v105(
                model,
                candidate,
                rows,
                adapter.catalogue,
                raw,
                maximum_depth=maximum_abstract_depth,
            )
        except Exception as error:
            if not error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            return None
        key = plan["initial_action_key"]
        if key not in legal:
            return None
        shield = shield_abstract_action_order_v99(
            abstract_proposal=(key,),
            partial_proposal=(key,),
            legal_action_keys=legal,
        )
        return {
            **plan,
            "agreement_shield_receipt": shield,
            "legacy_two_channel_shield_carries_one_identical_quotient_proposal": True,
        }

    return order


def _actual_receipts(
    episode: Mapping[str, Any],
) -> list[dict[str, Any]]:
    plans = {}
    for wrapper in episode["abstract_plan_receipts"]:
        raw = wrapper.get("raw_state") if type(wrapper) is dict else None
        if type(raw) is not list or tuple(raw) in plans:
            _fail("V105 quotient plan receipt inventory changed")
        plans[tuple(raw)] = wrapper
    result = []
    for base in episode["abstract_execution_receipts"]:
        raw = tuple(base["raw_state"])
        result.append(
            verify_actual_quotient_execution_receipt_v105(
                build_actual_quotient_execution_receipt_v105(
                    episode_index=episode["episode_index"],
                    base_execution_receipt=base,
                    quotient_plan_receipt=plans.get(raw),
                )
            )
        )
    return result


def run_persistent_quotient_sequence_v105(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    if (
        type(candidate) is not PartialFactorCandidateV15
        or type(observed_rows) is not tuple
        or not observed_rows
        or _group_count(observed_rows) != acquisition_ground_support_labels
        or type(episode_indices) is not tuple
        or len(episode_indices) < 2
        or len(set(episode_indices)) != len(episode_indices)
        or maximum_abstract_depth <= 0
        or maximum_execution_steps <= 0
        or maximum_incremental_certificate_ground_support_labels <= 0
    ):
        _fail("V105 persistent quotient sequence inventory changed")
    persistent_rows = _deduplicate(observed_rows)
    paid_certificate_labels = 0
    episodes = []
    models = []
    receipts = []
    previous_model_id = None
    previous_incremental = None
    for episode_index in episode_indices:
        model = compile_observation_quotient_graph_v105(
            candidate, persistent_rows, adapter.catalogue
        )
        if (
            previous_model_id is not None
            and model["quotient_graph_id"] != previous_model_id
            and not previous_incremental
        ):
            _fail("V105 quotient graph changed without a certificate-local overlay")
        orderer = _orderer(
            adapter,
            candidate,
            persistent_rows,
            model,
            maximum_abstract_depth=maximum_abstract_depth,
        )
        episode = run_receipted_preloaded_certificate_episode_v103(
            adapter,
            candidate,
            persistent_rows,
            preloaded_acquisition_ground_support_labels=_group_count(
                persistent_rows
            ),
            arm="OBSERVATION_DERIVED_QUOTIENT_GRAPH_ORDERING",
            abstract_orderer=orderer,
            episode_index=episode_index,
            maximum_execution_steps=maximum_execution_steps,
            maximum_incremental_certificate_ground_support_labels=(
                maximum_incremental_certificate_ground_support_labels
            ),
        )
        actual = _actual_receipts(episode)
        incremental = episode[
            "incremental_certificate_local_ground_support_labels"
        ]
        paid_certificate_labels += incremental
        new_rows = tuple(
            _row(document) for document in episode["raw_incremental_transition_rows"]
        )
        persistent_rows = _deduplicate((*persistent_rows, *new_rows))
        episodes.append(
            {
                **copy.deepcopy(episode),
                "quotient_graph_before_episode": copy.deepcopy(model),
                "actual_quotient_execution_receipts": actual,
                "actual_quotient_execution_receipt_count": len(actual),
                "quotient_proposal_admitted_execution_count": sum(
                    row["quotient_proposal_admitted_to_real_action_order"]
                    for row in actual
                ),
                "chosen_action_matches_admitted_quotient_proposal_count": sum(
                    row["chosen_action_matches_admitted_quotient_proposal"]
                    for row in actual
                ),
                "new_certificate_labels_charged_this_episode": incremental,
                "paid_certificate_labels_cumulative": paid_certificate_labels,
                "persistent_exact_support_group_count_after_episode": _group_count(
                    persistent_rows
                ),
            }
        )
        models.append(copy.deepcopy(model))
        receipts.extend(actual)
        previous_model_id = model["quotient_graph_id"]
        previous_incremental = incremental
    steps = sum(row["execution_steps"] for row in episodes)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
    )
    failures = [
        item for episode in episodes for item in episode["failed_certificates"]
    ]
    distinctions = [
        item for episode in episodes for item in episode["local_distinctions"]
    ]
    overlay = [row.to_document() for row in persistent_rows]
    payload = {
        "schema": "acfqp.generic_persistent_quotient_sequence.v105",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "initial_acquisition_ground_support_labels_paid_once": (
            acquisition_ground_support_labels
        ),
        "quotient_models_before_each_episode": models,
        "episodes": episodes,
        "all_actual_quotient_execution_receipts": receipts,
        "actual_quotient_execution_receipt_count": len(receipts),
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "quotient_proposal_admitted_strict_majority": 2 * admitted > steps,
        "chosen_action_matches_admitted_quotient_proposal_strict_majority": (
            2 * matches > steps
        ),
        "certificate_ground_support_labels_paid_once": paid_certificate_labels,
        "lifetime_target_ground_support_labels": (
            acquisition_ground_support_labels + paid_certificate_labels
        ),
        "persistent_exact_overlay_rows": overlay,
        "persistent_exact_overlay_sha256": hashlib.sha256(
            canonical_json_bytes(overlay)
        ).hexdigest(),
        "persistent_exact_support_group_count": _group_count(persistent_rows),
        "all_failed_certificates": failures,
        "all_local_distinctions": distinctions,
        "every_new_ground_query_followed_a_failed_certificate": all(
            row.get("ground_query_performed_before_failure") is False
            for row in failures
        )
        and all(
            row.get("query_after_failed_certificate") is True
            for row in distinctions
        ),
        "quotient_graph_updates_only_from_certificate_local_overlay": True,
        "actual_engine_action_order_receipts_not_posthoc_policy_matches": True,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": hashlib.sha256(
            _SEQUENCE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("run_persistent_quotient_sequence_v105",)
