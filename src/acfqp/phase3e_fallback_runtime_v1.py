"""Strict bubblewrap worker for the Phase-3E safe-chain ground fallback.

The worker is deliberately narrow.  It accepts one canonical request and one
read-only frozen Phase-3C bundle, reconstructs the registered safe-chain world,
revalidates query/build/action-catalogue/RAPM identities, and runs the capped
ground search once.  It does not receive a host-produced transition table and
does not emit semantic authority by itself.

When executed as a script, the address-space limit is installed before any
``acfqp`` module is imported.  The host later validates the exact output and
attestation bytes and mints the opaque trusted-runtime seal; it never reruns
the ground solver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence


REQUEST_SCHEMA = "acfqp.isolated_ground_fallback_request.v1"
OUTPUT_SCHEMA = "acfqp.isolated_ground_fallback_output.v1"
ATTESTATION_SCHEMA = "acfqp.isolated_ground_fallback_runtime_attestation.v1"
WORKING_SET_LIMIT_BYTES = 256 * 1024 * 1024


class IsolatedGroundFallbackRuntimeV1Error(ValueError):
    """The isolated request, frozen parent, or worker output is invalid."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _tree_measurement(root: Path) -> tuple[int, str, tuple[str, ...]]:
    files = tuple(
        sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file()
        )
    )
    digest = hashlib.sha256()
    total = 0
    for relative in files:
        raw = (root / relative).read_bytes()
        total += len(raw)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return total, digest.hexdigest(), files


def _bootstrap(runtime_source: Path) -> dict[str, Any]:
    runtime_root = str(runtime_source.resolve())
    if runtime_root not in sys.path:
        sys.path.insert(0, runtime_root)
    from acfqp.phase3e_ids import (  # pylint: disable=import-outside-toplevel
        GROUND_FALLBACK_ISOLATED_ATTESTATION_DOMAIN,
        GROUND_FALLBACK_ISOLATED_OUTPUT_DOMAIN,
        GROUND_FALLBACK_ISOLATED_REQUEST_DOMAIN,
        canonical_json_bytes,
        content_id,
        loads_canonical_json,
        parse_content_id,
        require_exact_fields,
    )

    return {
        "attestation_domain": GROUND_FALLBACK_ISOLATED_ATTESTATION_DOMAIN,
        "output_domain": GROUND_FALLBACK_ISOLATED_OUTPUT_DOMAIN,
        "request_domain": GROUND_FALLBACK_ISOLATED_REQUEST_DOMAIN,
        "canonical_json_bytes": canonical_json_bytes,
        "content_id": content_id,
        "loads_canonical_json": loads_canonical_json,
        "parse_content_id": parse_content_id,
        "require_exact_fields": require_exact_fields,
    }


@dataclass(frozen=True, slots=True)
class IsolatedGroundFallbackRequestV1:
    route_decision_context_id: str
    decision_point_id: str
    route_decision_id: str
    selected_upper_id: str
    route_attempt_id: str
    structural_id: str
    query_id: str
    build_epoch_id: str
    bound_ground_action_catalogue_id: str
    portable_rapm_id: str
    phase3c_manifest_sha256: str
    query_key: str
    constraint_delta: Fraction
    cap_profile: Mapping[str, Any]
    isolation_profile_id: str
    schema_version: str = "1.0.0"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REQUEST_SCHEMA,
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "route_decision_id": self.route_decision_id,
            "selected_upper_id": self.selected_upper_id,
            "route_attempt_id": self.route_attempt_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "bound_ground_action_catalogue_id": (
                self.bound_ground_action_catalogue_id
            ),
            "portable_rapm_id": self.portable_rapm_id,
            "phase3c_manifest_sha256": self.phase3c_manifest_sha256,
            "query_key": self.query_key,
            "constraint_delta": self.constraint_delta,
            "ground_fallback_cap_profile": dict(self.cap_profile),
            "isolation_profile_id": self.isolation_profile_id,
        }

    @property
    def request_id(self) -> str:
        from acfqp.phase3e_ids import (
            GROUND_FALLBACK_ISOLATED_REQUEST_DOMAIN,
            content_id,
        )

        return content_id(GROUND_FALLBACK_ISOLATED_REQUEST_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "IsolatedGroundFallbackRequestV1":
        from acfqp.phase3e_ids import parse_content_id, require_exact_fields

        expected = {
            "schema", "schema_version", "RouteDecisionContext_id",
            "decision_point_id", "route_decision_id", "selected_upper_id",
            "route_attempt_id", "structural_id", "query_id",
            "BuildEpoch_id", "bound_ground_action_catalogue_id", "portable_rapm_id",
            "phase3c_manifest_sha256", "query_key", "constraint_delta",
            "ground_fallback_cap_profile", "isolation_profile_id", "request_id",
        }
        require_exact_fields(document, expected, context="isolated fallback request")
        if document["schema"] != REQUEST_SCHEMA or document["schema_version"] != "1.0.0":
            raise IsolatedGroundFallbackRuntimeV1Error(
                "isolated fallback request schema/version mismatch"
            )
        for field in (
            "RouteDecisionContext_id", "decision_point_id", "route_decision_id",
            "selected_upper_id", "route_attempt_id",
            "structural_id", "query_id", "BuildEpoch_id",
            "bound_ground_action_catalogue_id", "portable_rapm_id",
            "phase3c_manifest_sha256", "isolation_profile_id", "request_id",
        ):
            parse_content_id(document[field])
        if not isinstance(document["ground_fallback_cap_profile"], Mapping):
            raise IsolatedGroundFallbackRuntimeV1Error(
                "ground fallback cap profile must be an object"
            )
        if type(document["query_key"]) is not str or not document["query_key"]:
            raise IsolatedGroundFallbackRuntimeV1Error(
                "isolated fallback query_key must be nonempty"
            )
        result = cls(
            document["RouteDecisionContext_id"], document["decision_point_id"],
            document["route_decision_id"], document["selected_upper_id"],
            document["route_attempt_id"], document["structural_id"],
            document["query_id"], document["BuildEpoch_id"],
            document["bound_ground_action_catalogue_id"],
            document["portable_rapm_id"], document["phase3c_manifest_sha256"],
            document["query_key"],
            Fraction(document["constraint_delta"]),
            dict(document["ground_fallback_cap_profile"]),
            document["isolation_profile_id"], document["schema_version"],
        )
        if document["request_id"] != result.request_id:
            raise IsolatedGroundFallbackRuntimeV1Error(
                "isolated fallback request content ID mismatch"
            )
        return result


def run_isolated(
    *,
    runtime_source: Path,
    phase3c_bundle: Path,
    request_path: Path,
    output_path: Path,
    attestation_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the frozen parent, execute once, and emit canonical evidence."""

    resource.setrlimit(
        resource.RLIMIT_AS,
        (WORKING_SET_LIMIT_BYTES, WORKING_SET_LIMIT_BYTES),
    )
    forbidden_roots = tuple(
        path
        for path in os.environ.get("ACFQP_FORBIDDEN_ROOTS", "").split(os.pathsep)
        if path
    )
    visible_forbidden_roots = tuple(
        path for path in forbidden_roots if Path(path).exists()
    )
    if visible_forbidden_roots:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback can see the host project checkout: "
            f"{visible_forbidden_roots!r}"
        )
    helpers = _bootstrap(runtime_source)
    from acfqp.frozen_phase3c import load_frozen_phase3c_world
    from acfqp.phase3e_fallback_v1 import (
        FALLBACK_ISOLATION_PROFILE_ID,
        GroundFallbackCapProfileV1,
        run_ground_fallback_search_v1,
        safe_chain_fallback_context_identity_v1,
    )

    if not sys.flags.no_site:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback runtime requires Python -S"
        )
    if output_path.parent.resolve() != attestation_path.parent.resolve():
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated result and attestation must share one output directory"
        )
    if tuple(output_path.parent.iterdir()):
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback output directory must start empty"
        )
    input_files = tuple(
        sorted(path.name for path in request_path.parent.iterdir() if path.is_file())
    )
    if input_files != (request_path.name,):
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback input directory must contain only request.json"
        )
    request_raw = request_path.read_bytes()
    request_doc = helpers["loads_canonical_json"](request_raw)
    if not isinstance(request_doc, Mapping):
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback request root must be an object"
        )
    request = IsolatedGroundFallbackRequestV1.from_dict(request_doc)
    if request.isolation_profile_id != FALLBACK_ISOLATION_PROFILE_ID:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback request uses another resource profile"
        )
    cap = GroundFallbackCapProfileV1.from_dict(request.cap_profile)
    world = load_frozen_phase3c_world(phase3c_bundle)
    identities = safe_chain_fallback_context_identity_v1(world)
    expected = {
        "structural_id": request.structural_id,
        "query_id": request.query_id,
        "build_epoch_id": request.build_epoch_id,
        "bound_ground_action_catalogue_id": request.bound_ground_action_catalogue_id,
        "portable_rapm_id": request.portable_rapm_id,
    }
    if any(identities[name] != value for name, value in expected.items()):
        raise IsolatedGroundFallbackRuntimeV1Error(
            "frozen query/build/action-catalogue/RAPM identity mismatch"
        )
    if world.source_manifest_sha256 != request.phase3c_manifest_sha256:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "frozen Phase-3C manifest identity mismatch"
        )
    # This profile registers one exact canonical safe-chain query.  Select it
    # by the frozen query key carried in the request rather than by position;
    # the content-addressed query_id check above additionally binds its bytes.
    matches = tuple(row for row in world.queries if row.query_key == request.query_key)
    if len(matches) != 1:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "frozen bundle does not contain exactly one requested query key"
        )
    query = matches[0].query
    if Fraction(query.delta) != request.constraint_delta:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "frozen query delta differs from isolated request"
        )

    raw = run_ground_fallback_search_v1(
        world.kernel,
        query,
        route_decision_context_id=request.route_decision_context_id,
        decision_point_id=request.decision_point_id,
        route_decision_id=request.route_decision_id,
        selected_upper_id=request.selected_upper_id,
        route_attempt_id=request.route_attempt_id,
        query_id=request.query_id,
        cap_profile=cap,
        recorder_id="phase3e_isolated_ground_fallback_worker_v1",
    )
    output_payload = {
        "schema": OUTPUT_SCHEMA,
        "schema_version": "1.0.0",
        "request_id": request.request_id,
        "ground_fallback_result": raw.result.to_dict(),
        "work_vector": raw.work_vector.to_dict(),
    }
    output_document = {
        **output_payload,
        "output_id": helpers["content_id"](
            helpers["output_domain"], output_payload
        ),
    }
    output_raw = helpers["canonical_json_bytes"](output_document)
    output_path.write_bytes(output_raw)

    loaded_module_origins: list[dict[str, str]] = []
    unexpected_module_origins: list[dict[str, str]] = []
    for name, module in sorted(sys.modules.items()):
        raw_origin = getattr(module, "__file__", None)
        if raw_origin is None:
            continue
        origin = str(Path(raw_origin).resolve())
        row = {"module": name, "origin": origin}
        loaded_module_origins.append(row)
        if not (origin.startswith("/usr/") or origin.startswith("/runtime-source/")):
            unexpected_module_origins.append(row)
    if unexpected_module_origins:
        raise IsolatedGroundFallbackRuntimeV1Error(
            "isolated fallback loaded code outside system/runtime mounts: "
            f"{unexpected_module_origins!r}"
        )

    runtime_bytes, runtime_sha, runtime_files = _tree_measurement(runtime_source)
    bundle_bytes, bundle_sha, bundle_files = _tree_measurement(phase3c_bundle)
    attestation_payload = {
        "schema": ATTESTATION_SCHEMA,
        "schema_version": "1.0.0",
        "request_id": request.request_id,
        "output_id": output_document["output_id"],
        "request_sha256": _sha256(request_raw),
        "output_sha256": _sha256(output_raw),
        "runtime_source_tree_sha256": runtime_sha,
        "runtime_source_tree_bytes": runtime_bytes,
        "runtime_source_files": list(runtime_files),
        "phase3c_bundle_tree_sha256": bundle_sha,
        "phase3c_bundle_bytes": bundle_bytes,
        "phase3c_bundle_files": list(bundle_files),
        "input_regular_files": list(input_files),
        "output_regular_files_before": [],
        "isolation_backend": "bubblewrap_mount_and_network_namespace",
        "network_namespace_unshared": True,
        "python_site_disabled": True,
        "project_checkout_visible": False,
        "visible_forbidden_roots": list(visible_forbidden_roots),
        "loaded_acfqp_modules": sorted(
            name
            for name in sys.modules
            if name == "acfqp" or name.startswith("acfqp.")
        ),
        "loaded_module_origins": loaded_module_origins,
        "unexpected_module_origins": unexpected_module_origins,
        "working_set_limit_bytes": WORKING_SET_LIMIT_BYTES,
        "peak_working_bytes": (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        ),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "hash_seed": os.environ.get("PYTHONHASHSEED", "unset"),
        "official_execution_allowed": False,
    }
    attestation = {
        **attestation_payload,
        "attestation_id": helpers["content_id"](
            helpers["attestation_domain"], attestation_payload
        ),
    }
    attestation_path.write_bytes(helpers["canonical_json_bytes"](attestation))
    return output_document, attestation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated safe-chain fallback")
    parser.add_argument("--runtime-source", type=Path, required=True)
    parser.add_argument("--phase3c-bundle", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run_isolated(
        runtime_source=args.runtime_source,
        phase3c_bundle=args.phase3c_bundle,
        request_path=args.request,
        output_path=args.output,
        attestation_path=args.attestation,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through bubblewrap
    raise SystemExit(main())


__all__ = [
    "ATTESTATION_SCHEMA",
    "IsolatedGroundFallbackRequestV1",
    "IsolatedGroundFallbackRuntimeV1Error",
    "OUTPUT_SCHEMA",
    "REQUEST_SCHEMA",
    "WORKING_SET_LIMIT_BYTES",
    "main",
    "run_isolated",
]
