"""Producer-free raw-evidence verifier for the frozen V61 campaign."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains_v59
from acfqp import construction_k7_domain_registry_extension_v61 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "8f0adc8821a7a5c1de892cdec14af67102c3d6fb8351611210e9493812d1f6ab"
CAMPAIGN_BYTE_COUNT = 9_318_414
CAMPAIGN_SHA256 = "4f7a087c511d3b3e38c8e7a8931a3a157e931115b84c9ee451941acfeda08e27"
PREREGISTRATION_ID = "b0d27cf87f48e5d2439e14279d8258fc52ca5cfb37c0cc1ed5f39fd4e103766c"
V60_CAMPAIGN_ID = "abb8c1dab6a8dd1599617dfd9927f741259e93102b06bdb650c849103aa5ff8c"
V60_VERIFICATION_ID = "d3a425b2f280ecd619a8aa8be2d41128ccc50acc7bc3c7038bd796645077e5c2"
VERIFICATION_ID = "5c5a1b9404a51b88d0decb24704c6bb493719e89c128811d016016fad7134399"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_245
EXPECTED_VERIFICATION_SHA256 = "0a6858c2c5ed40863984227e190a3a270c8361b2d437821476d8f7d0a543b645"


class ConstructionK7PersistentOverlayIndependentVerifierV61Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentOverlayIndependentVerifierV61Error(message)


def _content(document: Any, key: str, domain: str, function: Any) -> None:
    if type(document) is not dict:
        _fail(f"V61 {key} document shape changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != function(domain, payload):
        _fail(f"V61 {key} identity changed")


def _rows(batches: Any) -> list[dict[str, Any]]:
    if type(batches) is not list or not batches or any(type(batch) is not list for batch in batches):
        _fail("V61 raw batch inventory changed")
    rows = [row for batch in batches for row in batch]
    for row in rows:
        if (
            type(row) is not dict
            or set(row) != {
                "occurrence",
                "transition_index",
                "pre_vector",
                "legal_action_keys_before",
                "selected_action",
                "post_vector",
                "legal_action_keys_after",
                "terminal_acceptance_after",
                "outcome_tape_sha256",
            }
            or type(row["pre_vector"]) is not list
            or type(row["post_vector"]) is not list
            or len(row["pre_vector"]) != len(row["post_vector"])
            or type(row["selected_action"]) is not dict
            or row["selected_action"].get("action_key") not in row["legal_action_keys_before"]
            or (row["legal_action_keys_after"] and row["terminal_acceptance_after"] is not None)
            or (not row["legal_action_keys_after"] and type(row["terminal_acceptance_after"]) is not bool)
        ):
            _fail("V61 raw transition semantics changed")
    return rows


def _partial_factor_replay(acquisition: Mapping[str, Any], rows: list[dict[str, Any]]) -> int:
    candidate = acquisition["predecessor_acquisition"].get("candidate")
    if type(candidate) is not dict:
        _fail("V61 partial candidate is absent")
    _content(candidate, "candidate_id", domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN, domains_v59.extension_content_id_v59)
    layout = candidate.get("layout")
    state_order = layout.get("state_canonical_to_raw") if type(layout) is dict else None
    action_order = layout.get("action_canonical_to_raw") if type(layout) is dict else None
    assignments = candidate.get("compiled_factor_assignments")
    if type(assignments) is not list or type(state_order) is not list or type(action_order) is not list:
        _fail("V61 partial layout or assignments changed")
    targets = []
    for assignment in assignments:
        target = assignment.get("target_column")
        expression = assignment.get("expression")
        targets.append(target)
        for row in rows:
            pre = [row["pre_vector"][index] for index in state_order]
            post = [row["post_vector"][index] for index in state_order]
            action = [row["selected_action"]["anonymous_fields"][index] for index in action_order]
            if expression[0] == "E00":
                support = (pre[expression[1]],)
            elif expression[0] == "E01":
                support = (action[expression[1]],)
            elif expression[0] == "E07":
                base = pre[expression[1][1]]
                delta = action[expression[2][2][1]]
                support = tuple(sorted({base, base + delta}))
            else:
                _fail("V61 partial expression escaped its generic fragment")
            if post[target] not in support:
                _fail("V61 raw transition refuted its partial factor")
    if candidate.get("unknown_residual_target_columns") != sorted(
        set(range(candidate.get("state_width", -1))) - set(targets)
    ):
        _fail("V61 residual target complement changed")
    return len(assignments)


def _verify_acquisition(acquisition: Any, arm: str, evidence: Mapping[str, Any]) -> tuple[list[list[Any]], int, int]:
    _content(acquisition, "acquisition_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_ACQUISITION_V61_DOMAIN, domains.extension_content_id_v61)
    predecessor = acquisition.get("predecessor_acquisition")
    _content(predecessor, "acquisition_id", domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN, domains_v59.extension_content_id_v59)
    batches = acquisition.get("raw_transition_batches")
    rows = _rows(batches)
    labels = acquisition.get("ground_support_labels")
    if (
        acquisition.get("arm") != arm
        or acquisition.get("raw_evidence_id") != evidence.get("raw_evidence_id")
        or len(batches) != labels
        or batches != evidence["raw_transition_batches"][:labels]
        or acquisition.get("raw_transition_count") != len(rows)
        or acquisition.get("raw_transition_sha256") != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or predecessor.get("raw_transition_sha256") != acquisition.get("raw_transition_sha256")
        or predecessor.get("terminal_stop_update", {}).get("stopped") is not True
        or acquisition.get("reachable_frontier_exhaustion_input_consumed") is not False
    ):
        _fail("V61 acquisition/raw-evidence join changed")
    factor_count = _partial_factor_replay(acquisition, rows) if arm == "ANONYMOUS_FACTOR_PRIOR_ON" else 0
    return batches, len(rows), factor_count


def _verify_evidence_pair(certificate: Any, distinction: Any) -> list[dict[str, Any]]:
    _content(certificate, "failed_certificate_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_CERTIFICATE_V61_DOMAIN, domains.extension_content_id_v61)
    _content(distinction, "local_distinction_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_DISTINCTION_V61_DOMAIN, domains.extension_content_id_v61)
    failure = certificate.get("failure")
    ground = distinction.get("distinction")
    if (
        distinction.get("failed_certificate_id") != certificate.get("failed_certificate_id")
        or type(failure) is not dict
        or type(ground) is not dict
        or failure.get("failure_index") != ground.get("failure_index")
        or failure.get("ground_query_performed_before_failure") is not False
        or ground.get("query_after_failed_certificate") is not True
        or failure.get("raw_state") != ground.get("raw_state")
        or failure.get("action_key") != ground.get("action_key")
        or ground.get("ground_support_labels") != 1
    ):
        _fail("V61 certificate-before-query join changed")
    raw_rows = ground.get("raw_transition_rows", [])
    if ground.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
        if type(raw_rows) is not list or not raw_rows:
            _fail("V61 residual distinction omitted raw rows")
        _rows([raw_rows])
        if any(
            row["pre_vector"] != failure["raw_state"]
            or row["selected_action"]["action_key"] != failure["action_key"]
            for row in raw_rows
        ):
            _fail("V61 local row does not answer its certificate")
    elif ground.get("distinction_kind") != "QUERY_LOCAL_LEGAL_ACTION_SET" or "raw_transition_rows" in ground:
        _fail("V61 local distinction kind changed")
    return raw_rows


def _verify_episode(episode: Any, mode: str, acquisition_id: str) -> tuple[list[Any], list[Any], int, list[Any]]:
    _content(episode, "episode_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_EPISODE_V61_DOMAIN, domains.extension_content_id_v61)
    certificates = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        episode.get("mode") != mode
        or episode.get("acquisition_id") != acquisition_id
        or episode.get("success") is not True
        or type(certificates) is not list
        or type(distinctions) is not list
        or len(certificates) != len(distinctions)
    ):
        _fail("V61 episode identity or success changed")
    rows = []
    for certificate, distinction in zip(certificates, distinctions, strict=True):
        if certificate.get("mode") != mode or certificate.get("episode_index") != episode.get("episode_index"):
            _fail("V61 evidence episode projection changed")
        rows.extend(_verify_evidence_pair(certificate, distinction))
    label_key = "new_local_ground_support_labels" if mode == "PERSISTENT_OVERLAY" else "local_ground_support_labels"
    if episode.get(label_key) != len(distinctions):
        _fail("V61 episode label accounting changed")
    return certificates, distinctions, len(distinctions), rows


def _verify_run(run: Any, acquisition_id: str) -> tuple[int, int, int, int, int, int, int]:
    _content(run, "run_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_RUN_V61_DOMAIN, domains.extension_content_id_v61)
    persistent = run.get("persistent_episodes")
    cold = run.get("cold_restart_episodes")
    if (
        type(persistent) is not list
        or type(cold) is not list
        or len(persistent) != 3
        or len(cold) != 3
        or [row.get("episode_index") for row in persistent] != [0, 1, 2]
        or [row.get("episode_index") for row in cold] != [0, 1, 2]
    ):
        _fail("V61 matched episode inventory changed")
    persistent_certificates = []
    persistent_distinctions = []
    cold_certificates = []
    cold_distinctions = []
    overlay_rows = []
    persistent_labels = cold_labels = 0
    for episode in persistent:
        certificates, distinctions, labels, rows = _verify_episode(episode, "PERSISTENT_OVERLAY", acquisition_id)
        persistent_certificates.extend(certificates)
        persistent_distinctions.extend(distinctions)
        persistent_labels += labels
        overlay_rows.extend(rows)
    for episode in cold:
        certificates, distinctions, labels, _rows_local = _verify_episode(episode, "COLD_RESTART", acquisition_id)
        cold_certificates.extend(certificates)
        cold_distinctions.extend(distinctions)
        cold_labels += labels
    if (
        run.get("persistent_failed_certificates") != persistent_certificates
        or run.get("persistent_local_distinctions") != persistent_distinctions
        or run.get("cold_failed_certificates") != cold_certificates
        or run.get("cold_local_distinctions") != cold_distinctions
        or run.get("persistent_overlay_raw_transition_rows") != overlay_rows
        or run.get("persistent_local_ground_support_labels") != persistent_labels
        or run.get("cold_restart_local_ground_support_labels") != cold_labels
        or run.get("amortized_query_label_reduction") != cold_labels - persistent_labels
        or cold_labels <= persistent_labels
        or persistent[0]["new_local_ground_support_labels"] <= 0
        or any(row["new_local_ground_support_labels"] != 0 for row in persistent[1:])
        or run.get("later_episode_ground_query_count") != 0
        or [row["action_keys"] for row in persistent] != [row["action_keys"] for row in cold]
        or [row["outcome_tape_sha256"] for row in persistent] != [row["outcome_tape_sha256"] for row in cold]
        or run.get("only_switched_variable") != "OCCURRENCE_LOCAL_PROOF_OVERLAY_PERSISTENCE"
        or run.get("occurrence_identity_bound") is not True
        or run.get("cross_occurrence_ground_fact_reuse_allowed") is not False
        or run.get("complete_residual_world_model_synthesized") is not False
        or run.get("success") is not True
    ):
        _fail("V61 matched persistent-overlay Gate changed")
    return (
        persistent_labels,
        cold_labels,
        len(overlay_rows),
        sum(row["execution_steps"] for row in persistent),
        sum(row["execution_steps"] for row in cold),
        sum(row["new_abstract_planning_compute_events"] for row in persistent),
        sum(row["abstract_planning_compute_events"] for row in cold),
    )


def verify_persistent_overlay_campaign_bytes_v61(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V61 campaign bytes changed type")
    if CAMPAIGN_ID != "0" * 64 and (
        len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V61 frozen campaign byte envelope changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V61 campaign is not canonical JSON")
    _content(document, "campaign_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_CAMPAIGN_V61_DOMAIN, domains.extension_content_id_v61)
    if (
        (CAMPAIGN_ID != "0" * 64 and document.get("campaign_id") != CAMPAIGN_ID)
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v60_campaign_id") != V60_CAMPAIGN_ID
        or document.get("v60_verification_id") != V60_VERIFICATION_ID
    ):
        _fail("V61 campaign predecessor join changed")
    occurrences = document.get("occurrences")
    expected = [
        (family, seed)
        for family, start in (
            ("BALANCED_BATCH_REFINEMENT", 601_101),
            ("COUPLED_EXCHANGE", 602_101),
            ("MAINTENANCE_CASCADE", 603_101),
        )
        for seed in range(start, start + 4)
    ]
    if type(occurrences) is not list or [(row.get("family"), row.get("seed")) for row in occurrences] != expected:
        _fail("V61 occurrence identity inventory changed")
    persistent_labels = cold_labels = raw_rows = factor_assignments = local_rows = 0
    persistent_steps = cold_steps = persistent_compute = cold_compute = 0
    acquisition_labels = 0
    family_totals: dict[str, list[int]] = {}
    for occurrence in occurrences:
        evidence = occurrence.get("raw_evidence")
        _content(evidence, "raw_evidence_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_RAW_EVIDENCE_V61_DOMAIN, domains.extension_content_id_v61)
        evidence_rows = _rows(evidence.get("raw_transition_batches"))
        if evidence.get("maximum_observed_label_count") != len(evidence["raw_transition_batches"]) or evidence.get("generation_witness_present") is not False:
            _fail("V61 raw evidence contract changed")
        arms = occurrence.get("acquisitions")
        if type(arms) is not dict or set(arms) != {"ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"}:
            _fail("V61 acquisition arm inventory changed")
        prior_batches, prior_count, factors = _verify_acquisition(arms["ANONYMOUS_FACTOR_PRIOR_ON"], "ANONYMOUS_FACTOR_PRIOR_ON", evidence)
        strict_batches, strict_count, _ = _verify_acquisition(arms["STRICT_NO_PRIOR"], "STRICT_NO_PRIOR", evidence)
        common = min(len(prior_batches), len(strict_batches))
        if prior_batches[:common] != strict_batches[:common] or len(evidence["raw_transition_batches"]) != max(len(prior_batches), len(strict_batches)):
            _fail("V61 symmetric raw prefix changed")
        result = _verify_run(occurrence.get("run"), arms["ANONYMOUS_FACTOR_PRIOR_ON"]["acquisition_id"])
        p_labels, c_labels, local_count, p_steps, c_steps, p_compute, c_compute = result
        persistent_labels += p_labels
        cold_labels += c_labels
        local_rows += local_count
        persistent_steps += p_steps
        cold_steps += c_steps
        persistent_compute += p_compute
        cold_compute += c_compute
        raw_rows += len(evidence_rows)
        factor_assignments += factors
        acquisition_labels += arms["ANONYMOUS_FACTOR_PRIOR_ON"]["ground_support_labels"] + arms["STRICT_NO_PRIOR"]["ground_support_labels"]
        totals = family_totals.setdefault(occurrence["family"], [0, 0])
        totals[0] += p_labels
        totals[1] += c_labels
    sample = document.get("sample_tax")
    _content(sample, "sample_tax_id", domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_SAMPLE_TAX_V61_DOMAIN, domains.extension_content_id_v61)
    if (
        sample.get("persistent_overlay_local_labels") != persistent_labels
        or sample.get("cold_restart_local_labels") != cold_labels
        or sample.get("amortized_query_label_reduction") != cold_labels - persistent_labels
        or cold_labels <= persistent_labels
        or sample.get("same_partial_model_same_episodes_same_outcome_tapes") is not True
        or sample.get("only_switched_variable") != "OCCURRENCE_LOCAL_PROOF_OVERLAY_PERSISTENCE"
        or sample.get("official_break_even_claimed") is not False
    ):
        _fail("V61 sample-tax total changed")
    for family, (persistent, cold) in family_totals.items():
        if sample["family_projections"].get(family) != {
            "occurrence_count": 4,
            "episode_count": 12,
            "persistent_overlay_local_labels": persistent,
            "cold_restart_local_labels": cold,
            "amortized_query_label_reduction": cold - persistent,
        } or cold <= persistent:
            _fail("V61 family sample-tax projection changed")
    accounting = document.get("accounting")
    if (
        accounting.get("acquisition_target_labels") != acquisition_labels
        or accounting.get("persistent_overlay_local_labels") != persistent_labels
        or accounting.get("cold_restart_local_labels") != cold_labels
        or accounting.get("persistent_execution_steps") != persistent_steps
        or accounting.get("cold_restart_execution_steps") != cold_steps
        or accounting.get("persistent_planning_compute_events") != persistent_compute
        or accounting.get("cold_restart_planning_compute_events") != cold_compute
        or accounting.get("all_axes_separate") is not True
    ):
        _fail("V61 accounting axes changed")
    locks = {
        "raw_transition_bytes_embedded_for_producer_free_replay": True,
        "all_ground_queries_followed_failed_certificates": True,
        "occurrence_bound_persistent_overlay_used": True,
        "cross_occurrence_ground_fact_reuse_allowed": False,
        "complete_residual_world_model_synthesized": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V61 claim lock changed")
    payload = {
        "schema": "acfqp.persistent_overlay_independent_verification.v61",
        "campaign_id": document["campaign_id"],
        "campaign_byte_count": len(raw),
        "campaign_sha256": hashlib.sha256(raw).hexdigest(),
        "occurrence_count": 12,
        "episode_count_per_arm": 36,
        "raw_transition_row_count_replayed": raw_rows,
        "partial_factor_assignment_count_replayed": factor_assignments,
        "persistent_overlay_raw_transition_row_count_replayed": local_rows,
        "persistent_overlay_local_labels": persistent_labels,
        "cold_restart_local_labels": cold_labels,
        "amortized_query_label_reduction": cold_labels - persistent_labels,
        "raw_prefix_partial_factor_and_overlay_semantics_independently_replayed": True,
        "certificate_before_query_order_independently_replayed": True,
        "matched_action_and_outcome_tapes_independently_replayed": True,
        "all_content_ids_and_accounting_independently_recomputed": True,
        "producer_campaign_core_or_planner_imported": False,
        "complete_residual_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "outcome": "PRODUCER_FREE_PERSISTENT_QUERY_LOCAL_OVERLAY_VERIFIED",
    }
    result = {
        **payload,
        "verification_id": domains.extension_content_id_v61(
            domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_VERIFICATION_V61_DOMAIN,
            payload,
        ),
    }
    verification_raw = canonical_json_bytes(result)
    if VERIFICATION_ID != "0" * 64 and (
        result["verification_id"] != VERIFICATION_ID
        or len(verification_raw) != EXPECTED_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != EXPECTED_VERIFICATION_SHA256
    ):
        _fail("frozen V61 independent verification changed")
    return result


__all__ = ("verify_persistent_overlay_campaign_bytes_v61",)
