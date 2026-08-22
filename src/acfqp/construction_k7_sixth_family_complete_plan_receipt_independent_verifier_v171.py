"""Producer-free outcome replay and receipt verification for V171."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import applicable_plan_receipt_set_sequence_v168 as sequence_v168
from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v171 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_DISPATCH_FAMILY,
    build_reservoir_dispatch_adapter_v171,
    reservoir_dispatch_config_v171,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PREREGISTRATION_ID = "4c1047ed0b55077150f2bb7433f644525a380ba65650c78ab3ec11228fa0bc73"
PREREGISTRATION_BYTE_COUNT = 4_279
PREREGISTRATION_SHA256 = "508da1b214c972f798da66754bf72990810ff469f6daa56951b4ca6abd97abd0"
CAMPAIGN_ID = "ca284948d3d8886025fb13a84cffbab9bb535c242d292a2a68dd194bef4ed463"
CAMPAIGN_BYTE_COUNT = 14_712_225
CAMPAIGN_SHA256 = "95b2fb332a5813d83a50b4ba192cc5720e054c009e8af4b3e9ce8c93cf99f76a"
V168_CAMPAIGN_ID = "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce"
V170_AUDIT_ID = "0372043e8d6a3277070488777e3f0dc5f33702abb2b72a8fcabc12a60dd35944"
V170_VERIFICATION_ID = "f9b7570d565cb160d80aafadd9d4bcf49abdcb7879d782c597fd9f955cfa4217"
TARGETS = (
    (RESERVOIR_DISPATCH_FAMILY, 1_059_851),
    (RESERVOIR_DISPATCH_FAMILY, 1_059_852),
)
EPISODES = (963, 964, 965, 966)
V106_PLAN_DOMAIN = "acfqp:generic-legality-conditioned-quotient-plan:v106"
TAXONOMY = {
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "OBSERVATION_QUOTIENT_GRAPH",
    ): "OBSERVATION_DERIVED_QUOTIENT_ORDER",
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "COMPILED_FACTOR_PROGRAM_FALLBACK",
    ): "DIRECT_COMPILED_PROGRAM_ORDER",
    (
        "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
    ): "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    (
        "acfqp.generic_projected_program_memo_plan.v115",
        "COMPILED_FACTOR_PROGRAM_MEMOIZED",
    ): "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
}
VERIFICATION_ID = "422770529178614103624e873a5a1aaf732df6b949fe0bfe50edad3ad2fb78d0"
EXPECTED_CANONICAL_BYTE_COUNT = 1_894
EXPECTED_CANONICAL_SHA256 = (
    "a668ce94f507b62a22c85bdc8c569d39991394a29687069a531c8ac90138014c"
)


class ConstructionK7SixthFamilyCompletePlanReceiptIndependentVerifierV171Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SixthFamilyCompletePlanReceiptIndependentVerifierV171Error(
        message
    )


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _sha(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _config():
    config = v168.fifth_family_total_plan_receipt_set_campaign_config_v168()
    reservoir = reservoir_dispatch_config_v171()
    config["families"][RESERVOIR_DISPATCH_FAMILY] = copy.deepcopy(
        reservoir["families"][RESERVOIR_DISPATCH_FAMILY]
    )
    config["families"][RESERVOIR_DISPATCH_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


_TARGET_FAMILIES = (*v168.TARGET_FAMILIES, RESERVOIR_DISPATCH_FAMILY)
_SEQUENCE_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v171,
    CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V171_DOMAIN,
)
_SEQUENCE_GLOBALS = dict(sequence_v168.__dict__)
_SEQUENCE_GLOBALS["domains"] = _SEQUENCE_DOMAIN_PROXY
_ANNOTATE_BASE_SEQUENCE = FunctionType(
    sequence_v168.annotate_applicable_plan_receipt_set_sequence_v168.__code__,
    _SEQUENCE_GLOBALS,
    name="_independent_annotate_base_sequence_v171",
)
_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v171,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN,
)
_V160_GLOBALS = dict(v168._BASE_V160_OCCURRENCE_V168.__globals__)  # noqa: SLF001
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    _BUILDERS={
        **_V160_GLOBALS["_BUILDERS"],
        RESERVOIR_DISPATCH_FAMILY: build_reservoir_dispatch_adapter_v171,
    },
    annotate_applicable_plan_mode_sequence_v157=_ANNOTATE_BASE_SEQUENCE,
)
_BASE_V160 = FunctionType(
    v168._BASE_V160_OCCURRENCE_V168.__code__,  # noqa: SLF001
    _V160_GLOBALS,
    name="_independent_v160_occurrence_v171",
)
_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v171,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=domains.CONSTRUCTION_K7_CAMPAIGN_V171_DOMAIN,
)
_V166_GLOBALS = dict(v166.__dict__)
_V166_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160,
    TARGET_FAMILIES=_TARGET_FAMILIES,
)
_BASE_V166 = FunctionType(
    v166.build_fourth_family_sample_tax_occurrence_v166.__code__,
    _V166_GLOBALS,
    name="_independent_v166_occurrence_v171",
)
_V168_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v171,
    CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN,
)
_V168_GLOBALS = dict(v168.__dict__)
_V168_GLOBALS.update(
    domains=_V168_DOMAIN_PROXY,
    _BASE_V166_OCCURRENCE_V168=_BASE_V166,
    TARGET_FAMILIES=_TARGET_FAMILIES,
)
_BASE_V168 = FunctionType(
    v168.build_fifth_family_total_plan_receipt_set_occurrence_v168.__code__,
    _V168_GLOBALS,
    name="_independent_v168_occurrence_v171",
)


def _replay_target(args):
    config, family, seed, bank_raw, bank_verification_raw, classifier_raw = args
    return _BASE_V168(
        config,
        family=family,
        seed=seed,
        episode_indices=EPISODES,
        bank_raw=bank_raw,
        verification_raw=bank_verification_raw,
        classifier_receipt_raw=classifier_raw,
    )


def _plan_id(plan: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in plan.items()
        if key != "legality_conditioned_quotient_plan_id"
    }
    if plan["schema"] == "acfqp.generic_legality_conditioned_quotient_plan.v106":
        return _content_id(V106_PLAN_DOMAIN, payload)
    if plan["schema"] == "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109":
        return domains_v109.extension_content_id_v109(
            domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_PLAN_V109_DOMAIN,
            payload,
        )
    if plan["schema"] == "acfqp.generic_projected_program_memo_plan.v115":
        return domains_v115.extension_content_id_v115(
            domains_v115.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_PLAN_V115_DOMAIN,
            payload,
        )
    _fail("V171 independent plan schema escaped taxonomy")


def _typed_expected(sequence_id, episode, ordinal, wrapper):
    if type(wrapper) is not dict or set(wrapper) != {"raw_state", "abstract_plan"}:
        _fail("V171 independent plan wrapper changed")
    plan = wrapper["abstract_plan"]
    typed_source = TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
    if typed_source is None:
        _fail("V171 independent plan source escaped taxonomy")
    identity = _plan_id(plan)
    ground_values = [
        plan[name]
        for name in (
            "ground_transition_accessed_during_abstract_search",
            "ground_transition_accessed_during_dependency_revalidation",
            "ground_transition_accessed_during_program_memo_reuse",
        )
        if name in plan
    ]
    if not (
        plan.get("legality_conditioned_quotient_plan_id") == identity
        and plan.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
        and plan.get("complete_ground_world_model_claimed") is False
        and type(plan.get("initial_action_key")) is int
        and plan["initial_action_key"]
        in plan.get("exact_legal_action_keys_at_initial_state", [])
        and type(plan.get("projected_action_path")) is list
        and plan["projected_action_path"]
        and plan["projected_action_path"][0] == plan["initial_action_key"]
        and ground_values == [False]
    ):
        _fail("V171 independent plan identity or authority boundary changed")
    payload = {
        "schema": "acfqp.typed_abstract_plan_receipt.v171",
        "source_sequence_id": sequence_id,
        "episode_index": episode["episode_index"],
        "plan_ordinal": ordinal,
        "plan_schema": plan["schema"],
        "planning_source": plan["planning_source"],
        "typed_plan_source": typed_source,
        "source_plan_id": identity,
        "source_wrapper_sha256": _sha(wrapper),
        "raw_state_sha256": _sha(wrapper["raw_state"]),
        "initial_action_key": plan["initial_action_key"],
        "projected_action_count": len(plan["projected_action_path"]),
        "ground_transition_accessed_during_abstract_reasoning": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "typed_receipt_changes_planning_or_execution": False,
        "typed_receipt_is_safety_authority": False,
    }
    return {
        **payload,
        "typed_plan_receipt_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_TYPED_PLAN_RECEIPT_V171_DOMAIN, payload
        ),
    }


def _join_expected(sequence_id, episode, execution, typed, wrappers):
    source_payload = {
        key: value
        for key, value in execution.items()
        if key != "actual_dependency_revalidated_execution_receipt_id"
    }
    source_id = domains_v109.extension_content_id_v109(
        domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
        source_payload,
    )
    if not (
        execution.get("schema")
        == "acfqp.generic_dependency_revalidated_execution_receipt.v109"
        and execution.get("actual_dependency_revalidated_execution_receipt_id")
        == source_id
        and execution.get("receipt_is_observation_not_safety_authority") is True
        and execution.get("query_local_exact_overlay_remains_only_safety_authority")
        is True
    ):
        _fail("V171 independent V109 receipt changed")
    target = canonical_json_bytes(execution["quotient_plan_receipt"])
    matches = [
        index
        for index, wrapper in enumerate(wrappers)
        if canonical_json_bytes(wrapper) == target
    ]
    if len(matches) != 1:
        _fail("V171 independent execution join is not unique")
    ordinal = matches[0]
    item = typed[ordinal]
    plan = execution["quotient_plan_receipt"]["abstract_plan"]
    if not (
        execution["episode_index"] == episode["episode_index"]
        and execution["raw_state"] == execution["quotient_plan_receipt"]["raw_state"]
        and execution["quotient_plan_id"] == plan["legality_conditioned_quotient_plan_id"]
        and execution["quotient_proposed_action_key"] == plan["initial_action_key"]
        and execution["chosen_action_key"] in execution["legal_action_keys"]
    ):
        _fail("V171 independent plan/execution semantic join changed")
    payload = {
        "schema": "acfqp.typed_plan_execution_join_receipt.v171",
        "source_sequence_id": sequence_id,
        "episode_index": episode["episode_index"],
        "decision_index": execution["decision_index"],
        "source_v109_execution_receipt_id": source_id,
        "typed_plan_receipt_id": item["typed_plan_receipt_id"],
        "source_plan_ordinal": ordinal,
        "typed_plan_source": item["typed_plan_source"],
        "raw_state_sha256": item["raw_state_sha256"],
        "chosen_action_key": execution["chosen_action_key"],
        "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
        "quotient_proposal_admitted_to_real_action_order": execution[
            "quotient_proposal_admitted_to_real_action_order"
        ],
        "chosen_action_matches_admitted_quotient_proposal": execution[
            "chosen_action_matches_admitted_quotient_proposal"
        ],
        "actual_action_ordering_source": execution["actual_action_ordering_source"],
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "typed_join_changes_planning_or_execution": False,
        "typed_join_is_safety_authority": False,
    }
    return {
        **payload,
        "execution_join_receipt_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_EXECUTION_JOIN_RECEIPT_V171_DOMAIN, payload
        ),
    }


_SEQUENCE_EXTRA = {
    "source_v168_shape_sequence_id",
    "typed_plan_taxonomy_episode_rows",
    "typed_plan_receipt_count",
    "execution_join_receipt_count",
    "typed_plan_source_histogram",
    "untyped_abstract_plan_receipt_count",
    "unjoined_executed_action_count",
    "complete_four_source_taxonomy_applied",
    "every_abstract_plan_instance_typed",
    "every_executed_action_exactly_joined",
    "taxonomy_changes_planning_or_execution",
    "taxonomy_is_model_or_safety_authority",
}


def _verify_sequence(actual, base):
    base_projection = {
        **{
            key: value
            for key, value in actual.items()
            if key not in _SEQUENCE_EXTRA | {"schema", "sequence_id"}
        },
        "schema": "acfqp.applicable_plan_receipt_set_sequence.v168",
        "sequence_id": actual.get("source_v168_shape_sequence_id"),
    }
    if base_projection != base:
        _fail("V171 producer-free base sequence replay changed")
    rows = actual.get("typed_plan_taxonomy_episode_rows")
    if type(rows) is not list or len(rows) != len(base["episodes"]):
        _fail("V171 typed episode inventory changed")
    histogram = {source: 0 for source in TAXONOMY.values()}
    typed_ids = []
    join_ids = []
    for row, episode in zip(rows, base["episodes"], strict=True):
        wrappers = episode["abstract_plan_receipts"]
        typed = [
            _typed_expected(base["sequence_id"], episode, index, wrapper)
            for index, wrapper in enumerate(wrappers)
        ]
        joins = [
            _join_expected(
                base["sequence_id"], episode, execution, typed, wrappers
            )
            for execution in episode["actual_legality_conditioned_execution_receipts"]
        ]
        row_histogram = {
            source: sum(item["typed_plan_source"] == source for item in typed)
            for source in TAXONOMY.values()
        }
        expected_row = {
            "schema": "acfqp.complete_plan_receipt_taxonomy_episode.v171",
            "episode_index": episode["episode_index"],
            "typed_plan_receipts": typed,
            "typed_plan_receipt_count": len(typed),
            "typed_plan_source_histogram": row_histogram,
            "execution_join_receipts": joins,
            "execution_join_receipt_count": len(joins),
            "untyped_abstract_plan_receipt_count": 0,
            "unjoined_executed_action_count": 0,
        }
        if row != expected_row:
            _fail("V171 independent typed episode reconstruction changed")
        typed_ids.extend(item["typed_plan_receipt_id"] for item in typed)
        join_ids.extend(item["execution_join_receipt_id"] for item in joins)
        for source, count in row_histogram.items():
            histogram[source] += count
    expected_root = {
        "schema": "acfqp.complete_plan_receipt_taxonomy_sequence.v171",
        "source_v168_shape_sequence_id": base["sequence_id"],
        "typed_plan_receipt_count": len(typed_ids),
        "execution_join_receipt_count": len(join_ids),
        "typed_plan_source_histogram": histogram,
        "untyped_abstract_plan_receipt_count": 0,
        "unjoined_executed_action_count": 0,
        "complete_four_source_taxonomy_applied": True,
        "every_abstract_plan_instance_typed": True,
        "every_executed_action_exactly_joined": True,
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
    }
    if any(actual.get(key) != value for key, value in expected_root.items()):
        _fail("V171 independent typed sequence root changed")
    payload = {key: value for key, value in actual.items() if key != "sequence_id"}
    if actual.get("sequence_id") != domains.extension_content_id_v171(
        domains.CONSTRUCTION_K7_SEQUENCE_V171_DOMAIN, payload
    ):
        _fail("V171 typed sequence identity changed")
    return histogram, typed_ids, join_ids


_OCCURRENCE_EXTRA = {
    "typed_plan_source_histogram",
    "typed_plan_receipt_count",
    "execution_join_receipt_count",
    "v170_taxonomy_annotation_changes_planning_or_execution",
}
_GATE_EXTRA = {
    "complete_v170_taxonomy_applied_both_arms",
    "every_abstract_plan_instance_typed",
    "every_executed_action_exactly_joined",
    "taxonomy_does_not_change_planning_or_execution",
    "taxonomy_is_not_model_or_safety_authority",
    "factor_prior_strictly_reduces_sixth_family_acquisition_labels",
    "query_policy_has_zero_regression",
}


def _verify_occurrence(actual, base):
    for key, value in base.items():
        if key in {
            "schema",
            "occurrence_id",
            "progressive_prior_sequence",
            "progressive_strict_sequence",
            "registered_gate",
            "sample_tax_claim_scope",
        }:
            continue
        if actual.get(key) != value:
            _fail(f"V171 producer-free occurrence field changed: {key}")
    histograms = []
    typed_ids = []
    join_ids = []
    for key in ("progressive_prior_sequence", "progressive_strict_sequence"):
        histogram, sequence_typed, sequence_joins = _verify_sequence(
            actual[key], base[key]
        )
        histograms.append(histogram)
        typed_ids.extend(sequence_typed)
        join_ids.extend(sequence_joins)
    histogram = {
        source: sum(row[source] for row in histograms) for source in TAXONOMY.values()
    }
    if not (
        actual.get("typed_plan_source_histogram") == histogram
        and actual.get("typed_plan_receipt_count") == len(typed_ids)
        and actual.get("execution_join_receipt_count") == len(join_ids)
        and actual.get("sample_tax_claim_scope")
        == "ONLY_THIS_PREREGISTERED_V171_SIXTH_FAMILY_COHORT"
        and actual.get("v170_taxonomy_annotation_changes_planning_or_execution")
        is False
    ):
        _fail("V171 occurrence taxonomy summary changed")
    actual_gate = actual.get("registered_gate")
    base_gate = base["registered_gate"]
    if not (
        type(actual_gate) is dict
        and set(actual_gate) == set(base_gate) | _GATE_EXTRA
        and all(
            actual_gate[key] == value
            for key, value in base_gate.items()
            if key != "passed"
        )
        and all(actual_gate[key] is True for key in _GATE_EXTRA)
        and actual_gate["passed"] is True
        and actual["factor_prior_sample_reduction_within_progressive_policy"] > 0
        and actual["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
    ):
        _fail("V171 occurrence registered gate changed")
    payload = {key: value for key, value in actual.items() if key != "occurrence_id"}
    if not (
        actual.get("schema")
        == "acfqp.sixth_family_complete_plan_receipt_occurrence.v171"
        and actual.get("occurrence_id")
        == domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_OCCURRENCE_V171_DOMAIN, payload
        )
    ):
        _fail("V171 occurrence identity changed")
    return histogram, typed_ids, join_ids


def freeze_sixth_family_complete_plan_receipt_verification_v171(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    preregistration = loads_canonical_json(preregistration_raw)
    if not (
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID
    ):
        _fail("V171 frozen campaign changed")
    if not (
        canonical_json_bytes(preregistration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256
        and preregistration.get("preregistration_id") == PREREGISTRATION_ID
        and preregistration.get("claim_boundary", {}).get("target_outcomes_accessed")
        is False
    ):
        _fail("V171 frozen preregistration changed")
    config = _config()
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=2) as executor:
        replayed = list(executor.map(_replay_target, args))
    actual_rows = campaign.get("target_occurrences")
    if type(actual_rows) is not list or len(actual_rows) != len(replayed) == 2:
        _fail("V171 target occurrence inventory changed")
    histogram = {source: 0 for source in TAXONOMY.values()}
    typed_ids = []
    join_ids = []
    for actual, base in zip(actual_rows, replayed, strict=True):
        row_histogram, row_typed, row_joins = _verify_occurrence(actual, base)
        typed_ids.extend(row_typed)
        join_ids.extend(row_joins)
        for source, count in row_histogram.items():
            histogram[source] += count
    numeric = [
        key for key, value in actual_rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in actual_rows) for key in numeric
    }
    accounting.update(
        total_query_policy_labels_avoided_vs_exact_path_first=sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"]
            for row in actual_rows
        ),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in actual_rows
        ),
        typed_plan_receipt_count=len(typed_ids),
        execution_join_receipt_count=len(join_ids),
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    expected_gate = {
        "required_fresh_reservoir_occurrence_count": 2,
        "passed_fresh_reservoir_occurrence_count": 2,
        "every_target_is_fresh_reservoir_dispatch": True,
        "v168_and_v170_frozen_predecessors_preserved": True,
        "every_abstract_plan_instance_typed": True,
        "every_executed_action_exactly_joined": True,
        "zero_unknown_plan_sources": True,
        "sixth_family_factor_prior_strictly_reduces_labels": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in actual_rows
        ),
        "sixth_family_query_policy_noninferior": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in actual_rows
        ),
        "both_arm_receding_plans_succeed": True,
        "certificate_failure_only_local_ground_distinctions": True,
        "taxonomy_does_not_change_planning_or_execution": True,
        "passed": True,
    }
    root_checks = {
        "schema": "acfqp.sixth_family_complete_plan_receipt_campaign.v171",
        "preregistration_id": PREREGISTRATION_ID,
        "frozen_v168_campaign_id": V168_CAMPAIGN_ID,
        "frozen_v170_taxonomy_audit_id": V170_AUDIT_ID,
        "frozen_v170_taxonomy_verification_id": V170_VERIFICATION_ID,
        "target_occurrence_ids": [row["occurrence_id"] for row in actual_rows],
        "fresh_reservoir_accounting": accounting,
        "typed_plan_source_histogram": histogram,
        "registered_gate": expected_gate,
        "sixth_family_world_model_reuse_observed": True,
        "sixth_family_factor_prior_sample_tax_reduction_observed": True,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V171_SIXTH_FAMILY_COHORT",
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    if any(campaign.get(key) != value for key, value in root_checks.items()):
        _fail("V171 campaign root reconstruction changed")
    payload_without_id = {
        key: value for key, value in campaign.items() if key != "campaign_id"
    }
    if campaign["campaign_id"] != domains.extension_content_id_v171(
        domains.CONSTRUCTION_K7_CAMPAIGN_V171_DOMAIN, payload_without_id
    ):
        _fail("V171 campaign identity changed")
    payload = {
        "schema": "acfqp.sixth_family_complete_plan_receipt_verification.v171",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "verified_occurrence_ids": campaign["target_occurrence_ids"],
        "verified_target_seeds": [seed for _, seed in TARGETS],
        "verified_factor_prior_labels_avoided": accounting[
            "total_factor_prior_labels_avoided_within_same_query_policy"
        ],
        "verified_query_policy_labels_avoided": accounting[
            "total_query_policy_labels_avoided_vs_exact_path_first"
        ],
        "verified_typed_plan_receipt_count": len(typed_ids),
        "verified_execution_join_receipt_count": len(join_ids),
        "verified_typed_plan_source_histogram": histogram,
        "typed_plan_receipt_id_sequence_sha256": _sha(typed_ids),
        "execution_join_receipt_id_sequence_sha256": _sha(join_ids),
        "producer_free_target_outcome_reexecution": True,
        "producer_free_complete_taxonomy_reconstruction": True,
        "producer_free_unique_execution_join_reconstruction": True,
        "factor_prior_strict_sample_tax_reduction_independently_verified": True,
        "query_policy_noninferiority_independently_verified": True,
        "receding_planning_and_certificate_local_recovery_independently_verified": True,
        "taxonomy_changes_planning_or_execution": False,
        "taxonomy_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v171(
            domains.CONSTRUCTION_K7_VERIFICATION_V171_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V171 frozen verification changed")
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_sixth_family_complete_plan_receipt_verification_v171",
)
