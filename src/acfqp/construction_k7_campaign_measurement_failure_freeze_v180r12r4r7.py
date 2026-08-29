"""Freeze the consumed ordinal12 pre-child socket-capability failure.

Ordinal12 entered the scientific ledger and durably wrote ``ATTEMPT_OPEN``
and ``PROCESS_BIRTH_INTENT``.  Its source, host, and T1 placement checks
passed, but seqpacket buffer configuration failed before the child existed.
Consequently T2-v2 and T3 were not reached, no CounterRecord or vector was
issued, and none of the four scientific gates ran.

The twelve formal artifacts are frozen separately from the retained
post-failure socket probe.  The latter explains the otherwise generic formal
runtime error, but is not promoted into a campaign event or preregistered host
fact.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "db21603969ff7bcf28a73fe4081295a7b010ab869eeb7b4adcaed8d69c3e2c9a"
)
EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "0ca5a22fa7241f32418c5b2661534a318a1f0b94ca7c315b592c0780947acb50"
)
EXPECTED_CAMPAIGN_FAILURE_ID = (
    "fa7c9635a66509ba89d8f7408bc12c85fea8ce71c1c59fea9422e77f5520a1b6"
)
EXPECTED_EVENT_IDS = (
    "c5bc2d94bb56305294d2a204bf14f862b9a4d3d5fcbd0b2ca74da4f3117ebf9c",
    "7c335e1954c250b53665d6974576dd108b739cf4c869467ad020236f5c18b5ba",
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "993a456a5eeb1c80963806ab3d58aaa2cbb8ebb4d62ceb37ae9cdadb1b03a5ee"
)
EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "bd95f73e06f26cd1fff3849bd3ce41e4435117a2a4a26d8bbd1f36eae3e08801"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "a221f8d37ca354b7e1a753708d99229086ef6128fedd5cbf9879c89871846185"
)
EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "749ec332ec1dfa601ed830a65742df63bab220a84ab9259baf235a75260b0686"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "46a3d92a70424c296e0137380cdb98f99f11b47b565dce3175baeab8b3546a67"
)
EXPECTED_PROTOCOL_ID = (
    "39ac13c2dde86d2d4d1a97475e227def0f2d1cf79be7d7998564ca99cd5afe9e"
)
EXPECTED_AUTHORIZATION_ID = (
    "e4b7205f15e15b0bb656098d261bd083f700ff1962cb9eb5d25fa66dceef9671"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "28b36402184bada1bdebaf05d27c2bad3d11b488e6883e8d91bd7b61eb2fabad"
)
EXPECTED_C_PRE_COMMIT_ID = "2dfeb472576d9976f31e51f212e52b27bfbaa65d"
EXPECTED_C_PRE_TREE_ID = "e7fc1ce2ab283ca9c8c52faf2fb1cf10198778ed"
EXPECTED_EMPTY_BRIDGE_COMMIT_ID = "de5e56697223cbbb7bbcd80e498b5f52df6eb465"
EXPECTED_LITERAL_COMMIT_ID = "fb76735c79fdc73b62b5835dc06533e88ada1ba4"
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "b00bc6e59018f124e9939e6237ee9afc1852cf6120fb7130d536b7ff2cb682f4"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "fb3090b81da2b32d23cdff0f24888dbc843624308be35497797b8ae5383dbc67"
)
EXPECTED_LAUNCH_RULE_ID = (
    "590667c6806bfe8436b219cc78b27c71d4acd2675128eb453e967ece488aecee"
)
EXPECTED_MEASUREMENT_SERVICE_TOKEN = (
    "36ed4564c6b1e77e08ee99aac354f4fc9bc5aaa67b3ac0f6bf16e69996d338bf"
)
EXPECTED_UNIT_NAME = (
    "acfqp-v180r12r4-measurement-"
    + EXPECTED_MEASUREMENT_SERVICE_TOKEN
    + ".service"
)
EXPECTED_SOURCE_MEMBERSHIP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    + EXPECTED_UNIT_NAME
)
EXPECTED_T1_PID = 605_019
EXPECTED_FAILURE_CODE = "SUPERVISOR_BIRTH_FAILURE"
EXPECTED_FAILURE_STAGE = "SOCKET_BUFFER_CONFIGURATION"
EXPECTED_FAILURE_MESSAGE = (
    "V180R12R4RuntimeError: runtime IPC seqpacket buffers do not cover the "
    "frame cap"
)
EXPECTED_SOCKET_REQUEST_BYTES = 1_048_576
EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES = 2_097_152
REPAIR_SCOPE = "SOCKET_BUFFER_CAPABILITY_AND_T3_DIAGNOSTIC_CONFORMANCE"

ORDINAL12_CAMPAIGN_ATTEMPT_ID = EXPECTED_CAMPAIGN_ATTEMPT_ID
ORDINAL12_INNER_LAUNCH_FAILURE_ID = EXPECTED_INNER_LAUNCH_FAILURE_ID
ORDINAL12_OUTER_SERVICE_FAILURE_ID = EXPECTED_OUTER_SERVICE_FAILURE_ID

_SERVICE_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
_SERVICE_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
_ATTEMPT_RECORD_DOMAIN = (
    "acfqp:construction-k7-campaign-attempt-record:v180r12r4e"
)
_EVENT_DOMAIN = "acfqp:construction-k7-campaign-ledger-event:v180r12r4e"
_FAILURE_DOMAIN = (
    "acfqp:construction-k7-campaign-failure-state-receipt:v180r12r4e"
)
_FREEZE_DOMAIN = (
    "acfqp:construction-k7-ordinal12-failure-freeze:v180r12r4r7"
)
_GATE_NAMES = (
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
)
_ABSENT_PROGRESS_NAMES = (
    "evidence_inventory",
    "execution_closure",
    "launch_failure",
    "ledger_closure",
    "os_receipt",
    "receipt",
    "retained_replay",
    "runtime_cas",
    "terminal",
    "verification",
    "verification_failure",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RETAINED_ROOT = (
    _REPOSITORY_ROOT / "retained_evidence/v180r12r4r7_ordinal12_failure"
)


@dataclass(frozen=True, slots=True)
class _ArtifactFact:
    role: str
    relative_path: str
    byte_count: int
    sha256: str
    formal: bool = True


_FORMAL_ARTIFACT_FACTS = (
    _ArtifactFact(
        "external_root",
        "raw/external_root.json",
        4_416,
        "f785acee647b550fbf0491b58e6f725016226aff816fa68081287a3b06bac472",
    ),
    _ArtifactFact(
        "materialization",
        "raw/prelaunch/materialization_terminal.json",
        40_137,
        "78913c1c61da7687390a696087a65ae68a0d22dc01a0d375f59e96834bb7de1f",
    ),
    _ArtifactFact(
        "launch_manifest",
        "raw/prelaunch/launch_manifest.json",
        94_599,
        "a4298315e0b126925b603ffe505fa0fb5701ca1c8e9e26f0125e96dddfe67904",
    ),
    _ArtifactFact(
        "outer_service_attempt",
        "raw/prelaunch/outer_service_attempt.json",
        5_273,
        "0bf65695880b1ec8ec666d35a4a7aa7a5e8798138ee9829c9ebad3266a1aa0a4",
    ),
    _ArtifactFact(
        "inner_launch_attempt",
        "raw/prelaunch/inner_launch_attempt.json",
        4_071,
        "50f085d77fbcb4fb2ec585c8469d3e6ec5946be27974344fa810bd16d2bcb55e",
    ),
    _ArtifactFact(
        "outer_service_failure",
        "raw/outer_service_failure.json",
        7_870,
        "6fdd1396854f32a2d1959cbd344f090c087717870e83a1a66ad9e2193fff7e65",
    ),
    _ArtifactFact(
        "inner_launch_failure",
        "raw/inner_launch_failure.json",
        13_276,
        "5e807b63bfa9dc8f4c4620c99377623e672bfe7d9f6f658300131a4ca35d7ef0",
    ),
    _ArtifactFact(
        "host_conformance",
        "raw/host_conformance.json",
        3_962,
        "ed1f3bfbd0c379fa1244ff824de19e7bc12fee9c1664b23392ac9c86d0d66e68",
    ),
    _ArtifactFact(
        "campaign_attempt",
        "raw/campaign/scientific_attempt.json",
        1_182,
        "30b2c2dc4ec4b518429ec042f27fb13bb8b4c6ec4df4af3de7c46e2738d31210",
    ),
    _ArtifactFact(
        "campaign_failure",
        "raw/campaign/measurement_failure.json",
        7_093,
        "6fe2f5d2914175061469035b614888b26ad90b350d8d54dd5ab45f8361de60ae",
    ),
    _ArtifactFact(
        "attempt_open_event",
        "raw/campaign/EVENTS/000000.json",
        766,
        "2e089ff0c5056221ca2a653c37fe2f90fcef880650331959770943bb7b926caf",
    ),
    _ArtifactFact(
        "process_birth_intent_event",
        "raw/campaign/EVENTS/000001.json",
        774,
        "116b6da2d6c21192186bda0ed5ff7af449eac5992dbad69570ede6b8074c3b6a",
    ),
)
_DIAGNOSTIC_ARTIFACT_FACT = _ArtifactFact(
    "socket_capability_observation",
    "raw/post_failure_socket_capability_observation.json",
    1_728,
    "8b1d432dded49a54025f0a48e27261e00df5a5e30b79608a780aa4ba4b1f47f6",
    formal=False,
)
_ARTIFACT_FACTS = _FORMAL_ARTIFACT_FACTS + (_DIAGNOSTIC_ARTIFACT_FACT,)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}


class Ordinal12FailureFreezeV180r12r4r7Error(ValueError):
    """Raised when retained ordinal12 evidence no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal12FailureFreezeV180r12r4r7Error(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _require_self_id(
    document: dict[str, Any],
    field: str,
    expected: str,
    *,
    domain: str | None = None,
) -> str:
    payload = dict(document)
    claimed = payload.pop(field, None)
    identity_input = _canonical_bytes(payload)
    if domain is not None:
        identity_input = domain.encode("ascii") + b"\x00" + identity_input
    actual = hashlib.sha256(identity_input).hexdigest()
    _require(
        claimed == expected == actual,
        f"ordinal12 {field} canonical identity changed",
    )
    return expected


def _read_documents(
    retained_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    documents: dict[str, dict[str, Any]] = {}
    raw_by_role: dict[str, bytes] = {}
    for fact in _ARTIFACT_FACTS:
        path = retained_root / fact.relative_path
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise Ordinal12FailureFreezeV180r12r4r7Error(
                f"ordinal12 {fact.role} is unreadable"
            ) from error
        _require(
            len(raw) == fact.byte_count
            and hashlib.sha256(raw).hexdigest() == fact.sha256,
            f"ordinal12 {fact.role} raw bytes changed",
        )
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Ordinal12FailureFreezeV180r12r4r7Error(
                f"ordinal12 {fact.role} is not JSON"
            ) from error
        canonical_raw = _canonical_bytes(document)
        expected_encoding = (
            canonical_raw + b"\n" if not fact.formal else canonical_raw
        )
        _require(
            type(document) is dict and expected_encoding == raw,
            f"ordinal12 {fact.role} canonical bytes changed",
        )
        documents[fact.role] = document
        raw_by_role[fact.role] = raw
    return documents, raw_by_role


def _file_fact(role: str) -> dict[str, Any]:
    fact = _FACT_BY_ROLE[role]
    return {
        "byte_count": fact.byte_count,
        "mode": 0o400,
        "presence": "REGULAR_FILE",
        "sha256": fact.sha256,
    }


def _require_gates_not_run(document: dict[str, Any], label: str) -> None:
    _require(
        all(document.get(name) == "NOT_RUN" for name in _GATE_NAMES)
        and document.get("official_execution_allowed") is False,
        f"ordinal12 {label} gate boundary changed",
    )


_SOCKET_MISMATCH_ROWS = (
    {
        "expected_minimum": EXPECTED_SOCKET_REQUEST_BYTES,
        "field": "sysctl_observations.net.core.rmem_max",
        "observed": 212_992,
    },
    {
        "expected_minimum": EXPECTED_SOCKET_REQUEST_BYTES,
        "field": "sysctl_observations.net.core.wmem_max",
        "observed": 212_992,
    },
    {
        "expected_minimum": EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES,
        "field": "endpoint_observations.parent.so_rcvbuf",
        "observed": 425_984,
    },
    {
        "expected_minimum": EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES,
        "field": "endpoint_observations.parent.so_sndbuf",
        "observed": 425_984,
    },
    {
        "expected_minimum": EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES,
        "field": "endpoint_observations.child.so_rcvbuf",
        "observed": 425_984,
    },
    {
        "expected_minimum": EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES,
        "field": "endpoint_observations.child.so_sndbuf",
        "observed": 425_984,
    },
)
_SOCKET_CAUSE = {
    "error_type": "V180R12R4RuntimeError",
    "failure_code": "SOCKET_BUFFER_CAPABILITY_CONFORMANCE_FAILURE",
    "message": (
        "effective seqpacket send/receive buffers are below the frozen "
        "two-frame minimum"
    ),
    "scope": "PRE_CHILD_IPC_SEQPACKET_CAPABILITY",
}


def _freeze_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.v180r12r4r7_ordinal12_failure_freeze.v1",
        "campaign_attempt_id": EXPECTED_CAMPAIGN_ATTEMPT_ID,
        "campaign_attempt_record_id": EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        "campaign_failure_id": EXPECTED_CAMPAIGN_FAILURE_ID,
        "event_ids": list(EXPECTED_EVENT_IDS),
        "materialization_terminal_id": EXPECTED_MATERIALIZATION_TERMINAL_ID,
        "outer_service_launch_attempt_id": (
            EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID
        ),
        "outer_service_failure_id": EXPECTED_OUTER_SERVICE_FAILURE_ID,
        "inner_launch_attempt_id": EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
        "inner_launch_failure_id": EXPECTED_INNER_LAUNCH_FAILURE_ID,
        "formal_artifact_sha256s": {
            fact.role: fact.sha256 for fact in _FORMAL_ARTIFACT_FACTS
        },
        "post_failure_socket_capability_observation_sha256": (
            _DIAGNOSTIC_ARTIFACT_FACT.sha256
        ),
        "repair_scope": REPAIR_SCOPE,
    }


def _freeze_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _FREEZE_DOMAIN.encode("ascii") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


EXPECTED_ORDINAL12_FAILURE_FREEZE_ID = (
    "2f71e97fd2133c7983a400b5f536fe87740aa08c551580d62556aae5dcea496b"
)
ORDINAL12_FAILURE_FREEZE_ID = _freeze_id(_freeze_payload())


@dataclass(frozen=True, slots=True)
class FrozenOrdinal12FailureV180r12r4r7:
    freeze_id: str
    campaign_attempt_id: str
    campaign_attempt_record_id: str
    campaign_failure_id: str
    event_ids: tuple[str, str]
    materialization_terminal_id: str
    outer_service_launch_attempt_id: str
    outer_service_failure_id: str
    inner_launch_attempt_id: str
    inner_launch_failure_id: str
    host_conformance: dict[str, Any]
    t1_placement: dict[str, Any]
    socket_capability_observation: dict[str, Any]

    def to_contract(self) -> dict[str, Any]:
        """Return the claim-bounded ordinal12 failure contract."""

        return {
            "schema": "acfqp.v180r12r4r7_ordinal12_failure_freeze.v1",
            "freeze_id": self.freeze_id,
            "campaign_attempt_id": self.campaign_attempt_id,
            "campaign_attempt_record_id": self.campaign_attempt_record_id,
            "campaign_failure_id": self.campaign_failure_id,
            "event_ids": list(self.event_ids),
            "materialization_terminal_id": self.materialization_terminal_id,
            "outer_service_launch_attempt_id": (
                self.outer_service_launch_attempt_id
            ),
            "outer_service_failure_id": self.outer_service_failure_id,
            "inner_launch_attempt_id": self.inner_launch_attempt_id,
            "inner_launch_failure_id": self.inner_launch_failure_id,
            "formal_artifact_count": 12,
            "post_failure_diagnostic_artifact_count": 1,
            "post_failure_diagnostic_is_formal_campaign_artifact": False,
            "all_self_ids_verified": True,
            "self_id_count": 9,
            "prelaunch_materialization_succeeded": True,
            "source_root_count": 26,
            "full_source_conformance": True,
            "source_conformance_mismatch_count": 0,
            "source_conformance_cause": None,
            "full_host_conformance": True,
            "host_conformance_mismatch_count": 0,
            "host_conformance_cause": None,
            "host_conformance": self.host_conformance,
            "scientific_attempt_opened": True,
            "event_kinds": ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT"],
            "completed_event_count": 2,
            "failure_code": EXPECTED_FAILURE_CODE,
            "failure_stage": EXPECTED_FAILURE_STAGE,
            "failure_message": EXPECTED_FAILURE_MESSAGE,
            "launch_child_created": False,
            "launch_exec_observed": False,
            "launch_pidfd_acquired": False,
            "production_runtime_placement_t1": self.t1_placement,
            "production_runtime_placement_t1_complete": True,
            "production_runtime_placement_t2_reached": False,
            "production_runtime_placement_t3_reached": False,
            "t2_t3_full_conformance_reached": False,
            "cgroup_topology_conformance_diagnostic": None,
            "socket_capability_observation": (
                self.socket_capability_observation
            ),
            "socket_capability_full_conformance": False,
            "socket_capability_mismatch_count": 6,
            "socket_capability_mismatch_rows": [
                dict(row) for row in _SOCKET_MISMATCH_ROWS
            ],
            "socket_capability_cause": dict(_SOCKET_CAUSE),
            "socket_request_bytes": EXPECTED_SOCKET_REQUEST_BYTES,
            "socket_required_effective_min_bytes": (
                EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES
            ),
            "cleanup_complete": True,
            "post_failure_measurement_root_state": "ABSENT",
            "formal_service_collected": True,
            "process_may_remain": False,
            "oom_event_count": 0,
            "memory_peak_bytes": 262_144,
            "counter_record_count": 0,
            "work_vector_count": 0,
            "comparison_vector_count": 0,
            "counter_records_issued": False,
            "work_vectors_issued": False,
            "comparison_vectors_issued": False,
            "gate_statuses": {name: "NOT_RUN" for name in _GATE_NAMES},
            "official_execution_allowed": False,
            "terminal_present": False,
            "independent_replay_present": False,
            "scientific_effect_observed": False,
            "scientific_effect_claimed": False,
            "identity_consumed": True,
            "same_identity_rerun_forbidden": True,
            "fresh_successor_identity_required": True,
            "repair_scope": REPAIR_SCOPE,
        }


def freeze_ordinal12_failure_v180r12r4r7(
    retained_root: Path | None = None,
) -> FrozenOrdinal12FailureV180r12r4r7:
    """Validate and freeze the exact consumed ordinal12 failure."""

    root = _DEFAULT_RETAINED_ROOT if retained_root is None else Path(retained_root)
    documents, _raws = _read_documents(root)
    external = documents["external_root"]
    materialization = documents["materialization"]
    manifest = documents["launch_manifest"]
    outer_attempt = documents["outer_service_attempt"]
    inner_attempt = documents["inner_launch_attempt"]
    outer_failure = documents["outer_service_failure"]
    inner_failure = documents["inner_launch_failure"]
    host = documents["host_conformance"]
    campaign_attempt = documents["campaign_attempt"]
    campaign_failure = documents["campaign_failure"]
    events = (
        documents["attempt_open_event"],
        documents["process_birth_intent_event"],
    )
    socket_observation = documents["socket_capability_observation"]

    materialization_id = _require_self_id(
        materialization,
        "materialization_terminal_id",
        EXPECTED_MATERIALIZATION_TERMINAL_ID,
    )
    outer_attempt_id = _require_self_id(
        outer_attempt,
        "service_launch_attempt_id",
        EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID,
        domain=_SERVICE_ATTEMPT_DOMAIN,
    )
    inner_attempt_id = _require_self_id(
        inner_attempt,
        "launch_attempt_id",
        EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
    )
    outer_failure_id = _require_self_id(
        outer_failure,
        "service_launch_failure_id",
        EXPECTED_OUTER_SERVICE_FAILURE_ID,
        domain=_SERVICE_FAILURE_DOMAIN,
    )
    inner_failure_id = _require_self_id(
        inner_failure,
        "launch_failure_id",
        EXPECTED_INNER_LAUNCH_FAILURE_ID,
    )
    attempt_record_id = _require_self_id(
        campaign_attempt,
        "campaign_attempt_record_id",
        EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        domain=_ATTEMPT_RECORD_DOMAIN,
    )
    event_ids = tuple(
        _require_self_id(event, "event_id", expected, domain=_EVENT_DOMAIN)
        for event, expected in zip(events, EXPECTED_EVENT_IDS, strict=True)
    )
    campaign_failure_id = _require_self_id(
        campaign_failure,
        "failure_state_id",
        EXPECTED_CAMPAIGN_FAILURE_ID,
        domain=_FAILURE_DOMAIN,
    )

    frozen_context = external.get("frozen_authorization_context")
    _require(type(frozen_context) is dict, "ordinal12 frozen context changed")
    _require(
        external.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and external.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and external.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and external.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and external.get(
            "created_before_v180r12r4_authorized_measurement_execution"
        )
        is True
        and external.get("v180r12r4_outcome_bytes_accessed") is False
        and frozen_context.get("campaign_attempt_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and frozen_context.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and frozen_context.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and frozen_context.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID,
        "ordinal12 external authorization boundary changed",
    )
    _require(
        manifest.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and manifest.get("frozen_authorization_context") == frozen_context,
        "ordinal12 launch manifest context join changed",
    )

    topology = materialization.get("git_topology")
    _require(type(topology) is dict, "ordinal12 Git topology changed")
    _require(
        topology.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and topology.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and topology.get("empty_bridge_commit_id")
        == EXPECTED_EMPTY_BRIDGE_COMMIT_ID
        and topology.get("literal_commit_id") == EXPECTED_LITERAL_COMMIT_ID,
        "ordinal12 final source topology changed",
    )
    _require_gates_not_run(materialization, "materialization")
    _require(
        materialization.get("success") is True
        and materialization.get("construction_only") is True
        and materialization.get("campaign_actual_measurement") is False
        and materialization.get("scientific_occurrence_executed") is False
        and materialization.get("counter_records_issued") is False
        and materialization.get("work_vectors_issued") is False
        and materialization.get("comparison_vectors_issued") is False,
        "ordinal12 materialization boundary changed",
    )
    _require(
        materialization.get("external_root")
        == {
            "absolute_path": (
                "/home/erzhu419/mine_code/acfqp-v180r12r4r6-ordinal12/"
                ".tmp/exact-freeze/"
                "v180r12r4_campaign_measurement_prelaunch_external_root.json"
            ),
            "byte_count": _FACT_BY_ROLE["external_root"].byte_count,
            "immutable_mode": "0400",
            "sha256": _FACT_BY_ROLE["external_root"].sha256,
        }
        and materialization.get("launch_manifest")
        == {
            "byte_count": _FACT_BY_ROLE["launch_manifest"].byte_count,
            "relative_path": (
                ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch/"
                "launch_manifest.json"
            ),
            "sha256": _FACT_BY_ROLE["launch_manifest"].sha256,
        },
        "ordinal12 materialization raw-artifact join changed",
    )

    source = materialization.get("working_tree_source_conformance")
    _require(
        type(source) is dict
        and manifest.get("working_tree_source_conformance") == source,
        "ordinal12 source-conformance diagnostic join changed",
    )
    source_snapshots = source.get("snapshots")
    _require(
        source.get("source_root_count") == 26
        and source.get("mismatch_count") == 0
        and source.get("per_field_mismatches") == []
        and source.get("full_source_conformance") is True
        and source.get("unit_ownership_evaluated") is False
        and source.get("cause") is None
        and type(source_snapshots) is list
        and len(source_snapshots) == 26
        and all(
            type(row) is dict
            and row.get("conformant") is True
            and row.get("mismatch_fields") == []
            and row.get("observed_before") == row.get("observed_after")
            for row in source_snapshots
        ),
        "ordinal12 26-root full source conformance changed",
    )

    host_expected = host.get("expected")
    host_observed = host.get("observed")
    _require(
        type(host_expected) is dict and type(host_observed) is dict,
        "ordinal12 host property snapshots changed",
    )
    expected_parent = host_expected.get("cgroup_parent_fact")
    observed_parent = host_observed.get("cgroup_parent_fact")
    expected_runtime = host_expected.get("runtime_capability_fact")
    observed_runtime = host_observed.get("runtime_capability_fact")
    _require(
        all(
            type(value) is dict
            for value in (
                expected_parent,
                observed_parent,
                expected_runtime,
                observed_runtime,
            )
        ),
        "ordinal12 host fact snapshots changed",
    )
    parent_fields = host.get("cgroup_parent_compared_fields")
    runtime_fields = host.get("runtime_capability_compared_fields")
    _require(
        host.get("schema")
        == "acfqp.v180r12r4_pre_attempt_host_conformance.v1"
        and host.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and host.get("cgroup_parent_excluded_fields") == ["self_membership"]
        and type(parent_fields) is list
        and set(parent_fields) == set(expected_parent) - {"self_membership"}
        and set(expected_parent) == set(observed_parent)
        and type(runtime_fields) is list
        and set(runtime_fields) == set(expected_runtime) == set(observed_runtime)
        and all(expected_parent[field] == observed_parent[field] for field in parent_fields)
        and all(expected_runtime[field] == observed_runtime[field] for field in runtime_fields)
        and observed_parent.get("self_membership") == EXPECTED_SOURCE_MEMBERSHIP
        and host.get("mismatch_rows") == []
        and host.get("mismatch_count") == 0
        and host.get("cause") is None
        and host.get("full_host_conformance") is True
        and host.get("campaign_attempt_created") is False
        and host.get("campaign_event_or_counter_record_issued") is False,
        "ordinal12 full pre-attempt host conformance changed",
    )

    invocation = inner_attempt.get("production_systemd_service_invocation")
    _require(type(invocation) is dict, "ordinal12 service invocation changed")
    _require(
        invocation
        == outer_attempt.get("production_systemd_service_invocation")
        == outer_failure.get("production_systemd_service_invocation")
        == inner_failure.get("production_systemd_service_invocation")
        and invocation.get("target") == "measurement"
        and invocation.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and invocation.get("unit_name") == EXPECTED_UNIT_NAME
        and invocation.get("unit_kind") == "SERVICE_NOT_SCOPE"
        and invocation.get("service_type") == "exec"
        and invocation.get("delegate") is True,
        "ordinal12 production service identity changed",
    )
    _require(
        outer_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_sha256")
        == _FACT_BY_ROLE["materialization"].sha256
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and outer_attempt.get("unit_name") == EXPECTED_UNIT_NAME
        and outer_attempt.get("pre_scientific_outer_dispatch") is True
        and outer_attempt.get("campaign_event_or_evidence_document") is False,
        "ordinal12 outer service attempt join changed",
    )
    _require(
        inner_attempt.get("materialization_terminal_id") == materialization_id
        and inner_attempt.get("materialization_terminal_byte_count")
        == _FACT_BY_ROLE["materialization"].byte_count
        and inner_attempt.get("materialization_terminal_sha256")
        == _FACT_BY_ROLE["materialization"].sha256
        and inner_attempt.get("launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and inner_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_attempt.get("authorized_child_measurement_execution_completed")
        is False
        and inner_attempt.get("scientific_occurrence_started") is False,
        "ordinal12 inner launch attempt boundary changed",
    )

    _require(
        outer_failure.get("service_launch_attempt_id") == outer_attempt_id
        and outer_failure.get("inner_launch_attempt_id") == inner_attempt_id
        and outer_failure.get("inner_launch_attempt_fact")
        == _file_fact("inner_launch_attempt")
        and outer_failure.get("inner_launch_terminal_kind") == "FAILURE"
        and outer_failure.get("inner_launch_terminal_id") == inner_failure_id
        and outer_failure.get("inner_launch_failure_fact")
        == _file_fact("inner_launch_failure")
        and outer_failure.get("inner_launch_receipt_fact")
        == {"presence": "ABSENT"}
        and outer_failure.get("exact_attempt_terminal_join") is True
        and outer_failure.get("systemd_run_return_code") == 1
        and outer_failure.get("systemd_run_timed_out") is False
        and outer_failure.get("success") is False,
        "ordinal12 outer service failure join changed",
    )
    unit_absence = outer_failure.get("collected_unit_absence_observation")
    _require(
        type(unit_absence) is dict
        and unit_absence.get("expected_load_state") == "not-found"
        and unit_absence.get("unit_absent_after_wait_collect") is True
        and unit_absence.get("return_code") == 0
        and unit_absence.get("timed_out") is False,
        "ordinal12 collected service absence changed",
    )

    _require_gates_not_run(inner_failure, "inner launch failure")
    _require(
        inner_failure.get("launch_attempt_id") == inner_attempt_id
        and inner_failure.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_failure.get("failure_type")
        == "V180r12r4PrelaunchLaunchError"
        and inner_failure.get("failure_message")
        == "source-bound child did not reach its exact durable success state"
        and inner_failure.get("return_code") == 1
        and inner_failure.get("timed_out") is False
        and inner_failure.get("attempt_lock_preserved") is True
        and inner_failure.get("same_target_identity_rerun_forbidden") is True
        and inner_failure.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_failure.get("authorized_child_measurement_execution_completed")
        is False
        and inner_failure.get("campaign_actual_measurement") is False
        and inner_failure.get("producer_free_verification_attempted") is False
        and inner_failure.get("success") is False,
        "ordinal12 inner launch failure boundary changed",
    )

    placement_t1 = inner_failure.get("production_runtime_placement_t1")
    _require(type(placement_t1) is dict, "ordinal12 T1 placement changed")
    _require(
        placement_t1.get("schema")
        == "acfqp.v180r12r4_production_runtime_placement_t1.v1"
        and placement_t1.get("source_membership") == EXPECTED_SOURCE_MEMBERSHIP
        and placement_t1.get("expected_source_membership")
        == EXPECTED_SOURCE_MEMBERSHIP
        and placement_t1.get("unit_name") == EXPECTED_UNIT_NAME
        and placement_t1.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and placement_t1.get("self_pid") == EXPECTED_T1_PID
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and placement_t1.get("t1_complete_before_child_popen") is True
        and placement_t1.get("nearest_common_ancestor_is_app_slice") is True
        and placement_t1.get("planned_measurement_root_absent") is True,
        "ordinal12 complete T1 service placement changed",
    )
    _require(
        "production_runtime_placement_t2" not in inner_failure
        and "production_runtime_placement_t3" not in inner_failure,
        "ordinal12 unexpectedly reached T2 or T3",
    )

    _require(
        campaign_attempt.get("schema")
        == "acfqp.campaign_attempt_record.v180r12r4"
        and campaign_attempt.get("attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and campaign_attempt.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and campaign_attempt.get("authorization_id")
        == EXPECTED_AUTHORIZATION_ID
        and campaign_attempt.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and campaign_attempt.get("prelaunch_materialization_terminal_id")
        == materialization_id
        and campaign_attempt.get("prelaunch_launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and campaign_attempt.get("prelaunch_launch_rule_id")
        == EXPECTED_LAUNCH_RULE_ID
        and campaign_attempt.get("measurement_launch_attempt_id")
        == inner_attempt_id
        and campaign_attempt.get("one_shot_attempt_opened") is True,
        "ordinal12 scientific ATTEMPT authority join changed",
    )
    common_identity = (
        EXPECTED_PROTOCOL_ID,
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_CAMPAIGN_ATTEMPT_ID,
    )
    for event in events:
        _require(
            (
                event.get("protocol_id"),
                event.get("authorization_id"),
                event.get("attempt_id"),
            )
            == common_identity,
            "ordinal12 event identity join changed",
        )
    _require(
        events[0].get("sequence") == 0
        and events[0].get("previous_event_id") is None
        and events[0].get("phase") == "ATTEMPT"
        and events[0].get("actor_role") == "OBSERVER"
        and events[0].get("event_kind") == "ATTEMPT_OPEN"
        and events[0].get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": attempt_record_id,
            "measured_value": None,
            "outcome_code": "OPEN",
        }
        and events[1].get("sequence") == 1
        and events[1].get("previous_event_id") == event_ids[0]
        and events[1].get("phase") == "STAGE"
        and events[1].get("actor_role") == "OBSERVER"
        and events[1].get("event_kind") == "PROCESS_BIRTH_INTENT"
        and events[1].get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": None,
            "measured_value": None,
            "outcome_code": "INTENT",
        },
        "ordinal12 exact two-event campaign prefix changed",
    )

    _require(
        (
            campaign_failure.get("protocol_id"),
            campaign_failure.get("authorization_id"),
            campaign_failure.get("attempt_id"),
        )
        == common_identity
        and campaign_failure.get("schema")
        == "acfqp.campaign_failure_state.v180r12r4"
        and campaign_failure.get("failure_code") == EXPECTED_FAILURE_CODE
        and campaign_failure.get("launch_substage") == EXPECTED_FAILURE_STAGE
        and campaign_failure.get("phase") == "STAGE"
        and campaign_failure.get("last_event_id") == event_ids[1]
        and campaign_failure.get("completed_event_count") == 2
        and campaign_failure.get("message") == EXPECTED_FAILURE_MESSAGE
        and campaign_failure.get("message_sha256")
        == hashlib.sha256(EXPECTED_FAILURE_MESSAGE.encode("utf-8")).hexdigest()
        and campaign_failure.get("launch_child_created") is False
        and campaign_failure.get("launch_exec_observed") is False
        and campaign_failure.get("launch_pidfd_acquired") is False
        and campaign_failure.get("cgroup_topology_conformance_diagnostic")
        is None
        and campaign_failure.get("counter_records_issued") is False
        and campaign_failure.get("successful_ledger_claimed") is False
        and campaign_failure.get("process_may_remain") is False
        and campaign_failure.get("same_identity_rerun_forbidden") is True,
        "ordinal12 typed pre-child campaign failure boundary changed",
    )

    observations = campaign_failure.get("partial_artifact_observations")
    _require(type(observations) is list, "ordinal12 artifact inventory changed")
    by_path = {
        row.get("relative_path"): row
        for row in observations
        if type(row) is dict
    }
    output = ".tmp/exact-freeze/v180r12r4_campaign_measurement"
    events_path = f"{output}/EVENTS"
    _require(
        len(by_path) == len(observations) == 17
        and by_path[output].get("directory_entries") == ["EVENTS"]
        and by_path[events_path].get("directory_entries")
        == ["000000.json", "000001.json"]
        and by_path[f"{events_path}/000000.json"].get("sha256")
        == _FACT_BY_ROLE["attempt_open_event"].sha256
        and by_path[f"{events_path}/000001.json"].get("sha256")
        == _FACT_BY_ROLE["process_birth_intent_event"].sha256
        and by_path[
            ".tmp/exact-freeze/v180r12r4_campaign_measurement_attempt.json"
        ].get("sha256")
        == _FACT_BY_ROLE["campaign_attempt"].sha256,
        "ordinal12 exact two-event artifact inventory changed",
    )
    for relative_path in (
        f"{output}/EVIDENCE_INVENTORY.json",
        f"{output}/EXECUTION_CLOSURE.json",
        f"{output}/LEDGER_CLOSURE.json",
        f"{output}/OS_RECEIPT.json",
        f"{output}/SUBJECT_RESULT.json",
        f"{output}/SUBJECT_RESULT.json.partial",
        f"{output}/TERMINAL.json",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_cas",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_failure.json",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification.json",
        (
            ".tmp/exact-freeze/"
            "v180r12r4_campaign_measurement_verification_failure.json"
        ),
        (
            ".tmp/exact-freeze/"
            "v180r12r4_campaign_measurement_verification_replay.json"
        ),
    ):
        _require(
            by_path[relative_path].get("state") == "ABSENT",
            "ordinal12 terminal, CounterRecord, vector, or replay absence changed",
        )

    progress = inner_failure.get("progress_observations")
    _require(type(progress) is dict, "ordinal12 launch progress changed")
    _require(
        progress.get("attempt") == _file_fact("inner_launch_attempt")
        and progress.get("host_conformance") == _file_fact("host_conformance")
        and progress.get("measurement_failure") == _file_fact("campaign_failure")
        and progress.get("output_root")
        == {"mode": 0o700, "presence": "DIRECTORY"}
        and all(
            progress.get(name) == {"presence": "ABSENT"}
            for name in _ABSENT_PROGRESS_NAMES
        ),
        "ordinal12 retained progress join changed",
    )

    cleanup = inner_failure.get("measurement_cgroup_cleanup_observations")
    _require(
        type(cleanup) is list
        and [row.get("phase") for row in cleanup]
        == ["BEFORE_POPEN", "CLEANUP", "AFTER_CHILD"]
        and all(row.get("ownership_acquired") is True for row in cleanup)
        and all(row.get("root_state") == "ABSENT" for row in cleanup)
        and all(row.get("supervisor_state") == "ABSENT" for row in cleanup)
        and all(row.get("worker_state") == "ABSENT" for row in cleanup)
        and all(
            row.get("residual_tree_or_process_possible") is False
            for row in cleanup
        ),
        "ordinal12 cleanup or root-absence evidence changed",
    )
    cgroup_failure = campaign_failure.get("cgroup_failure_observation")
    _require(type(cgroup_failure) is dict, "ordinal12 cgroup failure fact changed")
    memory_events = cgroup_failure.get("memory_events")
    _require(
        cgroup_failure.get("kill_outcome") == "SUCCESS"
        and cgroup_failure.get("close_outcome") == "SUCCESS"
        and cgroup_failure.get("reap_outcome") == "NO_CHILD_HANDLE"
        and cgroup_failure.get("root_populated") == 0
        and cgroup_failure.get("root_process_count") == 0
        and cgroup_failure.get("supervisor_leaf_process_count") == 0
        and cgroup_failure.get("worker_leaf_process_count") == 0
        and cgroup_failure.get("memory_peak_bytes") == 262_144
        and type(memory_events) is list
        and all(row.get("value") == 0 for row in memory_events),
        "ordinal12 cleanup, memory, or no-child fact changed",
    )

    _require(
        socket_observation.get("schema")
        == "acfqp.v180r12r4r7_post_failure_socket_capability_observation.v1"
        and socket_observation.get("observation_kind")
        == "POST_FAILURE_READ_ONLY_DIAGNOSTIC"
        and socket_observation.get("campaign_attempt_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and socket_observation.get("campaign_failure_state_id")
        == campaign_failure_id
        and socket_observation.get("campaign_event_or_counter_record_issued")
        is False
        and socket_observation.get("failure_stage") == EXPECTED_FAILURE_STAGE
        and socket_observation.get("formal_failure_message")
        == EXPECTED_FAILURE_MESSAGE
        and socket_observation.get("scope")
        == "PRE_CHILD_IPC_SEQPACKET_CAPABILITY"
        and socket_observation.get("request_bytes")
        == EXPECTED_SOCKET_REQUEST_BYTES
        and socket_observation.get("required_effective_min_bytes")
        == EXPECTED_EFFECTIVE_BUFFER_MIN_BYTES
        and socket_observation.get("sysctl_observations")
        == {
            "net.core.rmem_max": 212_992,
            "net.core.wmem_max": 212_992,
        }
        and socket_observation.get("endpoint_observations")
        == [
            {
                "endpoint": "parent",
                "so_rcvbuf": 425_984,
                "so_sndbuf": 425_984,
            },
            {
                "endpoint": "child",
                "so_rcvbuf": 425_984,
                "so_sndbuf": 425_984,
            },
        ]
        and socket_observation.get("full_conformance") is False
        and socket_observation.get("mismatch_count") == 6
        and socket_observation.get("mismatch_rows")
        == list(_SOCKET_MISMATCH_ROWS)
        and socket_observation.get("cause") == _SOCKET_CAUSE,
        "ordinal12 exact six-field socket-capability diagnostic changed",
    )

    freeze_id = _freeze_id(_freeze_payload())
    _require(
        freeze_id == EXPECTED_ORDINAL12_FAILURE_FREEZE_ID,
        "ordinal12 failure-freeze identity changed",
    )
    return FrozenOrdinal12FailureV180r12r4r7(
        freeze_id=freeze_id,
        campaign_attempt_id=EXPECTED_CAMPAIGN_ATTEMPT_ID,
        campaign_attempt_record_id=attempt_record_id,
        campaign_failure_id=campaign_failure_id,
        event_ids=(event_ids[0], event_ids[1]),
        materialization_terminal_id=materialization_id,
        outer_service_launch_attempt_id=outer_attempt_id,
        outer_service_failure_id=outer_failure_id,
        inner_launch_attempt_id=inner_attempt_id,
        inner_launch_failure_id=inner_failure_id,
        host_conformance=host,
        t1_placement=placement_t1,
        socket_capability_observation=socket_observation,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID",
    "EXPECTED_CAMPAIGN_FAILURE_ID",
    "EXPECTED_EVENT_IDS",
    "EXPECTED_INNER_LAUNCH_ATTEMPT_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_ORDINAL12_FAILURE_FREEZE_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID",
    "FrozenOrdinal12FailureV180r12r4r7",
    "ORDINAL12_CAMPAIGN_ATTEMPT_ID",
    "ORDINAL12_FAILURE_FREEZE_ID",
    "ORDINAL12_INNER_LAUNCH_FAILURE_ID",
    "ORDINAL12_OUTER_SERVICE_FAILURE_ID",
    "Ordinal12FailureFreezeV180r12r4r7Error",
    "REPAIR_SCOPE",
    "freeze_ordinal12_failure_v180r12r4r7",
)
