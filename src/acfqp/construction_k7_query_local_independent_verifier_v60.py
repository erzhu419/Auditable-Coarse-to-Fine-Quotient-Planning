"""Producer-free semantic verifier for the frozen V60 campaign.

This module deliberately imports neither the campaign producer nor any model,
planner, adapter, or campaign-core implementation.  It replays the portable
raw-transition prefixes, the reusable partial-factor support semantics, the
certificate-before-query ordering, and every accounting/content-address join
directly from canonical bytes.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v59 as domains_v59
from acfqp import construction_k7_domain_registry_extension_v60 as domains_v60
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "abb8c1dab6a8dd1599617dfd9927f741259e93102b06bdb650c849103aa5ff8c"
CAMPAIGN_BYTE_COUNT = 4_843_044
CAMPAIGN_SHA256 = "820476b0d7a98ea5ea24383996a7b56d3202afdda265ff9f03779201c99ea69c"
PREREGISTRATION_ID = "3e5236983d198c9b491632363836c5088eebd6232bc10a5da94cbac6eaaff834"
V59_CAMPAIGN_ID = "60ecb969f8b2b6cd7aa000d7306c213ab194293fc76a01190c73bae22e8b8d18"
V59_VERIFICATION_ID = "b9b783080837cf9ac2641bf73036363bfe5813f8be1893b114c8fe7ec0f95a8f"
VERIFICATION_ID = "d3a425b2f280ecd619a8aa8be2d41128ccc50acc7bc3c7038bd796645077e5c2"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_534
EXPECTED_VERIFICATION_SHA256 = "1baad5793cc06d8573cd85b9e7ddcc34e848902d253641ad4f0d2de41f4ccf54"


class ConstructionK7QueryLocalIndependentVerifierV60Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryLocalIndependentVerifierV60Error(message)


def _content(
    document: Mapping[str, Any], key: str, domain: str, function: Any
) -> None:
    if type(document) is not dict:
        _fail(f"V60 {key} document shape changed")
    payload = {name: value for name, value in document.items() if name != key}
    if document.get(key) != function(domain, payload):
        _fail(f"V60 {key} content identity changed")


def _row(row: Any) -> None:
    keys = {
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
    if type(row) is not dict or set(row) != keys:
        _fail("V60 raw transition schema changed")
    pre = row["pre_vector"]
    post = row["post_vector"]
    action = row["selected_action"]
    before = row["legal_action_keys_before"]
    after = row["legal_action_keys_after"]
    if (
        type(row["occurrence"]) is not int
        or type(row["transition_index"]) is not int
        or type(pre) is not list
        or type(post) is not list
        or not pre
        or len(pre) != len(post)
        or any(type(value) is not int for value in [*pre, *post])
        or type(action) is not dict
        or set(action) != {"action_key", "anonymous_fields"}
        or type(action["action_key"]) is not int
        or type(action["anonymous_fields"]) is not list
        or not action["anonymous_fields"]
        or any(type(value) is not int for value in action["anonymous_fields"])
        or type(before) is not list
        or type(after) is not list
        or before != sorted(set(before))
        or after != sorted(set(after))
        or action["action_key"] not in before
    ):
        _fail("V60 raw transition semantics changed")
    terminal = row["terminal_acceptance_after"]
    if (after and terminal is not None) or (not after and type(terminal) is not bool):
        _fail("V60 terminal/legality join changed")
    tape = row["outcome_tape_sha256"]
    if tape is not None and (
        type(tape) is not str
        or len(tape) != 64
        or any(char not in "0123456789abcdef" for char in tape)
    ):
        _fail("V60 outcome-tape identity changed")


def _flat(batches: Any) -> list[dict[str, Any]]:
    if type(batches) is not list or not batches or any(type(batch) is not list for batch in batches):
        _fail("V60 raw batch inventory changed")
    result = [row for batch in batches for row in batch]
    if not result:
        _fail("V60 raw transition inventory became empty")
    for row in result:
        _row(row)
    return result


def _aligned(row: Mapping[str, Any], layout: Mapping[str, Any]) -> tuple[list[int], list[int], list[int]]:
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if (
        type(state_order) is not list
        or sorted(state_order) != list(range(len(row["pre_vector"])))
        or type(action_order) is not list
        or sorted(action_order)
        != list(range(len(row["selected_action"]["anonymous_fields"])))
    ):
        _fail("V60 compiled layout is not a pair of permutations")
    return (
        [row["pre_vector"][index] for index in state_order],
        [row["post_vector"][index] for index in state_order],
        [row["selected_action"]["anonymous_fields"][index] for index in action_order],
    )


def _support(expression: Any, pre: list[int], action: list[int]) -> tuple[int, ...]:
    if type(expression) is not list or not expression:
        _fail("V60 partial expression shape changed")
    if expression[0] == "E00" and len(expression) == 2 and type(expression[1]) is int:
        return (pre[expression[1]],)
    if expression[0] == "E01" and len(expression) == 2 and type(expression[1]) is int:
        return (action[expression[1]],)
    if (
        expression[0] == "E07"
        and len(expression) == 3
        and type(expression[1]) is list
        and expression[1][:1] == ["E00"]
        and type(expression[2]) is list
        and len(expression[2]) == 3
        and expression[2][0] == "E05"
        and expression[2][1] == expression[1]
        and type(expression[2][2]) is list
        and expression[2][2][:1] == ["E01"]
    ):
        base = pre[expression[1][1]]
        delta = action[expression[2][2][1]]
        return tuple(sorted({base, base + delta}))
    _fail("V60 partial expression escaped the registered generic fragment")


def _partial_semantics(acquisition: Mapping[str, Any], rows: list[dict[str, Any]]) -> int:
    predecessor = acquisition.get("predecessor_acquisition")
    candidate = predecessor.get("candidate") if type(predecessor) is dict else None
    if type(candidate) is not dict:
        _fail("V60 partial candidate is absent")
    _content(
        candidate,
        "candidate_id",
        domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
        domains_v59.extension_content_id_v59,
    )
    layout = candidate.get("layout")
    assignments = candidate.get("compiled_factor_assignments")
    if (
        type(layout) is not dict
        or acquisition.get("compiled_layout") != layout
        or type(assignments) is not list
        or len(assignments) < candidate.get("minimum_factor_assignment_count", 10**9)
        or candidate.get("target_slot_inventory_supplied_by_prior") is not False
        or candidate.get("target_bindings_derived_from_raw_observations") is not True
        or candidate.get("complete_world_model_claimed") is not False
        or candidate.get("planning_authority_present") is not False
    ):
        _fail("V60 partial-candidate claim boundary changed")
    targets = []
    for assignment in assignments:
        if type(assignment) is not dict or set(assignment) != {
            "target_column",
            "result_type",
            "expression",
            "signature_sha256",
            "state_dependencies",
            "action_dependencies",
        }:
            _fail("V60 partial assignment schema changed")
        target = assignment["target_column"]
        if type(target) is not int:
            _fail("V60 partial target changed")
        targets.append(target)
        for raw in rows:
            pre, post, action = _aligned(raw, layout)
            if target >= len(post) or post[target] not in _support(
                assignment["expression"], pre, action
            ):
                _fail("V60 raw transition refuted its frozen partial factor")
    if len(targets) != len(set(targets)):
        _fail("V60 partial target assignment duplicated")
    unknown = candidate.get("unknown_residual_target_columns")
    if unknown != sorted(set(range(candidate.get("state_width", -1))) - set(targets)):
        _fail("V60 unknown residual projection changed")
    issued = candidate.get("support_label_count_at_issuance")
    if type(issued) is not int or issued <= 0:
        _fail("V60 partial issuance label changed")
    return len(assignments)


def _verify_acquisition(
    acquisition: Any,
    arm: str,
    raw_evidence: Mapping[str, Any],
) -> tuple[list[list[dict[str, Any]]], int]:
    _content(
        acquisition,
        "acquisition_id",
        domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_ACQUISITION_V60_DOMAIN,
        domains_v60.extension_content_id_v60,
    )
    predecessor = acquisition.get("predecessor_acquisition")
    _content(
        predecessor,
        "acquisition_id",
        domains_v59.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
        domains_v59.extension_content_id_v59,
    )
    batches = acquisition.get("raw_transition_batches")
    rows = _flat(batches)
    labels = acquisition.get("ground_support_labels")
    if (
        acquisition.get("arm") != arm
        or acquisition.get("family") != raw_evidence.get("family")
        or acquisition.get("seed") != raw_evidence.get("seed")
        or acquisition.get("raw_evidence_id") != raw_evidence.get("raw_evidence_id")
        or type(labels) is not int
        or len(batches) != labels
        or batches != raw_evidence["raw_transition_batches"][:labels]
        or acquisition.get("raw_transition_count") != len(rows)
        or acquisition.get("raw_transition_sha256")
        != hashlib.sha256(canonical_json_bytes(rows)).hexdigest()
        or predecessor.get("ground_support_labels") != labels
        or predecessor.get("raw_transition_count") != len(rows)
        or predecessor.get("raw_transition_sha256")
        != acquisition.get("raw_transition_sha256")
        or predecessor.get("terminal_stop_update", {}).get("stopped") is not True
        or predecessor.get("reachable_frontier_exhaustion_input_consumed") is not False
        or acquisition.get("producer_free_raw_prefix_replay_enabled") is not True
        or acquisition.get("reachable_frontier_exhaustion_input_consumed") is not False
    ):
        _fail("V60 acquisition/raw-prefix join changed")
    factor_count = 0
    if arm == "ANONYMOUS_FACTOR_PRIOR_ON":
        if acquisition.get("compiled_program") is not None:
            _fail("V60 partial arm smuggled a complete program")
        factor_count = _partial_semantics(acquisition, rows)
    elif acquisition.get("compiled_program") is None:
        _fail("V60 strict arm omitted its complete program")
    return batches, factor_count


def _verify_prior_episode(episode: Any, acquisition_id: str) -> tuple[list[Any], list[Any], int, int]:
    _content(
        episode,
        "episode_id",
        domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_EPISODE_V60_DOMAIN,
        domains_v60.extension_content_id_v60,
    )
    certificates = episode.get("failed_certificates")
    distinctions = episode.get("local_distinctions")
    if (
        type(certificates) is not list
        or type(distinctions) is not list
        or len(certificates) != len(distinctions)
        or episode.get("acquisition_id") != acquisition_id
        or episode.get("success") is not True
        or episode.get("all_ground_queries_followed_failed_certificates") is not True
        or episode.get("query_local_exact_overlay_used") is not True
        or episode.get("robust_all_queried_branches_reachability_proved") is not True
        or episode.get("ground_transition_accessed_during_partial_abstract_action_proposal") is not False
        or episode.get("stream_prefix_residual_recovery_consumed") is not False
        or episode.get("complete_residual_world_model_synthesized") is not False
    ):
        _fail("V60 partial episode contract changed")
    local_rows = []
    local_labels = 0
    for index, (certificate, distinction) in enumerate(zip(certificates, distinctions, strict=True)):
        _content(
            certificate,
            "failed_certificate_id",
            domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_CERTIFICATE_V60_DOMAIN,
            domains_v60.extension_content_id_v60,
        )
        _content(
            distinction,
            "local_distinction_id",
            domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_DISTINCTION_V60_DOMAIN,
            domains_v60.extension_content_id_v60,
        )
        failure = certificate.get("failure")
        ground = distinction.get("distinction")
        if (
            distinction.get("failed_certificate_id")
            != certificate.get("failed_certificate_id")
            or type(failure) is not dict
            or type(ground) is not dict
            or failure.get("failure_index") != index
            or ground.get("failure_index") != index
            or failure.get("ground_query_performed_before_failure") is not False
            or ground.get("query_after_failed_certificate") is not True
            or ground.get("raw_state") != failure.get("raw_state")
            or ground.get("action_key") != failure.get("action_key")
            or ground.get("ground_support_labels") != 1
        ):
            _fail("V60 certificate-before-query join changed")
        batch = ground.get("raw_transition_rows", [])
        if ground.get("distinction_kind") == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT":
            if type(batch) is not list or not batch:
                _fail("V60 residual distinction omitted raw evidence")
            for row in batch:
                _row(row)
                if (
                    row["pre_vector"] != failure["raw_state"]
                    or row["selected_action"]["action_key"] != failure["action_key"]
                ):
                    _fail("V60 local raw row does not answer its certificate")
            local_rows.extend(batch)
        elif ground.get("distinction_kind") != "QUERY_LOCAL_LEGAL_ACTION_SET" or "raw_transition_rows" in ground:
            _fail("V60 query-local distinction kind changed")
        local_labels += 1
    if (
        episode.get("raw_local_transition_rows") != local_rows
        or episode.get("local_ground_support_labels") != local_labels
        or episode.get("queried_state_action_count")
        != sum(
            row["distinction"].get("distinction_kind")
            == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT"
            for row in distinctions
        )
    ):
        _fail("V60 query-local overlay accounting changed")
    return certificates, distinctions, local_labels, len(local_rows)


def verify_query_local_campaign_bytes_v60(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V60 frozen campaign byte envelope changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V60 campaign is not canonical JSON")
    _content(
        document,
        "campaign_id",
        domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_CAMPAIGN_V60_DOMAIN,
        domains_v60.extension_content_id_v60,
    )
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("v59_campaign_id") != V59_CAMPAIGN_ID
        or document.get("v59_verification_id") != V59_VERIFICATION_ID
    ):
        _fail("V60 predecessor identity join changed")
    raw_rows = document.get("raw_evidence")
    acquisitions = document.get("acquisitions")
    expected_pairs = [
        (family, seed)
        for family, start in (
            ("BALANCED_BATCH_REFINEMENT", 591_101),
            ("COUPLED_EXCHANGE", 592_101),
            ("MAINTENANCE_CASCADE", 593_101),
        )
        for seed in range(start, start + 12)
    ]
    if (
        type(raw_rows) is not list
        or len(raw_rows) != 36
        or [(row.get("family"), row.get("seed")) for row in raw_rows]
        != expected_pairs
        or type(acquisitions) is not dict
        or set(acquisitions) != {"ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"}
        or any(type(acquisitions[arm]) is not list or len(acquisitions[arm]) != 36 for arm in acquisitions)
    ):
        _fail("V60 occurrence inventory changed")
    factor_assignments_replayed = 0
    raw_transition_rows_replayed = 0
    acquisition_by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
    for index, raw_evidence in enumerate(raw_rows):
        _content(
            raw_evidence,
            "raw_evidence_id",
            domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_RAW_EVIDENCE_V60_DOMAIN,
            domains_v60.extension_content_id_v60,
        )
        evidence_batches = raw_evidence.get("raw_transition_batches")
        evidence_flat = _flat(evidence_batches)
        if (
            raw_evidence.get("maximum_observed_label_count") != len(evidence_batches)
            or raw_evidence.get("symmetric_common_prefix_reconstructible_from_bytes") is not True
            or raw_evidence.get("generation_witness_present") is not False
        ):
            _fail("V60 raw-evidence contract changed")
        prior_batches, factors = _verify_acquisition(
            acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"][index],
            "ANONYMOUS_FACTOR_PRIOR_ON",
            raw_evidence,
        )
        strict_batches, _ = _verify_acquisition(
            acquisitions["STRICT_NO_PRIOR"][index],
            "STRICT_NO_PRIOR",
            raw_evidence,
        )
        common = min(len(prior_batches), len(strict_batches))
        if prior_batches[:common] != strict_batches[:common]:
            _fail("V60 symmetric common prefix changed")
        if len(evidence_batches) != max(len(prior_batches), len(strict_batches)):
            _fail("V60 raw evidence did not preserve the longer arm")
        factor_assignments_replayed += factors
        raw_transition_rows_replayed += len(evidence_flat)
        for arm in acquisitions:
            row = acquisitions[arm][index]
            acquisition_by_key[(row["family"], row["seed"], arm)] = row
    episodes = document.get("episodes")
    if type(episodes) is not dict or any(
        type(episodes.get(arm)) is not list or len(episodes[arm]) != 3
        for arm in (
            "ANONYMOUS_FACTOR_PRIOR_ON",
            "STRICT_NO_PRIOR",
            "STRICT_EXACT_CONTEXT",
        )
    ):
        _fail("V60 episode inventory changed")
    embedded_certificates = []
    embedded_distinctions = []
    prior_local = 0
    local_raw_rows = 0
    for episode in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]:
        key = (episode.get("family"), episode.get("seed"), "ANONYMOUS_FACTOR_PRIOR_ON")
        if key not in acquisition_by_key:
            _fail("V60 episode occurrence join changed")
        certs, distinctions, labels, rows = _verify_prior_episode(
            episode, acquisition_by_key[key]["acquisition_id"]
        )
        embedded_certificates.extend(certs)
        embedded_distinctions.extend(distinctions)
        prior_local += labels
        local_raw_rows += rows
    for arm in ("STRICT_NO_PRIOR", "STRICT_EXACT_CONTEXT"):
        for episode in episodes[arm]:
            _content(
                episode,
                "episode_id",
                domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_EPISODE_V56_DOMAIN,
                domains_v56.extension_content_id_v56,
            )
            if episode.get("success") is not True:
                _fail("V60 retained exact-context episode changed")
    failures = document.get("failed_certificates")
    distinctions = document.get("local_distinctions")
    if type(failures) is not list or type(distinctions) is not list:
        _fail("V60 certificate inventory changed")
    v60_failures = [row for row in failures if row.get("schema") == "acfqp.query_local_failed_certificate.v60"]
    v60_distinctions = [row for row in distinctions if row.get("schema") == "acfqp.query_local_ground_distinction.v60"]
    if v60_failures != embedded_certificates or v60_distinctions != embedded_distinctions:
        _fail("V60 top-level query-local evidence projection changed")
    strict_failures = [row for row in failures if row.get("schema") == "acfqp.mdl_adaptive_failed_certificate.v56"]
    strict_distinctions = [row for row in distinctions if row.get("schema") == "acfqp.mdl_adaptive_local_distinction.v56"]
    if len(strict_failures) != len(strict_distinctions):
        _fail("V60 strict certificate/distinction cardinality changed")
    for failure, distinction in zip(strict_failures, strict_distinctions, strict=True):
        _content(failure, "failed_certificate_id", domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_FAILED_CERTIFICATE_V56_DOMAIN, domains_v56.extension_content_id_v56)
        _content(distinction, "local_distinction_id", domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_LOCAL_DISTINCTION_V56_DOMAIN, domains_v56.extension_content_id_v56)
        if (
            distinction.get("failed_certificate_id") != failure.get("failed_certificate_id")
            or failure.get("ground_query_performed_before_failure") is not False
            or distinction.get("query_after_failed_certificate") is not True
            or distinction.get("ground_support_labels") != 1
        ):
            _fail("V60 retained strict certificate ordering changed")
    prior_labels = sum(row["ground_support_labels"] for row in acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"])
    strict_labels = sum(row["ground_support_labels"] for row in acquisitions["STRICT_NO_PRIOR"])
    strict_local = sum(row["local_ground_support_labels"] for row in episodes["STRICT_NO_PRIOR"])
    sample = document.get("sample_tax")
    _content(sample, "sample_tax_id", domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_SAMPLE_TAX_V60_DOMAIN, domains_v60.extension_content_id_v60)
    online = strict_labels + strict_local - prior_labels - prior_local
    lifetime = online - sample.get("factor_library_labels_prior_on_only", -1)
    expected_sample = {
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": strict_labels,
        "incremental_acquisition_label_reduction": strict_labels - prior_labels,
        "factor_prior_on_query_local_labels": prior_local,
        "strict_no_prior_local_recovery_labels": strict_local,
        "online_label_reduction_including_local_queries": online,
        "lifetime_label_reduction_after_offline_tax": lifetime,
    }
    if any(sample.get(key) != value for key, value in expected_sample.items()) or online <= 0 or lifetime <= 0:
        _fail("V60 sample-tax arithmetic changed")
    accounting = document.get("accounting")
    expected_accounting = {
        "offline_factor_library_labels": sample["factor_library_labels_prior_on_only"],
        "factor_prior_on_target_labels": prior_labels,
        "strict_no_prior_target_labels": strict_labels,
        "factor_prior_on_query_local_labels": prior_local,
        "strict_no_prior_local_labels": strict_local,
        "factor_prior_on_execution_steps": sum(row["execution_steps"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]),
        "strict_no_prior_execution_steps": sum(row["execution_steps"] for row in episodes["STRICT_NO_PRIOR"]),
        "direct_execution_steps": sum(row["execution_steps"] for row in episodes["STRICT_EXACT_CONTEXT"]),
        "factor_prior_on_planning_compute_events": sum(row["abstract_planning_compute_events"] for row in episodes["ANONYMOUS_FACTOR_PRIOR_ON"]),
        "strict_no_prior_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["STRICT_NO_PRIOR"]),
        "direct_planning_compute_events": sum(row["planning_compute_events"] for row in episodes["STRICT_EXACT_CONTEXT"]),
        "certificate_compute_events": len(failures),
        "all_axes_separate": True,
    }
    if accounting != expected_accounting:
        _fail("V60 separated accounting axes changed")
    locks = {
        "raw_transition_bytes_embedded_for_producer_free_replay": True,
        "symmetric_common_prefix_reconstructible_from_bytes": True,
        "stream_prefix_residual_recovery_consumed": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_used": True,
        "complete_residual_world_model_synthesized": False,
        "reachable_frontier_exhaustion_stop_consumed": False,
        "heuristic_mdl_information_units_consumed": False,
        "predictive_evidence_to_mdl_credit_consumed": False,
        "arbitrary_domain_transfer_claimed": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("V60 claim lock changed")
    payload = {
        "schema": "acfqp.query_local_independent_verification.v60",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": len(raw),
        "campaign_sha256": hashlib.sha256(raw).hexdigest(),
        "occurrence_count": 36,
        "raw_transition_row_count_replayed": raw_transition_rows_replayed,
        "partial_factor_assignment_count_replayed": factor_assignments_replayed,
        "query_local_raw_transition_row_count_replayed": local_raw_rows,
        "failed_certificate_count": len(failures),
        "local_distinction_count": len(distinctions),
        "recomputed_sample_tax": expected_sample,
        "all_content_ids_and_internal_accounting_verified": True,
        "raw_prefix_semantics_independently_replayed": True,
        "partial_factor_dynamics_semantics_independently_replayed": True,
        "certificate_before_query_and_local_raw_evidence_independently_replayed": True,
        "producer_or_campaign_core_imported": False,
        "complete_program_semantic_reexecution_present": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "outcome": "PRODUCER_FREE_RAW_PARTIAL_DYNAMICS_AND_QUERY_LOCAL_EVIDENCE_VERIFIED",
    }
    result = {
        **payload,
        "verification_id": domains_v60.extension_content_id_v60(
            domains_v60.CONSTRUCTION_K7_QUERY_LOCAL_VERIFICATION_V60_DOMAIN,
            payload,
        ),
    }
    verification_raw = canonical_json_bytes(result)
    if VERIFICATION_ID != "0" * 64 and (
        result["verification_id"] != VERIFICATION_ID
        or len(verification_raw) != EXPECTED_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != EXPECTED_VERIFICATION_SHA256
    ):
        _fail("frozen V60 independent verification changed")
    return result


__all__ = ("verify_query_local_campaign_bytes_v60",)
