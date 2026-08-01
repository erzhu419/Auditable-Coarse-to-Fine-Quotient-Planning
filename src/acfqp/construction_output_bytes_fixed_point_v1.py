"""Deterministic in-memory fixed point for operational output bytes.

An output set that embeds ``io.output_bytes`` cannot be written first and
patched later: the patch changes the byte count.  This module instead calls a
frozen renderer with a candidate total, validates exactly eight ordered
role-labelled canonical JSON blobs, and monotonically iterates until the
candidate equals the sum of their sizes.  Role semantics are not validated and
nothing is committed by this module.

The result is a *structural mechanism only*.  Renderer identity is supplied as
an opaque content ID and source semantics are not independently verified.
Consequently a successful fixed point does not authorize a CounterRecord,
WorkVector, ComparisonVector, certificate, or official execution.

All content domains are registered in the Phase 3E identity authority.  That
registration provides role separation only; it does not grant the renderer or
the resulting structural mechanism semantic authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from typing import Any, Callable, Mapping

from acfqp.phase3e_ids import (
    CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN,
    CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN,
    CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN,
    CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN,
    CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_output_bytes_fixed_point_v1"

OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN = (
    CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN
)
OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN = (
    CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN
)
OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN = (
    CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN
)
OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN = (
    CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN
)
OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN = (
    CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN,
    OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN,
    OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN,
    OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN,
    OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN,
)
LOCAL_DOMAIN_TAGS = frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS)

DEFAULT_MAX_ROLE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_ITERATIONS = 32
HARD_MAX_ROLE_BYTES = 256 * 1024 * 1024
HARD_MAX_TOTAL_BYTES = 1024 * 1024 * 1024
HARD_MAX_ITERATIONS = 256


class ConstructionOutputBytesFixedPointV1Error(ValueError):
    """A profile, render, iteration, or replay failed closed."""


class OperationalArtifactRoleV1(str, Enum):
    BUSINESS_RESULT = "BUSINESS_RESULT"
    OPERATIONAL_TRACE = "OPERATIONAL_TRACE"
    TERMINAL_ARTIFACT = "TERMINAL_ARTIFACT"
    COUNTER_RECORD_SET = "COUNTER_RECORD_SET"
    WORK_VECTOR = "WORK_VECTOR"
    COMPARISON_VECTOR = "COMPARISON_VECTOR"
    ACTUAL_PROJECTION_PROOF = "ACTUAL_PROJECTION_PROOF"
    OUTPUT_MANIFEST = "OUTPUT_MANIFEST"


REGISTERED_OPERATIONAL_ARTIFACT_ROLES = tuple(
    role.value for role in OperationalArtifactRoleV1
)
OUTPUT_MANIFEST_ROLE = OperationalArtifactRoleV1.OUTPUT_MANIFEST.value

RendererV1 = Callable[[int], Mapping[str, bytes]]


def _fail(message: str) -> None:
    raise ConstructionOutputBytesFixedPointV1Error(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionOutputBytesFixedPointV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _positive(value: Any, field_name: str, hard_cap: int) -> int:
    if type(value) is not int or value <= 0 or value > hard_cap:
        _fail(f"{field_name} must be a positive exact integer within its hard cap")
    return value


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{field_name} must be a nonnegative exact integer")
    return value


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionOutputBytesFixedPointV1Error(
            f"unknown {field_name} {value!r}"
        ) from error


def _content_id(domain_tag: str, payload: Mapping[str, Any]) -> str:
    if domain_tag not in LOCAL_DOMAIN_TAGS:
        _fail("output fixed-point content ID used an undeclared domain")
    return content_id(domain_tag, dict(payload))


@dataclass(frozen=True, slots=True)
class OperationalArtifactRoleCapV1:
    role: OperationalArtifactRoleV1
    max_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "role",
            _enum(OperationalArtifactRoleV1, self.role, "artifact role"),
        )
        _positive(self.max_bytes, "role byte cap", HARD_MAX_ROLE_BYTES)

    def to_document(self) -> dict[str, Any]:
        return {"artifact_role": self.role.value, "max_bytes": self.max_bytes}


@dataclass(frozen=True, slots=True)
class OutputBytesFixedPointProfileV1:
    renderer_id: str
    execution_identity_id: str
    role_caps: tuple[OperationalArtifactRoleCapV1, ...]
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_iterations: int = DEFAULT_MAX_ITERATIONS

    def __post_init__(self) -> None:
        _cid(self.renderer_id, "renderer")
        _cid(self.execution_identity_id, "execution identity")
        if (
            type(self.role_caps) is not tuple
            or any(
                type(item) is not OperationalArtifactRoleCapV1
                for item in self.role_caps
            )
            or tuple(item.role.value for item in self.role_caps)
            != REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        ):
            _fail("profile must contain the exact ordered operational artifact roles")
        _positive(
            self.max_total_bytes,
            "total output byte cap",
            HARD_MAX_TOTAL_BYTES,
        )
        _positive(
            self.max_iterations,
            "fixed-point iteration cap",
            HARD_MAX_ITERATIONS,
        )
        if any(item.max_bytes > self.max_total_bytes for item in self.role_caps):
            _fail("a per-role byte cap exceeds the total output cap")

    @property
    def cap_by_role(self) -> dict[str, int]:
        return {item.role.value: item.max_bytes for item in self.role_caps}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_output_bytes_fixed_point_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "renderer_id": self.renderer_id,
            "execution_identity_id": self.execution_identity_id,
            "role_caps": [item.to_document() for item in self.role_caps],
            "required_artifact_roles": list(
                REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            ),
            "output_manifest_role": OUTPUT_MANIFEST_ROLE,
            "output_value_field": "io.output_bytes",
            "max_total_bytes": self.max_total_bytes,
            "max_iterations": self.max_iterations,
            "initial_candidate": 0,
            "iteration_rule": "candidate_next=sum(role_byte_lengths)",
            "monotonic_total_required": True,
            "same_candidate_double_render_required": True,
            "fixed_point_second_replay_required": True,
            "commit_before_fixed_point_forbidden": True,
            "central_domain_registered": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id(
            OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_bytes_fixed_point_profile_id": self.profile_id}


def freeze_output_bytes_fixed_point_profile_v1(
    *,
    renderer_id: str,
    execution_identity_id: str,
    role_byte_caps: Mapping[str, int] | None = None,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> OutputBytesFixedPointProfileV1:
    """Freeze the exact role set and finite resource caps before rendering."""

    if role_byte_caps is None:
        caps = {
            role: min(DEFAULT_MAX_ROLE_BYTES, max_total_bytes)
            for role in REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        }
    else:
        if type(role_byte_caps) is not dict:
            _fail("role byte caps must be one exact dict")
        if set(role_byte_caps) != set(REGISTERED_OPERATIONAL_ARTIFACT_ROLES):
            _fail("role byte caps must cover exactly the registered role set")
        caps = dict(role_byte_caps)
    return OutputBytesFixedPointProfileV1(
        renderer_id=renderer_id,
        execution_identity_id=execution_identity_id,
        role_caps=tuple(
            OperationalArtifactRoleCapV1(OperationalArtifactRoleV1(role), caps[role])
            for role in REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        ),
        max_total_bytes=max_total_bytes,
        max_iterations=max_iterations,
    )


@dataclass(frozen=True, slots=True)
class RenderedOperationalArtifactV1:
    profile_id: str
    candidate_output_bytes: int
    role: OperationalArtifactRoleV1
    canonical_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _cid(self.profile_id, "artifact profile")
        _nonnegative(self.candidate_output_bytes, "candidate output bytes")
        role = _enum(OperationalArtifactRoleV1, self.role, "artifact role")
        object.__setattr__(self, "role", role)
        if type(self.canonical_bytes) is not bytes or not self.canonical_bytes:
            _fail("rendered artifact must be nonempty immutable bytes")
        try:
            document = loads_canonical_json(self.canonical_bytes)
        except ValueError as error:
            raise ConstructionOutputBytesFixedPointV1Error(
                "rendered artifact is not canonical JSON bytes"
            ) from error
        if type(document) is not dict:
            _fail("rendered artifact must be one canonical JSON object")
        if document.get("artifact_role") != role.value:
            _fail("rendered artifact role differs from its mapping role")
        embedded = document.get("io.output_bytes")
        if role is OperationalArtifactRoleV1.OUTPUT_MANIFEST:
            if type(embedded) is not int or embedded != self.candidate_output_bytes:
                _fail("output manifest does not embed the exact candidate byte total")
        elif "io.output_bytes" in document and (
            type(embedded) is not int or embedded != self.candidate_output_bytes
        ):
            _fail("artifact embeds a stale or noninteger output-byte candidate")

    @property
    def byte_count(self) -> int:
        return len(self.canonical_bytes)

    @property
    def bytes_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_output_bytes_rendered_artifact.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "output_bytes_fixed_point_profile_id": self.profile_id,
            "candidate_output_bytes": self.candidate_output_bytes,
            "artifact_role": self.role.value,
            "canonical_bytes_sha256": self.bytes_sha256,
            "canonical_byte_count": self.byte_count,
            "canonical_json_verified": True,
            "bytes_retained_in_memory_before_commit": True,
            "accounting_provenance_digest_only": True,
            "central_domain_registered": True,
        }

    @property
    def artifact_render_id(self) -> str:
        return _content_id(
            OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "output_bytes_rendered_artifact_id": self.artifact_render_id,
        }


@dataclass(frozen=True, slots=True)
class RenderedOperationalArtifactSetV1:
    profile_id: str
    candidate_output_bytes: int
    artifacts: tuple[RenderedOperationalArtifactV1, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _cid(self.profile_id, "artifact-set profile")
        _nonnegative(self.candidate_output_bytes, "artifact-set candidate")
        if (
            type(self.artifacts) is not tuple
            or tuple(item.role.value for item in self.artifacts)
            != REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or any(
                type(item) is not RenderedOperationalArtifactV1
                or item.profile_id != self.profile_id
                or item.candidate_output_bytes != self.candidate_output_bytes
                for item in self.artifacts
            )
        ):
            _fail("rendered artifact set changed its exact role/profile/candidate binding")

    @property
    def total_bytes(self) -> int:
        return sum(item.byte_count for item in self.artifacts)

    @property
    def bytes_by_role(self) -> dict[str, bytes]:
        return {item.role.value: item.canonical_bytes for item in self.artifacts}

    @property
    def sizes_by_role(self) -> dict[str, int]:
        return {item.role.value: item.byte_count for item in self.artifacts}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_output_bytes_rendered_artifact_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "output_bytes_fixed_point_profile_id": self.profile_id,
            "candidate_output_bytes": self.candidate_output_bytes,
            "artifact_render_ids": [
                item.artifact_render_id for item in self.artifacts
            ],
            "role_byte_counts": [
                {
                    "artifact_role": item.role.value,
                    "byte_count": item.byte_count,
                }
                for item in self.artifacts
            ],
            "rendered_total_bytes": self.total_bytes,
            "role_set_exact": True,
            "canonical_bytes_verified": True,
            "committed": False,
            "central_domain_registered": True,
        }

    @property
    def artifact_set_id(self) -> str:
        return _content_id(
            OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "output_bytes_rendered_artifact_set_id": self.artifact_set_id,
        }


@dataclass(frozen=True, slots=True)
class OutputBytesFixedPointIterationV1:
    profile_id: str
    iteration_index: int
    candidate_output_bytes: int
    rendered_total_bytes: int
    role_byte_counts: tuple[int, ...]
    artifact_set_id: str

    def __post_init__(self) -> None:
        _cid(self.profile_id, "iteration profile")
        _positive(self.iteration_index, "iteration index", HARD_MAX_ITERATIONS)
        _nonnegative(self.candidate_output_bytes, "iteration candidate")
        _positive(
            self.rendered_total_bytes,
            "iteration rendered total",
            HARD_MAX_TOTAL_BYTES,
        )
        if (
            type(self.role_byte_counts) is not tuple
            or len(self.role_byte_counts) != len(REGISTERED_OPERATIONAL_ARTIFACT_ROLES)
            or any(type(value) is not int or value <= 0 for value in self.role_byte_counts)
            or sum(self.role_byte_counts) != self.rendered_total_bytes
        ):
            _fail("iteration role byte counts do not exactly sum to its total")
        _cid(self.artifact_set_id, "iteration artifact set")
        if self.rendered_total_bytes < self.candidate_output_bytes:
            _fail("output-byte iteration decreased and is not monotonic")

    @property
    def converged(self) -> bool:
        return self.rendered_total_bytes == self.candidate_output_bytes

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_output_bytes_fixed_point_iteration.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "output_bytes_fixed_point_profile_id": self.profile_id,
            "iteration_index": self.iteration_index,
            "candidate_output_bytes": self.candidate_output_bytes,
            "rendered_total_bytes": self.rendered_total_bytes,
            "role_byte_counts": [
                {"artifact_role": role, "byte_count": byte_count}
                for role, byte_count in zip(
                    REGISTERED_OPERATIONAL_ARTIFACT_ROLES,
                    self.role_byte_counts,
                )
            ],
            "rendered_artifact_set_id": self.artifact_set_id,
            "monotonic_step": True,
            "converged": self.converged,
            "central_domain_registered": True,
        }

    @property
    def iteration_id(self) -> str:
        return _content_id(
            OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_bytes_fixed_point_iteration_id": self.iteration_id}


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OutputBytesFixedPointResultV1:
    _issuer: InitVar[object]
    profile: OutputBytesFixedPointProfileV1 = field(repr=False)
    iterations: tuple[OutputBytesFixedPointIterationV1, ...] = field(repr=False)
    fixed_artifacts: RenderedOperationalArtifactSetV1 = field(repr=False)
    render_invocation_count: int
    same_candidate_determinism_replays: int
    fixed_point_replay_count: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("output-byte fixed-point result is caller-minted")
        if type(self.profile) is not OutputBytesFixedPointProfileV1:
            _fail("fixed-point result lacks one exact profile")
        if (
            type(self.iterations) is not tuple
            or not self.iterations
            or len(self.iterations) > self.profile.max_iterations
            or any(
                type(item) is not OutputBytesFixedPointIterationV1
                or item.profile_id != self.profile.profile_id
                for item in self.iterations
            )
        ):
            _fail("fixed-point result has an invalid iteration trace")
        if self.iterations[0].candidate_output_bytes != 0:
            _fail("fixed-point iteration must begin at zero")
        for previous, current in zip(self.iterations, self.iterations[1:]):
            if (
                previous.converged
                or current.iteration_index != previous.iteration_index + 1
                or current.candidate_output_bytes != previous.rendered_total_bytes
            ):
                _fail("fixed-point iteration recurrence or terminal position changed")
        terminal = self.iterations[-1]
        if not terminal.converged:
            _fail("fixed-point result does not terminate at an exact equality")
        if (
            type(self.fixed_artifacts) is not RenderedOperationalArtifactSetV1
            or self.fixed_artifacts.profile_id != self.profile.profile_id
            or self.fixed_artifacts.candidate_output_bytes
            != terminal.candidate_output_bytes
            or self.fixed_artifacts.total_bytes != terminal.rendered_total_bytes
            or self.fixed_artifacts.artifact_set_id != terminal.artifact_set_id
        ):
            _fail("fixed artifact set differs from the terminal iteration")
        _positive(
            self.render_invocation_count,
            "render invocation count",
            HARD_MAX_ITERATIONS * 4,
        )
        _positive(
            self.same_candidate_determinism_replays,
            "same-candidate replay count",
            HARD_MAX_ITERATIONS * 2,
        )
        if self.same_candidate_determinism_replays != len(self.iterations):
            _fail("each candidate must receive exactly one deterministic comparison replay")
        if self.fixed_point_replay_count != 2:
            _fail("the converged fixed point requires exactly two further replays")
        if self.render_invocation_count != 2 * len(self.iterations) + 2:
            _fail("render invocation count does not cover all deterministic replays")

    @property
    def output_bytes(self) -> int:
        return self.fixed_artifacts.total_bytes

    @property
    def artifact_bytes_by_role(self) -> dict[str, bytes]:
        return self.fixed_artifacts.bytes_by_role

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_output_bytes_fixed_point_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "output_bytes_fixed_point_profile_id": self.profile.profile_id,
            "renderer_id": self.profile.renderer_id,
            "execution_identity_id": self.profile.execution_identity_id,
            "iteration_ids": [item.iteration_id for item in self.iterations],
            "fixed_artifact_set_id": self.fixed_artifacts.artifact_set_id,
            "io.output_bytes": self.output_bytes,
            "render_invocation_count": self.render_invocation_count,
            "same_candidate_determinism_replays": (
                self.same_candidate_determinism_replays
            ),
            "fixed_point_replay_count": self.fixed_point_replay_count,
            "strict_role_set_verified": True,
            "canonical_role_bytes_verified": True,
            "size_caps_verified": True,
            "monotonic_iteration_verified": True,
            "exact_fixed_point_verified": True,
            "fixed_point_second_replay_verified": True,
            "artifact_bytes_committed": False,
            "outer_finalization_wrapper_in_render_set": False,
            "fixed_point_covers_outer_wrapper_bytes": False,
            "operational_artifact_role_semantics_verified": False,
            "operational_artifact_write_authorized": False,
            "renderer_identity_semantically_verified": False,
            "structural_mechanism_only": True,
            "counter_record_authorized": False,
            "work_vector_authorized": False,
            "comparison_vector_authorized": False,
            "certificate_authorized": False,
            "official_execution_allowed": False,
            "central_domain_registered": True,
        }

    @property
    def result_id(self) -> str:
        return _content_id(
            OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_bytes_fixed_point_result_id": self.result_id}


def _render_once(
    *,
    renderer: RendererV1,
    profile: OutputBytesFixedPointProfileV1,
    candidate: int,
) -> RenderedOperationalArtifactSetV1:
    try:
        rendered = renderer(candidate)
    except Exception as error:
        raise ConstructionOutputBytesFixedPointV1Error(
            "output renderer raised before producing the eight-role candidate set"
        ) from error
    if type(rendered) is not dict:
        _fail("renderer must return one exact role-to-bytes dict")
    if tuple(rendered) != REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        _fail("renderer mutated, reordered, omitted, or added an artifact role")
    artifacts: list[RenderedOperationalArtifactV1] = []
    caps = profile.cap_by_role
    running_total = 0
    for role_name in REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        raw = rendered[role_name]
        if type(raw) is not bytes:
            _fail("renderer returned a non-bytes artifact")
        if len(raw) > caps[role_name]:
            _fail("rendered artifact exceeds its preregistered role byte cap")
        running_total += len(raw)
        if running_total > profile.max_total_bytes:
            _fail("rendered artifact set exceeds its preregistered total byte cap")
        artifacts.append(
            RenderedOperationalArtifactV1(
                profile_id=profile.profile_id,
                candidate_output_bytes=candidate,
                role=OperationalArtifactRoleV1(role_name),
                canonical_bytes=raw,
            )
        )
    result = RenderedOperationalArtifactSetV1(
        profile_id=profile.profile_id,
        candidate_output_bytes=candidate,
        artifacts=tuple(artifacts),
    )
    if result.total_bytes != running_total or result.total_bytes <= 0:
        _fail("rendered output total changed during in-memory materialization")
    return result


def _assert_same_render(
    first: RenderedOperationalArtifactSetV1,
    second: RenderedOperationalArtifactSetV1,
    *,
    reason: str,
) -> None:
    if (
        first.profile_id != second.profile_id
        or first.candidate_output_bytes != second.candidate_output_bytes
        or first.bytes_by_role != second.bytes_by_role
        or first.artifact_set_id != second.artifact_set_id
    ):
        _fail(reason)


def solve_output_bytes_fixed_point_v1(
    *,
    profile: OutputBytesFixedPointProfileV1,
    renderer: RendererV1,
) -> OutputBytesFixedPointResultV1:
    """Render in memory until an exact deterministic byte-count fixed point."""

    if type(profile) is not OutputBytesFixedPointProfileV1:
        _fail("fixed-point solve requires one exact profile")
    if not callable(renderer):
        _fail("fixed-point renderer must be callable")

    candidate = 0
    iterations: list[OutputBytesFixedPointIterationV1] = []
    invocations = 0
    for iteration_index in range(1, profile.max_iterations + 1):
        first = _render_once(renderer=renderer, profile=profile, candidate=candidate)
        second = _render_once(renderer=renderer, profile=profile, candidate=candidate)
        invocations += 2
        _assert_same_render(
            first,
            second,
            reason="renderer is nondeterministic for the same candidate",
        )
        total = first.total_bytes
        if total < candidate:
            _fail("output-byte iteration decreased and is not monotonic")
        iteration = OutputBytesFixedPointIterationV1(
            profile_id=profile.profile_id,
            iteration_index=iteration_index,
            candidate_output_bytes=candidate,
            rendered_total_bytes=total,
            role_byte_counts=tuple(
                first.sizes_by_role[role]
                for role in REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            ),
            artifact_set_id=first.artifact_set_id,
        )
        iterations.append(iteration)
        if total == candidate:
            replay_one = _render_once(
                renderer=renderer,
                profile=profile,
                candidate=candidate,
            )
            replay_two = _render_once(
                renderer=renderer,
                profile=profile,
                candidate=candidate,
            )
            invocations += 2
            _assert_same_render(
                first,
                replay_one,
                reason="fixed-point first replay changed the rendered bytes",
            )
            _assert_same_render(
                first,
                replay_two,
                reason="fixed-point second replay changed the rendered bytes",
            )
            return OutputBytesFixedPointResultV1(
                _RESULT_ISSUER,
                profile,
                tuple(iterations),
                first,
                invocations,
                len(iterations),
                2,
            )
        candidate = total
    _fail("output-byte fixed point did not converge within the iteration cap")


def replay_output_bytes_fixed_point_v1(
    *,
    result: OutputBytesFixedPointResultV1,
    renderer: RendererV1,
) -> OutputBytesFixedPointResultV1:
    """Replay the final candidate twice without granting semantic authority."""

    if type(result) is not OutputBytesFixedPointResultV1:
        _fail("fixed-point replay requires one issued structural result")
    if not callable(renderer):
        _fail("fixed-point replay renderer must be callable")
    first = _render_once(
        renderer=renderer,
        profile=result.profile,
        candidate=result.output_bytes,
    )
    second = _render_once(
        renderer=renderer,
        profile=result.profile,
        candidate=result.output_bytes,
    )
    _assert_same_render(
        result.fixed_artifacts,
        first,
        reason="independent fixed-point replay differs from the sealed role bytes",
    )
    _assert_same_render(
        result.fixed_artifacts,
        second,
        reason="independent fixed-point second replay differs from the sealed role bytes",
    )
    if first.total_bytes != result.output_bytes:
        _fail("independent replay no longer satisfies the exact fixed point")
    return result


__all__ = [
    "ConstructionOutputBytesFixedPointV1Error",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_MAX_ROLE_BYTES",
    "DEFAULT_MAX_TOTAL_BYTES",
    "OperationalArtifactRoleCapV1",
    "OperationalArtifactRoleV1",
    "OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN",
    "OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN",
    "OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN",
    "OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN",
    "OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN",
    "OUTPUT_MANIFEST_ROLE",
    "OutputBytesFixedPointIterationV1",
    "OutputBytesFixedPointProfileV1",
    "OutputBytesFixedPointResultV1",
    "PROFILE_KEY",
    "REGISTERED_OPERATIONAL_ARTIFACT_ROLES",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "RenderedOperationalArtifactSetV1",
    "RenderedOperationalArtifactV1",
    "SCHEMA_VERSION",
    "freeze_output_bytes_fixed_point_profile_v1",
    "replay_output_bytes_fixed_point_v1",
    "solve_output_bytes_fixed_point_v1",
]
