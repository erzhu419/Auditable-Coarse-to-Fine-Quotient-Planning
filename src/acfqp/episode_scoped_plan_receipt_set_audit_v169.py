"""Audit per-episode receipt sets in the already frozen V168 campaign.

This is a post-hoc granularity audit, not a new target campaign.  It enumerates
every preregistered V168 episode rather than selecting a favorable window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v168 as domains_v168
from acfqp import construction_k7_domain_registry_extension_v169 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V168_CAMPAIGN_ID = (
    "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce"
)
V168_CAMPAIGN_BYTE_COUNT = 25_586_483
V168_CAMPAIGN_SHA256 = (
    "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5"
)
DIRECT_MODE = "DIRECT_GENERIC_FACTOR_PROGRAM"
MEMOIZED_MODE = "V115_MEMOIZED_COMPILED_PROGRAM"
REGISTERED_MODES = (DIRECT_MODE, MEMOIZED_MODE)
AUDIT_ID = "ecec75ea276cdd80627f162ab3e7a99caca236381ed7c0a07374d4b748ed78ef"
EXPECTED_CANONICAL_BYTE_COUNT = 17_662
EXPECTED_CANONICAL_SHA256 = (
    "10b0b93bef07a227d9354717aa2d96cce80cab41d899050da5cfe8001074139e"
)


class EpisodeScopedPlanReceiptSetAuditV169Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise EpisodeScopedPlanReceiptSetAuditV169Error(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _mode(plan: Mapping[str, Any]) -> str | None:
    if plan.get("schema") == "acfqp.generic_projected_program_memo_plan.v115":
        return MEMOIZED_MODE
    if plan.get("planning_source") == "COMPILED_FACTOR_PROGRAM_FALLBACK":
        return DIRECT_MODE
    return None


def _class(counts: Mapping[str, int]) -> str:
    modes = tuple(mode for mode in REGISTERED_MODES if counts[mode] > 0)
    if not modes:
        return "NONE"
    if modes == (DIRECT_MODE,):
        return "DIRECT_ONLY"
    if modes == (MEMOIZED_MODE,):
        return "MEMOIZED_ONLY"
    return "MIXED"


def _episode_row(occurrence, *, arm: str, sequence, episode):
    wrappers = episode["abstract_plan_receipts"]
    if any(
        type(wrapper) is not dict
        or type(wrapper.get("abstract_plan")) is not dict
        for wrapper in wrappers
    ):
        _fail("V169 episode abstract receipt inventory changed")
    counts = {mode: 0 for mode in REGISTERED_MODES}
    for wrapper in wrappers:
        mode = _mode(wrapper["abstract_plan"])
        if mode is not None:
            counts[mode] += 1
    receipt_class = _class(counts)
    payload = {
        "schema": "acfqp.episode_scoped_plan_receipt_set.v169",
        "source_v168_occurrence_id": occurrence["occurrence_id"],
        "source_v168_sequence_id": sequence["sequence_id"],
        "target_family": occurrence["target_family"],
        "seed": occurrence["seed"],
        "arm": arm,
        "episode_index": episode["episode_index"],
        "abstract_plan_receipt_count": len(wrappers),
        "registered_plan_receipt_count_by_mode": counts,
        "registered_plan_receipt_modes": [
            mode for mode in REGISTERED_MODES if counts[mode] > 0
        ],
        "registered_plan_receipt_set_class": receipt_class,
        "none_means_no_registered_compiled_receipt_not_no_execution_receipt": (
            receipt_class == "NONE"
        ),
        "source_sequence_all_executed_actions_have_v109_receipts": True,
        "source_sequence_query_local_exact_overlay_remains_only_safety_authority": True,
        "episode_receipt_set_changes_planning_or_execution": False,
        "episode_receipt_set_is_safety_authority": False,
    }
    return {
        **payload,
        "episode_receipt_set_id": domains.extension_content_id_v169(
            domains.CONSTRUCTION_K7_EPISODE_RECEIPT_SET_V169_DOMAIN, payload
        ),
    }


def build_episode_scoped_plan_receipt_set_audit_v169(
    v168_campaign_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v168_campaign_raw)
    if not (
        canonical_json_bytes(campaign) == v168_campaign_raw
        and len(v168_campaign_raw) == V168_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(v168_campaign_raw).hexdigest() == V168_CAMPAIGN_SHA256
        and campaign.get("campaign_id") == V168_CAMPAIGN_ID
        and campaign.get("registered_gate", {}).get("passed") is True
    ):
        _fail("V169 frozen V168 campaign changed")
    rows = []
    for occurrence in campaign["target_occurrences"]:
        for arm, key in (
            ("ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON", "progressive_prior_sequence"),
            ("STRICT_NO_PRIOR", "progressive_strict_sequence"),
        ):
            sequence = occurrence[key]
            if sequence.get("sequence_id") != _content_id(
                domains_v168.CONSTRUCTION_K7_SEQUENCE_V168_DOMAIN,
                {
                    name: value
                    for name, value in sequence.items()
                    if name != "sequence_id"
                },
            ):
                _fail("V169 source V168 sequence changed")
            actual = sequence["all_actual_legality_conditioned_execution_receipts"]
            if not (
                len(actual)
                == sequence["actual_legality_conditioned_execution_receipt_count"]
                == sequence["execution_step_count"]
                and sequence["all_executed_actions_have_v109_receipts"] is True
                and all(
                    receipt.get("schema")
                    == "acfqp.generic_dependency_revalidated_execution_receipt.v109"
                    and receipt.get("receipt_is_observation_not_safety_authority")
                    is True
                    and receipt.get(
                        "query_local_exact_overlay_remains_only_safety_authority"
                    )
                    is True
                    for receipt in actual
                )
            ):
                _fail("V169 source execution receipt boundary changed")
            rows.extend(
                _episode_row(
                    occurrence,
                    arm=arm,
                    sequence=sequence,
                    episode=episode,
                )
                for episode in sequence["episodes"]
            )
    histogram = {
        name: sum(row["registered_plan_receipt_set_class"] == name for row in rows)
        for name in ("DIRECT_ONLY", "MEMOIZED_ONLY", "MIXED", "NONE")
    }
    gate = {
        "all_preregistered_v168_episodes_enumerated": len(rows) == 16,
        "mixed_episode_receipt_set_observed": histogram["MIXED"] > 0,
        "none_episode_receipt_set_observed": histogram["NONE"] > 0,
        "none_retains_sequence_wide_v109_coverage": all(
            row["source_sequence_all_executed_actions_have_v109_receipts"]
            for row in rows
            if row["registered_plan_receipt_set_class"] == "NONE"
        ),
        "none_retains_query_local_certificate_authority": all(
            row[
                "source_sequence_query_local_exact_overlay_remains_only_safety_authority"
            ]
            for row in rows
            if row["registered_plan_receipt_set_class"] == "NONE"
        ),
        "episode_audit_does_not_change_planning_or_execution": all(
            row["episode_receipt_set_changes_planning_or_execution"] is False
            for row in rows
        ),
        "episode_audit_is_not_safety_authority": all(
            row["episode_receipt_set_is_safety_authority"] is False for row in rows
        ),
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.episode_scoped_plan_receipt_set_audit.v169",
        "source_v168_campaign": {
            "campaign_id": V168_CAMPAIGN_ID,
            "byte_count": V168_CAMPAIGN_BYTE_COUNT,
            "sha256": V168_CAMPAIGN_SHA256,
        },
        "audit_scope": "ALL_EPISODES_ALL_ARMS_ALL_OCCURRENCES_IN_FROZEN_V168",
        "receipt_set_rows": rows,
        "receipt_set_histogram": histogram,
        "registered_gate": gate,
        "post_hoc_granularity_audit_not_new_target_campaign": True,
        "favorable_window_selected": False,
        "episode_receipt_set_annotation_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "audit_id": domains.extension_content_id_v169(
            domains.CONSTRUCTION_K7_AUDIT_V169_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class EpisodeScopedPlanReceiptSetAuditV169:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    audit_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_episode_scoped_plan_receipt_set_audit_v169(v168_campaign_raw: bytes):
    document = build_episode_scoped_plan_receipt_set_audit_v169(v168_campaign_raw)
    raw = canonical_json_bytes(document)
    if AUDIT_ID != "0" * 64 and not (
        document["audit_id"] == AUDIT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V169 frozen audit changed")
    return EpisodeScopedPlanReceiptSetAuditV169(_ISSUER, raw, document["audit_id"])


__all__ = (
    "AUDIT_ID",
    "freeze_episode_scoped_plan_receipt_set_audit_v169",
)
