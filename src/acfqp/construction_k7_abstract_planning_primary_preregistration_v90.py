"""Registered deterministic analysis contract for the frozen V89 evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v90 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("eabd16d", "2e78b52")
PREREGISTRATION_ID = "848a6858108179348d53176e6113eeae145c3ce4f18c4181268e482cf2384c28"
EXPECTED_CANONICAL_BYTE_COUNT = 3_755
EXPECTED_CANONICAL_SHA256 = "26992e59d2441e71481f5f9740f860eee63a08ffce142bd8fc8bce6722c3dd66"
V89_CAMPAIGN_ID = "00e954daeda5823e22a4c489dbf72a207570f36b8ad008488cd38d649d90aaed"
V89_CAMPAIGN_BYTE_COUNT = 2_444_947
V89_CAMPAIGN_SHA256 = "277a28d516d4c73c01f1e5d58441d7d74775a2fe3caac80e885d90dcf578f21d"
V89_VERIFICATION_ID = "6dd9d5c1dab579ef7e0192bc64d486b82468e56a28d1d7a92595505c77dc8f39"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "artifacts/world_model/v86_projected_disagreement_model.json",
    "artifacts/world_model/v87_action_applicability_model.json",
    "src/acfqp/construction_k7_domain_registry_extension_v90.py",
    "src/acfqp/generic_portable_coordinate_aligned_inputs_v64.py",
    "src/acfqp/generic_abstract_proposal_primary_audit_v63.py",
    "src/acfqp/abstract_planning_primary_audit_core_v90.py",
    "src/acfqp/generic_applicability_conditioned_planner_v58.py",
)
FROZEN_SOURCE_FACTS = (
    ("artifacts/world_model/v86_projected_disagreement_model.json", 136251, "30c5b8775ae05039a971c20c52450efb29fcc8b57d81a38f70c9567fd9ef2bec"),
    ("artifacts/world_model/v87_action_applicability_model.json", 2978, "b564c19963692a593f38c8b64520643b71d28fb2c274d998fcd439553d1f7fd4"),
    ("src/acfqp/construction_k7_domain_registry_extension_v90.py", 1524, "f5cabb79d3378f18f21953e8aa06b66e63871f262b71a3c0d1097b9fd7999c67"),
    ("src/acfqp/generic_portable_coordinate_aligned_inputs_v64.py", 8188, "78062f8962e6d44e23c758a62398cdd2dbed0bd07dfaf7491a9fcb25415b5252"),
    ("src/acfqp/generic_abstract_proposal_primary_audit_v63.py", 5143, "9b7ff227b0ee73d0ec8d08eafb6717e3af2168f8857322f9efdba81d3a4958c7"),
    ("src/acfqp/abstract_planning_primary_audit_core_v90.py", 7802, "1a2a066da7a1d857a0b3390d1d585f17365a982e6d556898b445254fd351e9f7"),
    ("src/acfqp/generic_applicability_conditioned_planner_v58.py", 14772, "afd72df879951c941cee9b2dbb59b4eb9847d69e1cacc17c166b3b8ae93a20a6"),
)


class ConstructionK7AbstractPlanningPrimaryPreregistrationV90Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractPlanningPrimaryPreregistrationV90Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.abstract_planning_primary_preregistration.v90",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_input": {
            "v89_campaign_id": V89_CAMPAIGN_ID,
            "v89_campaign_byte_count": V89_CAMPAIGN_BYTE_COUNT,
            "v89_campaign_sha256": V89_CAMPAIGN_SHA256,
            "v89_verification_id": V89_VERIFICATION_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v90_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V90),
            "frozen_before_registered_v90_full_audit": True,
        },
        "analysis_contract": {
            "posthoc_deterministic_audit_of_already_frozen_v89_evidence": True,
            "fresh_target_outcome_claimed": False,
            "target_episode_reexecution_forbidden": True,
            "ground_kernel_access_forbidden": True,
            "every_exact_transition_query_state_replanned_from_portable_inputs": True,
            "first_certified_action_must_equal_replayed_abstract_proposal": True,
            "non_proposed_ground_action_query_count_must_be_zero": True,
            "replayed_compute_and_state_counts_must_equal_v89_accounting": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
        },
        "registered_gate": {
            "required_occurrence_audit_count": 6,
            "proposal_mismatch_count": 0,
            "non_proposed_ground_action_query_count": 0,
            "multi_step_planning_primarily_in_abstract_model_required": True,
            "claim_scope": "FROZEN_V89_PERMUTATION_MATCHED_BALANCED_BATCH_WORKLOAD_ONLY",
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "worker_count": 1,
            "maximum_abstract_depth": 12,
            "maximum_abstract_support_branch_evaluations_per_plan": 1_000_000,
            "abstract_support_feasible_beam_width": 32,
        },
        "claim_boundary": {
            "v90_full_audit_executed": False,
            "multi_step_planning_primarily_in_abstract_model_verified": False,
            "sample_tax_reduction_inherited_from_v89": True,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v90(
            domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_PREREGISTRATION_V90_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AbstractPlanningPrimaryPreregistrationV90:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v90(
                domains.CONSTRUCTION_K7_ABSTRACT_PRIMARY_PREREGISTRATION_V90_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V90 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: AbstractPlanningPrimaryPreregistrationV90 | None = None


def freeze_abstract_planning_primary_preregistration_v90(
) -> AbstractPlanningPrimaryPreregistrationV90:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V90 live analysis sources differ from registered facts")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V90 preregistration changed")
    _CACHE = AbstractPlanningPrimaryPreregistrationV90(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "PREREGISTRATION_ID",
    "freeze_abstract_planning_primary_preregistration_v90",
)
