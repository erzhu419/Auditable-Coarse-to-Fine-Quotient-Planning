"""Frozen post-hoc construction contract for the V170 receipt taxonomy.

V170 does not rerun or alter V168.  It totalizes every abstract-plan source in
the already frozen campaign and binds each executed action to the exact typed
plan instance embedded by its V109 execution receipt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v170 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[2]
V168_CAMPAIGN = (
    "v168_fifth_family_total_plan_receipt_set_campaign.json",
    25_586_483,
    "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5",
    "campaign_id",
    "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce",
)
V168_VERIFICATION = (
    "v168_fifth_family_total_plan_receipt_set_verification.json",
    10_215,
    "ecf1c0d10fc9cedc508353425cbf2c93533a52cbd2b07af2076eb5b9161cbc09",
    "verification_id",
    "11378538ea1d8340647b9e172f34c7e6f427a1d177a045074e596329c2cb8908",
)
V169_AUDIT = (
    "v169_episode_scoped_plan_receipt_set_audit.json",
    17_662,
    "10b0b93bef07a227d9354717aa2d96cce80cab41d899050da5cfe8001074139e",
    "audit_id",
    "ecec75ea276cdd80627f162ab3e7a99caca236381ed7c0a07374d4b748ed78ef",
)
V169_VERIFICATION = (
    "v169_episode_scoped_plan_receipt_set_verification.json",
    2_117,
    "5c05972664413f744cf92f187847c91341732ac8e15e6b76204fa034aa88f7df",
    "verification_id",
    "ef22b5bb5ca54f45baa8073bc4e767f712ed5eb9dab4876ae59190a5a617a507",
)

TAXONOMY = (
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "OBSERVATION_QUOTIENT_GRAPH",
        "OBSERVATION_DERIVED_QUOTIENT_ORDER",
    ),
    (
        "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "COMPILED_FACTOR_PROGRAM_FALLBACK",
        "DIRECT_COMPILED_PROGRAM_ORDER",
    ),
    (
        "acfqp.generic_dependency_revalidated_quotient_heuristic_plan.v109",
        "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
        "DEPENDENCY_REVALIDATED_QUOTIENT_REUSE",
    ),
    (
        "acfqp.generic_projected_program_memo_plan.v115",
        "COMPILED_FACTOR_PROGRAM_MEMOIZED",
        "SUCCESSOR_STATE_MEMOIZED_PROGRAM_REUSE",
    ),
)

CONTRACT_ID = "bb751f90d592f289cfcf1c00041a6b1f0579dc95c93a01b76a0598f0c2a0ae66"
EXPECTED_CANONICAL_BYTE_COUNT = 2_820
EXPECTED_CANONICAL_SHA256 = (
    "f527daa87f4389bfedd501ccb1eba21066413457bef1904abbaa5a7fec751575"
)


class ConstructionK7CompleteAbstractPlanReceiptTaxonomyContractV170Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CompleteAbstractPlanReceiptTaxonomyContractV170Error(message)


def _frozen(row):
    name, count, digest, identity_key, identity = row
    raw = (ROOT / ".tmp/exact-freeze" / name).read_bytes()
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V170 frozen predecessor changed: {name}")
    return document


def build_complete_abstract_plan_receipt_taxonomy_contract_v170():
    v168 = _frozen(V168_CAMPAIGN)
    v168_verification = _frozen(V168_VERIFICATION)
    v169 = _frozen(V169_AUDIT)
    v169_verification = _frozen(V169_VERIFICATION)
    if not (
        v168["registered_gate"]["passed"] is True
        and v168_verification[
            "fifth_family_factor_prior_sample_tax_transfer_independently_verified"
        ]
        is True
        and v169["registered_gate"]["passed"] is True
        and v169_verification["producer_free_all_episode_all_arm_reconstruction"]
        is True
    ):
        _fail("V170 predecessor gate changed")
    payload = {
        "schema": "acfqp.complete_abstract_plan_receipt_taxonomy_contract.v170",
        "frozen_predecessors": [
            {
                "name": row[0],
                "byte_count": row[1],
                "sha256": row[2],
                row[3]: row[4],
            }
            for row in (V168_CAMPAIGN, V168_VERIFICATION, V169_AUDIT, V169_VERIFICATION)
        ],
        "finite_typed_taxonomy": [
            {
                "plan_schema": schema,
                "planning_source": source,
                "typed_plan_source": typed,
            }
            for schema, source, typed in TAXONOMY
        ],
        "construction_scope": (
            "POST_HOC_TOTALIZATION_OF_ALL_ABSTRACT_PLAN_RECEIPTS_IN_FROZEN_V168"
        ),
        "required_joins": {
            "every_abstract_plan_instance_has_exactly_one_typed_receipt": True,
            "every_v109_executed_action_embeds_exactly_one_source_plan_instance": True,
            "every_executed_action_has_exactly_one_typed_plan_join_receipt": True,
            "unknown_plan_schema_or_planning_source_is_failure": True,
            "all_episodes_all_arms_all_occurrences_required": True,
        },
        "claim_boundary": {
            "post_hoc_taxonomy_not_new_target_campaign": True,
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
        },
    }
    return {
        **payload,
        "contract_id": domains.extension_content_id_v170(
            domains.CONSTRUCTION_K7_TAXONOMY_CONTRACT_V170_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CompleteAbstractPlanReceiptTaxonomyContractV170:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    contract_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_complete_abstract_plan_receipt_taxonomy_contract_v170():
    document = build_complete_abstract_plan_receipt_taxonomy_contract_v170()
    raw = canonical_json_bytes(document)
    if CONTRACT_ID != "0" * 64 and not (
        document["contract_id"] == CONTRACT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V170 frozen contract changed")
    return CompleteAbstractPlanReceiptTaxonomyContractV170(
        _ISSUER, raw, document["contract_id"]
    )


__all__ = (
    "CONTRACT_ID",
    "TAXONOMY",
    "freeze_complete_abstract_plan_receipt_taxonomy_contract_v170",
)
