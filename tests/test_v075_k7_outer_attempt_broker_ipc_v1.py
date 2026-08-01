from __future__ import annotations

import json

import pytest

from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
)
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc


def _id(label: str) -> str:
    return __import__("hashlib").sha256(
        b"acfqp:k7-outer-broker-ipc-test:v1\x00" + label.encode("ascii")
    ).hexdigest()


def _binding(label: str = "main") -> ipc.K7OuterAttemptBrokerIPCBindingV1:
    return ipc.K7OuterAttemptBrokerIPCBindingV1(
        _id(f"request-{label}"),
        _id(f"route-{label}"),
        _id(f"spec-{label}"),
        _id(f"nonce-{label}"),
    )


def _frames():
    role = ipc.K7OuterAttemptBrokerFrameRoleV1
    return (
        (role.WORKER_READY, {"worker_replay_id": _id("worker-replay")}),
        (role.BUSINESS_REQUEST, {"request_ordinal": 0}),
        (role.BUSINESS_RESULT, {"business_result_id": _id("business-result")}),
        (
            role.PARENT_OUTPUT,
            {"output_byte_count": 321, "output_sha256": _id("parent")},
        ),
        (role.WORKER_EOF, {"clean_close": True}),
    )


def _stream(binding=None) -> bytes:
    return ipc.encode_v075_k7_outer_attempt_broker_ipc_stream_v1(
        binding=_binding() if binding is None else binding,
        frames=_frames(),
    )


def _split(raw: bytes) -> list[bytes]:
    result: list[bytes] = []
    offset = 0
    while offset < len(raw):
        size = int(raw[offset : offset + ipc.FRAME_WIDTH], 16)
        end = offset + ipc.FRAME_WIDTH + size
        result.append(raw[offset:end])
        offset = end
    assert offset == len(raw)
    return result


def _body(framed: bytes) -> bytes:
    return framed[ipc.FRAME_WIDTH :]


def _frame(raw_body: bytes) -> bytes:
    return f"{len(raw_body):0{ipc.FRAME_WIDTH}x}".encode("ascii") + raw_body


def test_complete_stream_is_canonical_bound_and_structural_only() -> None:
    binding = _binding()
    profile = ipc.official_v075_k7_outer_attempt_broker_ipc_profile_v1()
    profile_document = profile.to_document()
    assert profile_document["proposed_contract_version"] == "2.0.4"
    assert profile_document["profile_key"] == ipc.PROFILE_KEY
    assert profile_document["frame_roles"] == [
        role.value for role in ipc.FRAME_ROLES
    ]
    assert profile_document["formal_locks"]
    assert set(profile_document["formal_locks"].values()) == {False}
    assert profile_document["launch_authority"] is False
    assert profile_document["caller_constructed_binding_allowed"] is True
    assert profile_document["live_session_nonce_consumption_implemented"] is False
    assert profile_document["live_peer_role_ownership_verified"] is False
    raw = _stream(binding)
    transcript = ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
        raw=raw,
        expected_binding=binding,
    )
    document = transcript.to_document()

    assert tuple(frame.role for frame in transcript.frames) == ipc.FRAME_ROLES
    assert [frame.sequence for frame in transcript.frames] == list(range(5))
    assert document["frame_roles"] == [role.value for role in ipc.FRAME_ROLES]
    assert document["frame_count"] == 5
    assert document["request_id"] == binding.request_id
    assert document["fixed_sequence_verified"] is True
    assert document["canonical_length_prefix_verified"] is True
    assert document["role_payload_schema_verified"] is True
    assert document["payload_semantics_verified"] is False
    assert document["structural_ipc_only"] is True
    assert document["formal_locks"]
    assert set(document["formal_locks"].values()) == {False}
    assert ipc.LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS
    for framed in _split(raw):
        size = len(_body(framed))
        assert framed[: ipc.FRAME_WIDTH] == f"{size:08x}".encode("ascii")


def test_verified_payload_is_immutable_and_document_access_is_a_copy() -> None:
    transcript = ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
        raw=_stream(),
        expected_binding=_binding(),
    )
    frame = transcript.frames[1]
    original_id = frame.frame_id
    with pytest.raises(TypeError):
        frame.payload["request_ordinal"] = 1  # type: ignore[index]
    document = frame.to_document()
    document["payload"]["request_ordinal"] = 1
    assert frame.payload["request_ordinal"] == 0
    assert frame.frame_id == original_id
    assert transcript.transcript_id


def test_duplicate_reorder_omission_and_extra_frames_fail_closed() -> None:
    binding = _binding()
    parts = _split(_stream(binding))
    attacks = (
        b"".join((parts[0], parts[0], *parts[2:])),
        b"".join((parts[1], parts[0], *parts[2:])),
        b"".join(parts[:-1]),
        b"".join((*parts, parts[-1])),
    )
    for attack in attacks:
        with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
            ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
                raw=attack,
                expected_binding=binding,
            )

    duplicated = list(_frames())
    duplicated[1] = duplicated[0]
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="duplicated, omitted, or out of order",
    ):
        ipc.encode_v075_k7_outer_attempt_broker_ipc_stream_v1(
            binding=binding,
            frames=tuple(duplicated),
        )


def test_cross_attempt_and_one_frame_transplant_fail_closed() -> None:
    original = _binding("original")
    foreign = _binding("foreign")
    raw = _stream(original)
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="crossed its attempt binding",
    ):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=raw,
            expected_binding=foreign,
        )

    parts = _split(raw)
    foreign_parts = _split(_stream(foreign))
    parts[2] = foreign_parts[2]
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="crossed its attempt binding",
    ):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=b"".join(parts),
            expected_binding=original,
        )


def test_noncanonical_json_header_and_trailing_bytes_are_rejected() -> None:
    binding = _binding()
    parts = _split(_stream(binding))

    noncanonical_body = _body(parts[0]) + b"\n"
    noncanonical = b"".join((_frame(noncanonical_body), *parts[1:]))
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="not canonical JSON",
    ):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=noncanonical,
            expected_binding=binding,
        )

    header = parts[0][: ipc.FRAME_WIDTH]
    upper_header = header.upper()
    if upper_header == header:
        # Force an equivalent, noncanonical header by using a leading plus.
        upper_header = b"+" + header[1:]
    malformed_header = b"".join((upper_header, _body(parts[0]), *parts[1:]))
    with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=malformed_header,
            expected_binding=binding,
        )

    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="extra, or trailing",
    ):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=_stream(binding) + b"x",
            expected_binding=binding,
        )


@pytest.mark.parametrize("field", ["sequence", "payload_byte_count"])
def test_bool_cannot_substitute_for_protocol_integer(field: str) -> None:
    binding = _binding()
    parts = _split(_stream(binding))
    document = loads_canonical_json(_body(parts[0]))
    assert type(document) is dict
    document[field] = True
    parts[0] = _frame(canonical_json_bytes(document))
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="exact integer|digest or exact byte count",
    ):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=b"".join(parts),
            expected_binding=binding,
        )


def test_payload_digest_identity_unknown_field_and_caps_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _binding()
    parts = _split(_stream(binding))
    for field, value in (
        ("payload_sha256", "0" * 64),
        ("outer_attempt_broker_ipc_frame_id", "0" * 64),
        ("unknown", False),
    ):
        document = loads_canonical_json(_body(parts[0]))
        assert type(document) is dict
        document[field] = value
        changed = list(parts)
        changed[0] = _frame(canonical_json_bytes(document))
        with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
            ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
                raw=b"".join(changed),
                expected_binding=binding,
            )

    oversized = f"{ipc.MAX_FRAME_BYTES + 1:08x}".encode("ascii")
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="noncanonical or over cap",
    ):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=oversized,
            expected_binding=binding,
        )

    monkeypatch.setattr(ipc, "MAX_PAYLOAD_BYTES", 4)
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="payload exceeds",
    ):
        ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
            binding=binding,
            role=ipc.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
            payload={"too_large": 1},
        )


def test_binding_payload_and_issued_types_are_strict() -> None:
    with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
        ipc.K7OuterAttemptBrokerIPCBindingV1(
            _id("request"), _id("route"), _id("spec"), "ABC"
        )
    with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
        ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
            binding=_binding(),
            role=ipc.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
            payload=[],  # type: ignore[arg-type]
        )
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="issuer-owned",
    ):
        ipc.K7OuterAttemptBrokerIPCProfileV1(object())
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="caller-minted",
    ):
        ipc.K7OuterAttemptBrokerIPCFrameV1(
            object(),
            _binding(),
            ipc.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY,
            0,
            {},
        )
    with pytest.raises(
        ipc.V075K7OuterAttemptBrokerIPCV1Error,
        match="caller-minted",
    ):
        ipc.V075K7OuterAttemptBrokerIPCTranscriptV1(
            object(),
            _binding(),
            (),
            "0" * 64,
            0,
        )


@pytest.mark.parametrize(
    "payload",
    (
        {"request_ordinal": 0, "fd": 7},
        {"request_ordinal": 0, "argv": ["python"]},
        {"request_ordinal": 0, "environment": {}},
        {"request_ordinal": 0, "cgroup": "worker"},
        {"request_ordinal": True},
        {"request_ordinal": 1},
    ),
)
def test_business_request_cannot_select_launch_authority(payload) -> None:
    with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
        ipc.encode_v075_k7_outer_attempt_broker_ipc_frame_v1(
            binding=_binding(),
            role=ipc.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST,
            payload=payload,
        )


def test_pretty_json_is_not_accepted_even_when_semantically_equal() -> None:
    binding = _binding()
    parts = _split(_stream(binding))
    document = loads_canonical_json(_body(parts[0]))
    pretty = json.dumps(document, indent=2, sort_keys=True).encode("utf-8")
    parts[0] = _frame(pretty)
    with pytest.raises(ipc.V075K7OuterAttemptBrokerIPCV1Error):
        ipc.verify_v075_k7_outer_attempt_broker_ipc_stream_v1(
            raw=b"".join(parts),
            expected_binding=binding,
        )
