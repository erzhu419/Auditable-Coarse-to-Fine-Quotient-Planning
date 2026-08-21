"""Producer-free verification of the successful V102 campaign."""

from __future__ import annotations
import hashlib
from typing import Any, Mapping, NoReturn
from acfqp import construction_k7_agreement_shielded_independent_verifier_v99 as v99
from acfqp import construction_k7_domain_registry_extension_v100 as d100
from acfqp import construction_k7_domain_registry_extension_v101 as d101
from acfqp import construction_k7_domain_registry_extension_v102 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json

CAMPAIGN_ID = "f0b45ab4a6466988ac6cef39bd2723869d7bb3d4409afc60b9d00e035609d3d7"
CAMPAIGN_BYTE_COUNT = 4_755_021
CAMPAIGN_SHA256 = "116d325ac9e2aa5f8cf34278fe97736b54a52586c5d6b5138d932644dc592a25"
PREREGISTRATION_ID = "961025ca99438c31ecedaf33431f8ec95817f1b1d99fe9edda4886a8e1395ba2"
V101_CAMPAIGN_ID = "f6cafbcdb148095f351202764d97550b1fda115e290dd8de3f205f62762ae155"
V101_VERIFICATION_ID = "a367b1c2f73096b7436527767d0f72eec1d605221ceb31618364c86866747e13"
TARGETS = (("BALANCED_BATCH_REFINEMENT", 1_013_101), ("BALANCED_BATCH_REFINEMENT", 1_013_102), ("MAINTENANCE_CASCADE", 1_013_103), ("MAINTENANCE_CASCADE", 1_013_104))
EPISODES = (111, 112, 113)
VERIFICATION_ID = "21cc3100d7caf82d6802a72899593a78d7fafec0524c285c53cec0cb9f42d00b"
EXPECTED_CANONICAL_BYTE_COUNT = 2_940
EXPECTED_CANONICAL_SHA256 = "1993fbecea9ac2ac39a2ecb3f1e702fe8e78f0a1540ceab6050430c1985f477a"


class ConstructionK7FamilyWideUtilizationIndependentVerifierV102Error(ValueError): pass
def _fail(message: str) -> NoReturn: raise ConstructionK7FamilyWideUtilizationIndependentVerifierV102Error(message)


def _id(doc: Any, key: str, domain: str, fn: Any) -> None:
    if type(doc) is not dict or doc.get(key) != fn(domain, {k: v for k, v in doc.items() if k != key}): _fail(f"V102 {key} identity changed")


def _shield_counts(sequence: Mapping[str, Any]) -> tuple[int, int]:
    first = sequence["first_agreement_shielded_online_episode"]
    v99._check_generic_id(first, "episode_id", v99._FIRST_EPISODE_DOMAIN)
    accept = disagree = 0
    for wrapper in first["agreement_shield_receipts"]:
        a, d = v99._check_shield(wrapper["shield"]); accept += a; disagree += d
    if (accept, disagree) != (first["agreement_shield_accept_count"], first["agreement_shield_disagreement_abstention_count"]): _fail("V102 first shield count changed")
    later_a = later_d = 0
    for episode, index in zip(sequence["later_persistent_episodes"], EPISODES[1:], strict=True):
        extras = {"new_certificate_labels_charged_this_episode", "paid_certificate_labels_cumulative", "persistent_exact_support_group_count"}
        payload = {k: v for k, v in episode.items() if k != "episode_id" and k not in extras}
        if episode["episode_id"] != v99._generic_id(v99._PRELOADED_EPISODE_DOMAIN, payload) or episode["episode_index"] != index: _fail("V102 later episode identity changed")
        v99._check_pairing(episode)
        for receipt in episode["abstract_plan_receipts"]:
            a, d = v99._check_shield(receipt["abstract_plan"]["agreement_shield_receipt"]); later_a += a; later_d += d
    if later_a != sequence["later_agreement_shield_accept_receipt_count"] or later_d != sequence["later_agreement_shield_disagreement_abstention_count"]: _fail("V102 later shield count changed")
    return accept + later_a, disagree + later_d


def _util(sequence: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    first = sequence["first_agreement_shielded_online_episode"]; later_matches = later_steps = 0
    for episode in sequence["later_persistent_episodes"]:
        values = episode["execution_action_matches_abstract_proposal"]
        if any(type(x) is not bool for x in values) or len(values) != episode["execution_steps"] or sum(values) != episode["execution_action_matches_abstract_proposal_count"]: _fail("V102 execution receipts changed")
        later_matches += sum(values); later_steps += len(values)
    if later_matches != sequence["later_execution_action_matches_abstract_proposal_count"]: _fail("V102 later execution total changed")
    first_m = first["shielded_joint_execution_action_match_count"]; first_s = first["execution_steps"]; matches = first_m + later_matches; steps = first_s + later_steps
    return ({"schema": "acfqp.abstract_execution_utilization.v101", "first_episode_abstract_execution_match_count": first_m, "later_episode_abstract_execution_match_count": later_matches, "persistent_sequence_abstract_execution_match_count": matches, "first_episode_execution_step_count": first_s, "later_episode_execution_step_count": later_steps, "persistent_sequence_execution_step_count": steps, "abstract_execution_match_fraction_numerator": matches, "abstract_execution_match_fraction_denominator": steps, "strict_majority_of_executed_actions_match_abstract_proposal": steps > 0 and 2 * matches > steps, "match_requires_abstract_partial_exact_action_agreement": True, "abstract_proposal_used_only_for_action_ordering": True, "query_local_exact_overlay_remains_only_safety_authority": True}, later_matches)


def _verify(doc: Any) -> dict[str, Any]:
    _id(doc, "campaign_id", domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_CAMPAIGN_V102_DOMAIN, domains.extension_content_id_v102)
    rows = doc.get("target_occurrences")
    if doc.get("schema") != "acfqp.family_wide_abstract_utilization_campaign.v102" or doc.get("campaign_id") != CAMPAIGN_ID or doc.get("preregistration_id") != PREREGISTRATION_ID or doc.get("v101_failed_campaign_id") != V101_CAMPAIGN_ID or doc.get("v101_failure_verification_id") != V101_VERIFICATION_ID or [(x.get("target_family"), x.get("seed")) for x in rows] != list(TARGETS): _fail("V102 campaign inventory changed")
    totals = {k: 0 for k in ("meta_activation", "no_prior_activation", "meta_labels", "no_prior_labels", "direct_labels", "meta_abstract_execution_match_count", "meta_execution_step_count")}; family = {}; lower = []
    for row, (name, seed) in zip(rows, TARGETS, strict=True):
        _id(row, "occurrence_id", domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_OCCURRENCE_V102_DOMAIN, domains.extension_content_id_v102)
        o101 = row["frozen_v101_measurement_observation"]; _id(o101, "occurrence_id", d101.CONSTRUCTION_K7_ABSTRACT_EXECUTION_UTILIZATION_OCCURRENCE_V101_DOMAIN, d101.extension_content_id_v101)
        o100 = o101["frozen_v100_sequence_wide_observation"]; _id(o100, "occurrence_id", d100.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_OCCURRENCE_V100_DOMAIN, d100.extension_content_id_v100)
        alg = o100["frozen_v99_algorithm_observation"]; v99._check_v99_id(alg, "occurrence_id", v99.domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_OCCURRENCE_V99_DOMAIN)
        if row["target_family"] != name or row["seed"] != seed or row["episode_indices"] != list(EPISODES): _fail("V102 occurrence join changed")
        meta = alg["meta_prior_persistent_sequence"]; no = alg["no_structure_prior_persistent_sequence"]
        if meta["every_new_ground_query_followed_a_failed_certificate"] is not True or meta["persistent_exact_overlay_exclusively_discharges_safety"] is not True: _fail("V102 safety discipline changed")
        util, later = _util(meta); no_util, _ = _util(no); accepts, disagreements = _shield_counts(meta)
        if o101["meta_prior_abstract_execution_utilization"] != util or o101["no_prior_abstract_execution_utilization"] != no_util or row["accept_path_count_for_family_aggregation"] != accepts or row["disagreement_path_count_for_family_aggregation"] != disagreements: _fail("V102 measurement changed")
        expected = {"abstract_ordering_matches_strict_majority_of_executed_actions": util["strict_majority_of_executed_actions_match_abstract_proposal"], "abstract_execution_match_rate_noninferior_to_no_prior": util["abstract_execution_match_fraction_numerator"] * no_util["abstract_execution_match_fraction_denominator"] >= no_util["abstract_execution_match_fraction_numerator"] * util["abstract_execution_match_fraction_denominator"], "abstract_accept_path_observed": accepts > 0, "certificate_failure_only_query_discipline_clean": True, "exact_overlay_exclusively_discharges_safety": True}; expected["passed"] = all(expected.values())
        if row["registered_gate"] != expected or not expected["passed"] or row["complete_world_model_synthesized"] is not False: _fail("V102 occurrence Gate changed")
        a = alg["accounting"]
        for key, source in (("meta_activation", "meta_model_activation_target_labels_with_right_censoring"), ("no_prior_activation", "no_prior_model_activation_target_labels_with_right_censoring"), ("meta_labels", "meta_lifetime_target_labels"), ("no_prior_labels", "no_prior_lifetime_target_labels"), ("direct_labels", "strict_cold_direct_lifetime_target_labels")): totals[key] += a[source]
        totals["meta_abstract_execution_match_count"] += util["persistent_sequence_abstract_execution_match_count"]; totals["meta_execution_step_count"] += util["persistent_sequence_execution_step_count"]
        f = family.setdefault(name, [0, 0]); f[0] += accepts; f[1] += disagreements
        lower.append({"target_family": name, "seed": seed, "later_episode_independently_replayed_match_count": later, "total_sequence_execution_step_count": util["persistent_sequence_execution_step_count"], "later_episode_lower_bound_alone_is_strict_majority": 2 * later > util["persistent_sequence_execution_step_count"]})
    expected_totals = {"meta_activation": 173, "no_prior_activation": 200, "meta_labels": 334, "no_prior_labels": 334, "direct_labels": 540, "meta_abstract_execution_match_count": 45, "meta_execution_step_count": 72}
    coverage = [{"target_family": name, "occurrence_count": 2, "accept_count": family[name][0], "disagreement_abstention_count": family[name][1], "both_shield_paths_observed_across_family": family[name][0] > 0 and family[name][1] > 0} for name in sorted(family)]
    if totals != expected_totals or doc["family_wide_shield_path_coverage"] != coverage or doc["registered_gate"]["passed"] is not True or doc["registered_gate"]["passed_target_occurrence_count"] != 4 or doc["accounting"] != {**expected_totals, "offline_source_labels_not_recharged": True, "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True, "scalar_cost_aggregation_performed": False} or doc["registered_multistep_execution_primarily_abstract_ordered_verified"] is not True or doc["complete_world_model_synthesized"] is not False or doc["official_scalar_cost"] is not None or doc["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN": _fail("V102 aggregate evidence changed")
    insufficient = [row for row in lower if row["later_episode_lower_bound_alone_is_strict_majority"] is False]
    if [(row["target_family"], row["seed"]) for row in insufficient] != [("MAINTENANCE_CASCADE", 1_013_103), ("MAINTENANCE_CASCADE", 1_013_104)]: _fail("V102 independent evidence insufficiency inventory changed")
    if 2 * sum(row["later_episode_independently_replayed_match_count"] for row in lower) <= totals["meta_execution_step_count"]: _fail("V102 aggregate producer-free utilization lower bound changed")
    return {"schema": "acfqp.family_wide_utilization_verification.v102", "campaign_id": CAMPAIGN_ID, "preregistration_id": PREREGISTRATION_ID, "verification_status": "REGISTERED_V102_PER_OCCURRENCE_UTILIZATION_EVIDENCE_INCOMPLETE", "verified_aggregate_evidence": {**totals, "activation_label_reduction": 27, "producer_free_later_episode_match_lower_bound_rows": lower, "producer_free_aggregate_later_episode_match_lower_bound_is_majority": True, "family_wide_shield_path_coverage": coverage, "all_axes_separate": True}, "campaign_declared_registered_gate_passed": True, "registered_v102_gate_independently_verified": False, "missing_evidence": {"kind": "FIRST_EPISODE_PER_EXECUTION_ABSTRACT_MATCH_RECEIPTS", "affected_occurrences": insufficient, "fresh_successor_required": True}, "ground_distinctions_only_after_certificate_failure_verified": True, "complete_world_model_synthesized": False, "official_execution_allowed": False, "official_scalar_cost": None, "official_N_break_even": None, "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN"}


def verify_family_wide_utilization_campaign_bytes_v102(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) != CAMPAIGN_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256: _fail("V102 campaign bytes changed")
    doc = loads_canonical_json(raw)
    if canonical_json_bytes(doc) != raw: _fail("V102 campaign is noncanonical")
    return _verify(doc)


def freeze_family_wide_utilization_verification_v102(raw: bytes) -> bytes:
    payload = verify_family_wide_utilization_campaign_bytes_v102(raw); doc = {**payload, "verification_id": domains.extension_content_id_v102(domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_VERIFICATION_V102_DOMAIN, payload)}; result = canonical_json_bytes(doc)
    if VERIFICATION_ID != "0" * 64 and (doc["verification_id"] != VERIFICATION_ID or len(result) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256): _fail("V102 verification changed")
    return result


__all__ = ("VERIFICATION_ID", "freeze_family_wide_utilization_verification_v102", "verify_family_wide_utilization_campaign_bytes_v102")
