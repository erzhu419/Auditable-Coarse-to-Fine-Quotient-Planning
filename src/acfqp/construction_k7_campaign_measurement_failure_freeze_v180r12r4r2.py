"""Freeze the consumed V180r12r4r2 ordinal8 formal failure.

The retained bytes close the exact launch chain from materialization through
the outer service and inner launcher to the one-event campaign prefix.  The
historical campaign failure called this ``SUPERVISOR_BIRTH_FAILURE`` even
though it records that no child was created; the exact exception is the
pre-birth cgroup topology/limits conformance rejection.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import tarfile
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "7dd2a5bdf2704655b41652b28a63c9309c557cc0470395870e77db7869b0a3f6"
)
EXPECTED_CAMPAIGN_FAILURE_ID = (
    "7f98d4f33e7e6d3c36636ffad27dbc56f54da32cd006f6d5e94cb217cd569a02"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "8be9a12c613373cdfde80d3fd9d64d18a8ca9aaca841ee0d2a454326748c5f43"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "62ed6bf62f94b8c1c9d53ff8bb902ee26045c5896263f59bf28dd8ac1114c458"
)

_EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "ea9d58b2cdeadaa8de414a867c73023ea03d0309efa6764d7d9022a4e8fc325a"
)
_EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "f0cc0f99f2d39a8c56f7a5ef72f7f565e9a0b76f518b157bf76ddea2d1a20d97"
)
_EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "12c447ffecdf1ea2b500783df5f4dc46e7dc323deed8d8866badc7ffde7471dd"
)
_EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "b878fa970e1233d2b567748cb58c9aec1d8f2db2fdfde44d40f1868edee3a8b9"
)
_EXPECTED_EVENT_ID = (
    "6c354c5a3cad2856589620ffedf1a5f7b97c8f1ad767453cff70bf3293abc355"
)
_EXPECTED_PROTOCOL_ID = (
    "53cdcefaec7e41f6703a4626e04d7d06387aeb9db3b8b980d8561cf87382e9fb"
)
_EXPECTED_AUTHORIZATION_ID = (
    "ab0466a12335d5144fdea32f338c31c84a675c8ad827851aecd6cdffb445db73"
)
_EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "a9baa3635dfaedcd7ee5133026cd8a20bc61cd69548099bbffe3e97c48e68e6a"
)
_EXPECTED_LAUNCH_RULE_ID = (
    "ff88515d54fef4fa5021f7c22d48e654b9b42e4545808bf2e6c06a83eb3e95fd"
)
_EXPECTED_LAUNCH_MANIFEST_SHA256 = (
    "90333ea3fc480bf319758df5fdd23ba3130af87c1063a71fd5acd384d3fcc91d"
)
_EXPECTED_MEASUREMENT_RUNNER_SHA256 = (
    "31a42007d081fac6d9cbf04aa51a113831cb577fcd1253d16a2b6320da3aceb2"
)
_EXPECTED_SOURCE_MEMBERSHIP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    "acfqp-v180r12r4-measurement-"
    "b0f62f739847f89027311d52e8861257ba471d28c47439eca41e9cf8cfa04004."
    "service"
)
_OBSERVED_PARENT_CONTROLLERS = ("cpu", "memory", "pids")
_HISTORICAL_PARENT_CONTRACT = ("memory", "pids")
_GATE_NAMES = (
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
)

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

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RETAINED_ROOT = (
    _REPOSITORY_ROOT / "retained_evidence/v180r12r4r2_ordinal8_failure"
)
_BUNDLE_NAME = "ordinal8_failure_artifacts.tar.gz.base64"


@dataclass(frozen=True, slots=True)
class _ArtifactFact:
    role: str
    member: str
    byte_count: int
    sha256: str


_ARTIFACT_FACTS = (
    _ArtifactFact(
        "launch_manifest",
        "v180r12r4_campaign_measurement_prelaunch/launch_manifest.json",
        58_584,
        _EXPECTED_LAUNCH_MANIFEST_SHA256,
    ),
    _ArtifactFact(
        "materialization",
        "v180r12r4_campaign_measurement_prelaunch/MATERIALIZATION_TERMINAL.json",
        7_148,
        "2a4c6d0994a34bf188f599ed4173192d5b0733ea5e46af10a9ded08e49f6305c",
    ),
    _ArtifactFact(
        "outer_service_attempt",
        "v180r12r4_campaign_measurement_prelaunch/"
        "MEASUREMENT_SERVICE_LAUNCH_ATTEMPT.json",
        5_193,
        "9802a6dc0fcc5b8e3ff4788241a816f90d1628f4649037b2c819f93dcaea51c1",
    ),
    _ArtifactFact(
        "outer_service_failure",
        "v180r12r4_campaign_measurement_prelaunch_"
        "measurement_service_launch_failure.json",
        7_782,
        "bfded9bb0e72cfdd4d8831202f1e3e9bca26135e33757c575d4b5da2694dc95a",
    ),
    _ArtifactFact(
        "inner_launch_attempt",
        "v180r12r4_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_ATTEMPT.json",
        3_989,
        "12577172160726bdfeb2ad15956425b8f7db5a764952eaba67e53d56f435dbf1",
    ),
    _ArtifactFact(
        "inner_launch_failure",
        "v180r12r4_campaign_measurement_prelaunch_"
        "measurement_launch_failure.json",
        13_119,
        "539946d95e9c3820d0dd89ad45489c4d353a3ececac47b2fc0f1619d9167ff81",
    ),
    _ArtifactFact(
        "campaign_attempt",
        "v180r12r4_campaign_measurement_attempt.json",
        1_182,
        "2c38ea746450e2590502b68ab85d60f0aa37d03e9ec71843484d852c0b584ae7",
    ),
    _ArtifactFact(
        "attempt_open_event",
        "v180r12r4_campaign_measurement/EVENTS/000000.json",
        765,
        "109ee9a1e6c8620e8f0bfede2201a47b3cfff5074d6bc6ce29b51e1b3d8e5f82",
    ),
    _ArtifactFact(
        "campaign_failure",
        "v180r12r4_campaign_measurement_failure.json",
        5_407,
        "a2b1e1a6ad4b36deac1048ee9e738e95de2853d115b00478e75e6bb6678e6c58",
    ),
)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}


class Ordinal8FailureFreezeV180r12r4r2Error(ValueError):
    """Raised when the retained ordinal8 failure no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal8FailureFreezeV180r12r4r2Error(message)


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
        identity_input = domain.encode("utf-8") + b"\x00" + identity_input
    actual = hashlib.sha256(identity_input).hexdigest()
    _require(
        claimed == expected == actual,
        f"ordinal8 {field} canonical identity changed",
    )
    return expected


def _read_retained_documents(
    retained_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    try:
        encoded = (retained_root / _BUNDLE_NAME).read_bytes()
        archive_bytes = base64.b64decode(b"".join(encoded.split()), validate=True)
        archive = tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz")
    except (OSError, ValueError, tarfile.TarError) as exc:
        _fail(f"ordinal8 retained bundle is unreadable: {type(exc).__name__}")

    expected_members = {fact.member for fact in _ARTIFACT_FACTS}
    with archive:
        members = {member.name: member for member in archive.getmembers()}
        _require(
            set(members) == expected_members
            and all(member.isfile() for member in members.values()),
            "ordinal8 retained artifact inventory changed",
        )
        raw_by_role: dict[str, bytes] = {}
        for fact in _ARTIFACT_FACTS:
            extracted = archive.extractfile(members[fact.member])
            _require(extracted is not None, f"ordinal8 {fact.role} is unreadable")
            raw = extracted.read()
            _require(
                len(raw) == fact.byte_count
                and hashlib.sha256(raw).hexdigest() == fact.sha256,
                f"ordinal8 {fact.role} raw bytes changed",
            )
            raw_by_role[fact.role] = raw

    documents: dict[str, dict[str, Any]] = {}
    for role, raw in raw_by_role.items():
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            _fail(f"ordinal8 {role} is not canonical JSON: {type(exc).__name__}")
        _require(
            type(document) is dict and _canonical_bytes(document) == raw,
            f"ordinal8 {role} canonical bytes changed",
        )
        documents[role] = document
    return documents, raw_by_role


def _require_all_gates_not_run(document: dict[str, Any], label: str) -> None:
    _require(
        all(document.get(name) == "NOT_RUN" for name in _GATE_NAMES)
        and document.get("official_execution_allowed") is False,
        f"ordinal8 {label} gate boundary changed",
    )


def _file_fact(role: str) -> dict[str, Any]:
    fact = _FACT_BY_ROLE[role]
    return {
        "byte_count": fact.byte_count,
        "mode": 256,
        "presence": "REGULAR_FILE",
        "sha256": fact.sha256,
    }


@dataclass(frozen=True, slots=True)
class FrozenOrdinal8FailureV180r12r4r2:
    campaign_attempt_id: str
    campaign_attempt_record_id: str
    campaign_failure_id: str
    event_id: str
    materialization_terminal_id: str
    outer_service_launch_attempt_id: str
    outer_service_failure_id: str
    inner_launch_attempt_id: str
    inner_launch_failure_id: str
    source_membership: str

    def to_contract(self) -> dict[str, Any]:
        """Return the exact claim-bounded ordinal8 failure contract."""

        return {
            "schema": "acfqp.v180r12r4r2_ordinal8_failure_freeze.v1",
            "campaign_attempt_id": self.campaign_attempt_id,
            "campaign_attempt_record_id": self.campaign_attempt_record_id,
            "campaign_failure_id": self.campaign_failure_id,
            "event_ids": [self.event_id],
            "event_kinds": ["ATTEMPT_OPEN"],
            "completed_event_count": 1,
            "materialization_terminal_id": self.materialization_terminal_id,
            "outer_service_launch_attempt_id": (
                self.outer_service_launch_attempt_id
            ),
            "outer_service_failure_id": self.outer_service_failure_id,
            "inner_launch_attempt_id": self.inner_launch_attempt_id,
            "inner_launch_failure_id": self.inner_launch_failure_id,
            "phase": "STAGE",
            "historical_failure_code": "SUPERVISOR_BIRTH_FAILURE",
            "diagnosed_failure_class": "CGROUP_TOPOLOGY_CONFORMANCE_FAILURE",
            "historical_failure_code_misclassified": True,
            "launch_child_created": False,
            "outer_service_unit_ownership_acquired": True,
            "full_cgroup_conformance": False,
            "counter_records_issued": False,
            "work_vectors_issued": False,
            "comparison_vectors_issued": False,
            "gate_statuses": {name: "NOT_RUN" for name in _GATE_NAMES},
            "official_execution_allowed": False,
            "same_identity_rerun_forbidden": True,
            "terminal_present": False,
            "independent_replay_present": False,
            "cgroup_parent_fact": {
                "controllers": list(_OBSERVED_PARENT_CONTROLLERS),
                "subtree_control": list(_OBSERVED_PARENT_CONTROLLERS),
                "self_membership": self.source_membership,
            },
            "historical_parent_contract": {
                "controllers": list(_HISTORICAL_PARENT_CONTRACT),
                "subtree_control": list(_HISTORICAL_PARENT_CONTRACT),
            },
            "parent_contract_mismatch_fields": [
                "controllers",
                "subtree_control",
            ],
            "full_property_diagnostic_recorded": False,
        }


def freeze_ordinal8_failure_v180r12r4r2(
    retained_root: Path | None = None,
) -> FrozenOrdinal8FailureV180r12r4r2:
    """Validate and freeze the exact consumed ordinal8 formal failure."""

    root = _DEFAULT_RETAINED_ROOT if retained_root is None else Path(retained_root)
    documents, raw_by_role = _read_retained_documents(root)
    manifest = documents["launch_manifest"]
    materialization = documents["materialization"]
    outer_attempt = documents["outer_service_attempt"]
    outer_failure = documents["outer_service_failure"]
    inner_attempt = documents["inner_launch_attempt"]
    inner_failure = documents["inner_launch_failure"]
    campaign_attempt = documents["campaign_attempt"]
    event = documents["attempt_open_event"]
    campaign_failure = documents["campaign_failure"]

    materialization_id = _require_self_id(
        materialization,
        "materialization_terminal_id",
        _EXPECTED_MATERIALIZATION_TERMINAL_ID,
    )
    outer_attempt_id = _require_self_id(
        outer_attempt,
        "service_launch_attempt_id",
        _EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID,
        domain=_SERVICE_ATTEMPT_DOMAIN,
    )
    outer_failure_id = _require_self_id(
        outer_failure,
        "service_launch_failure_id",
        EXPECTED_OUTER_SERVICE_FAILURE_ID,
        domain=_SERVICE_FAILURE_DOMAIN,
    )
    inner_attempt_id = _require_self_id(
        inner_attempt,
        "launch_attempt_id",
        _EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
    )
    inner_failure_id = _require_self_id(
        inner_failure,
        "launch_failure_id",
        EXPECTED_INNER_LAUNCH_FAILURE_ID,
    )
    attempt_record_id = _require_self_id(
        campaign_attempt,
        "campaign_attempt_record_id",
        _EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        domain=_ATTEMPT_RECORD_DOMAIN,
    )
    event_id = _require_self_id(
        event, "event_id", _EXPECTED_EVENT_ID, domain=_EVENT_DOMAIN
    )
    campaign_failure_id = _require_self_id(
        campaign_failure,
        "failure_state_id",
        EXPECTED_CAMPAIGN_FAILURE_ID,
        domain=_FAILURE_DOMAIN,
    )

    frozen_context = manifest.get("frozen_authorization_context")
    _require(type(frozen_context) is dict, "ordinal8 authorization context changed")
    parent_fact = frozen_context.get("cgroup_parent_fact")
    _require(type(parent_fact) is dict, "ordinal8 cgroup parent fact changed")
    source_membership = parent_fact.get("self_membership")
    _require(
        manifest.get("schema")
        == "acfqp.v180r12r4_source_bound_launch_manifest.v1"
        and manifest.get("targets", {}).get("measurement")
        == {
            "byte_count": 299_004,
            "relative_path": "scripts/run_v180r12r4_campaign_measurement.py",
            "sha256": _EXPECTED_MEASUREMENT_RUNNER_SHA256,
        }
        and frozen_context.get("protocol_id") == _EXPECTED_PROTOCOL_ID
        and frozen_context.get("authorization_id") == _EXPECTED_AUTHORIZATION_ID
        and frozen_context.get("authorization_evidence_id")
        == _EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and frozen_context.get("campaign_attempt_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and parent_fact.get("schema")
        == "acfqp.v180r12r4_cgroup_parent_fact.v1"
        and parent_fact.get("controllers") == list(_OBSERVED_PARENT_CONTROLLERS)
        and parent_fact.get("subtree_control")
        == list(_OBSERVED_PARENT_CONTROLLERS)
        and source_membership == _EXPECTED_SOURCE_MEMBERSHIP,
        "ordinal8 manifest parent-controller fact changed",
    )

    _require_all_gates_not_run(materialization, "materialization")
    _require(
        materialization.get("schema")
        == "acfqp.v180r12r4_prelaunch_materialization_terminal.v1"
        and materialization.get("success") is True
        and materialization.get("construction_only") is True
        and materialization.get("campaign_actual_measurement") is False
        and materialization.get("scientific_occurrence_executed") is False
        and materialization.get("counter_records_issued") is False
        and materialization.get("work_vectors_issued") is False
        and materialization.get("comparison_vectors_issued") is False
        and materialization.get("same_materialization_identity_rerun_forbidden")
        is True
        and materialization.get("launch_manifest")
        == {
            "byte_count": _FACT_BY_ROLE["launch_manifest"].byte_count,
            "relative_path": (
                ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch/"
                "launch_manifest.json"
            ),
            "sha256": _EXPECTED_LAUNCH_MANIFEST_SHA256,
        },
        "ordinal8 materialization boundary changed",
    )

    materialization_fact = _FACT_BY_ROLE["materialization"]
    _require(
        outer_attempt.get("schema")
        == "acfqp.v180r12r4_prelaunch_service_launch_attempt.v1"
        and outer_attempt.get("target") == "measurement"
        and outer_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and outer_attempt.get("launch_rule_id") == _EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("same_target_identity_rerun_forbidden") is True
        and outer_attempt.get("attempt_o_excl_before_systemd_run") is True,
        "ordinal8 outer service attempt join changed",
    )
    _require(
        outer_failure.get("schema")
        == "acfqp.v180r12r4_prelaunch_service_launch_failure.v1"
        and outer_failure.get("target") == "measurement"
        and outer_failure.get("service_launch_attempt_id") == outer_attempt_id
        and outer_failure.get("inner_launch_attempt_fact")
        == _file_fact("inner_launch_attempt")
        and outer_failure.get("inner_launch_receipt_fact") == {"presence": "ABSENT"}
        and outer_failure.get("inner_launch_failure_fact")
        == _file_fact("inner_launch_failure")
        and outer_failure.get("inner_launch_attempt_id") == inner_attempt_id
        and outer_failure.get("inner_launch_terminal_kind") == "FAILURE"
        and outer_failure.get("inner_launch_terminal_id") == inner_failure_id
        and outer_failure.get("exact_attempt_terminal_join") is True
        and outer_failure.get("attempt_lock_preserved") is True
        and outer_failure.get("same_target_identity_rerun_forbidden") is True
        and outer_failure.get("success") is False
        and outer_failure.get("collected_unit_absence_observation", {}).get(
            "unit_absent_after_wait_collect"
        )
        is True,
        "ordinal8 outer service failure join changed",
    )

    _require(
        inner_attempt.get("schema")
        == "acfqp.v180r12r4_prelaunch_launch_attempt.v1"
        and inner_failure.get("schema")
        == "acfqp.v180r12r4_prelaunch_launch_failure.v1"
        and inner_attempt.get("target")
        == inner_failure.get("target")
        == "measurement"
        and inner_failure.get("launch_attempt_id") == inner_attempt_id
        and inner_attempt.get("materialization_terminal_id") == materialization_id
        and inner_attempt.get("materialization_terminal_byte_count")
        == materialization_fact.byte_count
        and inner_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and inner_attempt.get("launch_manifest_sha256")
        == _EXPECTED_LAUNCH_MANIFEST_SHA256
        and inner_attempt.get("launch_rule_id")
        == inner_failure.get("launch_rule_id")
        == _EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_attempt.get("authorized_child_measurement_execution_completed")
        is False
        and inner_failure.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_failure.get("authorized_child_measurement_execution_completed")
        is False
        and inner_failure.get("attempt_lock_preserved") is True
        and inner_failure.get("same_target_identity_rerun_forbidden") is True
        and inner_failure.get("return_code") == 1
        and inner_failure.get("timed_out") is False
        and inner_failure.get("success") is False,
        "ordinal8 inner launch attempt/failure join changed",
    )
    _require_all_gates_not_run(inner_failure, "inner launch failure")

    placement_t1 = inner_failure.get("production_runtime_placement_t1")
    _require(
        type(placement_t1) is dict
        and placement_t1.get("source_membership") == source_membership
        and placement_t1.get("expected_source_membership") == source_membership
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and placement_t1.get("t1_complete_before_child_popen") is True,
        "ordinal8 outer service unit ownership evidence changed",
    )

    stderr_fact = inner_failure.get("child_stderr")
    _require(type(stderr_fact) is dict, "ordinal8 child stderr fact changed")
    try:
        stderr_raw = bytes.fromhex(stderr_fact.get("retained_prefix_hex", ""))
    except ValueError:
        _fail("ordinal8 child stderr encoding changed")
    _require(
        stderr_fact.get("retained_prefix_truncated") is False
        and stderr_fact.get("byte_count") == len(stderr_raw) == 1_868
        and stderr_fact.get("sha256") == hashlib.sha256(stderr_raw).hexdigest()
        and stderr_raw.endswith(
            b"ConstructionK7CampaignMeasurementSupervisorV180R12R4Error: "
            b"cgroup-v2 sibling-leaf topology or limits changed\n"
        ),
        "ordinal8 topology-conformance traceback changed",
    )

    _require(
        campaign_attempt.get("schema") == "acfqp.campaign_attempt_record.v180r12r4"
        and campaign_attempt.get("attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and campaign_attempt.get("protocol_id") == _EXPECTED_PROTOCOL_ID
        and campaign_attempt.get("authorization_id") == _EXPECTED_AUTHORIZATION_ID
        and campaign_attempt.get("authorization_evidence_id")
        == _EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and campaign_attempt.get("prelaunch_materialization_terminal_id")
        == materialization_id
        and campaign_attempt.get("prelaunch_launch_manifest_sha256")
        == _EXPECTED_LAUNCH_MANIFEST_SHA256
        and campaign_attempt.get("prelaunch_launch_rule_id")
        == _EXPECTED_LAUNCH_RULE_ID
        and campaign_attempt.get("measurement_launch_attempt_id")
        == inner_attempt_id
        and campaign_attempt.get("one_shot_attempt_opened") is True
        and campaign_attempt.get("scope")
        == "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR",
        "ordinal8 campaign ATTEMPT authority join changed",
    )

    common_identity = (
        _EXPECTED_PROTOCOL_ID,
        _EXPECTED_AUTHORIZATION_ID,
        EXPECTED_CAMPAIGN_ATTEMPT_ID,
    )
    _require(
        (
            event.get("protocol_id"),
            event.get("authorization_id"),
            event.get("attempt_id"),
        )
        == common_identity
        and event.get("schema")
        == "acfqp.campaign_measurement_ledger_event.v180r12r4"
        and event.get("sequence") == 0
        and event.get("previous_event_id") is None
        and event.get("phase") == "ATTEMPT"
        and event.get("actor_role") == "OBSERVER"
        and event.get("event_kind") == "ATTEMPT_OPEN"
        and event.get("operation_id") == campaign_attempt.get("operation_id")
        and event.get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": attempt_record_id,
            "measured_value": None,
            "outcome_code": "OPEN",
        },
        "ordinal8 one-event campaign prefix changed",
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
        and campaign_failure.get("failure_code") == "SUPERVISOR_BIRTH_FAILURE"
        and campaign_failure.get("phase") == "STAGE"
        and campaign_failure.get("last_event_id") == event_id
        and campaign_failure.get("completed_event_count") == 1
        and campaign_failure.get("message")
        == (
            "ConstructionK7CampaignMeasurementSupervisorV180R12R4Error: "
            "cgroup-v2 sibling-leaf topology or limits changed"
        )
        and campaign_failure.get("message_sha256")
        == hashlib.sha256(campaign_failure["message"].encode("utf-8")).hexdigest()
        and campaign_failure.get("launch_child_created") is False
        and campaign_failure.get("launch_exec_observed") is False
        and campaign_failure.get("launch_pidfd_acquired") is False
        and campaign_failure.get("cgroup_failure_observation") is None
        and "cgroup_topology_conformance_diagnostic" not in campaign_failure
        and campaign_failure.get("counter_records_issued") is False
        and campaign_failure.get("successful_ledger_claimed") is False
        and campaign_failure.get("same_identity_rerun_forbidden") is True,
        "ordinal8 typed campaign failure boundary changed",
    )

    progress = inner_failure.get("progress_observations")
    _require(type(progress) is dict, "ordinal8 launch progress changed")
    absent_progress = (
        "evidence_inventory",
        "execution_closure",
        "ledger_closure",
        "os_receipt",
        "receipt",
        "retained_replay",
        "runtime_cas",
        "terminal",
        "verification",
        "verification_failure",
    )
    _require(
        all(progress.get(name) == {"presence": "ABSENT"} for name in absent_progress)
        and progress.get("attempt") == _file_fact("inner_launch_attempt")
        and progress.get("measurement_failure") == _file_fact("campaign_failure"),
        "ordinal8 terminal/replay absence boundary changed",
    )

    observations = campaign_failure.get("partial_artifact_observations")
    _require(type(observations) is list, "ordinal8 artifact observations changed")
    observations_by_path = {
        row.get("relative_path"): row for row in observations if type(row) is dict
    }
    output_path = ".tmp/exact-freeze/v180r12r4_campaign_measurement"
    events_path = f"{output_path}/EVENTS"
    _require(
        len(observations_by_path) == len(observations) == 16
        and observations_by_path[output_path].get("directory_entries") == ["EVENTS"]
        and observations_by_path[events_path].get("directory_entries")
        == ["000000.json"]
        and observations_by_path[f"{events_path}/000000.json"].get("sha256")
        == _FACT_BY_ROLE["attempt_open_event"].sha256,
        "ordinal8 exact one-event artifact inventory changed",
    )

    return FrozenOrdinal8FailureV180r12r4r2(
        campaign_attempt_id=EXPECTED_CAMPAIGN_ATTEMPT_ID,
        campaign_attempt_record_id=attempt_record_id,
        campaign_failure_id=campaign_failure_id,
        event_id=event_id,
        materialization_terminal_id=materialization_id,
        outer_service_launch_attempt_id=outer_attempt_id,
        outer_service_failure_id=outer_failure_id,
        inner_launch_attempt_id=inner_attempt_id,
        inner_launch_failure_id=inner_failure_id,
        source_membership=source_membership,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CAMPAIGN_FAILURE_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "FrozenOrdinal8FailureV180r12r4r2",
    "Ordinal8FailureFreezeV180r12r4r2Error",
    "freeze_ordinal8_failure_v180r12r4r2",
)
