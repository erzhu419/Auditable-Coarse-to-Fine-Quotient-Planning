"""Producer-free verification of the preserved V99 registered failure."""

from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v99 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "2af478cf92b8f6ccb1869042a923487c0f5eb859dc4cbacfdef4a47643930bfd"
CAMPAIGN_BYTE_COUNT = 4_457_987
CAMPAIGN_SHA256 = "b359520c21165da737b317e71c45454febb9e90de72c63760819a047a40e8597"
PREREGISTRATION_ID = "1fa4860d395dd4c4d869d51c960d92b61565e3f06713c51e3ef40648ab4fcae6"
V98_CAMPAIGN_ID = "0c81232368a76e987b9921e3312fa70653eb5cdbf18e077c8c482aa7bd827f6b"
V98_VERIFICATION_ID = "f7b01805fb8b0192dee4137e416313eb05e9626925a2e49609cd70079f120dfb"
SOURCE_LIBRARY_ARTIFACT_ID = "4f0a9592f7d6ba2d7683e9328f76dbd01bd18a3a47a062ea764f7a20012caeba"
TARGETS = (
    ("BALANCED_BATCH_REFINEMENT", 1_005_101),
    ("BALANCED_BATCH_REFINEMENT", 1_005_102),
    ("MAINTENANCE_CASCADE", 1_005_103),
    ("MAINTENANCE_CASCADE", 1_005_104),
)
TARGET_EPISODES = (71, 72, 73)
VERIFICATION_ID = "747daf33b43a4c10cad95e37c3d0b76714ff264b7d5d9f9ff70d78da1b55d56c"
EXPECTED_CANONICAL_BYTE_COUNT = 1_352
EXPECTED_CANONICAL_SHA256 = "d5ece1f04f0dcec47677c1196cc51e845ca4701ec2435d621c33924ff935b4cb"

_SEQUENCE_DOMAIN = b"acfqp:generic-persistent-agreement-shielded-sequence:v99\x00"
_FIRST_EPISODE_DOMAIN = b"acfqp:agreement-shielded-online-certificate-episode:v99\x00"
_PRELOADED_EPISODE_DOMAIN = b"acfqp:generic-preloaded-certificate-receding-episode:v74\x00"
_SHIELD_DOMAIN = b"acfqp:abstract-partial-agreement-shield:v99\x00"
_BASE_ACQUISITION_DOMAIN = b"acfqp:generic-multi-residual-acquisition:v24\x00"
_DEPENDENCY_CANDIDATE_DOMAIN = b"acfqp:post-dependency-residual-candidate:v97\x00"
_DEPENDENCY_ACQUISITION_DOMAIN = b"acfqp:post-dependency-multi-residual-acquisition:v97\x00"
_ABSTRACT_PLAN_DOMAIN = b"acfqp:post-dependency-abstract-plan:v97\x00"


class ConstructionK7AgreementShieldedIndependentVerifierV99Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AgreementShieldedIndependentVerifierV99Error(message)


def _generic_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def _check_generic_id(document: Any, key: str, domain: bytes) -> None:
    if type(document) is not dict:
        _fail(f"V99 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != _generic_id(domain, payload):
        _fail(f"V99 {key} content identity changed")


def _check_v99_id(document: Any, key: str, domain: str) -> None:
    if type(document) is not dict:
        _fail(f"V99 {key} document type changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != domains.extension_content_id_v99(domain, payload):
        _fail(f"V99 {key} content identity changed")


def _group_count(rows: Any) -> int:
    if type(rows) is not list:
        _fail("V99 transition row inventory changed")
    groups = set()
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        if (
            type(row) is not dict
            or type(row.get("pre_vector")) is not list
            or type(row.get("post_vector")) is not list
            or type(action) is not dict
            or type(action.get("action_key")) is not int
        ):
            _fail("V99 transition row schema changed")
        groups.add((tuple(row["pre_vector"]), action["action_key"]))
    return len(groups)


def _check_pairing(episode: Mapping[str, Any]) -> None:
    failures = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        type(failures) is not list
        or type(distinctions) is not list
        or len(failures) != len(distinctions)
        or [row.get("failure_index") for row in failures]
        != list(range(len(failures)))
        or [row.get("failure_index") for row in distinctions]
        != list(range(len(distinctions)))
        or any(
            row.get("ground_query_performed_before_failure") is not False
            for row in failures
        )
        or any(
            row.get("query_after_failed_certificate") is not True
            for row in distinctions
        )
    ):
        _fail("V99 certificate-failure-only query pairing changed")


def _shield_receipt(
    abstract: list[int], partial: list[int], legal: list[int]
) -> dict[str, Any]:
    abstract_key = next((key for key in abstract if key in legal), None)
    partial_key = next((key for key in partial if key in legal), None)
    agreed = (
        abstract_key is not None
        and partial_key is not None
        and abstract_key == partial_key
    )
    ordered = []
    if agreed:
        ordered.append(abstract_key)
    if partial_key is not None and partial_key not in ordered:
        ordered.append(partial_key)
    ordered.extend(key for key in legal if key not in ordered)
    payload = {
        "schema": "acfqp.abstract_partial_agreement_shield.v99",
        "abstract_proposal": abstract,
        "partial_proposal": partial,
        "legal_action_keys": legal,
        "abstract_legal_proposal": abstract_key,
        "partial_legal_proposal": partial_key,
        "abstract_partial_agreement": agreed,
        "abstract_proposal_admitted_to_action_order": agreed,
        "abstract_disagreement_abstained": abstract_key is not None and not agreed,
        "shielded_action_order": ordered,
        "abstract_proposal_can_precede_partial_without_agreement": False,
        "same_shield_applied_to_prior_and_no_prior_arms": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "shield_receipt_id": _generic_id(_SHIELD_DOMAIN, payload),
    }


def _check_shield(receipt: Any) -> tuple[bool, bool]:
    if type(receipt) is not dict:
        _fail("V99 shield receipt type changed")
    expected = _shield_receipt(
        receipt.get("abstract_proposal", []),
        receipt.get("partial_proposal", []),
        receipt.get("legal_action_keys", []),
    )
    if receipt != expected:
        _fail("V99 shield receipt did not independently replay")
    return (
        receipt["abstract_partial_agreement"] is True,
        receipt["abstract_disagreement_abstained"] is True,
    )


def _signed_bits(value: int) -> int:
    return 1 + 2 * int(math.log2(abs(value) + 1))


def _check_dependency_candidate(
    candidate: Mapping[str, Any],
    rows: list[dict[str, Any]],
    order: list[int],
) -> None:
    _check_generic_id(candidate, "candidate_id", _DEPENDENCY_CANDIDATE_DOMAIN)
    target = candidate.get("target_column")
    driver = candidate.get("driver_post_column")
    lower = candidate.get("lower_inclusive_threshold")
    upper = candidate.get("upper_inclusive_threshold")
    leaves = candidate.get("leaf_supports")
    if (
        candidate.get("candidate_kind")
        != "POST_DEPENDENCY_THREE_BAND_FINITE_SUPPORT"
        or type(target) is not int
        or type(driver) is not int
        or type(lower) is not int
        or type(upper) is not int
        or not lower < upper
        or type(leaves) is not list
        or len(leaves) != 3
        or candidate.get("structure_prior_supplied_driver_thresholds_or_leaf_values")
        is not False
        or candidate.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V99 dependency candidate schema changed")
    excess = 0
    seen = [set(), set(), set()]
    for row in rows:
        post = [row["post_vector"][index] for index in order]
        band = 0 if post[driver] <= lower else 1 if post[driver] <= upper else 2
        if post[target] not in leaves[band]:
            _fail("V99 dependency candidate does not cover a raw successor")
        seen[band].add(post[target])
        excess += len(leaves[band]) - 1
    if [sorted(values) for values in seen] != leaves:
        _fail("V99 dependency leaf support contains unobserved values")
    state_bits = max(1, math.ceil(math.log2(max(2, len(order)))))
    support_bits = sum(_signed_bits(value) for leaf in leaves for value in leaf)
    expected_length = (
        (1 if candidate.get("structure_prior_enabled") is True else 8)
        + 2 * state_bits
        + _signed_bits(lower)
        + _signed_bits(upper)
        + support_bits
    )
    if (
        candidate.get("predictive_support_excess") != excess
        or candidate.get("description_length_bits") != expected_length
    ):
        _fail("V99 dependency support or description length changed")


def _check_acquisition(
    acquisition: Any,
    rows: list[dict[str, Any]],
    partial: Mapping[str, Any],
    structural_prior_enabled: bool,
) -> int:
    _check_generic_id(
        acquisition,
        "multi_residual_acquisition_id",
        _DEPENDENCY_ACQUISITION_DOMAIN,
    )
    base = acquisition.get("base_multi_residual_acquisition")
    _check_generic_id(
        base, "multi_residual_acquisition_id", _BASE_ACQUISITION_DOMAIN
    )
    candidates = acquisition.get("retrospective_post_dependency_candidates")
    order = partial.get("candidate", {}).get("layout", {}).get(
        "state_canonical_to_raw"
    )
    if (
        type(candidates) is not list
        or type(order) is not list
        or acquisition.get("structural_prior_enabled") is not structural_prior_enabled
        or acquisition.get("shared_physical_ground_support_labels")
        != _group_count(rows)
        or acquisition.get("all_residual_targets_have_compilable_proposals")
        is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V99 retained acquisition boundary changed")
    for candidate in candidates:
        _check_dependency_candidate(candidate, rows, order)
    return len(candidates)


def _check_first(
    first: Any,
    *,
    family: str,
    seed: int,
    partial: Mapping[str, Any],
    prior: bool,
) -> tuple[int, int, int, int, int]:
    _check_generic_id(first, "episode_id", _FIRST_EPISODE_DOMAIN)
    expected_units = 1 if prior else 8
    expected_arm = (
        "POST_DEPENDENCY_STRUCTURE_META_PRIOR_ON"
        if prior
        else "STRICT_NO_POST_DEPENDENCY_STRUCTURE_META_PRIOR"
    )
    rows = first.get("raw_local_transition_rows")
    history = first.get("adaptive_stopping_history")
    shield_rows = first.get("agreement_shield_receipts")
    if (
        first.get("schema")
        != "acfqp.agreement_shielded_online_certificate_episode.v99"
        or first.get("family") != family
        or first.get("seed") != seed
        or first.get("episode_index") != TARGET_EPISODES[0]
        or first.get("arm") != expected_arm
        or first.get("structure_prior_code_units") != expected_units
        or first.get("confidence_penalty_units") != 6
        or first.get("required_post_dependency_model_evidence_labels")
        != 6 + expected_units
        or first.get(
            "same_synthesizer_stopping_rule_and_agreement_shield_between_prior_arms"
        )
        is not True
        or first.get("abstract_proposal_can_precede_partial_without_agreement")
        is not False
        or first.get("query_local_exact_overlay_exclusively_used_for_safety")
        is not True
        or first.get("complete_world_model_synthesized") is not False
        or type(rows) is not list
        or type(history) is not list
        or type(shield_rows) is not list
    ):
        _fail("V99 first shielded episode boundary changed")
    _check_pairing(first)
    running_rows = []
    running_labels = 0
    offset = 0
    first_activation = None
    for distinction in first["local_distinctions"]:
        running_labels += distinction["ground_support_labels"]
        batch = distinction.get("raw_transition_rows")
        if batch is None:
            continue
        running_rows.extend(batch)
        item = history[offset]
        offset += 1
        dependency_count = item.get("dependency_candidate_count")
        complete = item.get("all_residual_targets_have_compilable_proposals")
        evidence_labels = _group_count(running_rows)
        required = (
            6 if complete is True and dependency_count == 0 else 6 + expected_units
        )
        activated = complete is True and evidence_labels >= required
        if (
            item.get("ground_support_labels") != running_labels
            or item.get("model_evidence_ground_support_labels") != evidence_labels
            or item.get("required_model_evidence_ground_support_labels") != required
            or item.get("activated") is not activated
        ):
            _fail("V99 activation stopping history changed")
        if activated and first_activation is None:
            first_activation = running_labels
    if offset != len(history):
        _fail("V99 stopping history cardinality changed")
    accepts = 0
    disagreements = 0
    for wrapper in shield_rows:
        if type(wrapper) is not dict or type(wrapper.get("raw_state")) is not list:
            _fail("V99 first shield wrapper changed")
        accepted, disagreed = _check_shield(wrapper.get("shield"))
        accepts += accepted
        disagreements += disagreed
    if (
        first.get("agreement_shield_accept_count") != accepts
        or first.get("agreement_shield_disagreement_abstention_count")
        != disagreements
        or first.get("candidate_activated_at_ground_support_label")
        != first_activation
        or first.get("local_ground_support_labels")
        != sum(row["ground_support_labels"] for row in first["local_distinctions"])
    ):
        _fail("V99 first shield or label accounting changed")
    final = first.get("final_post_dependency_acquisition")
    dependency_count = _check_acquisition(final, rows, partial, prior)
    if first.get("active_post_dependency_acquisition") != final:
        _fail("V99 active model did not retain final acquisition")
    return (
        first["local_ground_support_labels"],
        first_activation,
        dependency_count,
        accepts,
        disagreements,
    )


def _check_later_plan(plan: Any, acquisition_id: str) -> tuple[bool, bool, bool]:
    if type(plan) is not dict:
        _fail("V99 later plan type changed")
    accepted, disagreed = _check_shield(plan.get("agreement_shield_receipt"))
    if accepted:
        extras = {
            "persistent_online_model_used",
            "persistent_post_dependency_program_used",
            "persistent_partial_fallback_used",
            "agreement_shield_receipt",
        }
        payload = {
            key: value
            for key, value in plan.items()
            if key != "abstract_plan_id" and key not in extras
        }
        if (
            plan.get("abstract_plan_id") != _generic_id(_ABSTRACT_PLAN_DOMAIN, payload)
            or plan.get("multi_residual_acquisition_id") != acquisition_id
            or plan.get("persistent_online_model_used") is not True
            or plan.get("persistent_partial_fallback_used") is not False
            or plan.get("abstract_plan_used_as_safety_authority") is not False
        ):
            _fail("V99 accepted persistent abstract plan changed")
        return True, disagreed, plan.get("persistent_post_dependency_program_used") is True
    if (
        plan.get("schema")
        != "acfqp.generic_persistent_agreement_shielded_fallback_plan.v99"
        or plan.get("persistent_online_model_used") is not False
        or plan.get("persistent_partial_fallback_used") is not True
        or plan.get("abstract_plan_used_as_safety_authority") is not False
    ):
        _fail("V99 disagreement fallback plan changed")
    return False, disagreed, False


def _check_sequence(
    sequence: Any,
    *,
    family: str,
    seed: int,
    partial: Mapping[str, Any],
    prior: bool,
) -> tuple[int, int, int, int, int, int]:
    _check_generic_id(sequence, "sequence_id", _SEQUENCE_DOMAIN)
    first = sequence.get("first_agreement_shielded_online_episode")
    later = sequence.get("later_persistent_episodes")
    rows = sequence.get("persistent_exact_overlay_rows")
    if (
        sequence.get("schema")
        != "acfqp.generic_persistent_agreement_shielded_sequence.v99"
        or sequence.get("family") != family
        or sequence.get("seed") != seed
        or sequence.get("episode_indices") != list(TARGET_EPISODES)
        or type(later) is not list
        or len(later) != 2
        or type(rows) is not list
        or sequence.get("persistent_exact_overlay_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or sequence.get("persistent_exact_support_group_count") != _group_count(rows)
        or sequence.get("same_agreement_shield_applied_to_prior_and_no_prior_arms")
        is not True
        or sequence.get("abstract_proposal_can_precede_partial_without_agreement")
        is not False
        or sequence.get("persistent_exact_overlay_exclusively_discharges_safety")
        is not True
        or sequence.get("complete_world_model_synthesized") is not False
    ):
        _fail("V99 persistent shielded sequence changed")
    first_labels, activation, dependencies, first_accept, first_disagree = _check_first(
        first, family=family, seed=seed, partial=partial, prior=prior
    )
    acquisition = sequence.get("retained_active_post_dependency_acquisition")
    if acquisition != first["active_post_dependency_acquisition"]:
        _fail("V99 retained acquisition changed")
    acquisition_id = acquisition["multi_residual_acquisition_id"]
    later_labels = 0
    later_accept = 0
    later_disagree = 0
    later_dependency = 0
    for episode, index in zip(later, TARGET_EPISODES[1:], strict=True):
        wrapper_fields = {
            "new_certificate_labels_charged_this_episode",
            "paid_certificate_labels_cumulative",
            "persistent_exact_support_group_count",
        }
        payload = {
            key: value
            for key, value in episode.items()
            if key != "episode_id" and key not in wrapper_fields
        }
        if episode.get("episode_id") != _generic_id(_PRELOADED_EPISODE_DOMAIN, payload):
            _fail("V99 later episode content identity changed")
        _check_pairing(episode)
        if (
            episode.get("family") != family
            or episode.get("seed") != seed
            or episode.get("episode_index") != index
            or episode.get("arm")
            != "PERSISTENT_AGREEMENT_SHIELDED_POST_DEPENDENCY_TRANSFER"
            or episode.get("query_local_exact_overlay_exclusively_used_for_safety")
            is not True
            or episode.get("model_or_alignment_used_as_safety_authority") is not False
        ):
            _fail("V99 later episode boundary changed")
        later_labels += episode["incremental_certificate_local_ground_support_labels"]
        for receipt in episode["abstract_plan_receipts"]:
            accepted, disagreed, dependency = _check_later_plan(
                receipt["abstract_plan"], acquisition_id
            )
            later_accept += accepted
            later_disagree += disagreed
            later_dependency += dependency
    partial_labels = partial["ground_support_labels"]
    if (
        sequence.get("target_model_activation_ground_support_labels_with_right_censoring")
        != partial_labels + activation
        or sequence.get("later_agreement_shield_accept_receipt_count") != later_accept
        or sequence.get("later_agreement_shield_disagreement_abstention_count")
        != later_disagree
        or sequence.get("later_post_dependency_abstract_plan_receipt_count")
        != later_dependency
        or sequence.get("later_query_ground_support_labels") != later_labels
        or sequence.get("lifetime_target_ground_support_labels")
        != partial_labels + first_labels + later_labels
        or sequence.get("every_new_ground_query_followed_a_failed_certificate")
        is not True
    ):
        _fail("V99 sequence activation, shield, or label accounting changed")
    return (
        sequence["lifetime_target_ground_support_labels"],
        partial_labels + activation,
        dependencies,
        first_accept,
        first_disagree,
        later_accept,
    )


def _verify_campaign_document(document: Any) -> dict[str, Any]:
    _check_v99_id(
        document,
        "campaign_id",
        domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_CAMPAIGN_V99_DOMAIN,
    )
    occurrences = document.get("target_occurrences")
    if (
        document.get("schema")
        != "acfqp.agreement_shielded_cross_family_campaign.v99"
        or document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v98_campaign_id") != V98_CAMPAIGN_ID
        or document.get("v98_verification_id") != V98_VERIFICATION_ID
        or document.get("source_library_artifact_id") != SOURCE_LIBRARY_ARTIFACT_ID
        or type(occurrences) is not list
        or [(row.get("target_family"), row.get("seed")) for row in occurrences]
        != list(TARGETS)
    ):
        _fail("V99 campaign identity inventory changed")
    totals = {
        "meta_activation": 0,
        "no_prior_activation": 0,
        "meta_labels": 0,
        "no_prior_labels": 0,
        "direct_labels": 0,
        "passed": 0,
    }
    failed = []
    for occurrence, (family, seed) in zip(occurrences, TARGETS, strict=True):
        _check_v99_id(
            occurrence,
            "occurrence_id",
            domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_OCCURRENCE_V99_DOMAIN,
        )
        partial = occurrence.get("common_partial_acquisition")
        meta = _check_sequence(
            occurrence["meta_prior_persistent_sequence"],
            family=family,
            seed=seed,
            partial=partial,
            prior=True,
        )
        no_prior = _check_sequence(
            occurrence["no_structure_prior_persistent_sequence"],
            family=family,
            seed=seed,
            partial=partial,
            prior=False,
        )
        direct = occurrence["strict_cold_direct_sequence"][
            "lifetime_target_ground_support_labels"
        ]
        expected_exercised = meta[3] > 0 and meta[4] > 0
        expected_gate = {
            "meta_model_activated": True,
            "retained_model_covers_every_residual_target": True,
            "model_activation_strictly_earlier_than_no_prior": meta[1] < no_prior[1],
            "agreement_shield_exercised": expected_exercised,
            "persistent_agreement_shielded_abstract_planning_used": meta[5] > 0,
            "meta_task_labels_noninferior_to_no_prior": meta[0] <= no_prior[0],
            "meta_task_labels_strictly_below_cold_direct": meta[0] < direct,
            "certificate_failure_only_query_discipline_clean": True,
        }
        expected_gate["passed"] = all(expected_gate.values())
        if (
            occurrence.get("registered_gate") != expected_gate
            or occurrence.get("post_dependency_candidate_count") != meta[2]
            or occurrence.get("cross_family_structure_transfer") is not True
            or occurrence.get("abstract_model_used_only_after_partial_agreement")
            is not True
            or occurrence.get("abstract_or_partial_model_used_as_safety_authority")
            is not False
            or occurrence.get("persistent_exact_overlay_exclusively_used_for_safety")
            is not True
            or occurrence.get("complete_world_model_synthesized") is not False
        ):
            _fail("V99 occurrence Gate or claim boundary changed")
        accounting = occurrence.get("accounting")
        if (
            accounting.get("meta_model_activation_target_labels_with_right_censoring")
            != meta[1]
            or accounting.get("no_prior_model_activation_target_labels_with_right_censoring")
            != no_prior[1]
            or accounting.get("meta_lifetime_target_labels") != meta[0]
            or accounting.get("no_prior_lifetime_target_labels") != no_prior[0]
            or accounting.get("strict_cold_direct_lifetime_target_labels") != direct
            or accounting.get("meta_first_episode_shield_accept_count") != meta[3]
            or accounting.get("meta_first_episode_shield_disagreement_abstention_count")
            != meta[4]
            or accounting.get("scalar_cost_aggregation_performed") is not False
        ):
            _fail("V99 occurrence accounting changed")
        totals["meta_activation"] += meta[1]
        totals["no_prior_activation"] += no_prior[1]
        totals["meta_labels"] += meta[0]
        totals["no_prior_labels"] += no_prior[0]
        totals["direct_labels"] += direct
        totals["passed"] += expected_gate["passed"]
        if not expected_gate["passed"]:
            failed.append((family, seed, meta[3], meta[4], meta[5]))
    ood = document.get("incompatible_schema_no_transfer_control")
    if (
        type(ood) is not dict
        or ood.get("control_id")
        != _generic_id(
            b"acfqp:incompatible-schema-no-transfer-control:v99\x00",
            {key: value for key, value in ood.items() if key != "control_id"},
        )
        or ood.get("strict_ood_no_transfer") is not True
        or ood.get("learned_structure_prior_delivered") is not False
        or ood.get("target_outcomes_accessed") is not False
    ):
        _fail("V99 incompatible-schema no-transfer control changed")
    if (
        totals
        != {
            "meta_activation": 175,
            "no_prior_activation": 199,
            "meta_labels": 320,
            "no_prior_labels": 320,
            "direct_labels": 558,
            "passed": 3,
        }
        or failed != [("BALANCED_BATCH_REFINEMENT", 1_005_101, 0, 16, 2)]
        or document.get("registered_gate", {}).get("passed") is not False
        or document.get("registered_gate", {}).get("passed_target_occurrence_count")
        != 3
        or document.get("registered_gate", {}).get(
            "aggregate_model_activation_sample_tax_strictly_reduced"
        )
        is not True
        or document.get("registered_gate", {}).get("aggregate_negative_transfer_absent")
        is not True
        or document.get("registered_gate", {}).get(
            "strict_incompatible_schema_no_transfer_verified"
        )
        is not True
        or document.get("cross_family_structure_transfer_with_target_bindings_rederived")
        is not False
        or document.get("agreement_shield_prevented_observed_aggregate_negative_transfer")
        is not False
        or document.get("structural_prior_model_activation_sample_tax_advantage_verified")
        is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V99 registered failure or aggregate claims changed")
    return {
        "schema": "acfqp.agreement_shielded_verification.v99",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verification_status": "REGISTERED_AGREEMENT_SHIELDED_PATH_COVERAGE_FAILURE_VERIFIED",
        "verified_aggregate_evidence": {
            **totals,
            "activation_label_reduction": 24,
            "negative_transfer_label_delta": 0,
            "failed_occurrence": {
                "target_family": failed[0][0],
                "seed": failed[0][1],
                "first_episode_agreement_accept_count": failed[0][2],
                "first_episode_disagreement_abstention_count": failed[0][3],
                "later_agreement_accept_count": failed[0][4],
            },
            "all_axes_separate": True,
        },
        "shield_receipts_independently_replayed": True,
        "dependency_programs_checked_against_raw_successors": True,
        "failure_is_preregistered_first_episode_path_coverage_only": True,
        "aggregate_activation_tax_reduction_verified": True,
        "aggregate_negative_transfer_absent_verified": True,
        "registered_v99_gate_passed": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def verify_agreement_shielded_campaign_bytes_v99(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V99 campaign bytes differ from the frozen failure")
    document = loads_canonical_json(raw)
    if canonical_json_bytes(document) != raw:
        _fail("V99 campaign bytes are not canonical")
    return _verify_campaign_document(document)


def freeze_agreement_shielded_verification_v99(raw: bytes) -> bytes:
    payload = verify_agreement_shielded_campaign_bytes_v99(raw)
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v99(
            domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_VERIFICATION_V99_DOMAIN,
            payload,
        ),
    }
    result = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V99 frozen verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "freeze_agreement_shielded_verification_v99",
    "verify_agreement_shielded_campaign_bytes_v99",
)
