"""V56r1 successor with exact witness-blind frontier closure stopping.

Unchanged ground adapters, candidate synthesis, planning, certificate recovery,
validation, and OOD primitives are reused from the frozen V56 implementation.
Only acquisition termination and the enclosing sample/campaign roots are new.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as base
from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v56r1 as domains_v56r1
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    exact_candidate_replay_v11,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11r1 import (
    mdl_confidence_or_exact_frontier_stop_update_v11r1,
)


class AdaptiveMDLCrossDomainCampaignCoreV56R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AdaptiveMDLCrossDomainCampaignCoreV56R1Error(message)


def _acquisition_document(
    *,
    adapter: Any,
    arm: str,
    factor_prior_enabled: bool,
    labels: int,
    rows: tuple[Any, ...],
    candidate: MDLAdaptiveJointCandidateV11,
    issued_at: int,
    invalidated: int,
    program_disagreements: int,
    history: list[dict[str, Any]],
    stop: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_acquisition.v56r1",
        "failed_predecessor_id": config["v56_failure_id"],
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "factor_prior_enabled": factor_prior_enabled,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": base._raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": program_disagreements,
        "stopping_history": history,
        "terminal_stop_update": dict(stop),
        "stopped_by_mdl_confidence_margin": stop[
            "stopped_by_mdl_confidence_margin"
        ],
        "stopped_by_exact_reachable_frontier_closure": stop[
            "exact_reachable_frontier_closure_stop"
        ],
        "candidate_synthesis_attempted_after_every_support_query": True,
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "witness_blind_depth_frontier_policy": True,
        "generation_witness_accessed": False,
        "full_frontier_calibration_consumed": False,
        "same_synthesizer_query_order_mdl_confidence_and_frontier_rule": True,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }
    return {
        **payload,
        "acquisition_id": domains_v56r1.extension_content_id_v56r1(
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
    program_disagreements = 0
    previous_fingerprint = None
    pending = {
        "ANONYMOUS_FACTOR_PRIOR_ON": True,
        "STRICT_NO_PRIOR": False,
    }
    histories = {arm: [] for arm in pending}
    results: dict[str, dict[str, Any]] = {}
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    generator = iter(base._witness_blind_depth_frontier(adapter))
    try:
        batch = next(generator)
    except StopIteration:  # pragma: no cover
        _fail("V56r1 ground frontier was empty")
    for labels in range(1, maximum + 1):
        try:
            next_batch = next(generator)
            frontier_exhausted = False
        except StopIteration:
            next_batch = None
            frontier_exhausted = True
        rows.extend(batch)
        batches.append(batch)
        reason = "NO_COMPLETE_CANDIDATE_YET"
        replay = None
        if candidate is not None:
            replay = exact_candidate_replay_v11(
                candidate, tuple(rows), adapter.catalogue
            )
            if replay["exact"] is not True:
                invalidated += 1
                previous_fingerprint = candidate.public_document[
                    "program_fingerprint_sha256"
                ]
                candidate = None
                reason = "COUNTEREVIDENCE_INVALIDATED_COMPLETE_CANDIDATE"
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
                            "witness_blind_reachable_frontier_exhausted": (
                                frontier_exhausted
                            ),
                        }
                    )
                if frontier_exhausted:
                    _fail(
                        "V56r1 exact frontier closed without a complete candidate "
                        f"for {adapter.family} seed {adapter.seed}"
                    )
                if next_batch is None:  # pragma: no cover
                    raise AssertionError
                batch = next_batch
                continue
            issued_at = labels
            fingerprint = candidate.public_document[
                "program_fingerprint_sha256"
            ]
            if previous_fingerprint is not None and fingerprint != previous_fingerprint:
                program_disagreements += 1
            reason = (
                "FIRST_COMPLETE_CANDIDATE_SYNTHESIZED"
                if invalidated == 0
                else "COUNTEREVIDENCE_TRIGGERED_COMPLETE_RESYNTHESIS"
            )
        for arm, enabled in tuple(pending.items()):
            stop = mdl_confidence_or_exact_frontier_stop_update_v11r1(
                candidate,
                tuple(rows),
                adapter.catalogue,
                factor_prior_enabled=enabled,
                invalidated_candidate_count=invalidated,
                candidate_program_disagreement_count=program_disagreements,
                factor_signature_credit_units=config[
                    "factor_signature_credit_units"
                ],
                confidence_reserve_units=config["confidence_reserve_units"],
                invalidated_candidate_penalty_units=config[
                    "invalidated_candidate_penalty_units"
                ],
                minimum_reusable_factor_count=config[
                    "minimum_reusable_factor_count"
                ],
                witness_blind_reachable_frontier_exhausted=frontier_exhausted,
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
                factor_prior_enabled=enabled,
                labels=labels,
                rows=tuple(rows),
                candidate=candidate,
                issued_at=issued_at,
                invalidated=invalidated,
                program_disagreements=program_disagreements,
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
            prior = results["ANONYMOUS_FACTOR_PRIOR_ON"]
            no_prior = results["STRICT_NO_PRIOR"]
            common = tuple(
                row
                for item in no_prior["batches"][: len(prior["batches"])]
                for row in item
            )
            if prior["rows"] != common:
                _fail("V56r1 matched acquisition prefix changed")
            return results
        if frontier_exhausted:
            _fail(
                "V56r1 exact frontier closure failed to stop all arms for "
                f"{adapter.family} seed {adapter.seed}; pending={sorted(pending)}"
            )
        if next_batch is None:  # pragma: no cover
            raise AssertionError
        batch = next_batch
    _fail(
        "V56r1 adaptive acquisition crossed its label cap for "
        f"{adapter.family} seed {adapter.seed}; pending={sorted(pending)}"
    )


def _run_occurrence(
    args: tuple[str, int, int, Mapping[str, Any], Mapping[str, Any]]
) -> dict[str, Any]:
    family, episode_index, seed, factor_library, config = args
    adapter = base._adapter(family, seed, config)
    acquisitions = _acquire_matched(adapter, factor_library, config)
    result = {
        "family": family,
        "seed": seed,
        "acquisitions": {
            arm: row["document"] for arm, row in acquisitions.items()
        },
        "common_prefix_sha256": base._raw_sha(
            acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]["rows"]
        ),
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
        action_rows = [row["action_keys"] for row in result["episodes"].values()]
        if any(row != action_rows[0] for row in action_rows[1:]):
            _fail(f"V56r1 matched plans changed for {family} seed {seed}")
        if not all(row["success"] for row in result["episodes"].values()):
            _fail(f"V56r1 held-out planning failed for {family} seed {seed}")
        result["isolated_validation"] = base._isolated_validation(
            adapter, acquisitions, config
        )
    return result


def build_adaptive_mdl_cross_domain_campaign_document_v56r1(
    config: Mapping[str, Any],
    preregistration_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    if factor_library.get("factor_library_id") != config["factor_library_id"]:
        _fail("V56r1 factor-library identity changed")
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
        row["local_ground_support_labels"] for row in episodes["STRICT_NO_PRIOR"]
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
            "factor_prior_on_exact_frontier_closure_count": sum(
                row["stopped_by_exact_reachable_frontier_closure"]
                for row in prior_family
            ),
            "strict_no_prior_exact_frontier_closure_count": sum(
                row["stopped_by_exact_reachable_frontier_closure"]
                for row in no_prior_family
            ),
        }
        family_rows[family]["incremental_label_reduction"] = (
            family_rows[family]["strict_no_prior_acquisition_labels"]
            - family_rows[family]["factor_prior_on_acquisition_labels"]
        )
        if family_rows[family]["incremental_label_reduction"] <= 0:
            _fail(f"V56r1 factor prior did not reduce sample tax in {family}")
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
        start=1,
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
    incremental = no_prior_labels - prior_labels
    online = (no_prior_labels + no_prior_local) - (prior_labels + prior_local)
    lifetime = online - config["factor_library_labels"]
    if incremental <= 0 or online <= 0 or lifetime <= 0 or break_even is None:
        _fail("V56r1 registered cross-domain sample tax was not reduced")
    sample_payload = {
        "schema": "acfqp.mdl_adaptive_sample_tax.v56r1",
        "failed_v56_predecessor_id": config["v56_failure_id"],
        "factor_library_labels_prior_on_only": config["factor_library_labels"],
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": incremental,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": lifetime,
        "diagnostic_break_even_occurrence_count": break_even,
        "family_projections": family_rows,
        "prefix_curve": prefix_curve,
        "same_synthesizer_query_order_mdl_confidence_and_frontier_rule": True,
        "only_registered_factor_code_credit_switched": True,
        "fixed_minimum_label_floor_consumed": False,
        "fixed_confirmation_block_consumed": False,
        "official_break_even_claimed": False,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": domains_v56r1.extension_content_id_v56r1(
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
        _fail("V56r1 incompatible OOD domain was admitted")
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
        "schema": "acfqp.mdl_adaptive_cross_domain_campaign.v56r1",
        "preregistration_id": preregistration_id,
        "failed_v56_predecessor_id": config["v56_failure_id"],
        "frozen_v55_campaign_id": config["v55_campaign_id"],
        "frozen_v55_verification_id": config["v55_verification_id"],
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
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "full_frontier_target_layout_calibration_consumed": False,
        "exact_frontier_closure_is_a_stop_not_a_calibration_input": True,
        "same_synthesizer_used_in_both_families": True,
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
        "campaign_id": domains_v56r1.extension_content_id_v56r1(
            config["successor_domains"]["campaign"], payload
        ),
    }


__all__ = (
    "AdaptiveMDLCrossDomainCampaignCoreV56R1Error",
    "build_adaptive_mdl_cross_domain_campaign_document_v56r1",
)
