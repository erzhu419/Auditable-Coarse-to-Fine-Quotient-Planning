"""Producer-free reconstruction of the fair V129r1 sample-tax campaign."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_generic_quotient_compiler_independent_verifier_v123r1 as generic
from acfqp import construction_k7_standalone_generic_model_independent_verifier_v125 as model
from acfqp import construction_k7_third_family_owned_sequence_independent_verifier_v128 as predecessor
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_dual_budget_adapter_v119 import (
    FAMILY as DUAL,
    build_dual_budget_adapter_v119,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY as INVENTORY,
    build_inventory_assembly_adapter_v118,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.unified_factor_prior_ablation_acquisition_v129 import (
    exact_generic_artifact_factor_replay_v121,
    synthesize_unified_factor_candidate_v129,
    unified_factor_prior_stop_update_v129,
)


CAMPAIGN_ID = "f99bb57dd7d6210c8ee55193a603c8e7195690457df4de9a952fa59c71cda447"
CAMPAIGN_BYTE_COUNT = 13_247_464
CAMPAIGN_SHA256 = "2196206b7533f885b301ae5f8f68c58222dc34a2ad80691d3079d5214dcfe24c"
PREREGISTRATION_ID = "d1565e2058f8640d5d3645205fd789517155928d74531a489d9efd1a419b03ae"
FAILED_V129_PREREGISTRATION_ID = "2057f4bc9b8ba3ad78ef56a63cc7fcdb814b36ce55be51e4e036086d5112bf9c"
FAILED_V129_BYTE_COUNT = 1_674
FAILED_V129_SHA256 = "a778be8fd64f5d77544e1dd8c97593c02f788ab074d62a79500d9336e431c94b"
V128_CAMPAIGN_ID = predecessor.CAMPAIGN_ID
V128_VERIFICATION_ID = predecessor.VERIFICATION_ID
EXPECTED_OCCURRENCES = (
    (INVENTORY, 1_045_101),
    (INVENTORY, 1_045_102),
    (DUAL, 1_045_103),
    (DUAL, 1_045_104),
    (MODULAR, 1_045_105),
    (MODULAR, 1_045_106),
)
EXPECTED_EPISODES = (329, 330, 331)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


_DOMAINS = {
    "campaign": "acfqp:construction-k7-fair-unified-factor-prior-ablation-campaign:v129r1",
    "occurrence": "acfqp:construction-k7-fair-unified-factor-prior-ablation-occurrence:v129r1",
    "acquisition": "acfqp:construction-k7-fair-unified-factor-prior-ablation-acquisition-arm:v129r1",
    "sequence": "acfqp:construction-k7-standalone-generic-owned-sequence:v126",
    "verification": "acfqp:construction-k7-fair-unified-factor-prior-ablation-verification:v129r1",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
    "ood": "acfqp:incompatible-schema-no-transfer-control:v99",
}
_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
}
_PREDECESSOR_NAMES = (
    "v128_campaign",
    "v128_verification",
    "v127_campaign",
    "v127_verification",
    "v126_campaign",
    "v126_verification",
    "v125_campaign",
    "v125_verification",
    "v124_campaign",
    "v124_verification",
    "v123r1_campaign",
    "v123r1_verification",
    "v122_campaign",
    "v122_verification",
    "failed_v123",
    "v121r1_campaign",
    "v121_failed_campaign",
    "v121r1_verification",
    "failed_v129",
)


class ConstructionK7FairUnifiedFactorPriorAblationIndependentVerifierV129R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FairUnifiedFactorPriorAblationIndependentVerifierV129R1Error(
        message
    )


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V129r1 {key} changed")


def _config() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    for family in _BUILDERS:
        config["families"][family]["maximum_acquisition_labels"] = 320
    return config


def _transition_batch(
    adapter: Any, state: Any, key: int, index: int
) -> tuple[FlatRawTransitionV4, ...]:
    legal = adapter.actions(state)
    action = adapter.action(key)
    _require(action in legal, "V129r1 verifier observed an illegal acquisition action")
    rows = []
    for offset, outcome in enumerate(adapter.kernel.step(state, action)):
        successor = outcome.next_state
        legal_after = adapter.actions(successor)
        rows.append(
            FlatRawTransitionV4(
                0,
                index + offset,
                adapter.encode(state),
                tuple(adapter.action_key(row) for row in legal),
                adapter.catalogue[key],
                adapter.encode(successor),
                tuple(adapter.action_key(row) for row in legal_after),
                None if legal_after else adapter.success(successor),
            )
        )
    return tuple(rows)


def _path_first_batches(adapter: Any) -> Iterator[tuple[FlatRawTransitionV4, ...]]:
    seen: set[Any] = set()
    transition_index = 0

    def visit(state: Any) -> Iterator[tuple[FlatRawTransitionV4, ...]]:
        nonlocal transition_index
        if state in seen:
            return
        seen.add(state)
        for action in adapter.actions(state):
            key = adapter.action_key(action)
            batch = _transition_batch(adapter, state, key, transition_index)
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


def _rebuild_acquisition(
    recorded: Mapping[str, Any],
    adapter: Any,
    projection: Mapping[str, Any],
    batches: tuple[tuple[FlatRawTransitionV4, ...], ...],
    *,
    enabled: bool,
    config: Mapping[str, Any],
) -> tuple[Any, tuple[FlatRawTransitionV4, ...]]:
    target = recorded["ground_support_labels"]
    _require(
        type(target) is int and 0 < target <= len(batches),
        "V129r1 acquisition label count changed",
    )
    candidate = None
    issued = invalidated = disagreements = epoch = successes = 0
    previous = None
    history = []
    derivation_compute = selected_artifact = 0
    rows: list[FlatRawTransitionV4] = []
    accepting_label = None
    terminal_stop = None
    for labels, batch in enumerate(batches[:target], 1):
        rows.extend(batch)
        current = tuple(rows)
        if accepting_label is None and any(
            row.terminal_acceptance_after is True for row in batch
        ):
            accepting_label = labels
        if candidate is not None:
            replay = exact_generic_artifact_factor_replay_v121(
                candidate, current, adapter.catalogue
            )
            if replay["exact"] is True:
                successes += 1
            else:
                previous = candidate.public_document["candidate_id"]
                candidate = None
                invalidated += 1
                epoch += 1
                successes = 0
        if candidate is None:
            try:
                candidate, compute = synthesize_unified_factor_candidate_v129(
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
                issued = labels
                derivation_compute += compute[
                    "generic_atomic_expression_evaluations"
                ]
                selected_artifact = compute["artifact_expression_selected_count"]
                if (
                    previous is not None
                    and candidate.public_document["candidate_id"] != previous
                ):
                    disagreements += 1
            except Exception as error:  # independent reconstruction of a recorded miss
                history.append(
                    {
                        "support_label_count": labels,
                        "candidate_available": False,
                        "constructor_error_type": type(error).__name__,
                    }
                )
                continue
        stop = unified_factor_prior_stop_update_v129(
            candidate,
            current,
            adapter.catalogue,
            projection,
            factor_prior_enabled=enabled,
            candidate_epoch=epoch,
            invalidated_candidate_count=invalidated,
            post_issuance_exact_prediction_success_count=successes,
            global_alpha_denominator=config["global_alpha_denominator"],
        )
        history.append(
            {
                "support_label_count": labels,
                "candidate_available": True,
                "candidate_id": candidate.public_document["candidate_id"],
                "stopped_by_shared_rule": stop["stopped"],
                "accepting_projection_available": accepting_label is not None,
            }
        )
        if labels == target:
            terminal_stop = stop
    _require(
        candidate is not None
        and terminal_stop is not None
        and terminal_stop["stopped"] is True
        and accepting_label is not None,
        (
            "V129r1 recorded acquisition did not independently stop: "
            f"{adapter.family} seed={adapter.seed} enabled={enabled} target={target} "
            f"accepting={accepting_label} stopped="
            f"{None if terminal_stop is None else terminal_stop['stopped']}"
        ),
    )
    raw_rows = tuple(rows)
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
        "ground_support_labels": target,
        "raw_transition_count": len(raw_rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in raw_rows])
        ).hexdigest(),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "first_accepting_observation_label": accepting_label,
        "terminal_stop_update": dict(terminal_stop),
        "stopping_history": history,
        "derivation_compute_events": derivation_compute,
        "artifact_expression_selected_count": selected_artifact,
        "sample_labels_and_derivation_compute_separate": True,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    rebuilt = {
        **payload,
        "acquisition_id": _content_id(_DOMAINS["acquisition"], payload),
    }
    _require(rebuilt == recorded, "V129r1 acquisition reconstruction changed")
    return candidate, raw_rows


def _verify_sequence(
    sequence: Mapping[str, Any],
    candidate: Mapping[str, Any],
    acquisition_rows: tuple[FlatRawTransitionV4, ...],
    *,
    family: str,
    seed: int,
) -> dict[str, int]:
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    _require(
        sequence["schema"] == "acfqp.standalone_generic_owned_sequence.v126"
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and sequence["family"] == family
        and sequence["seed"] == seed
        and tuple(sequence["episode_indices"]) == EXPECTED_EPISODES,
        "V129r1 sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"]
        == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate["candidate_id"]
        and dependency["compiled_factor_assignments"]
        == candidate["compiled_factor_assignments"],
        "V129r1 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    persistent = sequence["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == sequence["persistent_exact_overlay_sha256"],
        "V129r1 persistent evidence hash changed",
    )
    acquisition_documents = [row.to_document() for row in acquisition_rows]
    acquisition_unique = {
        model._raw_key(raw): raw for raw in acquisition_documents  # noqa: SLF001
    }
    initial_documents = tuple(
        acquisition_unique[key] for key in sorted(acquisition_unique)
    )
    current = {
        model._raw_key(raw): raw  # noqa: SLF001
        for raw in initial_documents
    }
    initial_rows = tuple(current.values())
    facts = model._project(initial_rows, candidate, actions)  # noqa: SLF001
    _require(
        facts["model"] == sequence["quotient_models_before_each_episode"][0]
        and model._bootstrap_receipt(initial_rows, facts)  # noqa: SLF001
        == sequence["bootstrap_receipt"]
        and model._match_receipt(facts, initial_rows, None)  # noqa: SLF001
        == sequence["bootstrap_full_rebuild_match"],
        "V129r1 bootstrap reconstruction changed",
    )
    updates = sequence["standalone_model_update_receipts"]
    matches = sequence["standalone_full_rebuild_match_receipts"]
    _require(
        len(sequence["episodes"])
        == len(updates)
        == len(matches)
        == len(EXPECTED_EPISODES),
        "V129r1 episode/receipt cardinality changed",
    )
    rebuilt_models = []
    path_checks = direct = reused = 0
    all_plans = []
    for index, episode in enumerate(sequence["episodes"]):
        before = model._project(tuple(current.values()), candidate, actions)  # noqa: SLF001
        _require(
            before["model"] == sequence["quotient_models_before_each_episode"][index]
            and episode["quotient_graph_before_episode"] == before["model"]
            and episode["standalone_model_state_id_before_episode"]
            == before["state_id"]
            and updates[index]["previous_successor_state_id"] == before["state_id"],
            "V129r1 before-model reconstruction changed",
        )
        rebuilt_models.append(before["model"])
        for wrapper in episode["abstract_plan_receipts"]:
            plan = wrapper["abstract_plan"]
            all_plans.append(plan)
            source = plan["planning_source"]
            if source in {
                "OBSERVATION_QUOTIENT_GRAPH",
                "COMPILED_FACTOR_PROGRAM_FALLBACK",
            }:
                _verify_id(
                    plan, "legality_conditioned_quotient_plan_id", _DOMAINS["plan"]
                )
                _require(
                    tuple(
                        plan["embedded_projected_plan"]["terminal_projection_rule"]
                    )
                    == before["rules"],
                    "V129r1 terminal projection rule changed",
                )
                path_checks += generic._verify_plan(  # noqa: SLF001
                    plan,
                    wrapper["raw_state"],
                    candidate,
                    actions,
                    before["model"],
                    before["rules"],
                )
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["generic_factor_program_execution_adapter_used"] is True
                        and plan[
                            "legacy_shape_specific_planner_execution_adapter_called"
                        ]
                        is False,
                        "V129r1 direct generic plan changed",
                    )
            elif source in {
                "COMPILED_FACTOR_PROGRAM_MEMOIZED",
                "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
            }:
                reused += 1
                if source == "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER":
                    _require(
                        plan["cached_ordering_used_as_safety_authority"] is False
                        and plan["dependency_revalidation"][
                            "current_quotient_graph_id"
                        ]
                        == before["model"]["quotient_graph_id"],
                        "V129r1 dependency reuse changed",
                    )
            else:
                _fail("V129r1 unknown planning source")
        delta_rows = tuple(episode["raw_incremental_transition_rows"])
        novel_rows = tuple(
            raw for raw in delta_rows if model._raw_key(raw) not in current  # noqa: SLF001
        )
        novel = (
            model._project(novel_rows, candidate, actions)  # noqa: SLF001
            if novel_rows
            else {"raw_keys": frozenset(), "checks": 0}
        )
        for raw in delta_rows:
            current[model._raw_key(raw)] = raw  # noqa: SLF001
        after = model._project(tuple(current.values()), candidate, actions)  # noqa: SLF001
        expected_update = model._update_receipt(  # noqa: SLF001
            before, after, delta_rows, novel
        )
        expected_match = model._match_receipt(  # noqa: SLF001
            after, tuple(current.values()), expected_update
        )
        _require(
            expected_update == updates[index]
            and expected_match == matches[index]
            and episode["standalone_model_update_after_episode"] == expected_update
            and episode["standalone_full_rebuild_match_after_episode"]
            == expected_match
            and episode["quotient_graph_after_episode"] == after["model"]
            and episode["standalone_model_state_id_after_episode"]
            == after["state_id"]
            and after["model"] == sequence["quotient_models_after_each_episode"][index],
            "V129r1 update/full-match reconstruction changed",
        )
        rebuilt_models.append(after["model"])
        _require(
            episode["success"] is True
            and episode[
                "all_incremental_ground_queries_followed_failed_certificates"
            ]
            is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V129r1 certificate discipline changed",
        )
    _require(
        [current[key] for key in sorted(current)] == list(persistent),
        "V129r1 persistent inventory changed",
    )
    actual_compute = sum(
        episode["abstract_planning_compute_events"] for episode in sequence["episodes"]
    )
    uncached_compute = sum(
        plan.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            plan["abstract_support_branch_evaluations"],
        )
        for plan in all_plans
    )
    dependency_compute = len(EXPECTED_EPISODES) * (
        len(dependency["compiled_factor_assignments"])
        + len(dependency["canonical_action_catalogue"])
    )
    _require(
        sequence["dependency_receipt_rederivation_count"] == len(EXPECTED_EPISODES)
        and sequence["dependency_derivation_compute_events"] == dependency_compute
        and sequence["actual_new_abstract_planning_compute_events"] == actual_compute
        and sequence["matched_uncached_abstract_planning_compute_events"]
        == uncached_compute
        and sequence["planning_compute_events_avoided_against_uncached"]
        == uncached_compute - actual_compute
        and sequence["direct_generic_factor_program_plan_count"] == direct
        and sequence["owned_episode_loop_implementation_present"] is True
        and sequence["standalone_v125_state_carrier_verified"] is True
        and sequence["retained_v113_state_carrier_present"] is False
        and sequence["retained_v113_sequence_orchestration_present"] is False
        and sequence["retained_v119_sequence_orchestration_present"] is False
        and sequence[
            "compiled_model_cache_or_receipt_used_as_safety_authority"
        ]
        is False,
        "V129r1 sequence accounting/claim boundary changed",
    )
    return {
        "model_epoch_count": len(rebuilt_models),
        "receipt_count": 2 + 2 * len(sequence["episodes"]),
        "plan_path_support_checks": path_checks,
        "reused_plan_count": reused,
        "direct_plan_count": direct,
    }


def _verify_occurrence(
    row: Mapping[str, Any],
    projection: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    family = row["target_family"]
    seed = row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row["schema"]
        == "acfqp.fair_unified_factor_prior_ablation_occurrence.v129r1"
        and tuple(row["episode_indices"]) == EXPECTED_EPISODES,
        "V129r1 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    config = _config()
    adapter = _BUILDERS[family](seed, config)
    strict_labels = row["strict_no_prior_acquisition"]["ground_support_labels"]
    stream = _path_first_batches(adapter)
    batches = tuple(next(stream) for _ in range(strict_labels))
    prior_candidate, prior_rows = _rebuild_acquisition(
        row["factor_prior_acquisition"],
        adapter,
        projection,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = _rebuild_acquisition(
        row["strict_no_prior_acquisition"],
        adapter,
        projection,
        batches,
        enabled=False,
        config=config,
    )
    prior_sequence = _verify_sequence(
        row["factor_prior_owned_sequence"],
        prior_candidate.public_document,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence = _verify_sequence(
        row["strict_no_prior_owned_sequence"],
        strict_candidate.public_document,
        strict_rows,
        family=family,
        seed=seed,
    )
    prior_doc = row["factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "factor_prior_ground_support_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_factor_prior": reduction,
        "factor_prior_label_ratio_numerator": prior_doc["ground_support_labels"],
        "factor_prior_label_ratio_denominator": strict_doc["ground_support_labels"],
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_rows
        == strict_rows[: len(prior_rows)],
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_registered_factor_prior": True,
        "sample_labels_and_derivation_compute_separate": True,
    }
    _require(row["sample_tax_comparison"] == sample_tax, "V129r1 sample tax changed")
    prior_owned = row["factor_prior_owned_sequence"]
    strict_owned = row["strict_no_prior_owned_sequence"]
    accounting = {
        "factor_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_factor_prior": reduction,
        "factor_prior_certificate_local_labels": prior_owned[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_owned[
            "certificate_ground_support_labels_paid_once"
        ],
        "factor_prior_lifetime_target_labels": prior_owned[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_owned[
            "lifetime_target_ground_support_labels"
        ],
        "factor_prior_execution_steps": prior_owned["execution_step_count"],
        "strict_no_prior_execution_steps": strict_owned["execution_step_count"],
        "factor_prior_derivation_compute_events": prior_doc["derivation_compute_events"],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "factor_prior_planning_compute_events": prior_owned[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_owned[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "factor_prior_stops_before_strict_no_prior": reduction > 0,
        "same_raw_transition_prefix_through_common_label": True,
        "same_synthesizer_representation_and_stop_rule": True,
        "only_arm_switch_is_registered_factor_prior": True,
        "both_arm_receding_episodes_succeed": True,
        "both_arms_use_certificate_failure_only_local_ground_distinctions": True,
        "both_planners_consume_compiled_model_without_raw_rows": True,
        "retained_sequence_orchestration_absent": True,
        "passed": True,
    }
    _require(
        row["accounting"] == accounting
        and row["registered_gate"] == gate
        and row["registered_workload_sample_efficiency_improvement_observed"] is True
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["official_N_break_even"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V129r1 occurrence Gate/accounting changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "factor_prior_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "factor_prior_sequence": prior_sequence,
        "strict_no_prior_sequence": strict_sequence,
        "accounting": accounting,
    }


def freeze_fair_unified_factor_prior_ablation_verification_v129r1(
    campaign_raw: bytes,
    predecessor_artifacts: Mapping[str, bytes],
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    _require(
        tuple(sorted(predecessor_artifacts)) == tuple(sorted(_PREDECESSOR_NAMES)),
        "V129r1 predecessor inventory changed",
    )
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V129r1 frozen campaign identity/bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    p = predecessor_artifacts
    expected_v128_verification = predecessor.freeze_third_family_owned_sequence_verification_v128(
        p["v128_campaign"],
        p["v127_campaign"],
        p["v127_verification"],
        p["v126_campaign"],
        p["v126_verification"],
        p["v125_campaign"],
        p["v125_verification"],
        p["v124_campaign"],
        p["v124_verification"],
        p["v123r1_campaign"],
        p["v123r1_verification"],
        p["v122_campaign"],
        p["v122_verification"],
        p["failed_v123"],
        p["v121r1_campaign"],
        p["v121_failed_campaign"],
        p["v121r1_verification"],
        dict(source_campaign_bytes),
    )
    _require(
        expected_v128_verification == p["v128_verification"],
        "V129r1 producer-free V128 predecessor changed",
    )
    failed_raw = p["failed_v129"]
    failure = json.loads(failed_raw)
    _require(
        len(failed_raw) == FAILED_V129_BYTE_COUNT
        and hashlib.sha256(failed_raw).hexdigest() == FAILED_V129_SHA256
        and canonical_json_bytes(failure) == failed_raw.rstrip(b"\n")
        and failure["preregistration_id"] == FAILED_V129_PREREGISTRATION_ID
        and failure["same_identity_rerun_forbidden"] is True
        and failure["complete_campaign_document_emitted"] is False,
        "V129r1 retained V129 failure changed",
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v128_success_campaign_id"] == V128_CAMPAIGN_ID
        and campaign["v128_success_verification_id"] == V128_VERIFICATION_ID
        and campaign["retained_failed_v129_preregistration_id"]
        == FAILED_V129_PREREGISTRATION_ID
        and campaign["retained_failed_v129_artifact_sha256"] == FAILED_V129_SHA256
        and campaign["failed_v129_identity_rerun"] is False,
        "V129r1 predecessor joins changed",
    )
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    _require(
        campaign["artifact_factor_library_id"] == library["factor_library_id"],
        "V129r1 factor library changed",
    )
    projection = library["v15_partial_synthesizer_projection"]
    rows = tuple(
        _verify_occurrence(row, projection, source_campaign_bytes)
        for row in campaign["target_occurrences"]
    )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V129r1 target occurrence identities changed",
    )
    ood = campaign["incompatible_schema_no_transfer_control"]
    _require(
        ood["control_id"]
        == _content_id(
            _DOMAINS["ood"],
            {key: value for key, value in ood.items() if key != "control_id"},
        )
        and ood["strict_ood_no_transfer"] is True
        and ood["learned_structure_prior_delivered"] is False
        and ood["target_outcomes_accessed"] is False,
        "V129r1 strict OOD control changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    gate = {
        "required_target_occurrence_count": 6,
        "passed_target_occurrence_count": 6,
        "every_occurrence_has_strictly_positive_label_reduction": True,
        "same_synthesizer_representation_and_stop_rule_in_every_occurrence": True,
        "both_arm_receding_episodes_succeed_everywhere": True,
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": True,
    }
    _require(
        campaign["accounting"] == accounting
        and campaign["registered_gate"] == gate
        and campaign[
            "registered_workload_sample_efficiency_improvement_observed"
        ]
        is True
        and campaign["sample_efficiency_improvement_claim_scope"]
        == "ONLY_THE_PREREGISTERED_V129R1_THREE_FAMILY_WORKLOAD"
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V129r1 campaign Gate/accounting changed",
    )
    payload = {
        "schema": "acfqp.fair_unified_factor_prior_ablation_verification.v129r1",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v128_predecessor_verification_id": V128_VERIFICATION_ID,
        "retained_failed_v129_preregistration_id": FAILED_V129_PREREGISTRATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_fair_path_first_batch_reconstruction": True,
        "producer_free_per_label_candidate_and_stop_reconstruction": True,
        "producer_free_raw_transition_model_epoch_reconstruction": True,
        "producer_free_receipt_and_plan_reconstruction": True,
        "same_synthesizer_representation_and_stop_rule_independently_verified": True,
        "registered_workload_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V129R1_THREE_FAMILY_WORKLOAD"
        ),
        "arbitrary_unseen_domain_transfer_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": _content_id(_DOMAINS["verification"], payload),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V129r1 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_fair_unified_factor_prior_ablation_verification_v129r1",
)
