"""Compile-time-blocked V20 activation-successor scaffold.

This revision is intentionally incapable of issuing consumer evidence, an
activation successor, a terminal closure, or any durable journal record.  It
may report which proposed V19 public names are visible for diagnostics, but
runtime discovery of those names can never unlock issuance.  A later positive
implementation requires a separate contract bump after the V19 binding seam
and its dependencies have been independently frozen and audited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_h1_lease_bound_three_birth_runtime_v1 as launch_v19


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = (
    "2.0.63-E-C-E5B-B2-D-V20-ACTIVATION-SUCCESSOR-BLOCKED-SCAFFOLD"
)
PROFILE_KEY = "construction_k7_h1_guardian_runtime_activation_successor_v1"
READINESS = "COMPILE_TIME_BLOCKED_SCAFFOLD_NO_SUCCESSOR_ISSUANCE"

CONSUMER_EVIDENCE_SCHEMA_SCAFFOLD_PRESENT = True
ACTIVATION_SUCCESSOR_SCHEMA_SCAFFOLD_PRESENT = True
SCHEMA_NAMES_RESERVED_ONLY = True
ISSUANCE_CODE_PRESENT = False
DURABLE_SUCCESSOR_JOURNAL_CODE_PRESENT = False
FRESH_V20_CONSUMER_EVIDENCE_PRESENT = False
FRESH_V20_ACTIVATION_SUCCESSOR_PRESENT = False
DURABLE_SUCCESSOR_ARTIFACT_PRESENT = False
V19_PUBLIC_CAPSULE_BINDING_SEAM_AVAILABLE = False
PUBLIC_SUCCESSOR_ISSUANCE_REACHABLE = False
NO_RAW_GRANT_OR_FD_ACCESSOR_PRESENT = True
NO_CONSUMER_CALLBACK_PRESENT = True

REQUIRED_V19_CAPSULE_BINDING_SEAM = (
    "prepare_lease_bound_three_birth_prebound_clone_v1",
    "verify_lease_bound_three_birth_prebound_clone_binding_v1",
    "cancel_lease_bound_three_birth_prebound_clone_v1",
)

PERMIT_CONSUMPTION_PATH_PRESENT = False
PREBOUND_NATIVE_EDGE_ACTIVATED = False
CLONE_SYSCALL_PERFORMED = False
ACTUAL_PROCESS_BIRTH_PRESENT = False
PROCESS_LAUNCH_COUNT_AUTHORITY_PRESENT = False
THREE_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"


class ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error(RuntimeError):
    """The blocked V20 scaffold was asked to issue successor authority."""


def _source_fact(path: Path, sha256: Any) -> tuple[int, int, int, int, str]:
    status = path.stat()
    raw = path.read_bytes()
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        sha256(raw).hexdigest(),
    )


def _build_blocked_prepare(error_type: type[RuntimeError]):
    # The error type and message live in this function's closure.  The body has
    # no dynamic seam lookup and no predecessor, path, object, journal, or
    # native-edge operation that could be reached by changing module globals.
    message = (
        "V20 activation-successor issuance is compile-time blocked in this "
        "scaffold; no object, journal record, permit consumption, or native "
        "edge was created"
    )

    def blocked_prepare(
        *,
        guardian_takeover: object,
        launch_preparation: object,
        prebound_capsule: object,
        journal_path: object,
    ) -> NoReturn:
        raise error_type(message)

    blocked_prepare.__name__ = "prepare_h1_guardian_runtime_activation_successor_v1"
    blocked_prepare.__qualname__ = blocked_prepare.__name__
    return blocked_prepare


def _build_surface_verifier(
    *,
    launch_module: Any,
    required_names: tuple[str, ...],
    source_paths: tuple[tuple[str, Path], ...],
    import_source_facts: tuple[tuple[str, tuple[int, int, int, int, str]], ...],
    sha256: Any,
    error_type: type[RuntimeError],
):
    expected_by_label = dict(import_source_facts)

    def verify_surface() -> dict[str, Any]:
        source_rows: list[dict[str, Any]] = []
        for label, path in source_paths:
            status = path.stat()
            raw = path.read_bytes()
            observed = (
                status.st_dev,
                status.st_ino,
                status.st_mode,
                status.st_size,
                sha256(raw).hexdigest(),
            )
            if observed != expected_by_label[label]:
                raise error_type(
                    f"V20 blocked activation-successor source changed: {label}"
                )
            source_rows.append(
                {
                    "label": label,
                    "device": observed[0],
                    "inode": observed[1],
                    "mode": observed[2],
                    "byte_count": observed[3],
                    "sha256": observed[4],
                }
            )

        exports = set(getattr(launch_module, "__all__", ()))
        rows = []
        for name in required_names:
            value = getattr(launch_module, name, None)
            rows.append(
                {
                    "name": name,
                    "exported": name in exports,
                    "callable": callable(value),
                    "owned_by_v19": (
                        callable(value)
                        and getattr(value, "__globals__", None)
                        is launch_module.__dict__
                    ),
                    "observation_is_diagnostic_only": True,
                }
            )
        observed_complete = all(
            row["exported"] and row["callable"] and row["owned_by_v19"]
            for row in rows
        )
        return {
            "schema": (
                "acfqp.k7_h1_guardian_runtime_v2_activation_successor_surface.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "readiness": READINESS,
            "source_closure": source_rows,
            "scaffold_only": True,
            "schema_names_reserved_only": True,
            "consumer_evidence_schema_scaffold_present": True,
            "activation_successor_schema_scaffold_present": True,
            "issuance_code_present": False,
            "durable_successor_journal_code_present": False,
            "fresh_v20_consumer_evidence_present": False,
            "fresh_v20_activation_successor_present": False,
            "durable_successor_artifact_present": False,
            "v19_public_capsule_binding_seam_observation": {
                "required_names": list(required_names),
                "rows": rows,
                "observed_complete": observed_complete,
                "authoritative": False,
            },
            # These are literal authority locks.  They do not depend on the
            # diagnostic rows above and cannot be upgraded by runtime names.
            "v19_public_capsule_binding_seam_available": False,
            "public_successor_issuance_reachable": False,
            "blocked_before_argument_validation": True,
            "blocked_before_predecessor_call": True,
            "blocked_before_path_resolution": True,
            "blocked_before_authority_object_creation": True,
            "blocked_before_successor_object_creation": True,
            "blocked_before_journal_open": True,
            "blocked_before_native_edge": True,
            "raw_grant_or_fd_accessor_present": False,
            "consumer_callback_present": False,
            "permit_consumption_path_present": False,
            "prebound_native_edge_activated": False,
            "clone_syscall_performed": False,
            "actual_process_birth_present": False,
            "process_launch_count_authority_present": False,
            "three_birth_prefix_authority_present": False,
            "five_birth_process_authority_present": False,
            "actual_observed_e3_v2_completion_present": False,
            "e4_v2_completion_present": False,
            "production_shared_resource_receipts_present": False,
            "fq11_counter_completeness_present": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_issued": False,
            "formal_comparison_vector_issued": False,
            "formal_actual_projection_proof_issued": False,
            "current_access_authority_present": False,
            "formal_v7_authority_present": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        }

    verify_surface.__name__ = (
        "verify_h1_guardian_runtime_activation_successor_surface_v1"
    )
    verify_surface.__qualname__ = verify_surface.__name__
    return verify_surface


_self_path = Path(__file__).resolve(strict=True)
_source_paths = (
    ("guardian_activation_successor_blocked_scaffold_v1", _self_path),
    ("lease_bound_three_birth_runtime_v1", Path(launch_v19.__file__).resolve(strict=True)),
)
_sha256 = hashlib.sha256
_source_facts = tuple(
    (label, _source_fact(path, _sha256)) for label, path in _source_paths
)

prepare_h1_guardian_runtime_activation_successor_v1 = _build_blocked_prepare(
    ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error
)
verify_h1_guardian_runtime_activation_successor_surface_v1 = _build_surface_verifier(
    launch_module=launch_v19,
    required_names=REQUIRED_V19_CAPSULE_BINDING_SEAM,
    source_paths=_source_paths,
    import_source_facts=_source_facts,
    sha256=_sha256,
    error_type=ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error,
)

# Do not leave a callable that can recapture substituted globals or rebaseline
# source/callable expectations after import.
del _build_blocked_prepare
del _build_surface_verifier
del _source_fact
del _self_path
del _source_paths
del _source_facts
del _sha256


__all__ = (
    "ACTIVATION_SUCCESSOR_SCHEMA_SCAFFOLD_PRESENT",
    "ACTUAL_PROCESS_BIRTH_PRESENT",
    "CLONE_SYSCALL_PERFORMED",
    "CONSUMER_EVIDENCE_SCHEMA_SCAFFOLD_PRESENT",
    "ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error",
    "DURABLE_SUCCESSOR_ARTIFACT_PRESENT",
    "DURABLE_SUCCESSOR_JOURNAL_CODE_PRESENT",
    "FRESH_V20_ACTIVATION_SUCCESSOR_PRESENT",
    "FRESH_V20_CONSUMER_EVIDENCE_PRESENT",
    "ISSUANCE_CODE_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PUBLIC_SUCCESSOR_ISSUANCE_REACHABLE",
    "READINESS",
    "REQUIRED_V19_CAPSULE_BINDING_SEAM",
    "SCHEMA_NAMES_RESERVED_ONLY",
    "SCHEMA_VERSION",
    "V19_PUBLIC_CAPSULE_BINDING_SEAM_AVAILABLE",
    "prepare_h1_guardian_runtime_activation_successor_v1",
    "verify_h1_guardian_runtime_activation_successor_surface_v1",
)
