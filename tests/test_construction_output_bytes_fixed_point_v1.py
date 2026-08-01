from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-output-bytes-fixed-point-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _profile(
    label: str,
    *,
    role_cap: int = 64 * 1024,
    total_cap: int = 256 * 1024,
    max_iterations: int = 16,
) -> fixed_v1.OutputBytesFixedPointProfileV1:
    return fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=_id(f"{label}-renderer"),
        execution_identity_id=_id(f"{label}-execution"),
        role_byte_caps={
            role: role_cap
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_total_bytes=total_cap,
        max_iterations=max_iterations,
    )


def _renderer(
    candidate: int,
    *,
    padding_by_role: dict[str, int] | None = None,
    nonce: int | None = None,
) -> dict[str, bytes]:
    padding = padding_by_role or {}
    result: dict[str, bytes] = {}
    for index, role in enumerate(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES):
        document = {
            "artifact_role": role,
            "payload": f"role-{index}" + "x" * padding.get(role, 0),
        }
        if role == fixed_v1.OUTPUT_MANIFEST_ROLE:
            document["io.output_bytes"] = candidate
            document["ordered_artifact_roles"] = list(
                fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            )
        if nonce is not None:
            document["nonce"] = nonce
        result[role] = canonical_json_bytes(document)
    return result


def test_exact_fixed_point_replays_complete_role_bytes_without_authority() -> None:
    profile = _profile("success")
    result = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile,
        renderer=_renderer,
    )

    assert result.output_bytes == sum(
        len(raw) for raw in result.artifact_bytes_by_role.values()
    )
    assert tuple(result.artifact_bytes_by_role) == (
        fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    )
    assert result.iterations[0].candidate_output_bytes == 0
    assert result.iterations[-1].candidate_output_bytes == result.output_bytes
    assert result.iterations[-1].rendered_total_bytes == result.output_bytes
    assert all(
        current.candidate_output_bytes == previous.rendered_total_bytes
        and current.rendered_total_bytes >= current.candidate_output_bytes
        for previous, current in zip(result.iterations, result.iterations[1:])
    )
    assert result.same_candidate_determinism_replays == len(result.iterations)
    assert result.fixed_point_replay_count == 2
    assert result.render_invocation_count == 2 * len(result.iterations) + 2
    assert (
        fixed_v1.replay_output_bytes_fixed_point_v1(
            result=result,
            renderer=_renderer,
        )
        is result
    )

    document = result.to_document()
    assert document["exact_fixed_point_verified"] is True
    assert document["artifact_bytes_committed"] is False
    assert document["outer_finalization_wrapper_in_render_set"] is False
    assert document["fixed_point_covers_outer_wrapper_bytes"] is False
    assert document["operational_artifact_role_semantics_verified"] is False
    assert document["operational_artifact_write_authorized"] is False
    assert document["structural_mechanism_only"] is True
    assert document["renderer_identity_semantically_verified"] is False
    assert document["counter_record_authorized"] is False
    assert document["work_vector_authorized"] is False
    assert document["comparison_vector_authorized"] is False
    assert document["certificate_authorized"] is False
    assert document["official_execution_allowed"] is False


def test_role_set_order_and_embedded_role_are_strict() -> None:
    profile = _profile("roles")

    def missing(candidate: int) -> dict[str, bytes]:
        result = _renderer(candidate)
        result.pop(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES[-1])
        return result

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="mutated, reordered, omitted, or added",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=missing,
        )

    def reordered(candidate: int) -> dict[str, bytes]:
        source = _renderer(candidate)
        return {key: source[key] for key in reversed(tuple(source))}

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="mutated, reordered, omitted, or added",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=reordered,
        )

    def crossed_role(candidate: int) -> dict[str, bytes]:
        result = _renderer(candidate)
        role = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES[0]
        result[role] = canonical_json_bytes(
            {
                "artifact_role": fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES[1],
                "payload": "crossed",
            }
        )
        return result

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="role differs",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=crossed_role,
        )


def test_noncanonical_bytes_stale_claim_and_size_caps_fail_closed() -> None:
    profile = _profile("canonical")

    def noncanonical(candidate: int) -> dict[str, bytes]:
        result = _renderer(candidate)
        role = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES[0]
        result[role] = b'{"artifact_role": "BUSINESS_RESULT"}'
        return result

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="not canonical JSON bytes",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=noncanonical,
        )

    def stale_claim(candidate: int) -> dict[str, bytes]:
        result = _renderer(candidate)
        result[fixed_v1.OUTPUT_MANIFEST_ROLE] = canonical_json_bytes(
            {
                "artifact_role": fixed_v1.OUTPUT_MANIFEST_ROLE,
                "io.output_bytes": candidate + 1,
            }
        )
        return result

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="does not embed the exact candidate",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=stale_claim,
        )

    tiny_profile = _profile("tiny", role_cap=32, total_cap=1024)
    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="role byte cap",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=tiny_profile,
            renderer=_renderer,
        )


def test_same_candidate_nondeterminism_is_rejected() -> None:
    profile = _profile("nondeterministic")
    calls = 0

    def nondeterministic(candidate: int) -> dict[str, bytes]:
        nonlocal calls
        calls += 1
        return _renderer(candidate, nonce=calls)

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="nondeterministic for the same candidate",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=nondeterministic,
        )


def test_fixed_point_second_replay_detects_delayed_nondeterminism() -> None:
    profile = _profile("delayed-nondeterminism")
    calls_by_candidate: dict[int, int] = {}

    def delayed(candidate: int) -> dict[str, bytes]:
        count = calls_by_candidate.get(candidate, 0) + 1
        calls_by_candidate[candidate] = count
        # The first deterministic pair agrees.  A mutation appears only when
        # the already-converged candidate is rendered for the required replay.
        return _renderer(candidate, nonce=1 if count <= 2 else count)

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="fixed-point first replay changed",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=delayed,
        )


def test_decreasing_iteration_and_nonconvergence_are_rejected() -> None:
    decreasing_profile = _profile(
        "decreasing",
        role_cap=32 * 1024,
        total_cap=128 * 1024,
    )

    def decreasing(candidate: int) -> dict[str, bytes]:
        padding = 10_000 if candidate == 0 else 0
        return _renderer(
            candidate,
            padding_by_role={
                fixed_v1.OperationalArtifactRoleV1.BUSINESS_RESULT.value: padding
            },
        )

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="decreased and is not monotonic",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=decreasing_profile,
            renderer=decreasing,
        )

    nonconvergent_profile = _profile(
        "nonconvergent",
        role_cap=64 * 1024,
        total_cap=128 * 1024,
        max_iterations=3,
    )

    def growing(candidate: int) -> dict[str, bytes]:
        return _renderer(
            candidate,
            padding_by_role={
                fixed_v1.OperationalArtifactRoleV1.BUSINESS_RESULT.value: candidate
            },
        )

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="did not converge",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=nonconvergent_profile,
            renderer=growing,
        )


def test_role_mutation_on_a_later_iteration_is_rejected() -> None:
    profile = _profile("later-role-mutation")

    def mutate_after_zero(candidate: int) -> dict[str, bytes]:
        result = _renderer(candidate)
        if candidate > 0:
            result.pop(fixed_v1.OUTPUT_MANIFEST_ROLE)
        return result

    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="mutated, reordered, omitted, or added",
    ):
        fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=mutate_after_zero,
        )


def test_domains_are_centrally_registered_and_profile_role_caps_are_exact() -> None:
    assert fixed_v1.REQUESTED_PHASE3E_DOMAIN_TAGS == tuple(
        sorted(fixed_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)
    )
    assert len(fixed_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) == 5
    assert all(
        tag.startswith("acfqp:construction-output-bytes-")
        for tag in fixed_v1.REQUESTED_PHASE3E_DOMAIN_TAGS
    )
    assert set(fixed_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS

    caps = {
        role: 4096
        for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    }
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=_id("caps-renderer"),
        execution_identity_id=_id("caps-execution"),
        role_byte_caps=caps,
        max_total_bytes=32 * 1024,
        max_iterations=8,
    )
    assert tuple(profile.cap_by_role) == fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    assert set(profile.cap_by_role.values()) == {4096}

    incomplete = dict(caps)
    incomplete.pop(fixed_v1.OUTPUT_MANIFEST_ROLE)
    with pytest.raises(
        fixed_v1.ConstructionOutputBytesFixedPointV1Error,
        match="cover exactly",
    ):
        fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
            renderer_id=_id("bad-caps-renderer"),
            execution_identity_id=_id("bad-caps-execution"),
            role_byte_caps=incomplete,
        )
