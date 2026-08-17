"""Fresh relation-certified V49r2 atomic-composition campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_atomic_composition_campaign_v49r1 as frozen_helpers
from acfqp import construction_k7_atomic_composition_failure_v49r1 as v49r1_failure
from acfqp import construction_k7_atomic_composition_preregistration_v49r2 as pre
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularState,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
    select_seeded_stochastic_modular_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    derive_atomic_dependency_support_v4,
    execute_generic_atomic_support_v4,
    plan_generic_atomic_program_v4,
    synthesize_generic_atomic_program_v4,
    target_binding_from_initial_vector_v4,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = "49.2.0"
CAMPAIGN_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7AtomicCompositionCampaignV49R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AtomicCompositionCampaignV49R2Error(message)


def _verify_frozen_helper_boundary() -> None:
    raw = (pre.SOURCE_ROOT / v49r1_failure.FAILED_PRODUCER_RELATIVE_PATH).read_bytes()
    if (
        len(raw) != v49r1_failure.FAILED_PRODUCER_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != v49r1_failure.FAILED_PRODUCER_SHA256
    ):
        _fail("V49r2 source-pinned algorithmic helper boundary changed")
    if not (
        pre.SOURCE_SPEC == frozen_helpers.pre.SOURCE_SPEC
        and pre.TARGET_SPEC == frozen_helpers.pre.TARGET_SPEC
        and pre.SHARED_MODE_TOKENS == frozen_helpers.pre.SHARED_MODE_TOKENS
        and pre.SHARED_CLASS_TOKENS == frozen_helpers.pre.SHARED_CLASS_TOKENS
        and pre.SHARED_TERMINAL_TOKENS == frozen_helpers.pre.SHARED_TERMINAL_TOKENS
        and pre.STATE_LAYOUT_ORDER == frozen_helpers.pre.STATE_LAYOUT_ORDER
        and pre.ACTION_FIELD_ORDER == frozen_helpers.pre.ACTION_FIELD_ORDER
    ):
        _fail("V49r2 helper schema projection changed")


def _raw_archive(
    occurrence: int,
    seed: int,
    catalogue: tuple[FlatRawActionV4, ...],
    rows: tuple[Any, ...],
    legacy_archive: Mapping[str, Any],
) -> dict[str, Any]:
    layout_payload = {
        "state_width": len(pre.STATE_LAYOUT_ORDER),
        "action_field_width": len(pre.ACTION_FIELD_ORDER),
        "state_layout_commitment": hashlib.sha256(bytes(pre.STATE_LAYOUT_ORDER)).hexdigest(),
        "action_layout_commitment": hashlib.sha256(bytes(pre.ACTION_FIELD_ORDER)).hexdigest(),
        "semantic_role_names_serialized": False,
    }
    payload = {
        "schema": "acfqp.atomic_composition_raw_observation.v49r2",
        "occurrence": occurrence,
        "seed": seed,
        "opaque_layout_id": content_id(pre.FUTURE_DOMAINS["observation"], layout_payload),
        "anonymous_action_catalogue": [row.to_document() for row in catalogue],
        "raw_transitions": [row.to_document() for row in rows],
        "source_support_labels": legacy_archive["source_support_labels"],
        "raw_outcome_rows": len(rows),
        "reachable_active_state_count": legacy_archive["reachable_active_state_count"],
        "generation_witness_accessed": False,
        "source_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_FRONTIER_ALL_LEGAL_ACTION_SUPPORTS",
    }
    return {
        **payload,
        "raw_observation_id": content_id(pre.FUTURE_DOMAINS["observation"], payload),
    }


def _relation_fields(program: Mapping[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if (
            len(expression) >= 3
            and expression[0] == "E04"
            and type(expression[1]) is str
            and type(expression[2]) is list
            and expression[2][:1] == ["E01"]
        ):
            incumbent = result.setdefault(expression[1], expression[2][1])
            if incumbent != expression[2][1]:
                _fail("V49r2 relation used more than one anonymous input field")
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    if not result:
        _fail("V49r2 compiled program carried no reusable relation")
    return result


def _episode(
    *,
    seed: int,
    arm: str,
    actions: list[int],
    tapes: list[str],
    final_status: StochasticModularStatus,
    planning_compute: int,
    peak_cache: int,
    labels: int,
    failures: int,
    local_labels: int,
    overlay_reuses: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.atomic_composition_receding_episode.v49r2",
        "seed": seed,
        "arm": arm,
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning_compute,
        "peak_planning_cache_entries": peak_cache,
        "ground_support_labels": labels,
        "failed_certificate_count": failures,
        "local_ground_support_labels": local_labels,
        "immutable_overlay_reuse_count": overlay_reuses,
        "final_status": final_status.value,
        "success": final_status is StochasticModularStatus.SUCCESS,
    }
    return {
        **payload,
        "episode_id": content_id(pre.FUTURE_DOMAINS["episode"], payload),
    }


def _build_campaign_document() -> dict[str, Any]:
    _verify_frozen_helper_boundary()
    prereg = pre.verify_atomic_composition_preregistration_v49r2(
        pre.freeze_atomic_composition_preregistration_v49r2()
    )
    all_rows = []
    catalogues = {}
    archives = []
    source_labels = 0
    for occurrence, seed in enumerate(pre.SOURCE_SEEDS):
        catalogue, rows, legacy_archive = frozen_helpers._source_occurrence(
            occurrence, seed
        )
        archive = _raw_archive(
            occurrence, seed, catalogue, rows, legacy_archive
        )
        catalogues[occurrence] = catalogue
        all_rows.extend(rows)
        archives.append(archive)
        source_labels += archive["source_support_labels"]
    program = synthesize_generic_atomic_program_v4(
        tuple(all_rows), catalogues, program_domain=pre.FUTURE_DOMAINS["program"]
    )
    support = derive_atomic_dependency_support_v4(
        program,
        tuple(all_rows),
        catalogues,
        support_domain=pre.FUTURE_DOMAINS["support"],
    )
    if {"E06", "E07", "E12"} - set(program["used_opcode_names"]):
        _fail("V49r2 program omitted a registered atomic composition")
    source_relations = frozen_helpers._required_relations(program)
    relation_fields = _relation_fields(program)

    first_target_kernel, witness = generate_stochastic_modular_routing(
        **pre.TARGET_SPEC, seed=pre.TARGET_SEEDS[0], require_last_mode=True
    )
    del witness
    first_catalogue, first_encode, _layout = frozen_helpers._raw_interface(
        pre.TARGET_SEEDS[0], first_target_kernel
    )
    first_initial = first_target_kernel.initial_distribution()[0][1]
    first_binding = target_binding_from_initial_vector_v4(
        program,
        first_encode(first_initial),
        base_relations=source_relations,
        terminal_tokens=pre.SHARED_TERMINAL_TOKENS,
    )
    source_binding = program["occurrence_bindings"][0]
    changed_constants = sorted(
        name
        for name, value in first_binding["constants"].items()
        if source_binding["constants"].get(name) != value
    )
    if not changed_constants:
        _fail("V49r2 relation transport certificate unexpectedly passed")
    failure_payload = {
        "schema": "acfqp.atomic_composition_failed_certificate.v49r2",
        "seed": pre.TARGET_SEEDS[0],
        "program_id": program["program_id"],
        "changed_anonymous_occurrence_constants": changed_constants,
        "relation_names_requiring_target_attestation": sorted(relation_fields),
        "ground_query_performed_before_failure": False,
        "outcome": "FAILED_RELATION_TRANSPORT_CERTIFICATE",
    }
    failure = {
        **failure_payload,
        "failed_certificate_id": content_id(
            pre.FUTURE_DOMAINS["failed_certificate"], failure_payload
        ),
    }

    overlay: dict[str, dict[int, int]] = {}
    distinctions = []
    for relation_name, field in sorted(relation_fields.items()):
        values = sorted({action.fields[field] for action in first_catalogue})
        for relation_input in values:
            action = next(
                row for row in first_catalogue if row.fields[field] == relation_input
            )
            edge = first_target_kernel.edges[action.key]
            probe_state = StochasticModularState(
                edge.source,
                0,
                0,
                edge.source,
                StochasticModularStatus.ACTIVE,
            )
            raw_state = first_encode(probe_state)
            actual_support = {
                first_encode(row.next_state)
                for row in first_target_kernel.step(
                    probe_state, StochasticModularAction(action.key)
                )
            }
            output = frozen_helpers._recover_local_value(
                program,
                first_binding,
                raw_state,
                action,
                actual_support,
                relation_name,
                relation_input,
                overlay,
            )
            distinction_payload = {
                "schema": "acfqp.atomic_composition_local_distinction.v49r2",
                "failed_certificate_id": failure["failed_certificate_id"],
                "program_id": program["program_id"],
                "seed": pre.TARGET_SEEDS[0],
                "anonymous_pre_vector": list(raw_state),
                "anonymous_action": action.to_document(),
                "anonymous_successor_support": [list(row) for row in sorted(actual_support)],
                "relation_name": relation_name,
                "relation_input_value": relation_input,
                "relation_output_value": output,
                "ground_support_labels": 1,
                "query_after_failed_certificate": True,
                "witness_blind_exemplar_selection": True,
            }
            distinction = {
                **distinction_payload,
                "local_distinction_id": content_id(
                    pre.FUTURE_DOMAINS["distinction"], distinction_payload
                ),
            }
            distinctions.append(distinction)
            overlay = {
                **overlay,
                relation_name: {
                    **overlay.get(relation_name, {}),
                    relation_input: output,
                },
            }
    if len(distinctions) > len(pre.SHARED_MODE_TOKENS):
        _fail("V49r2 target relation recovery exceeded its frozen local cap")

    structural_episodes = []
    strict_episodes = []
    structural_planning = 0
    strict_planning = 0
    structural_steps = 0
    strict_steps = 0
    strict_labels = 0
    overlay_reuses = 0
    for episode_index, seed in enumerate(pre.TARGET_SEEDS):
        kernel, witness = generate_stochastic_modular_routing(
            **pre.TARGET_SPEC, seed=seed, require_last_mode=True
        )
        del witness
        catalogue, encode, _layout = frozen_helpers._raw_interface(seed, kernel)
        by_key = {row.key: row for row in catalogue}
        state = kernel.initial_distribution()[0][1]
        binding = target_binding_from_initial_vector_v4(
            program,
            encode(state),
            base_relations=source_relations,
            terminal_tokens=pre.SHARED_TERMINAL_TOKENS,
        )
        actions: list[int] = []
        tapes: list[str] = []
        planning = 0
        peak = 0
        decision = 0
        while state.status is StochasticModularStatus.ACTIVE:
            plan, evaluations, cache_size = plan_generic_atomic_program_v4(
                program,
                encode(state),
                catalogue,
                binding,
                relation_overlay=overlay,
            )
            if not plan:
                _fail("V49r2 structural planner returned an empty active plan")
            action_key = plan[0]
            outcomes = kernel.step(state, StochasticModularAction(action_key))
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    encode(state),
                    by_key[action_key],
                    binding,
                    relation_overlay=overlay,
                )
            )
            if predicted != {encode(row.next_state) for row in outcomes}:
                _fail("V49r2 compiled support disagreed with target kernel")
            selected, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=decision,
            )
            state = selected.next_state
            actions.append(action_key)
            tapes.append(tape)
            planning += evaluations
            peak = max(peak, cache_size)
            overlay_reuses += 1
            decision += 1
        if state.status is not StochasticModularStatus.SUCCESS:
            _fail("V49r2 structural episode failed")
        structural_episodes.append(
            _episode(
                seed=seed,
                arm=pre.ARMS[0],
                actions=actions,
                tapes=tapes,
                final_status=state.status,
                planning_compute=planning,
                peak_cache=peak,
                labels=len(distinctions) if episode_index == 0 else 0,
                failures=1 if episode_index == 0 else 0,
                local_labels=len(distinctions) if episode_index == 0 else 0,
                overlay_reuses=len(actions),
            )
        )
        structural_planning += planning
        structural_steps += len(actions)

        direct_state = kernel.initial_distribution()[0][1]
        direct_cache = {}
        direct_actions = []
        direct_tapes = []
        direct_compute = 0
        direct_peak = 0
        direct_decision = 0
        while direct_state.status is StochasticModularStatus.ACTIVE:
            action_key, cache_size = frozen_helpers._strict_choice(
                kernel, direct_state, direct_cache
            )
            outcomes = kernel.step(direct_state, StochasticModularAction(action_key))
            selected, tape = select_seeded_stochastic_modular_outcome_v1(
                outcomes,
                seed=seed,
                episode_index=episode_index,
                decision_index=direct_decision,
            )
            direct_state = selected.next_state
            direct_actions.append(action_key)
            direct_tapes.append(tape)
            direct_compute += cache_size
            direct_peak = max(direct_peak, len(direct_cache))
            direct_decision += 1
        if direct_state.status is not StochasticModularStatus.SUCCESS:
            _fail("V49r2 strict episode failed")
        strict_labels += len(direct_cache)
        strict_episodes.append(
            _episode(
                seed=seed,
                arm=pre.ARMS[1],
                actions=direct_actions,
                tapes=direct_tapes,
                final_status=direct_state.status,
                planning_compute=direct_compute,
                peak_cache=direct_peak,
                labels=len(direct_cache),
                failures=0,
                local_labels=0,
                overlay_reuses=0,
            )
        )
        strict_planning += direct_compute
        strict_steps += len(direct_actions)

    composed_labels = source_labels + len(distinctions)
    if composed_labels >= strict_labels:
        _fail("V49r2 did not reduce the matched registered support-label tax")
    average_strict = strict_labels / len(pre.TARGET_SEEDS)
    sample_payload = {
        "schema": "acfqp.atomic_composition_sample_tax.v49r2",
        "offline_source_support_labels": source_labels,
        "target_local_support_labels": len(distinctions),
        "composed_total_registered_support_labels": composed_labels,
        "strict_target_support_labels": strict_labels,
        "registered_support_label_savings": strict_labels - composed_labels,
        "sample_tax_reduced_on_frozen_campaign": True,
        "diagnostic_break_even_occurrences": max(
            1, int(source_labels // max(1.0, average_strict)) + 1
        ),
        "official_N_break_even": None,
        "planning_compute_not_counted_as_sample_labels": True,
    }
    sample_tax = {
        **sample_payload,
        "sample_tax_id": content_id(pre.FUTURE_DOMAINS["sample_tax"], sample_payload),
    }
    partial_payload = {
        "schema": "acfqp.atomic_composition_partial_dynamics.v49r2",
        "program_id": program["program_id"],
        "finite_successor_support_authority_present": True,
        "exact_probability_authority_present": False,
        "maximum_observed_support_cardinality": 2,
        "robust_all_successor_planning_required": True,
        "higher_order_multistep_branching_evaluated": True,
    }
    partial = {
        **partial_payload,
        "partial_dynamics_id": content_id(pre.FUTURE_DOMAINS["partial"], partial_payload),
    }
    acquisition_payload = {
        "schema": "acfqp.atomic_composition_adaptive_acquisition.v49r2",
        "arms": list(pre.ARMS),
        "source_raw_observation_ids": [row["raw_observation_id"] for row in archives],
        "failed_certificate_ids": [failure["failed_certificate_id"]],
        "local_distinction_ids": [row["local_distinction_id"] for row in distinctions],
        "failed_certificate_precedes_every_local_label": True,
        "target_relation_exemplar_label_count": len(distinctions),
        "overlay_reuse_count": overlay_reuses,
        "matched_target_seed_ids": list(pre.TARGET_SEEDS),
    }
    acquisition = {
        **acquisition_payload,
        "adaptive_acquisition_id": content_id(
            pre.FUTURE_DOMAINS["acquisition"], acquisition_payload
        ),
    }
    ood_payload = {
        "schema": "acfqp.atomic_composition_ood_rejection.v49r2",
        "input_schema": "OPAQUE_CONTINUOUS_REAL_VECTOR_WITH_INCOMPATIBLE_WIDTH",
        "program_schema": program["schema"],
        "schema_compatible": False,
        "prior_transfer_attempted": False,
        "outcome_execution_performed": False,
        "status": "STRICT_OOD_NO_TRANSFER",
    }
    ood = {
        **ood_payload,
        "ood_rejection_id": content_id(pre.FUTURE_DOMAINS["ood"], ood_payload),
    }
    accounting = {
        "offline_source_support_labels": source_labels,
        "target_local_support_labels": len(distinctions),
        "structural_execution_steps": structural_steps,
        "strict_execution_steps": strict_steps,
        "atomic_derivation_compute_events": program["atomic_expression_evaluations"],
        "structural_planning_compute_events": structural_planning,
        "strict_planning_compute_events": strict_planning,
        "certificate_compute_events": support["candidate_dependency_count"],
        "peak_structural_cache_entries": max(
            row["peak_planning_cache_entries"] for row in structural_episodes
        ),
        "all_axes_separate": True,
    }
    payload = {
        "schema": "acfqp.atomic_composition_campaign.v49r2",
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": prereg.preregistration_id,
        "preregistration_canonical_sha256": hashlib.sha256(prereg.canonical_bytes).hexdigest(),
        "preserved_v49_failure_id": pre.V49_FAILURE_ID,
        "preserved_v49r1_failure_id": pre.V49R1_FAILURE_ID,
        "source_pinned_v49r1_algorithmic_helper_reuse": True,
        "source_archives": archives,
        "compiled_program": program,
        "dependency_support": support,
        "partial_dynamics": partial,
        "failed_certificates": [failure],
        "local_distinctions": distinctions,
        "relation_overlay": {
            name: [[key, value] for key, value in sorted(rows.items())]
            for name, rows in sorted(overlay.items())
        },
        "adaptive_acquisition": acquisition,
        "structural_episodes": structural_episodes,
        "strict_episodes": strict_episodes,
        "sample_tax": sample_tax,
        "ood_rejection": ood,
        "accounting": accounting,
        "required_positive_conditions_passed": True,
        "fresh_fourth_combination_domain_observed": True,
        "fourth_unrelated_domain_authority_claimed": False,
        "higher_order_finite_support_planning_observed": True,
        "exact_probability_authority_present": False,
        "open_ended_layout_discovery_claimed": False,
        "broad_world_model_synthesis_claimed": False,
        "broad_cross_domain_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {
        **payload,
        "atomic_composition_campaign_id": content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AtomicCompositionCampaignV49R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V49r2 campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V49r2 campaign bytes changed")
        payload = {key: value for key, value in document.items() if key != "atomic_composition_campaign_id"}
        if document.get("atomic_composition_campaign_id") != self.campaign_id or content_id(
            pre.FUTURE_DOMAINS["campaign"], payload
        ) != self.campaign_id:
            _fail("V49r2 campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def run_atomic_composition_campaign_v49r2() -> AtomicCompositionCampaignV49R2:
    document = _build_campaign_document()
    raw = canonical_json_bytes(document)
    identity = document["atomic_composition_campaign_id"]
    if CAMPAIGN_ID != "0" * 64 and (
        identity != CAMPAIGN_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r2 campaign changed")
    return AtomicCompositionCampaignV49R2(_ISSUER, raw, identity)


def verify_atomic_composition_campaign_v49r2(
    value: AtomicCompositionCampaignV49R2,
) -> AtomicCompositionCampaignV49R2:
    if type(value) is not AtomicCompositionCampaignV49R2:
        _fail("V49r2 campaign rejects foreign values")
    value.__post_init__()
    if (
        value.campaign_id != CAMPAIGN_ID
        or len(value.canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(value.canonical_bytes).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V49r2 campaign identity changed")
    return value


__all__ = (
    "AtomicCompositionCampaignV49R2",
    "CAMPAIGN_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "run_atomic_composition_campaign_v49r2",
    "verify_atomic_composition_campaign_v49r2",
)
