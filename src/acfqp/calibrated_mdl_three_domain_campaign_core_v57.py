"""V57 three-domain campaign with calibrated predictive stopping."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import random
from typing import Any, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as base
from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v57 as domains_v57
from acfqp.domains.stochastic_maintenance_cascade import (
    MaintenanceCascadeAction,
    MaintenanceCascadeState,
    MaintenanceCascadeStatus,
    generate_stochastic_maintenance_cascade,
    select_seeded_maintenance_cascade_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_calibrated_mdl_joint_synthesizer_v12 import (
    calibrated_mdl_predictive_stop_update_v12,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    exact_candidate_replay_v11,
)


class CalibratedMDLThreeDomainCampaignCoreV57Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CalibratedMDLThreeDomainCampaignCoreV57Error(message)


@dataclass(frozen=True, slots=True)
class _MaintenanceAdapter:
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    encode: Any

    def initial(self) -> Any:
        return self.kernel.initial_distribution()[0][1]

    def actions(self, state: Any) -> tuple[Any, ...]:
        return tuple(self.kernel.actions(state))

    def action_key(self, action: Any) -> int:
        return action.task

    def action(self, key: int) -> Any:
        return MaintenanceCascadeAction(key)

    def active(self, state: Any) -> bool:
        return state.status is MaintenanceCascadeStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is MaintenanceCascadeStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        return MaintenanceCascadeState(
            rule.source_zone,
            0,
            0,
            0,
            0,
            rule.source_zone,
            MaintenanceCascadeStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_maintenance_cascade_outcome_v1(
            self.kernel.step(state, MaintenanceCascadeAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def _maintenance_interface(seed: int, kernel: Any, tokens: Mapping[str, int]):
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x57E61).shuffle(state_order)
    random.Random(seed ^ 0x57F73).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + rule.source_zone,
                    seed * 100 + rule.destination_zone,
                    rule.repair_increment,
                    rule.spare_increment,
                    rule.hazard_increment,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: MaintenanceCascadeState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is MaintenanceCascadeStatus.ACTIVE
            else "S"
            if state.status is MaintenanceCascadeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.zone,
            state.repaired_units,
            state.spare_units,
            state.latent_load,
            state.hazard,
            state.elapsed,
            status,
            kernel.hazard_capacity,
            kernel.repair_target,
            seed * 100 + kernel.goal_zone,
        )
        return tuple(semantic[index] for index in state_order)

    return catalogue, encode


def _adapter(family: str, seed: int, config: Mapping[str, Any]):
    if family != "MAINTENANCE_CASCADE":
        return base._adapter(family, seed, config)
    spec = config["families"][family]
    kernel, witness = generate_stochastic_maintenance_cascade(
        zone_count=spec["zone_count"],
        repair_base=spec["repair_base"],
        seed=seed,
    )
    catalogue, encode = _maintenance_interface(
        seed, kernel, config["terminal_tokens"]
    )
    del witness
    return _MaintenanceAdapter(family, seed, kernel, catalogue, encode)


def _acquisition_document(
    *,
    adapter: Any,
    arm: str,
    prior: bool,
    labels: int,
    rows: tuple[Any, ...],
    candidate: MDLAdaptiveJointCandidateV11,
    issued_at: int,
    invalidated: int,
    disagreements: int,
    candidate_epoch: int,
    predictive_successes: int,
    history: list[dict[str, Any]],
    stop: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.calibrated_mdl_acquisition.v57",
        "v56r1_campaign_id": config["v56r1_campaign_id"],
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "factor_prior_enabled": prior,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": base._raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_epoch": candidate_epoch,
        "post_issuance_exact_prediction_success_count": predictive_successes,
        "stopping_history": history,
        "terminal_stop_update": dict(stop),
        "stopped_by_calibrated_mdl_predictive_rule": stop["stopped"],
        "candidate_synthesis_attempted_after_every_support_query": True,
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "fixed_confidence_reserve_consumed": False,
        "reachable_frontier_exhaustion_input_consumed": False,
        "witness_blind_depth_frontier_policy": True,
        "generation_witness_accessed": False,
        "full_frontier_calibration_consumed": False,
        "same_synthesizer_query_order_mdl_and_confidence_rule": True,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }
    return {
        **payload,
        "acquisition_id": domains_v57.extension_content_id_v57(
            config["successor_domains"]["acquisition"], payload
        ),
    }


def _acquire_matched(
    adapter: Any,
    factor_library: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    candidate: MDLAdaptiveJointCandidateV11 | None = None
    issued_at = 0
    invalidated = 0
    disagreements = 0
    candidate_epoch = 0
    predictive_successes = 0
    previous_fingerprint = None
    pending = {
        "ANONYMOUS_FACTOR_PRIOR_ON": True,
        "STRICT_NO_PRIOR": False,
    }
    histories = {arm: [] for arm in pending}
    results: dict[str, dict[str, Any]] = {}
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    for labels, batch in enumerate(base._witness_blind_depth_frontier(adapter), 1):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        reason = "NO_COMPLETE_CANDIDATE_YET"
        replay = None
        if candidate is not None:
            replay = exact_candidate_replay_v11(
                candidate, tuple(rows), adapter.catalogue
            )
            if replay["exact"] is True:
                predictive_successes += 1
                reason = "PREISSUED_CANDIDATE_EXACTLY_PREDICTED_NEW_BATCH"
            else:
                invalidated += 1
                candidate_epoch += 1
                predictive_successes = 0
                previous_fingerprint = candidate.public_document[
                    "program_fingerprint_sha256"
                ]
                candidate = None
                reason = "NEW_BATCH_INVALIDATED_PREISSUED_CANDIDATE"
        if candidate is None:
            try:
                candidate = base._candidate(
                    tuple(rows), adapter.catalogue, factor_library, labels, config
                )
            except Exception:
                for arm in tuple(pending):
                    histories[arm].append(
                        {
                            "support_label_count": labels,
                            "raw_transition_sha256": base._raw_sha(tuple(rows)),
                            "update_reason": reason,
                            "candidate_available": False,
                        }
                    )
                continue
            issued_at = labels
            fingerprint = candidate.public_document[
                "program_fingerprint_sha256"
            ]
            if previous_fingerprint is not None and fingerprint != previous_fingerprint:
                disagreements += 1
            reason = (
                "FIRST_COMPLETE_CANDIDATE_SYNTHESIZED"
                if invalidated == 0
                else "COUNTEREVIDENCE_TRIGGERED_COMPLETE_RESYNTHESIS"
            )
        for arm, prior in tuple(pending.items()):
            stop = calibrated_mdl_predictive_stop_update_v12(
                candidate,
                tuple(rows),
                adapter.catalogue,
                factor_prior_enabled=prior,
                invalidated_candidate_count=invalidated,
                candidate_program_disagreement_count=disagreements,
                candidate_epoch=candidate_epoch,
                post_issuance_exact_prediction_success_count=predictive_successes,
                factor_signature_credit_units=config[
                    "factor_signature_credit_units"
                ],
                invalidated_candidate_penalty_units=config[
                    "invalidated_candidate_penalty_units"
                ],
                minimum_reusable_factor_count=config[
                    "minimum_reusable_factor_count"
                ],
                global_alpha_denominator=config["global_alpha_denominator"],
                epoch_alpha_spending_base=config["epoch_alpha_spending_base"],
                success_evalue_multiplier_numerator=config[
                    "success_evalue_multiplier_numerator"
                ],
                success_evalue_multiplier_denominator=config[
                    "success_evalue_multiplier_denominator"
                ],
                predictive_evidence_credit_units_per_bit=config[
                    "predictive_evidence_credit_units_per_bit"
                ],
            )
            histories[arm].append(
                {
                    "support_label_count": labels,
                    "raw_transition_sha256": base._raw_sha(tuple(rows)),
                    "update_reason": reason,
                    "candidate_available": True,
                    "candidate_id": candidate.public_document["candidate_id"],
                    "exact_replay": replay,
                    "stop_update": stop,
                }
            )
            if stop["stopped"] is not True:
                continue
            document = _acquisition_document(
                adapter=adapter,
                arm=arm,
                prior=prior,
                labels=labels,
                rows=tuple(rows),
                candidate=candidate,
                issued_at=issued_at,
                invalidated=invalidated,
                disagreements=disagreements,
                candidate_epoch=candidate_epoch,
                predictive_successes=predictive_successes,
                history=list(histories[arm]),
                stop=stop,
                config=config,
            )
            results[arm] = {
                "document": document,
                "candidate": candidate,
                "rows": tuple(rows),
                "batches": tuple(batches),
            }
            del pending[arm]
        if not pending:
            prior_result = results["ANONYMOUS_FACTOR_PRIOR_ON"]
            no_prior_result = results["STRICT_NO_PRIOR"]
            common = tuple(
                row
                for item in no_prior_result["batches"][
                    : len(prior_result["batches"])
                ]
                for row in item
            )
            if prior_result["rows"] != common:
                _fail("V57 matched raw acquisition prefix changed")
            return results
    _fail(
        "V57 calibrated stop did not close before the witness-blind stream or "
        f"registered cap for {adapter.family} seed {adapter.seed}; "
        f"pending={sorted(pending)}"
    )


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, episode_index, seed, factor_library, config = args
    adapter = _adapter(family, seed, config)
    acquisitions = _acquire_matched(adapter, factor_library, config)
    result = {
        "family": family,
        "seed": seed,
        "acquisitions": {
            arm: row["document"] for arm, row in acquisitions.items()
        },
        "episodes": {},
        "failures": [],
        "distinctions": [],
        "isolated_validation": None,
    }
    if episode_index < config["families"][family]["planning_seed_count"]:
        for arm, acquisition in acquisitions.items():
            episode, failures, distinctions = base._episode(
                adapter=adapter,
                arm=arm,
                episode_index=episode_index,
                acquisition=acquisition,
                factor_library=factor_library,
                config=config,
            )
            result["episodes"][arm] = episode
            result["failures"].extend(failures)
            result["distinctions"].extend(distinctions)
        result["episodes"]["STRICT_EXACT_CONTEXT"] = base._strict_episode(
            adapter, episode_index, config
        )
        abstract_actions = [
            result["episodes"][arm]["action_keys"]
            for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR")
        ]
        if abstract_actions[0] != abstract_actions[1]:
            _fail(f"V57 prior switch changed the abstract plan for {family} {seed}")
        if not all(row["success"] for row in result["episodes"].values()):
            _fail(f"V57 held-out planning failed for {family} seed {seed}")
        result["isolated_validation"] = base._isolated_validation(
            adapter, acquisitions, config
        )
    return result


def build_calibrated_mdl_three_domain_campaign_document_v57(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    if factor_library.get("factor_library_id") != config["factor_library_id"]:
        _fail("V57 factor-library identity changed")
    arguments = [
        (family, index, seed, factor_library, config)
        for family, spec in config["families"].items()
        for index, seed in enumerate(spec["target_seeds"])
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    acquisitions = {
        arm: [row["acquisitions"][arm] for row in occurrences]
        for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR")
    }
    episodes = {
        arm: [
            row["episodes"][arm]
            for row in occurrences
            if arm in row["episodes"]
        ]
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    }
    failures = [item for row in occurrences for item in row["failures"]]
    distinctions = [item for row in occurrences for item in row["distinctions"]]
    validations = [
        row["isolated_validation"]
        for row in occurrences
        if row["isolated_validation"] is not None
    ]
    prior_labels = sum(
        row["ground_support_labels"]
        for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    )
    no_prior_labels = sum(
        row["ground_support_labels"]
        for row in acquisitions["STRICT_NO_PRIOR"]
    )
    prior_local = sum(
        row["local_ground_support_labels"]
        for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]
    )
    no_prior_local = sum(
        row["local_ground_support_labels"]
        for row in episodes["STRICT_NO_PRIOR"]
    )
    family_rows = {}
    for family in config["families"]:
        prior_family = [
            row
            for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
            if row["family"] == family
        ]
        no_prior_family = [
            row
            for row in acquisitions["STRICT_NO_PRIOR"]
            if row["family"] == family
        ]
        family_rows[family] = {
            "occurrence_count": len(prior_family),
            "factor_prior_on_acquisition_labels": sum(
                row["ground_support_labels"] for row in prior_family
            ),
            "strict_no_prior_acquisition_labels": sum(
                row["ground_support_labels"] for row in no_prior_family
            ),
            "factor_prior_on_terminal_predictive_success_count_sum": sum(
                row["post_issuance_exact_prediction_success_count"]
                for row in prior_family
            ),
            "strict_no_prior_terminal_predictive_success_count_sum": sum(
                row["post_issuance_exact_prediction_success_count"]
                for row in no_prior_family
            ),
        }
        family_rows[family]["incremental_label_reduction"] = (
            family_rows[family]["strict_no_prior_acquisition_labels"]
            - family_rows[family]["factor_prior_on_acquisition_labels"]
        )
        if family_rows[family]["incremental_label_reduction"] <= 0:
            _fail(f"V57 factor prior did not reduce sample tax in {family}")
    prefix_curve = []
    prior_running = config["factor_library_labels"]
    no_prior_running = 0
    break_even = None
    for index, (prior, no_prior) in enumerate(
        zip(
            acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"],
            acquisitions["STRICT_NO_PRIOR"],
            strict=True,
        ),
        1,
    ):
        prior_running += prior["ground_support_labels"]
        no_prior_running += no_prior["ground_support_labels"]
        reduction = no_prior_running - prior_running
        prefix_curve.append(
            {
                "occurrence_count": index,
                "family": prior["family"],
                "factor_prior_on_lifetime_labels": prior_running,
                "strict_no_prior_lifetime_labels": no_prior_running,
                "net_label_reduction": reduction,
            }
        )
        if break_even is None and reduction > 0:
            break_even = index
    online = (no_prior_labels + no_prior_local) - (prior_labels + prior_local)
    lifetime = online - config["factor_library_labels"]
    if (
        no_prior_labels - prior_labels <= 0
        or online <= 0
        or lifetime <= 0
        or break_even is None
    ):
        _fail("V57 registered sample tax was not reduced")
    sample_payload = {
        "schema": "acfqp.calibrated_mdl_sample_tax.v57",
        "v56r1_campaign_id": config["v56r1_campaign_id"],
        "factor_library_labels_prior_on_only": config["factor_library_labels"],
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": no_prior_labels - prior_labels,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": lifetime,
        "diagnostic_break_even_occurrence_count": break_even,
        "family_projections": family_rows,
        "prefix_curve": prefix_curve,
        "same_synthesizer_query_order_mdl_and_calibrated_confidence_rule": True,
        "only_registered_factor_code_credit_switched": True,
        "fixed_minimum_label_floor_consumed": False,
        "fixed_confirmation_block_consumed": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": domains_v57.extension_content_id_v57(
            config["successor_domains"]["sample_tax"], sample_payload
        ),
    }
    ood_rows, ood_catalogue = base._ood_rows()
    ood_model = synthesize_joint_factor_residual_world_model_v9(
        {0: ood_rows},
        {0: ood_catalogue},
        factor_library,
        layout_domain=config["generic_domains"]["layout"],
        program_domain=config["generic_domains"]["program"],
        support_domain=config["generic_domains"]["support"],
        factor_domain=config["generic_domains"]["model"],
        result_domain=config["generic_domains"]["model"],
        minimum_reusable_factor_count=config["minimum_reusable_factor_count"],
    )
    if ood_model["transfer_admitted"] is not False:
        _fail("V57 incompatible OOD domain was admitted")
    ood_payload = {
        "schema": "acfqp.mdl_adaptive_ood_rejection.v56",
        "joint_model_id": ood_model["joint_model_id"],
        "factorable_reusable_count": ood_model["factorable_reusable_count"],
        "minimum_reusable_factor_count": config["minimum_reusable_factor_count"],
        "complete_ood_program_synthesized_from_raw_observations": True,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER",
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": domains_v56.extension_content_id_v56(
            config["domains"]["ood"], ood_payload
        ),
    }
    payload = {
        "schema": "acfqp.calibrated_mdl_three_domain_campaign.v57",
        "preregistration_id": preregistration_id,
        "v56r1_campaign_id": config["v56r1_campaign_id"],
        "v56r1_verification_id": config["v56r1_verification_id"],
        "factor_library_id": config["factor_library_id"],
        "families": list(config["families"]),
        "acquisitions": acquisitions,
        "episodes": episodes,
        "failed_certificates": failures,
        "local_distinctions": distinctions,
        "isolated_full_frontier_validations": validations,
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": {
            "offline_factor_library_labels": config["factor_library_labels"],
            "factor_prior_on_target_acquisition_labels": prior_labels,
            "strict_no_prior_target_acquisition_labels": no_prior_labels,
            "factor_prior_on_local_recovery_labels": prior_local,
            "strict_no_prior_local_recovery_labels": no_prior_local,
            "isolated_validation_labels": sum(
                row["full_frontier_ground_support_labels"] for row in validations
            ),
            "factor_prior_on_execution_steps": sum(
                row["execution_steps"]
                for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]
            ),
            "strict_no_prior_execution_steps": sum(
                row["execution_steps"] for row in episodes["STRICT_NO_PRIOR"]
            ),
            "direct_execution_steps": sum(
                row["execution_steps"] for row in episodes["STRICT_EXACT_CONTEXT"]
            ),
            "factor_prior_on_planning_compute_events": sum(
                row["planning_compute_events"]
                for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]
            ),
            "strict_no_prior_planning_compute_events": sum(
                row["planning_compute_events"]
                for row in episodes["STRICT_NO_PRIOR"]
            ),
            "direct_planning_compute_events": sum(
                row["planning_compute_events"]
                for row in episodes["STRICT_EXACT_CONTEXT"]
            ),
            "certificate_compute_events": len(failures),
            "all_axes_separate": True,
        },
        "candidate_synthesis_attempted_after_every_support_query": True,
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "fixed_confidence_reserve_consumed": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "full_frontier_target_layout_calibration_consumed": False,
        "same_synthesizer_used_in_all_three_families": True,
        "matched_direct_baseline_same_ground_kernel_and_objective": True,
        "identical_action_sequence_across_distinct_planners_required": False,
        "anytime_valid_for_registered_predictive_null": True,
        "distribution_free_global_dynamics_confidence_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains_v57.extension_content_id_v57(
            config["successor_domains"]["campaign"], payload
        ),
    }


__all__ = (
    "CalibratedMDLThreeDomainCampaignCoreV57Error",
    "build_calibrated_mdl_three_domain_campaign_document_v57",
)
