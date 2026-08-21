"""V129r1: fair path-first backtracking with the unchanged V129 synthesizer."""

from __future__ import annotations

from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v129r1 as domains
from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp.generic_artifact_derived_factor_projection_v120 import verify_artifact_factor_projection_v120
from acfqp.unified_factor_prior_ablation_acquisition_v129 import (
    exact_generic_artifact_factor_replay_v121,
    synthesize_unified_factor_candidate_v129,
    unified_factor_prior_stop_update_v129,
)


class FairUnifiedFactorPriorAblationAcquisitionV129R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise FairUnifiedFactorPriorAblationAcquisitionV129R1Error(message)


def fair_witness_blind_path_first_stream_v129r1(adapter: Any) -> Iterator[tuple[Any, ...]]:
    """Explore one observed path before siblings, then backtrack exhaustively."""

    seen = set()
    transition_index = 0

    def visit(state: Any) -> Iterator[tuple[Any, ...]]:
        nonlocal transition_index
        if state in seen:
            return
        seen.add(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            batch = ground._transition_batch(adapter, state, key, transition_index)  # noqa: SLF001
            transition_index += len(batch)
            successors = tuple(
                outcome.next_state
                for outcome in adapter.kernel.step(state, action)
                if adapter.active(outcome.next_state)
            )
            yield batch
            for successor in successors:
                yield from visit(successor)

    yield from visit(adapter.initial())


def acquire_matched_fair_unified_factor_arms_v129r1(
    adapter: Any,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    verified = verify_artifact_factor_projection_v120(
        artifact_factor_library, source_campaign_bytes
    )
    projection = artifact_factor_library.get("v15_partial_synthesizer_projection")
    if verified["derived_subprogram_count"] != 3 or type(projection) is not dict:
        _fail("V129r1 artifact projection changed")
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
    for labels, batch in enumerate(fair_witness_blind_path_first_stream_v129r1(adapter), 1):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        if accepting_label is None and any(row.terminal_acceptance_after is True for row in batch):
            accepting_label = labels
        for enabled in (True, False):
            if enabled in results:
                continue
            state = states[enabled]
            candidate = state["candidate"]
            if candidate is not None:
                replay = exact_generic_artifact_factor_replay_v121(candidate, current, adapter.catalogue)
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
                    candidate, compute = synthesize_unified_factor_candidate_v129(
                        current,
                        adapter.catalogue,
                        projection,
                        support_label_count=labels,
                        factor_prior_enabled=enabled,
                        layout_domain=config["generic_domains"]["layout"],
                        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
                    )
                    state["candidate"] = candidate
                    state["issued"] = labels
                    state["derivation_compute"] += compute["generic_atomic_expression_evaluations"]
                    state["selected_artifact"] = compute["artifact_expression_selected_count"]
                    if state["previous"] is not None and candidate.public_document["candidate_id"] != state["previous"]:
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
            stop = unified_factor_prior_stop_update_v129(
                candidate,
                current,
                adapter.catalogue,
                projection,
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
                "schema": "acfqp.fair_unified_factor_acquisition_arm.v129r1",
                "family": adapter.family,
                "seed": adapter.seed,
                "arm": "FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR",
                "factor_prior_enabled": enabled,
                "fair_witness_blind_path_first_backtracking": True,
                "generation_witness_accessed": False,
                "reachable_frontier_exhaustion_used_as_stopping_input": False,
                "only_arm_switch_is_registered_factor_prior": True,
                "same_generic_atomic_hypothesis_pool": True,
                "same_candidate_carrier_and_schema": True,
                "same_candidate_replay_function": True,
                "same_stopping_rule_function": True,
                "ground_support_labels": labels,
                "raw_transition_count": len(prefix),
                "raw_transition_sha256": ground._raw_sha(prefix),  # noqa: SLF001
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
            document = {
                **payload,
                "acquisition_id": domains.extension_content_id_v129r1(
                    domains.CONSTRUCTION_K7_FAIR_UNIFIED_FACTOR_ACQUISITION_ARM_V129R1_DOMAIN,
                    payload,
                ),
            }
            results[enabled] = {
                "document": document,
                "candidate": candidate,
                "rows": prefix,
                "batches": tuple(batches[:labels]),
            }
        if len(results) == 2:
            prior, strict = results[True], results[False]
            common = min(len(prior["batches"]), len(strict["batches"]))
            if tuple(row for batch in prior["batches"][:common] for row in batch) != tuple(
                row for batch in strict["batches"][:common] for row in batch
            ):
                _fail("V129r1 matched arms diverged before their common stop")
            return {"FACTOR_PRIOR_ON": prior, "STRICT_NO_PRIOR": strict}
    _fail(f"V129r1 fair unified acquisition did not close before cap for {adapter.family} seed {adapter.seed}")


__all__ = (
    "acquire_matched_fair_unified_factor_arms_v129r1",
    "fair_witness_blind_path_first_stream_v129r1",
)
