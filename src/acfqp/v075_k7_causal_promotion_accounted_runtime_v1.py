"""Sealed worker for the non-fresh K7 causal-promotion occurrence.

The worker owns the full twelve-stage business execution.  It emits one
candidate-independent ``OPERATIONAL_TRACE`` document containing the exact
stage event/record/vector/projection documents and a globally metered business
SHA-256 count.  Accounting/provenance hashes used to serialize this trace are
outside the operational hash window; the trusted parent supplies process,
I/O, and wait4 peak evidence and later solves the final output-byte fixed
point.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import resource
import sys
from typing import Any


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_k7_causal_promotion_accounted_runtime_v1"
TRACE_SCHEMA = "acfqp.v075_k7_causal_promotion_operational_trace.v2"
TRACE_SCHEMA_VERSION = "2.0.0"
MODEL_EXPORT_TRACE_SCHEMA = (
    "acfqp.v075_k7_reusable_model_operational_trace.v1"
)
MODEL_EXPORT_TRACE_SCHEMA_VERSION = "1.0.0"
RECOVERY_EXPORT_TRACE_SCHEMA = (
    "acfqp.v075_k7_causal_recovery_operational_trace.v1"
)
RECOVERY_EXPORT_TRACE_SCHEMA_VERSION = "1.0.0"


class _BusinessHashMeterV1:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_BusinessHashMeterV1":
        if self._original is not None:
            raise RuntimeError("causal-promotion hash meter is single-use")
        self._original = hashlib.sha256

        def metered_sha256(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return self._original(*args, **kwargs)

        self._installed = metered_sha256
        hashlib.sha256 = metered_sha256  # type: ignore[assignment]
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        changed = hashlib.sha256 is not self._installed
        hashlib.sha256 = self._original  # type: ignore[assignment]
        if changed:
            raise RuntimeError("causal-promotion hash meter binding changed")


class _NamedObligationsV1:
    def __init__(self) -> None:
        self.integrity: list[str] = []
        self.protocol: list[str] = []

    def checked_integrity(self, name: str) -> None:
        if type(name) is not str or not name or name in self.integrity:
            raise RuntimeError("child integrity obligation is invalid or duplicated")
        self.integrity.append(name)

    def checked_protocol(self, name: str) -> None:
        if type(name) is not str or not name or name in self.protocol:
            raise RuntimeError("child protocol obligation is invalid or duplicated")
        self.protocol.append(name)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-source", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--trace-output", required=True, type=Path)
    parser.add_argument("--export-root-model", action="store_true")
    parser.add_argument("--export-recovery-chain", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.export_root_model and args.export_recovery_chain:
        raise RuntimeError("model and recovery exports are mutually exclusive")
    export_model = args.export_root_model or args.export_recovery_chain
    runtime_source = args.runtime_source.resolve(strict=True)
    sys.path.insert(0, str(runtime_source))

    # Infrastructure imports happen before the operational hash window.  The
    # fixture itself performs no work at import time.
    from acfqp import construction_accounting_live_v3 as live_v3
    from acfqp import construction_accounting_owned_runtime_v2 as owned_v2
    from acfqp import construction_accounting_registry_v6 as registry_v6
    from acfqp import v075_k7_causal_promotion_construction_fixture_v1 as fixture
    from acfqp import v075_k7_causal_promotion_terminal_authority_v1 as terminal_v1
    from acfqp.phase3e_ids import (
        V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN,
        V075_K7_CAUSAL_RECOVERY_OPERATIONAL_TRACE_V1_DOMAIN,
        V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN,
        CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN,
        V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN,
        canonical_json_bytes,
        content_id,
        loads_canonical_json,
        require_exact_fields,
    )

    obligations = _NamedObligationsV1()
    meter = _BusinessHashMeterV1()
    with meter:
        request_raw = args.request.read_bytes()
        request = loads_canonical_json(request_raw)
        if type(request) is not dict or canonical_json_bytes(request) != request_raw:
            raise RuntimeError("supervised request is not one canonical object")
        require_exact_fields(
            request,
            {
                "schema",
                "schema_version",
                "profile_key",
                "runtime_preparation_id",
                "runtime_tree_id",
                "construction_fixture_marker",
                "construction_only",
                "fresh_heldout_accessed",
                "official_execution_allowed",
                "supervised_request_id",
            },
            context="causal-promotion supervised request",
        )
        if (
            request["schema"]
            != "acfqp.v075_k7_causal_promotion_supervised_request.v1"
            or request["schema_version"] != SCHEMA_VERSION
            or request["profile_key"]
            != "v075_k7_causal_promotion_accounted_executor_v1"
            or request["construction_only"] is not True
            or request["fresh_heldout_accessed"] is not False
            or request["official_execution_allowed"] is not False
        ):
            raise RuntimeError("supervised request contract changed")
        request_payload = dict(request)
        observed_request_id = request_payload.pop("supervised_request_id")
        if observed_request_id != content_id(
            V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN,
            request_payload,
        ):
            raise RuntimeError("supervised request content ID mismatch")
        obligations.checked_integrity("request-canonical-and-content-id-replayed")
        obligations.checked_protocol("request-construction-only-profile-bound")

        result = fixture.run_v075_k7_causal_promotion_construction_fixture_v1(
            repository_root=runtime_source,
            marker=request["construction_fixture_marker"],
        )
        result_document = result.to_document()
        if (
            result_document["terminal_target_class"]
            != "ATTEMPT_CLOSURE_NONCERTIFICATE"
            or result_document["terminal_target_code"]
            != "ATTEMPT_BUDGET_EXHAUSTED"
            or result_document["observer_closed_and_exactly_reconciled"] is not True
            or result_document["official_execution_allowed"] is not False
        ):
            raise RuntimeError("causal-promotion terminal semantics changed")
        obligations.checked_integrity("terminal-identity-chain-replayed")
        obligations.checked_protocol("budget-exhaustion-route-outcome-replayed")
        budget_attestation = (
            terminal_v1
            .issue_v075_k7_causal_promotion_budget_replay_attestation_v1(
                budget_closure=result.budget_closure,
                budget_closure_verification=result.budget_closure_verification,
            )
        )
        budget_attestation_document = budget_attestation.to_document()
        terminal_v1.verify_v075_k7_causal_promotion_budget_replay_attestation_document_v1(
            budget_attestation_document
        )
        obligations.checked_integrity(
            "budget-closure-semantic-verification-consumed"
        )
        obligations.checked_protocol(
            "construction-terminal-mapping-prerequisites-frozen"
        )

        registry = registry_v6.official_counter_registry_v6()
        stage_profile = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(
            registry,
            comparison,
        )
        stages = result.accounting_result.recorded_stages
        if (
            len(stages) != 12
            or tuple(
                registry_v6.ConstructionStageKindV6(
                    row.stage_start.stage_kind.value
                )
                for row in stages
            )
            != owned_v2.CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
        ):
            raise RuntimeError("causal-promotion stage plan changed")
        obligations.checked_integrity("twelve-stage-inventory-replayed")
        stage_documents: list[dict[str, Any]] = []
        for index, recorded in enumerate(stages, 1):
            live_v3.verify_recorded_stage_work_v3(
                recorded,
                registry,
                stage_profile,
                comparison,
                actual,
            )
            if recorded.stage_start.stage_index != index:
                raise RuntimeError("causal-promotion stage sequence changed")
            stage_documents.append(recorded.to_document())
            obligations.checked_integrity(
                f"stage-{index:02d}-event-to-vector-replay"
            )
            obligations.checked_protocol(
                f"stage-{index:02d}-owner-and-sequence-binding"
            )

        occurrence_id = result.schedule.occurrence.occurrence_id
        accounted_occurrence_id = result.result_id
        owned_accounting_result_id = result.accounting_result.result_id
        science_summary = {
            "occurrence_id": occurrence_id,
            "accounted_occurrence_id": accounted_occurrence_id,
            "owned_accounting_result_id": owned_accounting_result_id,
            "schedule_id": result.schedule.schedule_id,
            "schedule_verification_id": result.schedule_verification.verification_id,
            "root_execution_id": result.root_execution.execution_id,
            "root_model_epoch_id": result.root_epoch.model_epoch_id,
            "causal_child_authorization_id": result.child_authorization.authorization_id,
            "causal_child_execution_bundle_id": result.child_execution.bundle_id,
            "causal_promotion_bundle_id": result.promotion_bundle.bundle_id,
            "budget_closure_id": result.budget_closure.closure_id,
            "budget_closure_verification_id": (
                result.budget_closure_verification.verification_id
            ),
            "budget_replay_attestation_id": budget_attestation.attestation_id,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "ATTEMPT_BUDGET_EXHAUSTED",
            "route_attempts": 1,
            "route_successes": 0,
            "route_failures": 1,
            "solver_attempts": 0,
            "solver_successes": 0,
            "solver_failures": 0,
            "observer_closed_and_exactly_reconciled": True,
            "stage_instance_count": len(stages),
            "stage_local_counter_record_count": sum(
                len(row.work_vector.records) for row in stages
            ),
        }
        obligations.checked_integrity("science-summary-derived-from-live-result")
        obligations.checked_protocol("route-and-solver-reconciliation-derived")

        causal_recovery_chain_document: dict[str, Any] | None = None
        if args.export_recovery_chain:
            root_proof = result.root_epoch.proof
            root_frontier = root_proof.failed_frontier
            final_epoch = result.promotion_bundle.final_epoch
            final_proof = final_epoch.proof
            final_frontier = final_proof.failed_frontier
            if root_frontier is None or final_frontier is None:
                raise RuntimeError("recovery export requires failed root/final proofs")
            chain_payload = {
                "schema": "acfqp.construction_k7_causal_recovery_chain.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "occurrence_id": occurrence_id,
                "root_model_epoch_id": result.root_epoch.model_epoch_id,
                "root_numerical_model_id": result.root_epoch.model.model_id,
                "root_proof_id": root_proof.proof_id,
                "root_frontier_id": root_frontier.frontier_id,
                "causal_child_authorization_id": (
                    result.child_authorization.authorization_id
                ),
                "causal_child_authorization_verification_id": (
                    result.child_authorization_verification.verification_id
                ),
                "causal_child_execution_bundle_id": result.child_execution.bundle_id,
                "causal_promotion_bundle_id": result.promotion_bundle.bundle_id,
                "final_model_epoch_id": final_epoch.model_epoch_id,
                "final_numerical_model_id": final_epoch.model.model_id,
                "final_proof_id": final_proof.proof_id,
                "final_frontier_id": final_frontier.frontier_id,
                "root_model_epoch": result.root_epoch.to_document(),
                "root_numerical_proof": root_proof.to_document(),
                "causal_child_authorization": (
                    result.child_authorization.to_document()
                ),
                "causal_child_authorization_verification": (
                    result.child_authorization_verification.to_document()
                ),
                "causal_child_execution_bundle": result.child_execution.to_document(),
                "causal_promotion_bundle": result.promotion_bundle.to_document(),
                "final_model_epoch": final_epoch.to_document(),
                "final_numerical_proof": final_proof.to_document(),
                "root_failed_proof_precedes_causal_authorization": True,
                "authorization_target_access_count": 0,
                "authorization_kernel_call_count": 0,
                "ground_acquisition_executed_after_authorization": True,
                "immutable_successor_epoch_present": True,
                "post_recovery_replanning_present": True,
                "source_occurrence_recovery_only": True,
                "fresh_query_rebinding_performed": False,
                "local_ground_recovery_authority_for_fresh_query": False,
                "final_plan_certificate_issued": False,
                "official_execution_allowed": False,
            }
            causal_recovery_chain_document = {
                **chain_payload,
                "causal_recovery_chain_id": content_id(
                    CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN,
                    chain_payload,
                ),
            }

    if meter.count <= 0:
        raise RuntimeError("causal-promotion business hash window is empty")
    peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    payload = {
        "artifact_role": "OPERATIONAL_TRACE",
        "schema": (
            RECOVERY_EXPORT_TRACE_SCHEMA
            if args.export_recovery_chain
            else (MODEL_EXPORT_TRACE_SCHEMA if args.export_root_model else TRACE_SCHEMA)
        ),
        "schema_version": (
            RECOVERY_EXPORT_TRACE_SCHEMA_VERSION
            if args.export_recovery_chain
            else (
                MODEL_EXPORT_TRACE_SCHEMA_VERSION
                if args.export_root_model
                else TRACE_SCHEMA_VERSION
            )
        ),
        "profile_key": PROFILE_KEY,
        "supervised_request_id": observed_request_id,
        "runtime_preparation_id": request["runtime_preparation_id"],
        "runtime_tree_id": request["runtime_tree_id"],
        "science_summary": science_summary,
        "budget_replay_attestation": budget_attestation_document,
        "recorded_stages": stage_documents,
        "business_hash_invocations": meter.count,
        "child_integrity_obligations": sorted(obligations.integrity),
        "child_protocol_obligations": sorted(obligations.protocol),
        "child_self_peak_working_bytes_diagnostic": peak_bytes,
        "hash_measurement_window_start": "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS",
        "hash_measurement_window_end": (
            "AFTER_STAGE_AND_TERMINAL_REPLAY_BEFORE_TRACE_PROVENANCE"
        ),
        "accounting_provenance_hashes_excluded": True,
        "global_hashlib_sha256_constructor_hook_present": True,
        "construction_only": True,
        "fresh_heldout_accessed": False,
        "formal_counter_record_issued_by_worker": False,
        "occurrence_vector_issued_by_worker": False,
        "official_execution_allowed": False,
    }
    if export_model:
        payload.update(
            {
                "root_numerical_model": result.root_epoch.model.to_document(),
                "root_model_id": result.root_epoch.model.model_id,
                "root_model_epoch_id": result.root_epoch.model_epoch_id,
                "model_occurrence_or_arm_fields_present": False,
                "model_threshold_fields_present": False,
                "model_private_law_access": False,
                "reusable_model_export_only": True,
            }
        )
    if args.export_recovery_chain:
        assert causal_recovery_chain_document is not None
        payload.update(
            {
                "causal_recovery_chain": causal_recovery_chain_document,
                "causal_recovery_chain_id": causal_recovery_chain_document[
                    "causal_recovery_chain_id"
                ],
                "reusable_model_export_only": False,
                "causal_recovery_export_only": True,
            }
        )
    trace_domain = (
        V075_K7_CAUSAL_RECOVERY_OPERATIONAL_TRACE_V1_DOMAIN
        if args.export_recovery_chain
        else (
            V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN
            if args.export_root_model
            else V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN
        )
    )
    document = {
        **payload,
        "operational_trace_id": content_id(
            trace_domain,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    descriptor = os.open(
        args.trace_output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        written = 0
        while written < len(raw):
            count = os.write(descriptor, raw[written:])
            if count <= 0:
                raise RuntimeError("operational trace write made no progress")
            written += count
    finally:
        os.close(descriptor)
    return 0


if __name__ == "__main__":  # pragma: no cover - executed by the supervisor
    raise SystemExit(main())
