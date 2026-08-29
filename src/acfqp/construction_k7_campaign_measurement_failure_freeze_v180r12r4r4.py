"""Freeze the consumed ordinal9 pre-campaign source-conformance failure.

Ordinal9 acquired the retained production systemd service and entered the
source-bound launcher.  The child rejected one historical failure-freeze
source before creating a campaign-attempt artifact because its working-tree
mode was 0664 while the frozen source contract required 0644.  This module
keeps service-unit ownership separate from full source conformance and never
turns the postmortem diagnosis into a scientific campaign event.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    "1007e510b08d7559dadbc2595e97fa95b3b4059b5091378de2cb8963aa6194fa"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "1a3e0bb6a690a5598b4a77a65788267eda05b9ec22d1b28a817f3086540dc9bb"
)
EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "4b3d7ce35193b9b51d92d86b08240d9741af37c28e3e8612f861504d6805fcf0"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "975593a7652cd71314c203a27d87b7071e9b344d983dc2b72448e1627c45146c"
)
EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "f715ef4fb4615a0e75b7b75f3324a476ea09c3990dcf4cc7b4560353fa37e432"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "a08d14c74426ecc83a23d2851cced5f52f23fd8b99c11f9230846cb7df4ecd7a"
)
EXPECTED_MEASUREMENT_SERVICE_TOKEN = (
    "6796c5433437385a8984bec3663780fd722592210fcafb41a8ea35432c832f2e"
)
EXPECTED_LAUNCH_RULE_ID = (
    "54d92c0c5887605fd97ad18adf27be20ec05d7169174b500eb1c3477f8898b11"
)
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "391275364a4dc21028612643cd25c29d4b87c26fcb9e4bfd92ad2043fa663a8b"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "06222b180023ea967be5e4d88072e646239d06769945073bd29fcf1699f65228"
)
EXPECTED_C_PRE_COMMIT_ID = "9856da3d835842a76d13b3a07fdaa8974865935e"
EXPECTED_C_PRE_TREE_ID = "b856835023d37f956664813cebbbaa462779acb0"

FAILED_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3.py"
)
EXPECTED_FAILED_SOURCE_MODE = 0o644
OBSERVED_FAILED_SOURCE_MODE = 0o664
EXPECTED_FAILED_SOURCE_BYTE_COUNT = 18_677
EXPECTED_FAILED_SOURCE_SHA256 = (
    "93b52ecb67eb71c0965d37a8cf4194b5d21128798f6e5fc68a30947d8d74ded4"
)
EXPECTED_FAILED_SOURCE_GIT_BLOB_ID = (
    "2258fef806253f0c451ad60afd087c60f4269752"
)
EXPECTED_RUNTIME_EXCEPTION_TYPE = "CampaignMeasurementProtocolV180R12R4Error"
EXPECTED_RUNTIME_EXCEPTION_MESSAGE = (
    "V180r12r3 failure-freeze source byte identity changed"
)
REPAIR_SCOPE = "WORKING_TREE_SOURCE_MODE_CONFORMANCE_AND_TYPED_DIAGNOSTIC"

_SERVICE_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
_SERVICE_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
_FREEZE_DOMAIN = (
    "acfqp:construction-k7-ordinal9-failure-freeze:v180r12r4r4"
)
_GATE_NAMES = (
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RETAINED_ROOT = (
    _REPOSITORY_ROOT / "retained_evidence/v180r12r4r4_ordinal9_failure"
)


@dataclass(frozen=True, slots=True)
class _ArtifactFact:
    role: str
    relative_path: str
    byte_count: int
    sha256: str


_ARTIFACT_FACTS = (
    _ArtifactFact(
        "external_root",
        "raw/external_root.json",
        4_462,
        "252e8766be4d8c0e634dacd8980ccee7132843dbbae4e9c0680446b27e0630f4",
    ),
    _ArtifactFact(
        "launch_manifest",
        "raw/prelaunch/launch_manifest.json",
        59_490,
        "28fc55529c75d348f8ca048f0673b4eb916b8667ad6e8fb5c42880e288d71120",
    ),
    _ArtifactFact(
        "materialization",
        "raw/prelaunch/materialization_terminal.json",
        7_148,
        "5b5a481668b09c8d39533e945b35fefd537a53df4b8c9113afd3e84a3101cb5a",
    ),
    _ArtifactFact(
        "outer_service_attempt",
        "raw/prelaunch/outer_service_attempt.json",
        5_273,
        "bbad9e61bbf10d2d2d2e34027e11463610f0ef6d03b8d5de35e51e899a84728f",
    ),
    _ArtifactFact(
        "inner_launch_attempt",
        "raw/prelaunch/inner_launch_attempt.json",
        4_068,
        "34e318dc4dc000f98dfb16f3b93fb634411cdd9314e3e25f9410af0769002082",
    ),
    _ArtifactFact(
        "outer_service_failure",
        "raw/outer_service_failure.json",
        7_861,
        "1d95c8aa5996bff37d617795d93d6223255388bc7c272398b6deda3d0c62762f",
    ),
    _ArtifactFact(
        "inner_launch_failure",
        "raw/inner_launch_failure.json",
        16_746,
        "e54f8ab43f4d9890e79cc352a691658ed6fa899513c297841064fa5c757d7527",
    ),
    _ArtifactFact(
        "postmortem",
        "source_conformance_postmortem.json",
        1_485,
        "f8ec18272b71319315b38d9c4fa6e16e47e5a14b3c2137332150a6d884bb5daf",
    ),
)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}


class Ordinal9FailureFreezeV180r12r4r4Error(ValueError):
    """Raised when the retained ordinal9 failure no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal9FailureFreezeV180r12r4r4Error(message)


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
    _require(claimed == expected == actual, f"ordinal9 {field} identity changed")
    return expected


def _read_documents(
    retained_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    documents: dict[str, dict[str, Any]] = {}
    raws: dict[str, bytes] = {}
    for fact in _ARTIFACT_FACTS:
        try:
            raw = (retained_root / fact.relative_path).read_bytes()
        except OSError as error:
            raise Ordinal9FailureFreezeV180r12r4r4Error(
                f"ordinal9 {fact.role} is unreadable"
            ) from error
        _require(
            len(raw) == fact.byte_count
            and hashlib.sha256(raw).hexdigest() == fact.sha256,
            f"ordinal9 {fact.role} raw bytes changed",
        )
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Ordinal9FailureFreezeV180r12r4r4Error(
                f"ordinal9 {fact.role} is not JSON"
            ) from error
        canonical_raw = (
            raw[:-1]
            if fact.role == "postmortem" and raw.endswith(b"\n")
            else raw
        )
        _require(
            type(document) is dict and _canonical_bytes(document) == canonical_raw,
            f"ordinal9 {fact.role} canonical bytes changed",
        )
        documents[fact.role] = document
        raws[fact.role] = raw
    return documents, raws


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
        f"ordinal9 {label} gate boundary changed",
    )


@dataclass(frozen=True, slots=True)
class FrozenOrdinal9FailureV180r12r4r4:
    freeze_id: str
    logical_campaign_attempt_id: str
    materialization_terminal_id: str
    outer_service_launch_attempt_id: str
    outer_service_failure_id: str
    inner_launch_attempt_id: str
    inner_launch_failure_id: str
    source_membership: str
    source_conformance_diagnostic: dict[str, Any]

    def to_contract(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v180r12r4r4_ordinal9_failure_freeze.v1",
            "freeze_id": self.freeze_id,
            "logical_campaign_attempt_id": self.logical_campaign_attempt_id,
            "campaign_attempt_artifact_present": False,
            "campaign_started": False,
            "campaign_ledger_event_count": 0,
            "materialization_terminal_id": self.materialization_terminal_id,
            "outer_service_launch_attempt_id": self.outer_service_launch_attempt_id,
            "outer_service_failure_id": self.outer_service_failure_id,
            "inner_launch_attempt_id": self.inner_launch_attempt_id,
            "inner_launch_failure_id": self.inner_launch_failure_id,
            "failure_phase": "SOURCE_BOUND_PROTOCOL_REPLAY_BEFORE_CAMPAIGN",
            "failure_class": "WORKING_TREE_SOURCE_MODE_CONFORMANCE_FAILURE",
            "runtime_exception_type": EXPECTED_RUNTIME_EXCEPTION_TYPE,
            "runtime_exception_message": EXPECTED_RUNTIME_EXCEPTION_MESSAGE,
            "outer_service_unit_ownership_acquired": True,
            "source_membership": self.source_membership,
            "full_source_conformance": False,
            "runtime_full_property_diagnostic_recorded": False,
            "postmortem_full_property_diagnostic_recorded": True,
            "source_conformance_diagnostic": self.source_conformance_diagnostic,
            "counter_records_issued": False,
            "work_vectors_issued": False,
            "comparison_vectors_issued": False,
            "gate_statuses": {name: "NOT_RUN" for name in _GATE_NAMES},
            "official_execution_allowed": False,
            "independent_replay_present": False,
            "identity_consumed": True,
            "same_identity_rerun_forbidden": True,
            "fresh_successor_identity_required": True,
            "repair_scope": REPAIR_SCOPE,
        }


def _freeze_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _FREEZE_DOMAIN.encode("ascii") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


def freeze_ordinal9_failure_v180r12r4r4(
    retained_root: Path | None = None,
) -> FrozenOrdinal9FailureV180r12r4r4:
    """Validate and freeze the exact consumed ordinal9 pre-campaign failure."""

    root = _DEFAULT_RETAINED_ROOT if retained_root is None else Path(retained_root)
    documents, _raws = _read_documents(root)
    external = documents["external_root"]
    manifest = documents["launch_manifest"]
    materialization = documents["materialization"]
    outer_attempt = documents["outer_service_attempt"]
    outer_failure = documents["outer_service_failure"]
    inner_attempt = documents["inner_launch_attempt"]
    inner_failure = documents["inner_launch_failure"]
    postmortem = documents["postmortem"]

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
    outer_failure_id = _require_self_id(
        outer_failure,
        "service_launch_failure_id",
        EXPECTED_OUTER_SERVICE_FAILURE_ID,
        domain=_SERVICE_FAILURE_DOMAIN,
    )
    inner_attempt_id = _require_self_id(
        inner_attempt,
        "launch_attempt_id",
        EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
    )
    inner_failure_id = _require_self_id(
        inner_failure,
        "launch_failure_id",
        EXPECTED_INNER_LAUNCH_FAILURE_ID,
    )

    frozen_context = external.get("frozen_authorization_context")
    _require(type(frozen_context) is dict, "ordinal9 frozen context changed")
    _require(
        external.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and external.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and external.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and external.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and frozen_context.get("campaign_attempt_id")
        == EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID,
        "ordinal9 external authorization boundary changed",
    )
    _require(
        manifest.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and manifest.get("frozen_authorization_context") == frozen_context,
        "ordinal9 launch manifest context join changed",
    )

    _require_gates_not_run(materialization, "materialization")
    _require(
        materialization.get("success") is True
        and materialization.get("construction_only") is True
        and materialization.get("campaign_actual_measurement") is False
        and materialization.get("scientific_occurrence_executed") is False
        and materialization.get("counter_records_issued") is False
        and materialization.get("work_vectors_issued") is False
        and materialization.get("comparison_vectors_issued") is False
        and materialization.get("same_materialization_identity_rerun_forbidden")
        is True,
        "ordinal9 materialization boundary changed",
    )

    materialization_fact = _FACT_BY_ROLE["materialization"]
    _require(
        outer_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and outer_attempt.get("same_target_identity_rerun_forbidden") is True,
        "ordinal9 outer attempt join changed",
    )
    _require(
        inner_attempt.get("materialization_terminal_id") == materialization_id
        and inner_attempt.get("materialization_terminal_byte_count")
        == materialization_fact.byte_count
        and inner_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and inner_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_attempt.get("authorized_child_measurement_execution_completed")
        is False,
        "ordinal9 inner attempt join changed",
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
        and outer_failure.get("exact_attempt_terminal_join") is True
        and outer_failure.get("systemd_run_return_code") == 1
        and outer_failure.get("systemd_run_timed_out") is False
        and outer_failure.get("success") is False,
        "ordinal9 outer failure join changed",
    )
    _require_gates_not_run(inner_failure, "inner failure")
    _require(
        inner_failure.get("launch_attempt_id") == inner_attempt_id
        and inner_failure.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_failure.get("return_code") == 1
        and inner_failure.get("timed_out") is False
        and inner_failure.get("attempt_lock_preserved") is True
        and inner_failure.get("same_target_identity_rerun_forbidden") is True
        and inner_failure.get("campaign_actual_measurement") is False
        and inner_failure.get("success") is False,
        "ordinal9 inner failure boundary changed",
    )

    placement = inner_failure.get("production_runtime_placement_t1")
    _require(type(placement) is dict, "ordinal9 T1 placement changed")
    source_membership = placement.get("source_membership")
    _require(
        source_membership == placement.get("expected_source_membership")
        and placement.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and placement.get("self_pid_in_source_cgroup_procs") is True
        and placement.get("t1_complete_before_child_popen") is True
        and placement.get("nearest_common_ancestor_is_app_slice") is True,
        "ordinal9 service-unit ownership evidence changed",
    )
    cleanup = inner_failure.get("measurement_cgroup_cleanup_observations")
    _require(
        type(cleanup) is list
        and len(cleanup) == 3
        and all(row.get("ownership_acquired") is True for row in cleanup)
        and all(row.get("root_state") == "ABSENT" for row in cleanup)
        and all(row.get("residual_tree_or_process_possible") is False for row in cleanup),
        "ordinal9 cleanup evidence changed",
    )

    progress = inner_failure.get("progress_observations")
    _require(type(progress) is dict, "ordinal9 progress observations changed")
    _require(
        progress.get("attempt") == _file_fact("inner_launch_attempt")
        and all(
            progress.get(name) == {"presence": "ABSENT"}
            for name in (
                "output_root",
                "measurement_failure",
                "terminal",
                "receipt",
                "verification",
                "verification_failure",
                "retained_replay",
                "ledger_closure",
                "evidence_inventory",
                "execution_closure",
                "os_receipt",
                "runtime_cas",
            )
        ),
        "ordinal9 pre-campaign absence boundary changed",
    )

    stderr = inner_failure.get("child_stderr")
    _require(type(stderr) is dict, "ordinal9 child stderr changed")
    try:
        stderr_raw = bytes.fromhex(stderr.get("retained_prefix_hex", ""))
    except ValueError:
        _fail("ordinal9 child stderr encoding changed")
    _require(
        stderr.get("retained_prefix_truncated") is False
        and stderr.get("byte_count") == len(stderr_raw) == 3_703
        and stderr.get("sha256") == hashlib.sha256(stderr_raw).hexdigest()
        and stderr_raw.endswith(
            (EXPECTED_RUNTIME_EXCEPTION_TYPE + ": " + EXPECTED_RUNTIME_EXCEPTION_MESSAGE + "\n").encode("ascii")
        ),
        "ordinal9 exact runtime exception changed",
    )

    snapshot = postmortem.get("failed_source_snapshot")
    expected = postmortem.get("expected")
    _require(type(snapshot) is dict and type(expected) is dict, "ordinal9 source snapshot changed")
    before = snapshot.get("before")
    after = snapshot.get("after")
    _require(
        postmortem.get("observation_kind")
        == "POSTMORTEM_FORENSIC_READ_NOT_RUNTIME_FAILURE_ARTIFACT"
        and postmortem.get("source_root_count") == 23
        and postmortem.get("all_source_roots_mode_0664") is True
        and postmortem.get("all_source_root_modes") == [OBSERVED_FAILED_SOURCE_MODE] * 23
        and postmortem.get("campaign_attempt_artifact_present") is False
        and postmortem.get("runtime_exception_type")
        == EXPECTED_RUNTIME_EXCEPTION_TYPE
        and postmortem.get("runtime_exception_message")
        == EXPECTED_RUNTIME_EXCEPTION_MESSAGE
        and postmortem.get("mismatch_fields") == ["mode"]
        and snapshot.get("relative_path") == FAILED_SOURCE_RELATIVE_PATH
        and snapshot.get("regular") is True
        and snapshot.get("sha256") == EXPECTED_FAILED_SOURCE_SHA256
        and snapshot.get("git_blob_id") == EXPECTED_FAILED_SOURCE_GIT_BLOB_ID
        and type(before) is dict
        and type(after) is dict
        and before == after
        and before.get("mode") == OBSERVED_FAILED_SOURCE_MODE
        and before.get("st_size") == EXPECTED_FAILED_SOURCE_BYTE_COUNT
        and before.get("st_nlink") == 1
        and expected
        == {
            "git_blob_id": EXPECTED_FAILED_SOURCE_GIT_BLOB_ID,
            "mode": EXPECTED_FAILED_SOURCE_MODE,
            "regular": True,
            "sha256": EXPECTED_FAILED_SOURCE_SHA256,
            "st_nlink": 1,
            "st_size": EXPECTED_FAILED_SOURCE_BYTE_COUNT,
        },
        "ordinal9 full property snapshot or per-field mismatch changed",
    )

    base_payload = {
        "schema": "acfqp.v180r12r4r4_ordinal9_failure_freeze.v1",
        "logical_campaign_attempt_id": EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID,
        "materialization_terminal_id": materialization_id,
        "outer_service_launch_attempt_id": outer_attempt_id,
        "outer_service_failure_id": outer_failure_id,
        "inner_launch_attempt_id": inner_attempt_id,
        "inner_launch_failure_id": inner_failure_id,
        "source_membership": source_membership,
        "source_conformance_diagnostic_sha256": _FACT_BY_ROLE["postmortem"].sha256,
        "repair_scope": REPAIR_SCOPE,
    }
    freeze_id = _freeze_id(base_payload)
    return FrozenOrdinal9FailureV180r12r4r4(
        freeze_id=freeze_id,
        logical_campaign_attempt_id=EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID,
        materialization_terminal_id=materialization_id,
        outer_service_launch_attempt_id=outer_attempt_id,
        outer_service_failure_id=outer_failure_id,
        inner_launch_attempt_id=inner_attempt_id,
        inner_launch_failure_id=inner_failure_id,
        source_membership=source_membership,
        source_conformance_diagnostic=postmortem,
    )


ORDINAL9_FAILURE_FREEZE_ID = _freeze_id(
    {
        "schema": "acfqp.v180r12r4r4_ordinal9_failure_freeze.v1",
        "logical_campaign_attempt_id": EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID,
        "materialization_terminal_id": EXPECTED_MATERIALIZATION_TERMINAL_ID,
        "outer_service_launch_attempt_id": EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID,
        "outer_service_failure_id": EXPECTED_OUTER_SERVICE_FAILURE_ID,
        "inner_launch_attempt_id": EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
        "inner_launch_failure_id": EXPECTED_INNER_LAUNCH_FAILURE_ID,
        "source_membership": (
            "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
            "acfqp-v180r12r4-measurement-"
            + EXPECTED_MEASUREMENT_SERVICE_TOKEN
            + ".service"
        ),
        "source_conformance_diagnostic_sha256": _FACT_BY_ROLE["postmortem"].sha256,
        "repair_scope": REPAIR_SCOPE,
    }
)


__all__ = (
    "EXPECTED_INNER_LAUNCH_ATTEMPT_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID",
    "FAILED_SOURCE_RELATIVE_PATH",
    "FrozenOrdinal9FailureV180r12r4r4",
    "OBSERVED_FAILED_SOURCE_MODE",
    "ORDINAL9_FAILURE_FREEZE_ID",
    "Ordinal9FailureFreezeV180r12r4r4Error",
    "REPAIR_SCOPE",
    "freeze_ordinal9_failure_v180r12r4r4",
)
