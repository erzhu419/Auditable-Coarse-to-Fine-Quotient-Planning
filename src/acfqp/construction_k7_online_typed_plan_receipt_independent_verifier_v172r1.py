"""Producer-free reexecution of the frozen V172r1 online receipt campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import contextvars
import hashlib
from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import applicable_plan_receipt_set_sequence_v168 as sequence_v168
from acfqp import certified_memoized_planner_sequence_v154 as v154
from acfqp import construction_k7_domain_registry_extension_v109 as domains_v109
from acfqp import construction_k7_domain_registry_extension_v115 as domains_v115
from acfqp import construction_k7_domain_registry_extension_v172 as domains
from acfqp import fifth_family_total_plan_receipt_set_campaign_core_v168 as v168
from acfqp import fourth_family_sample_tax_transfer_campaign_core_v166 as v166
from acfqp.generic_reservoir_dispatch_adapter_v171 import (
    FAMILY as RESERVOIR_DISPATCH_FAMILY,
    build_reservoir_dispatch_adapter_v171,
    reservoir_dispatch_config_v171,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / ".tmp/exact-freeze"
PREREGISTRATION_ID = "210c762b7ac7c99790d294046f0f1abc3f24f506300ebe003777d2a310037d59"
PREREGISTRATION_BYTE_COUNT = 3_530
PREREGISTRATION_SHA256 = "b0fa67cf2790a84819e4ff53debaffe8441bfcfe96fae66b655aaeea5bef77a6"
CAMPAIGN_ID = "c904d48bd590a287c4a1085ffecf41920ddde5cbba7a958e3906232afdd4128b"
CAMPAIGN_BYTE_COUNT = 14_761_292
CAMPAIGN_SHA256 = "2988188d53f74266839e107fb2e6a378cf3d2b8dfbe5f29fae3076b36556fb99"
FAILED_V172_ID = "a8eb6fa5978d45c70c9412c444b3f25e8ad78eb8e1cda3d317242b4c771fb653"
TARGETS = (
    (RESERVOIR_DISPATCH_FAMILY, 1_079_851),
    (RESERVOIR_DISPATCH_FAMILY, 1_079_852),
)
EPISODES = (983, 984, 985, 986)
TARGET_WORKERS = 2
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
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


class ConstructionK7OnlineTypedPlanReceiptIndependentVerifierV172R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlineTypedPlanReceiptIndependentVerifierV172R1Error(
        message
    )


def _clone(function, namespace):
    clone = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _sha(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


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
    _fail("V172r1 independent plan schema escaped taxonomy")


_TRACE: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "v172r1_independent_online_trace", default=None
)
_DELEGATE_ORDERER = v154._RUN.__globals__["_owned_orderer"]  # noqa: SLF001


def _independent_orderer(*args, **kwargs):
    delegate = _DELEGATE_ORDERER(*args, **kwargs)

    def order(raw, legal, support_source, failure_index):
        plan = delegate(raw, legal, support_source, failure_index)
        if plan is None:
            return None
        trace = _TRACE.get()
        if trace is None:
            _fail("V172r1 independent orderer lacks its trace")
        before = canonical_json_bytes(plan)
        typed_source = TAXONOMY.get((plan.get("schema"), plan.get("planning_source")))
        plan_id = _plan_id(plan)
        if not (
            typed_source is not None
            and plan.get("legality_conditioned_quotient_plan_id") == plan_id
            and plan.get("initial_action_key") in legal
            and plan.get("query_local_exact_overlay_remains_only_safety_authority")
            is True
            and plan.get("complete_ground_world_model_claimed") is False
        ):
            _fail("V172r1 independent online plan boundary changed")
        wrapper_bytes = canonical_json_bytes(
            {"raw_state": list(raw), "abstract_plan": plan}
        )
        payload = {
            "schema": "acfqp.online_typed_abstract_plan_issuance_receipt.v172",
            "issuance_ordinal": len(trace),
            "plan_schema": plan["schema"],
            "planning_source": plan["planning_source"],
            "typed_plan_source": typed_source,
            "source_plan_id": plan_id,
            "source_plan_wrapper_sha256": hashlib.sha256(wrapper_bytes).hexdigest(),
            "raw_state_sha256": _sha(list(raw)),
            "exact_legal_action_keys": list(legal),
            "exact_legal_action_keys_sha256": _sha(list(legal)),
            "legality_support_source": support_source,
            "legality_failure_index": failure_index,
            "initial_action_key": plan["initial_action_key"],
            "delegate_plan_sha256_before_receipt": hashlib.sha256(before).hexdigest(),
            "receipt_issued_before_orderer_return": True,
            "caller_has_not_received_plan_at_receipt_issuance": True,
            "delegate_plan_returned_byte_exact": True,
            "receipt_changes_plan_or_action_order": False,
            "receipt_is_model_or_safety_authority": False,
            "query_local_exact_overlay_remains_only_safety_authority": True,
        }
        receipt = {
            **payload,
            "online_plan_issuance_receipt_id": domains.extension_content_id_v172(
                domains.CONSTRUCTION_K7_ONLINE_PLAN_ISSUANCE_V172_DOMAIN, payload
            ),
        }
        if canonical_json_bytes(plan) != before:
            _fail("V172r1 independent receipt changed delegate plan bytes")
        trace.append({"wrapper_bytes": wrapper_bytes, "receipt": receipt})
        return plan

    return order


_RUN_GLOBALS = dict(v154._RUN.__globals__)  # noqa: SLF001
_RUN_GLOBALS["_owned_orderer"] = _independent_orderer
_RUN = _clone(v154._RUN, _RUN_GLOBALS)  # noqa: SLF001
_V154_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v154=domains.extension_content_id_v172,
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN,
)
_V154_GLOBALS = dict(v154.__dict__)
_V154_GLOBALS.update(_RUN=_RUN, domains=_V154_DOMAIN_PROXY)
_BASE_SEQUENCE = _clone(
    v154.run_certified_memoized_planner_sequence_v154, _V154_GLOBALS
)


def _execution_join(sequence_id, execution, event, ordinal):
    source_payload = {
        key: value
        for key, value in execution.items()
        if key != "actual_dependency_revalidated_execution_receipt_id"
    }
    source_id = domains_v109.extension_content_id_v109(
        domains_v109.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_EXECUTION_RECEIPT_V109_DOMAIN,
        source_payload,
    )
    receipt = event["receipt"]
    if not (
        execution.get("actual_dependency_revalidated_execution_receipt_id")
        == source_id
        and canonical_json_bytes(execution.get("quotient_plan_receipt"))
        == event["wrapper_bytes"]
        and execution.get("quotient_plan_id") == receipt["source_plan_id"]
        and execution.get("quotient_proposed_action_key")
        == receipt["initial_action_key"]
    ):
        _fail("V172r1 independent execution join changed")
    payload = {
        "schema": "acfqp.online_typed_plan_execution_join.v172",
        "source_sequence_id": sequence_id,
        "execution_join_ordinal": ordinal,
        "episode_index": execution["episode_index"],
        "decision_index": execution["decision_index"],
        "source_v109_execution_receipt_id": source_id,
        "online_plan_issuance_receipt_id": receipt[
            "online_plan_issuance_receipt_id"
        ],
        "typed_plan_source": receipt["typed_plan_source"],
        "chosen_action_key": execution["chosen_action_key"],
        "quotient_proposed_action_key": execution["quotient_proposed_action_key"],
        "chosen_action_matches_admitted_quotient_proposal": execution[
            "chosen_action_matches_admitted_quotient_proposal"
        ],
        "receipt_was_issued_before_plan_return": True,
        "receipt_changes_plan_or_action_order": False,
        "receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "online_execution_join_receipt_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_ONLINE_EXECUTION_JOIN_V172_DOMAIN, payload
        ),
    }


def _run_online_sequence(*args, **kwargs):
    trace: list[dict[str, Any]] = []
    token = _TRACE.set(trace)
    try:
        historical = _BASE_SEQUENCE(*args, **kwargs)
    finally:
        _TRACE.reset(token)
    flattened = [
        wrapper
        for episode in historical["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
    ]
    if not (
        len(flattened) == len(trace)
        and all(
            canonical_json_bytes(wrapper) == event["wrapper_bytes"]
            for wrapper, event in zip(flattened, trace, strict=True)
        )
    ):
        _fail("V172r1 independent online trace changed")
    index = {}
    cursor = 0
    for episode in historical["episodes"]:
        for wrapper in episode["abstract_plan_receipts"]:
            key = (episode["episode_index"], canonical_json_bytes(wrapper))
            if key in index:
                _fail("V172r1 independent wrapper identity is ambiguous")
            index[key] = trace[cursor]
            cursor += 1
    joins = []
    for execution in historical["all_actual_legality_conditioned_execution_receipts"]:
        event = index.get(
            (
                execution["episode_index"],
                canonical_json_bytes(execution["quotient_plan_receipt"]),
            )
        )
        if event is None:
            _fail("V172r1 independent execution lacks online receipt")
        joins.append(_execution_join(historical["sequence_id"], execution, event, len(joins)))
    histogram = {
        source: sum(event["receipt"]["typed_plan_source"] == source for event in trace)
        for source in TAXONOMY.values()
    }
    payload = {
        **{
            key: value
            for key, value in historical.items()
            if key not in {"schema", "sequence_id"}
        },
        "schema": "acfqp.online_typed_plan_receipt_sequence.v172",
        "source_v154_shape_sequence_id": historical["sequence_id"],
        "online_plan_issuance_receipts": [event["receipt"] for event in trace],
        "online_plan_issuance_receipt_count": len(trace),
        "online_execution_join_receipts": joins,
        "online_execution_join_receipt_count": len(joins),
        "online_typed_plan_source_histogram": histogram,
        "every_abstract_plan_receipt_issued_before_orderer_return": True,
        "every_executed_action_joins_prior_online_receipt": (
            len(joins) == historical["execution_step_count"]
        ),
        "delegate_plan_byte_identity_preserved": True,
        "online_receipt_changes_planning_or_execution": False,
        "online_receipt_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN, payload
        ),
    }


_SEQUENCE_SOURCE_PROXY = SimpleNamespace(
    CONSTRUCTION_K7_SEQUENCE_V154_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN,
)
_SEQUENCE_OUTPUT_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v172,
    CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN,
)
_ANNOTATOR_GLOBALS = dict(sequence_v168.__dict__)
_ANNOTATOR_GLOBALS.update(
    domains_v154=_SEQUENCE_SOURCE_PROXY,
    domains=_SEQUENCE_OUTPUT_PROXY,
)
_ANNOTATE = _clone(
    sequence_v168.annotate_applicable_plan_receipt_set_sequence_v168,
    _ANNOTATOR_GLOBALS,
)


def _config():
    config = v168.fifth_family_total_plan_receipt_set_campaign_config_v168()
    reservoir = reservoir_dispatch_config_v171()
    config["families"][RESERVOIR_DISPATCH_FAMILY] = dict(
        reservoir["families"][RESERVOIR_DISPATCH_FAMILY]
    )
    config["families"][RESERVOIR_DISPATCH_FAMILY][
        "maximum_acquisition_labels"
    ] = 2_048
    return config


_TARGET_FAMILIES = (*v168.TARGET_FAMILIES, RESERVOIR_DISPATCH_FAMILY)
_V160_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v172,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN,
)
_V160_GLOBALS = dict(v168._BASE_V160_OCCURRENCE_V168.__globals__)  # noqa: SLF001
_V160_GLOBALS.update(
    domains=_V160_DOMAIN_PROXY,
    _BUILDERS={
        **_V160_GLOBALS["_BUILDERS"],
        RESERVOIR_DISPATCH_FAMILY: build_reservoir_dispatch_adapter_v171,
    },
    run_certified_memoized_planner_sequence_v154=_run_online_sequence,
    annotate_applicable_plan_mode_sequence_v157=_ANNOTATE,
)
_BASE_V160 = _clone(v168._BASE_V160_OCCURRENCE_V168, _V160_GLOBALS)  # noqa: SLF001
_V166_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v166=domains.extension_content_id_v172,
    CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN,
    CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN=domains.CONSTRUCTION_K7_CAMPAIGN_V172_DOMAIN,
)
_V166_GLOBALS = dict(v166.__dict__)
_V166_GLOBALS.update(
    domains=_V166_DOMAIN_PROXY,
    _BASE_OCCURRENCE=_BASE_V160,
    TARGET_FAMILIES=_TARGET_FAMILIES,
)
_BASE_V166 = _clone(v166.build_fourth_family_sample_tax_occurrence_v166, _V166_GLOBALS)
_V168_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v168=domains.extension_content_id_v172,
    CONSTRUCTION_K7_OCCURRENCE_V168_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN,
)
_V168_GLOBALS = dict(v168.__dict__)
_V168_GLOBALS.update(
    domains=_V168_DOMAIN_PROXY,
    _BASE_V166_OCCURRENCE_V168=_BASE_V166,
    TARGET_FAMILIES=_TARGET_FAMILIES,
)
_BASE_V168 = _clone(v168.build_fifth_family_total_plan_receipt_set_occurrence_v168, _V168_GLOBALS)


def _replay_target(args):
    config, family, seed, bank_raw, verification_raw, classifier_raw = args
    return _BASE_V168(
        config,
        family=family,
        seed=seed,
        episode_indices=EPISODES,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_raw,
    )


def _exact_frozen(raw, *, count, digest, identity_key, identity, label):
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V172r1 independent frozen {label} changed")
    return document


def _verify_sequence(sequence):
    payload = {key: value for key, value in sequence.items() if key != "sequence_id"}
    if sequence.get("sequence_id") != domains.extension_content_id_v172(
        domains.CONSTRUCTION_K7_SEQUENCE_V172_DOMAIN, payload
    ):
        _fail("V172r1 independent sequence identity changed")
    receipts = sequence["online_plan_issuance_receipts"]
    joins = sequence["online_execution_join_receipts"]
    receipt_ids = set()
    for receipt in receipts:
        row_payload = {
            key: value
            for key, value in receipt.items()
            if key != "online_plan_issuance_receipt_id"
        }
        expected = domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_ONLINE_PLAN_ISSUANCE_V172_DOMAIN,
            row_payload,
        )
        if receipt.get("online_plan_issuance_receipt_id") != expected:
            _fail("V172r1 independent issuance identity changed")
        receipt_ids.add(expected)
    for join in joins:
        row_payload = {
            key: value
            for key, value in join.items()
            if key != "online_execution_join_receipt_id"
        }
        if not (
            join.get("online_execution_join_receipt_id")
            == domains.extension_content_id_v172(
                domains.CONSTRUCTION_K7_ONLINE_EXECUTION_JOIN_V172_DOMAIN,
                row_payload,
            )
            and join.get("online_plan_issuance_receipt_id") in receipt_ids
            and join.get("receipt_was_issued_before_plan_return") is True
        ):
            _fail("V172r1 independent join identity changed")


def verify_online_typed_plan_receipt_campaign_v172r1(
    preregistration_raw: bytes,
    campaign_raw: bytes,
    classifier_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
):
    preregistration = _exact_frozen(
        preregistration_raw,
        count=PREREGISTRATION_BYTE_COUNT,
        digest=PREREGISTRATION_SHA256,
        identity_key="preregistration_id",
        identity=PREREGISTRATION_ID,
        label="preregistration",
    )
    campaign = _exact_frozen(
        campaign_raw,
        count=CAMPAIGN_BYTE_COUNT,
        digest=CAMPAIGN_SHA256,
        identity_key="campaign_id",
        identity=CAMPAIGN_ID,
        label="campaign",
    )
    campaign_payload = {
        key: value for key, value in campaign.items() if key != "campaign_id"
    }
    if not (
        campaign["campaign_id"]
        == domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_CAMPAIGN_V172_DOMAIN, campaign_payload
        )
        and campaign["preregistration_id"] == preregistration["preregistration_id"]
        and preregistration["failed_v172_attempt_id_reused"] is False
        and preregistration["frozen_predecessors"][2]["failure_id"]
        == FAILED_V172_ID
    ):
        _fail("V172r1 independent campaign/preregistration join changed")
    config = _config()
    args = [
        (config, family, seed, bank_raw, bank_verification_raw, classifier_raw)
        for family, seed in TARGETS
    ]
    with ProcessPoolExecutor(max_workers=TARGET_WORKERS) as executor:
        replayed = list(executor.map(_replay_target, args))
    campaign_rows = campaign["target_occurrences"]
    if len(campaign_rows) != len(replayed) != 0:
        _fail("V172r1 independent target cardinality changed")
    total_receipts = total_joins = factor_avoided = query_avoided = 0
    histogram = {source: 0 for source in TAXONOMY.values()}
    verified_occurrence_ids = []
    for (family, seed), base, row in zip(TARGETS, replayed, campaign_rows, strict=True):
        if not (
            row["target_family"] == family
            and row["seed"] == seed
            and row["episode_indices"] == list(EPISODES)
            and canonical_json_bytes(row["progressive_prior_sequence"])
            == canonical_json_bytes(base["progressive_prior_sequence"])
            and canonical_json_bytes(row["progressive_strict_sequence"])
            == canonical_json_bytes(base["progressive_strict_sequence"])
            and row["factor_prior_sample_reduction_within_progressive_policy"]
            == base["factor_prior_sample_reduction_within_progressive_policy"]
            and row["query_policy_sample_reduction_vs_legacy_path_first"]
            == base["query_policy_sample_reduction_vs_legacy_path_first"]
        ):
            _fail("V172r1 independent target outcome replay changed")
        row_payload = {
            key: value for key, value in row.items() if key != "occurrence_id"
        }
        if row["occurrence_id"] != domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_OCCURRENCE_V172_DOMAIN, row_payload
        ):
            _fail("V172r1 independent occurrence identity changed")
        sequences = (
            row["progressive_prior_sequence"],
            row["progressive_strict_sequence"],
        )
        for sequence in sequences:
            _verify_sequence(sequence)
        row_receipts = sum(
            sequence["online_plan_issuance_receipt_count"] for sequence in sequences
        )
        row_joins = sum(
            sequence["online_execution_join_receipt_count"] for sequence in sequences
        )
        if not (
            row_receipts == row["online_plan_issuance_receipt_count"]
            and row_joins == row["online_execution_join_receipt_count"]
            and row_joins == sum(sequence["execution_step_count"] for sequence in sequences)
            and row["registered_gate"]["passed"] is True
        ):
            _fail("V172r1 independent occurrence receipt accounting changed")
        total_receipts += row_receipts
        total_joins += row_joins
        factor_avoided += row["factor_prior_sample_reduction_within_progressive_policy"]
        query_avoided += row["query_policy_sample_reduction_vs_legacy_path_first"]
        for source in histogram:
            histogram[source] += row["online_typed_plan_source_histogram"][source]
        verified_occurrence_ids.append(row["occurrence_id"])
    if not (
        campaign["target_occurrence_ids"] == verified_occurrence_ids
        and campaign["online_receipt_accounting"]["online_plan_issuance_receipt_count"]
        == total_receipts
        and campaign["online_receipt_accounting"]["online_execution_join_receipt_count"]
        == total_joins
        and campaign["online_receipt_accounting"][
            "total_factor_prior_labels_avoided_within_same_query_policy"
        ]
        == factor_avoided
        and campaign["online_receipt_accounting"][
            "total_query_policy_labels_avoided_vs_exact_path_first"
        ]
        == query_avoided
        and campaign["online_typed_plan_source_histogram"] == histogram
        and campaign["registered_gate"]["passed"] is True
        and factor_avoided > 0
        and query_avoided >= 0
        and campaign["online_receipts_change_planning_or_execution"] is False
        and campaign["online_receipts_are_model_or_safety_authority"] is False
        and campaign["query_local_exact_overlay_remains_only_safety_authority"] is True
        and campaign["complete_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    ):
        _fail("V172r1 independent aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.online_typed_plan_receipt_verification.v172r1",
        "preregistration_id": PREREGISTRATION_ID,
        "campaign_id": CAMPAIGN_ID,
        "preserved_failed_v172_id": FAILED_V172_ID,
        "verified_target_seeds": [seed for _, seed in TARGETS],
        "verified_occurrence_ids": verified_occurrence_ids,
        "verified_online_plan_issuance_receipt_count": total_receipts,
        "verified_online_execution_join_receipt_count": total_joins,
        "verified_online_typed_plan_source_histogram": histogram,
        "verified_factor_prior_labels_avoided": factor_avoided,
        "verified_query_policy_labels_avoided": query_avoided,
        "producer_free_target_outcome_reexecution": True,
        "producer_free_online_issuance_reconstruction": True,
        "producer_free_execution_join_reconstruction": True,
        "delegate_plan_byte_identity_independently_verified": True,
        "factor_prior_strict_sample_tax_reduction_independently_verified": True,
        "query_policy_noninferiority_independently_verified": True,
        "online_receipt_is_model_or_safety_authority": False,
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
        "verification_id": domains.extension_content_id_v172(
            domains.CONSTRUCTION_K7_VERIFICATION_V172_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V172r1 frozen independent verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_online_typed_plan_receipt_campaign_v172r1",
)
