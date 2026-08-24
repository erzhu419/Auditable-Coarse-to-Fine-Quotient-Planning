"""Outcome-free preregistration for the additive V180r7r1 source repair.

The failed V180r7 occurrence is immutable.  This protocol records why its
construction-source call was malformed and fixes the only admissible repair:
inventory a bounded complete candidate namespace, compute the exact recursive
static closure against that namespace, and pass only the reachable subset to
the unchanged V2 closure builder.  It authorizes no occurrence and observes no
new scientific outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_all_path_fallback_execution_authorization_v180r7 as predecessor_authorization
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp import construction_k7_full_ground_fallback_execution_failure_freeze_v180r7 as predecessor_failure
from acfqp import construction_k7_recovery_eligible_source_closure_successor_v180r7r1 as closure_successor
from acfqp import phase3e_sealed_executor_v1 as sealed_runtime
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PREREGISTRATION_ID = (
    "30a0aa732e44389f9b246a3664bacf13f5465233c7a1e3a1782baac80dbf38b8"
)
EXPECTED_CANONICAL_BYTE_COUNT = 7_045
EXPECTED_CANONICAL_SHA256 = (
    "dc9852248e583060b6bce18b0c1cf3ec16d41d7fd0e6e8e1b6850948137cedaa"
)

FAILED_EXECUTION_BOUNDARY_COMMIT = (
    "fbf314a0d31acbe6e3055a9199c0a6f104492d0e"
)
PRESERVED_FAILURE_FREEZE_COMMIT = (
    "7345339ed5c4c31f7f2789932b5a4bf81dcc6213"
)
PRESERVED_AUTHORIZATION_ID = (
    "445851c4b3ceb25be1858e0c4c07e436631486efe12853db8fef4fdf9c5573e9"
)
PRESERVED_FAILURE_ID = (
    "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
)
PRESERVED_FAILURE_CANONICAL_SHA256 = (
    "b39a368f7299e44344108afeab84d8feef8c8a0dc19585f1a465c16557d62bdb"
)
PRESERVED_FAILURE_CANONICAL_BYTE_COUNT = 649
PRESERVED_RETAINED_INPUT_FACTS = (
    (
        ".tmp/recovery-eligible-retained-v1/SOURCE_BUNDLE_BINDING.json",
        4_405,
        "bf5d7f5292a4b38136b141745b9349bc4e86c2ab7e67592e8d25c19b5daa527f",
    ),
    (
        ".tmp/recovery-eligible-retained-v1/REUSABLE_RAPM_SNAPSHOT.json",
        388_638,
        "18056b6f1aba853cb3b705041be93bce31700c79d45fa894fd956b144f0e7823",
    ),
    (
        ".tmp/recovery-eligible-retained-v1/PROOF_DEPENDENCY_TRANSITION.json",
        859_154,
        "e2278f8b499b13f45ab1c8fcba29be9665d472d4cd9ab65e1ee124187bfbbe30",
    ),
)

# These are exact read-only diagnostics at the frozen failure boundary.  The
# diagnostic closure ID is deliberately not registered as production evidence.
FAILED_CANDIDATE_MODULE_COUNT = 1_951
FAILED_CANDIDATE_SOURCE_BYTE_COUNT = 49_436_039
FAILED_PRIMARY_ROOT_COUNT = 1
FAILED_DYNAMIC_ROOT_COUNT = 150
FAILED_TOTAL_ROOT_COUNT = 151
DIAGNOSTIC_REACHABLE_MODULE_COUNT = 307
DIAGNOSTIC_REACHABLE_SOURCE_BYTE_COUNT = 15_129_926

MAXIMUM_CANDIDATE_MODULE_COUNT = 4_096
MAXIMUM_CANDIDATE_SOURCE_BYTE_COUNT = 64 * 1024 * 1024
MAXIMUM_SOURCE_BYTES_PER_MODULE = 16 * 1024 * 1024
MAXIMUM_V2_REACHABLE_MODULE_COUNT = 1_024
MAXIMUM_RUNTIME_FILE_COUNT = 512
MAXIMUM_RUNTIME_TOTAL_BYTES = 16 * 1024 * 1024

SELECTOR_MODULE = (
    "acfqp.construction_k7_recovery_eligible_source_closure_successor_v180r7r1"
)
SELECTOR_ENTRYPOINT = (
    SELECTOR_MODULE + ":build_recovery_eligible_source_closure_successor_v180r7r1"
)
REQUIRE_SELECTOR_ENTRYPOINT = (
    SELECTOR_MODULE + ":require_recovery_eligible_source_closure_successor_v180r7r1"
)

_ROOT = Path(__file__).resolve().parents[2]
_BOUND_SOURCE_PATHS = (
    "src/acfqp/_v075_construction_source_runtime_v2.py",
    "src/acfqp/construction_k7_all_path_fallback_execution_authorization_v180r7.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r7.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r7r1.py",
    "src/acfqp/construction_k7_full_ground_fallback_execution_failure_freeze_v180r7.py",
    "src/acfqp/construction_k7_recovery_eligible_source_closure_successor_v180r7r1.py",
    "src/acfqp/construction_k7_recovery_eligible_supervised_executor_v1.py",
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/phase3e_sealed_executor_v1.py",
)

_REPAIR_STEPS = (
    "LOAD_AND_REPLAY_FROZEN_V180R7_FAILURE",
    "VALIDATE_SORTED_UNIQUE_ROOT_MODULES",
    "VALIDATE_COMPLETE_CALLER_SUPPLIED_CANDIDATE_KEYSET",
    "ENFORCE_CANDIDATE_COUNT_AND_TOTAL_SOURCE_BYTE_CAPS",
    "REPLAY_REGULAR_SYMLINK_FREE_SOURCE_BYTES",
    "PARSE_STATIC_ACFQP_IMPORTS_AGAINST_COMPLETE_CANDIDATE_NAMESPACE",
    "ADD_EVERY_REACHABLE_PARENT_PACKAGE",
    "ENFORCE_UNCHANGED_V2_REACHABLE_MODULE_CAP",
    "ENFORCE_RUNTIME_FILE_AND_TOTAL_BYTE_CAPS",
    "PASS_ONLY_EXACT_REACHABLE_SUBSET_TO_UNCHANGED_V2_BUILDER",
    "REQUIRE_V2_MODULE_SET_EQUALS_INDEPENDENTLY_DISCOVERED_REACHABLE_SET",
)


class FullGroundFallbackSourceInventoryPreregistrationV180r7r1Error(ValueError):
    """The preserved failure or the outcome-free repair protocol changed."""


def _source_facts() -> list[dict[str, Any]]:
    rows = []
    for relative_path in _BOUND_SOURCE_PATHS:
        raw = (_ROOT / relative_path).read_bytes()
        rows.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def _retained_input_facts() -> list[dict[str, Any]]:
    rows = []
    for relative_path, _byte_count, _sha256 in PRESERVED_RETAINED_INPUT_FACTS:
        raw = (_ROOT / relative_path).read_bytes()
        rows.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def build_full_ground_fallback_source_inventory_preregistration_v180r7r1(
) -> dict[str, Any]:
    frozen_failure = (
        predecessor_failure.load_frozen_full_ground_fallback_execution_failure_v180r7()
    )
    failure_document = frozen_failure.to_document()
    retained_input_facts = _retained_input_facts()
    expected_retained_input_facts = [
        {
            "relative_path": relative_path,
            "byte_count": byte_count,
            "sha256": sha256,
        }
        for relative_path, byte_count, sha256 in PRESERVED_RETAINED_INPUT_FACTS
    ]
    if not (
        predecessor_authorization.EXPECTED_AUTHORIZATION_ID
        == PRESERVED_AUTHORIZATION_ID
        and predecessor_failure.EXPECTED_FAILURE_ID == PRESERVED_FAILURE_ID
        and predecessor_failure.EXPECTED_CANONICAL_SHA256
        == PRESERVED_FAILURE_CANONICAL_SHA256
        and predecessor_failure.EXPECTED_CANONICAL_BYTE_COUNT
        == PRESERVED_FAILURE_CANONICAL_BYTE_COUNT
        and predecessor_authorization.EXPECTED_BINDING_BYTE_COUNT
        == PRESERVED_RETAINED_INPUT_FACTS[0][1]
        and predecessor_authorization.EXPECTED_BINDING_SHA256
        == PRESERVED_RETAINED_INPUT_FACTS[0][2]
        and predecessor_authorization.EXPECTED_SNAPSHOT_BYTE_COUNT
        == PRESERVED_RETAINED_INPUT_FACTS[1][1]
        and predecessor_authorization.EXPECTED_SNAPSHOT_SHA256
        == PRESERVED_RETAINED_INPUT_FACTS[1][2]
        and predecessor_authorization.EXPECTED_TRANSITION_BYTE_COUNT
        == PRESERVED_RETAINED_INPUT_FACTS[2][1]
        and predecessor_authorization.EXPECTED_TRANSITION_SHA256
        == PRESERVED_RETAINED_INPUT_FACTS[2][2]
        and frozen_failure.failure_id == PRESERVED_FAILURE_ID
        and failure_document["fallback_execution_authorization_id"]
        == PRESERVED_AUTHORIZATION_ID
        and failure_document["retained_output_file_count"] == 0
        and failure_document["same_authorization_rerun_forbidden"] is True
        and failure_document["success_claimed"] is False
        and source_runtime_v2.MAX_MODULES == MAXIMUM_V2_REACHABLE_MODULE_COUNT
        and source_runtime_v2.MAX_SOURCE_BYTES_PER_MODULE
        == MAXIMUM_SOURCE_BYTES_PER_MODULE
        and sealed_runtime.RUNTIME_MANIFEST_MAX_FILE_COUNT
        == MAXIMUM_RUNTIME_FILE_COUNT
        and sealed_runtime.RUNTIME_MANIFEST_MAX_TOTAL_BYTES
        == MAXIMUM_RUNTIME_TOTAL_BYTES
        and closure_successor.MAX_CANDIDATE_CATALOG_MODULES
        == MAXIMUM_CANDIDATE_MODULE_COUNT
        and closure_successor.MAX_CANDIDATE_CATALOG_SOURCE_BYTES
        == MAXIMUM_CANDIDATE_SOURCE_BYTE_COUNT
        and closure_successor.V2_MAX_REACHABLE_MODULES
        == MAXIMUM_V2_REACHABLE_MODULE_COUNT
        and closure_successor.MAX_RECOVERY_RUNTIME_FILES
        == MAXIMUM_RUNTIME_FILE_COUNT
        and closure_successor.MAX_RECOVERY_RUNTIME_SOURCE_BYTES
        == MAXIMUM_RUNTIME_TOTAL_BYTES
        and closure_successor.build_recovery_eligible_source_closure_successor_v180r7r1.__module__
        == SELECTOR_MODULE
        and closure_successor.require_recovery_eligible_source_closure_successor_v180r7r1.__module__
        == SELECTOR_MODULE
        and retained_input_facts == expected_retained_input_facts
    ):
        raise FullGroundFallbackSourceInventoryPreregistrationV180r7r1Error(
            "V180r7 failure or inherited finite caps changed"
        )

    payload = {
        "schema": (
            "acfqp.full_ground_fallback_source_inventory_preregistration."
            "v180r7r1"
        ),
        "preserved_failure": {
            "failed_execution_boundary_commit": (
                FAILED_EXECUTION_BOUNDARY_COMMIT
            ),
            "failure_freeze_commit": PRESERVED_FAILURE_FREEZE_COMMIT,
            "failed_authorization_id": PRESERVED_AUTHORIZATION_ID,
            "failure_id": PRESERVED_FAILURE_ID,
            "failure_canonical_byte_count": (
                PRESERVED_FAILURE_CANONICAL_BYTE_COUNT
            ),
            "failure_canonical_sha256": PRESERVED_FAILURE_CANONICAL_SHA256,
            "failure_type": failure_document["failure_type"],
            "failure_message": failure_document["failure_message"],
            "retained_output_file_count": 0,
            "runtime_cas_created": failure_document["cas_root_created"],
            "output_root_created": failure_document["output_root_created"],
            "same_failed_authorization_rerun_forbidden": True,
            "failed_evidence_must_remain_byte_identical": True,
        },
        "failure_diagnosis": {
            "failed_candidate_module_count": FAILED_CANDIDATE_MODULE_COUNT,
            "failed_candidate_source_byte_count": (
                FAILED_CANDIDATE_SOURCE_BYTE_COUNT
            ),
            "primary_runtime_root_count": FAILED_PRIMARY_ROOT_COUNT,
            "dynamic_v075_root_count": FAILED_DYNAMIC_ROOT_COUNT,
            "total_root_count": FAILED_TOTAL_ROOT_COUNT,
            "v2_input_module_cap": MAXIMUM_V2_REACHABLE_MODULE_COUNT,
            "malformed_predicate": (
                "len(module_sources) > _v075_construction_source_runtime_v2."
                "MAX_MODULES"
            ),
            "failure_preceded_static_closure_traversal": True,
            "retained_input_digest_and_canonical_checks_preceded_failure": True,
            "failure_preceded_runtime_cas_creation": True,
            "failure_preceded_worker_launch": True,
            "failure_preceded_scientific_outcome_access": True,
            "diagnostic_reachable_module_count": (
                DIAGNOSTIC_REACHABLE_MODULE_COUNT
            ),
            "diagnostic_reachable_source_byte_count": (
                DIAGNOSTIC_REACHABLE_SOURCE_BYTE_COUNT
            ),
            "diagnostic_reachable_set_within_unchanged_v2_cap": True,
            "diagnostic_reachable_set_within_runtime_manifest_caps": True,
            "diagnostic_closure_identity_registered_as_outcome_evidence": False,
        },
        "retained_predecessor_input_facts": retained_input_facts,
        "candidate_inventory_contract": {
            "inventory_kind": "EXACT_CALLER_SUPPLIED_COMPLETE_ACFQP_NAMESPACE",
            "maximum_candidate_module_count": MAXIMUM_CANDIDATE_MODULE_COUNT,
            "maximum_candidate_source_byte_count": (
                MAXIMUM_CANDIDATE_SOURCE_BYTE_COUNT
            ),
            "maximum_source_bytes_per_module": MAXIMUM_SOURCE_BYTES_PER_MODULE,
            "candidate_names_sources_and_paths_have_identical_keysets": True,
            "candidate_module_names_are_sorted_unique_and_validated": True,
            "candidate_source_byte_count_is_summed_before_ast_traversal": True,
            "candidate_paths_must_be_absolute_regular_and_symlink_free": True,
            "fresh_authorization_must_freeze_exact_candidate_facts": True,
            "unregistered_live_repository_files_are_not_authority": True,
            "candidate_namespace_scope": (
                "FROZEN_RECOVERY_WORKER_STATIC_RESOLUTION_NAMESPACE"
            ),
            "future_identity_wrappers_require_external_manifest_or_proven_exclusion": True,
            "authorization_source_must_not_contain_a_catalog_identity_that_hashes_itself": True,
        },
        "reachable_closure_contract": {
            "selector_entrypoint": SELECTOR_ENTRYPOINT,
            "strict_replay_entrypoint": REQUIRE_SELECTOR_ENTRYPOINT,
            "repair_steps": list(_REPAIR_STEPS),
            "unchanged_v2_reachable_module_cap": (
                MAXIMUM_V2_REACHABLE_MODULE_COUNT
            ),
            "runtime_manifest_file_cap": MAXIMUM_RUNTIME_FILE_COUNT,
            "runtime_manifest_total_byte_cap": MAXIMUM_RUNTIME_TOTAL_BYTES,
            "v2_max_modules_global_mutation_forbidden": True,
            "v2_builder_source_edit_forbidden": True,
            "candidate_cap_must_not_replace_reachable_closure_cap": True,
            "full_candidate_namespace_used_only_for_static_resolution": True,
            "only_exact_reachable_subset_passed_to_v2_builder": True,
            "every_reachable_parent_package_required": True,
            "independent_reachable_set_equality_required": True,
        },
        "source_facts": _source_facts(),
        "source_inventory_preregistration_wrapper_excluded_from_bound_sources": True,
        "claim_locks": {
            "same_failed_authorization_rerun": False,
            "retained_scientific_input_bytes_changed": False,
            "scientific_contract_changed": False,
            "algorithm_changed": False,
            "source_closure_transport_repair_only": True,
            "bounded_frozen_candidate_namespace_only": True,
            "open_world_source_completeness_claimed": False,
            "fresh_execution_authorization_issued": False,
            "fresh_fallback_execution_started": False,
            "production_outcome_accessed": False,
            "producer_free_verification_present": False,
            "success_claimed": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        },
        "construction_only": True,
        "preregistered_before_any_v180r7r1_outcome": True,
    }
    return {
        **payload,
        "source_inventory_preregistration_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_SOURCE_INVENTORY_PREREGISTRATION_V180R7R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackSourceInventoryPreregistrationV180r7r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("source_inventory_preregistration_id")
            == self.preregistration_id
        ):
            raise FullGroundFallbackSourceInventoryPreregistrationV180r7r1Error(
                "V180r7r1 preregistration is foreign or noncanonical"
            )

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1(
) -> FullGroundFallbackSourceInventoryPreregistrationV180r7r1:
    document = (
        build_full_ground_fallback_source_inventory_preregistration_v180r7r1()
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["source_inventory_preregistration_id"]
        == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise FullGroundFallbackSourceInventoryPreregistrationV180r7r1Error(
            "V180r7r1 source-inventory preregistration changed"
        )
    return FullGroundFallbackSourceInventoryPreregistrationV180r7r1(
        _ISSUER,
        raw,
        document["source_inventory_preregistration_id"],
    )


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PREREGISTRATION_ID",
    "FullGroundFallbackSourceInventoryPreregistrationV180r7r1",
    "FullGroundFallbackSourceInventoryPreregistrationV180r7r1Error",
    "build_full_ground_fallback_source_inventory_preregistration_v180r7r1",
    "freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1",
)
