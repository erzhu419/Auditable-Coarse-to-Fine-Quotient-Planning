"""Freeze the consumed ordinal11 T1/T2 process-role failure.

Ordinal11 closed the pre-attempt host-conformance defect and entered the
scientific campaign.  The retained host artifact reports full conformance with
zero mismatches, after which the durable ATTEMPT record and ledger event zero
were written.  The run then rejected one and only one T1/T2 comparison:
``t2.pid`` expected the service-entry launcher's PID 528492 while the bootstrap
child correctly observed its own PID 528493.

Both observations name the same formal systemd service, source membership,
service directory, and cgroup namespace.  This freeze therefore records a
process-role conflation, not service-placement drift, and preserves the exact
one-event failed prefix without claiming a scientific result.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "8d3580a47093351543fcbb7f48c2a15fb1517c9605a756bd4965212014aac63e"
)
EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "72951ca8cd8a25d56c014b0bce46d9fadb01e7802e84a4641e2b08038a62c68d"
)
EXPECTED_CAMPAIGN_FAILURE_ID = (
    "10955e1c58fdaac9583d37bba5ed9278e762b8311f83283b88a300e8b6a8955b"
)
EXPECTED_EVENT_ID = (
    "85d07bc9d094d136d38567354467acdc51d9dd59b56dfbdab15f5e4667c95c86"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "95144b50769048ac82c45a258d0cf820b1934712100e740d3ab36ae48b90c349"
)
EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "cdc99f6b3d4659ccee40332520856daab59a09f2fd739ee1dad7d53fbcb840e7"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "2bd19d84bf24877697395ff7f2c7bdea12d3a6f1331dc56b132a322176681cce"
)
EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "7f41c8089475b6cb323f4674ec674e74a9cb54e1931c5b7d5f3a21f65bb22289"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "96cf56e7e7bb36105d2065b4252e9e7a3cc1052b6aa92ead94ef0d60dd498892"
)
EXPECTED_PROTOCOL_ID = (
    "2aab7e4f285e05072378e1813b0345b966f1fac066a3713c16293f521bf001d5"
)
EXPECTED_AUTHORIZATION_ID = (
    "2de21cf9e7cf746619f5ecb9abad523881da33f65e7fee9319e58cda85661e00"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "ec04806b9341636903698bb9bbffc4b1b633112bbf281cc47bc28cf7f4dbab64"
)
EXPECTED_LOGICAL_OCCURRENCE_ID = (
    "a37770e56698857e162b2099766573ec5cabfc876145496f7d54756271d66599"
)
EXPECTED_EXECUTION_SLOT_ID = (
    "f69bcf6b049a12e7b2d8e1e1a710c64059f8a9a4a58cbda2f58f2fa4986fc3c7"
)
EXPECTED_EXECUTION_NONCE = (
    "7d4ebffb564caeb42550670bf06276f9ef7f456cfa5231acef56497f2bd62ea4"
)
EXPECTED_LAUNCH_RULE_ID = (
    "77943eb671fdc3f1d90c977b7b6405f7127284b223ced1491ba69fda8e91e28a"
)
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "7f0d63c0143c72d3a41f9a4ad25b9fc29f6952ae05a1b4797cded68728d27090"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "0dfee347b3b36527bcc06b81228545043b3aeff8c0163738001653b27e363b91"
)
EXPECTED_C_PRE_COMMIT_ID = "4cbc7a31b6a9c2ee904c6bd404afcd806e9ce9ea"
EXPECTED_C_PRE_TREE_ID = "d5297b4edf045d94849122793ced83be17c96eae"
EXPECTED_EMPTY_BRIDGE_COMMIT_ID = "d87110705a5bf195d4ab57a3ff91f255813dfabb"
EXPECTED_LITERAL_COMMIT_ID = "40b0f66403fcda2dcfd0a3826f07bd0fb9312a07"
EXPECTED_MEASUREMENT_SERVICE_TOKEN = (
    "36656cf3abb876d291de1e6707f86a9971efe447b224ac32b1909bd0d4166297"
)
EXPECTED_PREDECESSOR_FREEZE_ID = (
    "4671ff59a5b141816c8cfe9a692a55354b799f077e6bf4efc8764ee991a34dc7"
)
EXPECTED_PREDECESSOR_INNER_FAILURE_ID = (
    "d1fbf4b24625927cfa723fb33fe72ef633122c62ffc003ab73648f2fb7539f07"
)
EXPECTED_PREDECESSOR_OUTER_FAILURE_ID = (
    "83496c3cf1b3e01b81715e1529c182d4930fccccdb110d1656af737e07f110ec"
)
EXPECTED_SOURCE_MEMBERSHIP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    "acfqp-v180r12r4-measurement-"
    + EXPECTED_MEASUREMENT_SERVICE_TOKEN
    + ".service"
)
EXPECTED_UNIT_NAME = (
    "acfqp-v180r12r4-measurement-"
    + EXPECTED_MEASUREMENT_SERVICE_TOKEN
    + ".service"
)
EXPECTED_T1_PID = 528_492
OBSERVED_T2_PID = 528_493
EXPECTED_FAILURE_CODE = "CGROUP_TOPOLOGY_CONFORMANCE_FAILURE"
EXPECTED_FAILURE_MESSAGE = (
    "CgroupTopologyConformanceErrorV180R12R4R3: "
    "cgroup topology conformance mismatch: t2.pid"
)
EXPECTED_CHILD_STDERR_SHA256 = (
    "14939d3508b7c0e9fcda7ae28cc852d6979d16d1061be59c8500e9f9c439f301"
)
REPAIR_SCOPE = "T1_T2_ROLE_AWARE_PROCESS_ID_CONFORMANCE"

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
    "acfqp:construction-k7-ordinal11-failure-freeze:v180r12r4r6"
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
_PREDECESSOR_T2_V1_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t2.v1"
)
_SUCCESSOR_T2_V2_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t2.v2"
)
_PREDECESSOR_T2_V1_FIELDS = frozenset(
    {
        "boundary",
        "cgroup_namespace_inode",
        "expected_source_membership",
        "nearest_common_ancestor_is_app_slice",
        "nearest_common_ancestor_path",
        "parent_cgroup_procs_o_wronly_openable",
        "planned_measurement_root_state",
        "schema",
        "scientific_progress_absent",
        "scientific_progress_present_paths",
        "self_pid",
        "self_pid_in_source_cgroup_procs",
        "source_membership",
        "source_service_device",
        "source_service_fd",
        "source_service_inode",
        "target",
        "token",
        "unit_name",
    }
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RETAINED_ROOT = (
    _REPOSITORY_ROOT / "retained_evidence/v180r12r4r6_ordinal11_failure"
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
        4_416,
        "a099fcb7a263d9b8ece8b54c319d3b71f78d6c0f1f2e575d1e9b388fc570bcf2",
    ),
    _ArtifactFact(
        "launch_manifest",
        "raw/prelaunch/launch_manifest.json",
        92_704,
        "bc389289f9beab7b3824539b063907e6efe146b5c8e5493df5082c1d503761bc",
    ),
    _ArtifactFact(
        "materialization",
        "raw/prelaunch/materialization_terminal.json",
        38_876,
        "5f16796dfe7f9986ff386c98102c726990c1391e9ea72b2c84bb7d676830242b",
    ),
    _ArtifactFact(
        "outer_service_attempt",
        "raw/prelaunch/outer_service_attempt.json",
        5_313,
        "6ec1df351eca5782d54c80b22661d3357213427348e3800a0d042a74d0128654",
    ),
    _ArtifactFact(
        "inner_launch_attempt",
        "raw/prelaunch/inner_launch_attempt.json",
        4_111,
        "bde00cea28412ce8353ff8111b3a1b12197ced9a2c77bf581743ba35e2334322",
    ),
    _ArtifactFact(
        "outer_service_failure",
        "raw/outer_service_failure.json",
        7_910,
        "ce2f5a47818e90c6a41dd63ee14a2800af0dc752b0cef19eb54aef8bc71d7405",
    ),
    _ArtifactFact(
        "inner_launch_failure",
        "raw/inner_launch_failure.json",
        13_365,
        "463258ce8c811c6e1c4d4bbca931d3a9b5cd89a647aaf4b267490f31036dfc10",
    ),
    _ArtifactFact(
        "host_conformance",
        "raw/host_conformance.json",
        3_962,
        "18f0d46eab5a9b57d670be08a71571b6e9e6c9e60f6cea0b48e39c78f178319e",
    ),
    _ArtifactFact(
        "campaign_attempt",
        "raw/campaign/scientific_attempt.json",
        1_182,
        "3af6e12e011f434c6274b577606003d2cf01191623aba1d7f3f5ef9920c21b12",
    ),
    _ArtifactFact(
        "campaign_failure",
        "raw/campaign/measurement_failure.json",
        18_040,
        "248f1fce864192b32ccecc49689609150c6d624e28f582e2a5d135a0f7694552",
    ),
    _ArtifactFact(
        "attempt_open_event",
        "raw/campaign/EVENTS/000000.json",
        766,
        "aa034a844baee5cdeeaf199dd7d1fff10f00a301f48fa58a865adf90eb475cbb",
    ),
)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}


class Ordinal11FailureFreezeV180r12r4r6Error(ValueError):
    """Raised when retained ordinal11 evidence no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal11FailureFreezeV180r12r4r6Error(message)


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
        f"ordinal11 {field} canonical identity changed",
    )
    return expected


def _read_documents(
    retained_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    documents: dict[str, dict[str, Any]] = {}
    raw_by_role: dict[str, bytes] = {}
    for fact in _ARTIFACT_FACTS:
        try:
            raw = (retained_root / fact.relative_path).read_bytes()
        except OSError as error:
            raise Ordinal11FailureFreezeV180r12r4r6Error(
                f"ordinal11 {fact.role} is unreadable"
            ) from error
        _require(
            len(raw) == fact.byte_count
            and hashlib.sha256(raw).hexdigest() == fact.sha256,
            f"ordinal11 {fact.role} raw bytes changed",
        )
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Ordinal11FailureFreezeV180r12r4r6Error(
                f"ordinal11 {fact.role} is not JSON"
            ) from error
        _require(
            type(document) is dict and _canonical_bytes(document) == raw,
            f"ordinal11 {fact.role} canonical bytes changed",
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
        f"ordinal11 {label} gate boundary changed",
    )


def _freeze_payload(source_membership: str) -> dict[str, Any]:
    return {
        "schema": "acfqp.v180r12r4r6_ordinal11_failure_freeze.v1",
        "campaign_attempt_id": EXPECTED_CAMPAIGN_ATTEMPT_ID,
        "campaign_attempt_record_id": EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        "campaign_failure_id": EXPECTED_CAMPAIGN_FAILURE_ID,
        "event_id": EXPECTED_EVENT_ID,
        "materialization_terminal_id": EXPECTED_MATERIALIZATION_TERMINAL_ID,
        "outer_service_launch_attempt_id": (
            EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID
        ),
        "outer_service_failure_id": EXPECTED_OUTER_SERVICE_FAILURE_ID,
        "inner_launch_attempt_id": EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
        "inner_launch_failure_id": EXPECTED_INNER_LAUNCH_FAILURE_ID,
        "host_conformance_sha256": _FACT_BY_ROLE["host_conformance"].sha256,
        "source_membership": source_membership,
        "t1_pid": EXPECTED_T1_PID,
        "t2_pid": OBSERVED_T2_PID,
        "repair_scope": REPAIR_SCOPE,
    }


def _freeze_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _FREEZE_DOMAIN.encode("ascii") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


EXPECTED_ORDINAL11_FAILURE_FREEZE_ID = (
    "afdc3acd283daf018243acdf9920dfa32140459a6de1dd6bfc3a70c113579105"
)
ORDINAL11_FAILURE_FREEZE_ID = _freeze_id(
    _freeze_payload(EXPECTED_SOURCE_MEMBERSHIP)
)
if ORDINAL11_FAILURE_FREEZE_ID != EXPECTED_ORDINAL11_FAILURE_FREEZE_ID:
    raise RuntimeError("V180r12r4r6 ordinal11 failure-freeze identity changed")


@dataclass(frozen=True, slots=True)
class FrozenOrdinal11FailureV180r12r4r6:
    freeze_id: str
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
    host_conformance: dict[str, Any]
    topology_diagnostic: dict[str, Any]

    def to_contract(self) -> dict[str, Any]:
        """Return the claim-bounded ordinal11 failure contract."""

        return {
            "schema": "acfqp.v180r12r4r6_ordinal11_failure_freeze.v1",
            "freeze_id": self.freeze_id,
            "campaign_attempt_id": self.campaign_attempt_id,
            "campaign_attempt_record_id": self.campaign_attempt_record_id,
            "campaign_failure_id": self.campaign_failure_id,
            "materialization_terminal_id": self.materialization_terminal_id,
            "outer_service_launch_attempt_id": (
                self.outer_service_launch_attempt_id
            ),
            "outer_service_failure_id": self.outer_service_failure_id,
            "inner_launch_attempt_id": self.inner_launch_attempt_id,
            "inner_launch_failure_id": self.inner_launch_failure_id,
            "full_source_conformance": True,
            "source_root_count": 25,
            "host_conformance": self.host_conformance,
            "full_host_conformance": True,
            "host_conformance_mismatch_count": 0,
            "host_conformance_cause": None,
            "scientific_attempt_opened": True,
            "event_ids": [self.event_id],
            "event_kinds": ["ATTEMPT_OPEN"],
            "completed_event_count": 1,
            "failure_code": EXPECTED_FAILURE_CODE,
            "failure_message": EXPECTED_FAILURE_MESSAGE,
            "topology_diagnostic": self.topology_diagnostic,
            "full_t1_t2_conformance": False,
            "topology_diagnostic_unit_ownership_acquired": False,
            "t1_t2_same_formal_service": True,
            "t1_t2_same_source_membership": True,
            "t1_t2_same_service_directory": True,
            "source_membership": self.source_membership,
            "only_mismatch": {
                "field": "t2.pid",
                "expected": EXPECTED_T1_PID,
                "observed": OBSERVED_T2_PID,
            },
            "exact_failure_cause": "T1_T2_PID_ROLE_CONFLATION",
            "t1_process_role": "SERVICE_ENTRY_LAUNCHER",
            "t2_process_role": "BOOTSTRAP_CHILD",
            "distinct_process_roles": True,
            "predecessor_t2_schema": _PREDECESSOR_T2_V1_SCHEMA,
            "successor_t2_schema": _SUCCESSOR_T2_V2_SCHEMA,
            "predecessor_t2_exact_field_count": len(
                _PREDECESSOR_T2_V1_FIELDS
            ),
            "ordinal11_t3_present": False,
            "measurement_root_created_before_failure": True,
            "cleanup_complete": True,
            "post_child_measurement_root_state": "ABSENT",
            "residual_tree_or_process_possible": False,
            "process_may_remain": False,
            "formal_service_collected": True,
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


def freeze_ordinal11_failure_v180r12r4r6(
    retained_root: Path | None = None,
) -> FrozenOrdinal11FailureV180r12r4r6:
    """Validate and freeze the exact consumed ordinal11 failure."""

    root = _DEFAULT_RETAINED_ROOT if retained_root is None else Path(retained_root)
    documents, _raws = _read_documents(root)
    external = documents["external_root"]
    manifest = documents["launch_manifest"]
    materialization = documents["materialization"]
    outer_attempt = documents["outer_service_attempt"]
    inner_attempt = documents["inner_launch_attempt"]
    outer_failure = documents["outer_service_failure"]
    inner_failure = documents["inner_launch_failure"]
    host = documents["host_conformance"]
    campaign_attempt = documents["campaign_attempt"]
    campaign_failure = documents["campaign_failure"]
    event = documents["attempt_open_event"]

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
    event_id = _require_self_id(
        event, "event_id", EXPECTED_EVENT_ID, domain=_EVENT_DOMAIN
    )
    campaign_failure_id = _require_self_id(
        campaign_failure,
        "failure_state_id",
        EXPECTED_CAMPAIGN_FAILURE_ID,
        domain=_FAILURE_DOMAIN,
    )

    frozen_context = external.get("frozen_authorization_context")
    _require(type(frozen_context) is dict, "ordinal11 frozen context changed")
    _require(
        external.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and external.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and external.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and external.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and external.get("created_before_v180r12r4_authorized_measurement_execution")
        is True
        and external.get("v180r12r4_outcome_bytes_accessed") is False
        and frozen_context.get("campaign_attempt_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and frozen_context.get("logical_occurrence_id")
        == EXPECTED_LOGICAL_OCCURRENCE_ID
        and frozen_context.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and frozen_context.get("campaign_measurement_execution_slot_id")
        == EXPECTED_EXECUTION_SLOT_ID
        and frozen_context.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and frozen_context.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and frozen_context.get("execution_nonce") == EXPECTED_EXECUTION_NONCE,
        "ordinal11 external authorization boundary changed",
    )
    _require(
        manifest.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and manifest.get("frozen_authorization_context") == frozen_context,
        "ordinal11 launch manifest context join changed",
    )

    topology = materialization.get("git_topology")
    _require(type(topology) is dict, "ordinal11 Git topology changed")
    _require(
        topology.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and topology.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and topology.get("empty_bridge_commit_id")
        == EXPECTED_EMPTY_BRIDGE_COMMIT_ID
        and topology.get("literal_commit_id") == EXPECTED_LITERAL_COMMIT_ID,
        "ordinal11 final source topology changed",
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
        "ordinal11 materialization boundary changed",
    )
    _require(
        materialization.get("external_root")
        == {
            "absolute_path": (
                "/home/erzhu419/mine_code/acfqp-v180r12r4r5-ordinal11/"
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
        "ordinal11 materialization raw-artifact join changed",
    )

    source_diagnostic = materialization.get("working_tree_source_conformance")
    _require(
        type(source_diagnostic) is dict
        and manifest.get("working_tree_source_conformance") == source_diagnostic,
        "ordinal11 source-conformance diagnostic join changed",
    )
    source_snapshots = source_diagnostic.get("snapshots")
    _require(
        source_diagnostic.get("source_root_count") == 25
        and source_diagnostic.get("mismatch_count") == 0
        and source_diagnostic.get("per_field_mismatches") == []
        and source_diagnostic.get("full_source_conformance") is True
        and source_diagnostic.get("unit_ownership_evaluated") is False
        and source_diagnostic.get("cause") is None
        and type(source_snapshots) is list
        and len(source_snapshots) == 25
        and all(
            type(row) is dict
            and row.get("conformant") is True
            and row.get("mismatch_fields") == []
            and row.get("observed_before") == row.get("observed_after")
            for row in source_snapshots
        ),
        "ordinal11 25-root full source conformance changed",
    )

    host_expected = host.get("expected")
    host_observed = host.get("observed")
    _require(
        type(host_expected) is dict and type(host_observed) is dict,
        "ordinal11 host property snapshots changed",
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
        "ordinal11 host fact snapshots changed",
    )
    parent_compared = host.get("cgroup_parent_compared_fields")
    parent_excluded = host.get("cgroup_parent_excluded_fields")
    runtime_compared = host.get("runtime_capability_compared_fields")
    _require(
        parent_excluded == ["self_membership"]
        and type(parent_compared) is list
        and set(parent_compared) == set(expected_parent) - {"self_membership"}
        and set(expected_parent) == set(observed_parent)
        and type(runtime_compared) is list
        and set(runtime_compared) == set(expected_runtime) == set(observed_runtime)
        and all(expected_parent[field] == observed_parent[field] for field in parent_compared)
        and all(expected_runtime[field] == observed_runtime[field] for field in runtime_compared)
        and observed_parent.get("self_membership") == EXPECTED_SOURCE_MEMBERSHIP
        and host.get("schema")
        == "acfqp.v180r12r4_pre_attempt_host_conformance.v1"
        and host.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and host.get("mismatch_rows") == []
        and host.get("mismatch_count") == 0
        and host.get("cause") is None
        and host.get("full_host_conformance") is True
        and host.get("campaign_attempt_created") is False
        and host.get("campaign_event_or_counter_record_issued") is False
        and host.get("working_tree_source_conformance_joined") is False
        and host.get("production_unit_ownership_t1_joined") is False,
        "ordinal11 full pre-attempt host conformance changed",
    )

    materialization_fact = _FACT_BY_ROLE["materialization"]
    _require(
        outer_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and outer_attempt.get("unit_name") == EXPECTED_UNIT_NAME
        and outer_attempt.get("pre_scientific_outer_dispatch") is True
        and outer_attempt.get("campaign_event_or_evidence_document") is False
        and outer_attempt.get("same_target_identity_rerun_forbidden") is True,
        "ordinal11 outer service attempt join changed",
    )
    _require(
        inner_attempt.get("materialization_terminal_id") == materialization_id
        and inner_attempt.get("materialization_terminal_byte_count")
        == materialization_fact.byte_count
        and inner_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and inner_attempt.get("launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and inner_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_attempt.get("authorized_child_measurement_execution_completed")
        is False
        and inner_attempt.get("scientific_occurrence_started") is False
        and inner_attempt.get("campaign_actual_measurement") is False
        and inner_attempt.get("producer_free_verification_attempted") is False
        and inner_attempt.get("same_target_identity_rerun_forbidden") is True,
        "ordinal11 inner launch attempt boundary changed",
    )

    invocation = outer_attempt.get("production_systemd_service_invocation")
    _require(type(invocation) is dict, "ordinal11 service invocation changed")
    _require(
        invocation
        == inner_attempt.get("production_systemd_service_invocation")
        == outer_failure.get("production_systemd_service_invocation")
        == inner_failure.get("production_systemd_service_invocation")
        and invocation.get("target") == "measurement"
        and invocation.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and invocation.get("unit_name") == EXPECTED_UNIT_NAME
        and invocation.get("unit_kind") == "SERVICE_NOT_SCOPE"
        and invocation.get("service_type") == "exec"
        and invocation.get("delegate") is True
        and invocation.get("token_input")
        == {
            "failed_inner_launch_failure_id": (
                EXPECTED_PREDECESSOR_INNER_FAILURE_ID
            ),
            "failed_outer_service_failure_id": (
                EXPECTED_PREDECESSOR_OUTER_FAILURE_ID
            ),
            "failed_predecessor_freeze_id": EXPECTED_PREDECESSOR_FREEZE_ID,
            "purpose": "MEASUREMENT",
            "repair_scope": (
                "PRE_ATTEMPT_CGROUP_RUNTIME_PROPERTY_SNAPSHOTS_AND_"
                "PER_FIELD_MISMATCH_DIAGNOSTIC"
            ),
        },
        "ordinal11 predecessor repair or service-token join changed",
    )
    launcher_command = invocation.get("launcher_command")
    child_argv = inner_attempt.get("child_argv")
    _require(
        type(launcher_command) is list
        and launcher_command[-3:]
        == [
            "service-entry",
            "measurement",
            "/home/erzhu419/mine_code/acfqp-v180r12r4r5-ordinal11",
        ]
        and launcher_command[-4].endswith("/launcher.py")
        and type(child_argv) is list
        and child_argv[6].endswith("/bootstrap.py")
        and child_argv[7] == "measurement",
        "ordinal11 service-entry/bootstrap process roles changed",
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
        "ordinal11 outer service failure join changed",
    )
    unit_absence = outer_failure.get("collected_unit_absence_observation")
    _require(
        type(unit_absence) is dict
        and unit_absence.get("expected_load_state") == "not-found"
        and unit_absence.get("unit_absent_after_wait_collect") is True
        and unit_absence.get("return_code") == 0
        and unit_absence.get("timed_out") is False,
        "ordinal11 collected service absence changed",
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
        "ordinal11 inner launch failure boundary changed",
    )

    placement_t1 = inner_failure.get("production_runtime_placement_t1")
    _require(type(placement_t1) is dict, "ordinal11 T1 placement changed")
    source_membership = placement_t1.get("source_membership")
    _require(
        source_membership == EXPECTED_SOURCE_MEMBERSHIP
        and placement_t1.get("expected_source_membership") == source_membership
        and placement_t1.get("unit_name") == EXPECTED_UNIT_NAME
        and placement_t1.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and placement_t1.get("self_pid") == EXPECTED_T1_PID
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and placement_t1.get("t1_complete_before_child_popen") is True
        and placement_t1.get("nearest_common_ancestor_is_app_slice") is True
        and placement_t1.get("planned_measurement_root_absent") is True,
        "ordinal11 T1 service-entry placement changed",
    )

    _require(
        campaign_attempt.get("schema")
        == "acfqp.campaign_attempt_record.v180r12r4"
        and campaign_attempt.get("attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and campaign_attempt.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and campaign_attempt.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
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
        and campaign_attempt.get("one_shot_attempt_opened") is True
        and campaign_attempt.get("scope")
        == "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR",
        "ordinal11 scientific ATTEMPT authority join changed",
    )
    common_identity = (
        EXPECTED_PROTOCOL_ID,
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_CAMPAIGN_ATTEMPT_ID,
    )
    _require(
        (event.get("protocol_id"), event.get("authorization_id"), event.get("attempt_id"))
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
        "ordinal11 one-event campaign prefix changed",
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
        and campaign_failure.get("phase") == "STAGE"
        and campaign_failure.get("last_event_id") == event_id
        and campaign_failure.get("completed_event_count") == 1
        and campaign_failure.get("message") == EXPECTED_FAILURE_MESSAGE
        and campaign_failure.get("message_sha256")
        == hashlib.sha256(EXPECTED_FAILURE_MESSAGE.encode("utf-8")).hexdigest()
        and campaign_failure.get("launch_child_created") is False
        and campaign_failure.get("launch_exec_observed") is False
        and campaign_failure.get("launch_pidfd_acquired") is False
        and campaign_failure.get("counter_records_issued") is False
        and campaign_failure.get("successful_ledger_claimed") is False
        and campaign_failure.get("process_may_remain") is False
        and campaign_failure.get("same_identity_rerun_forbidden") is True,
        "ordinal11 typed campaign failure boundary changed",
    )

    diagnostic = campaign_failure.get("cgroup_topology_conformance_diagnostic")
    _require(type(diagnostic) is dict, "ordinal11 topology diagnostic changed")
    expected_properties = diagnostic.get("expected_properties")
    observed_properties = diagnostic.get("observed_properties")
    snapshots = diagnostic.get("property_snapshots")
    _require(
        type(expected_properties) is dict
        and type(observed_properties) is dict
        and set(expected_properties) == set(observed_properties)
        and type(snapshots) is dict,
        "ordinal11 topology property snapshots changed",
    )
    recomputed_mismatches = [
        {
            "expected": expected_properties[field],
            "field": field,
            "observed": observed_properties[field],
        }
        for field in sorted(expected_properties)
        if expected_properties[field] != observed_properties[field]
    ]
    exact_mismatch = {
        "expected": EXPECTED_T1_PID,
        "field": "t2.pid",
        "observed": OBSERVED_T2_PID,
    }
    _require(
        diagnostic.get("schema")
        == "acfqp.campaign_cgroup_topology_conformance_diagnostic.v180r12r4r3"
        and diagnostic.get("scope") == "T1_T2_PLACEMENT"
        and diagnostic.get("full_conformance") is False
        and diagnostic.get("unit_ownership_acquired") is False
        and diagnostic.get("mismatch_rows") == [exact_mismatch]
        and recomputed_mismatches == [exact_mismatch]
        and diagnostic.get("cause")
        == {
            "error_type": "CgroupTopologyConformanceErrorV180R12R4R3",
            "failure_code": EXPECTED_FAILURE_CODE,
            "message": "cgroup topology conformance mismatch: t2.pid",
            "scope": "T1_T2_PLACEMENT",
        },
        "ordinal11 exact t2.pid mismatch changed",
    )
    unit_ownership = snapshots.get("unit_ownership")
    measurement_topology = snapshots.get("measurement_topology")
    _require(
        type(unit_ownership) is dict and type(measurement_topology) is dict,
        "ordinal11 topology snapshots changed",
    )
    snapshot_t1 = unit_ownership.get("production_runtime_placement_t1")
    placement_t2 = unit_ownership.get("production_runtime_placement_t2")
    _require(
        snapshot_t1 == placement_t1
        and type(placement_t2) is dict
        and set(placement_t2) == _PREDECESSOR_T2_V1_FIELDS
        and placement_t2.get("schema") == _PREDECESSOR_T2_V1_SCHEMA
        and placement_t2.get("boundary")
        == "T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL"
        and placement_t2.get("self_pid") == OBSERVED_T2_PID
        and placement_t2.get("self_pid_in_source_cgroup_procs") is True
        and placement_t2.get("source_membership") == source_membership
        and placement_t2.get("expected_source_membership") == source_membership
        and placement_t2.get("unit_name") == placement_t1.get("unit_name")
        and placement_t2.get("token") == placement_t1.get("token")
        and placement_t2.get("cgroup_namespace_inode")
        == placement_t1.get("cgroup_namespace_inode")
        and placement_t2.get("source_service_device")
        == placement_t1.get("source_service_fd_fact", {}).get("device")
        and placement_t2.get("source_service_inode")
        == placement_t1.get("source_service_fd_fact", {}).get("inode")
        and placement_t2.get("source_service_fd")
        == placement_t1.get("source_service_fd_fact", {}).get("fd")
        and EXPECTED_T1_PID != OBSERVED_T2_PID,
        "ordinal11 same-service distinct-role T1/T2 evidence changed",
    )
    _require(
        type(measurement_topology.get("measurement_root")) is dict
        and measurement_topology["measurement_root"].get("role")
        == "MEASUREMENT_ROOT"
        and type(measurement_topology.get("supervisor_leaf")) is dict
        and type(measurement_topology.get("worker_leaf")) is dict,
        "ordinal11 created measurement topology changed",
    )

    stderr = inner_failure.get("child_stderr")
    _require(type(stderr) is dict, "ordinal11 child stderr changed")
    try:
        stderr_raw = bytes.fromhex(stderr.get("retained_prefix_hex", ""))
    except ValueError:
        _fail("ordinal11 child stderr encoding changed")
    _require(
        stderr.get("retained_prefix_truncated") is False
        and stderr.get("byte_count") == len(stderr_raw) == 1_855
        and stderr.get("sha256")
        == hashlib.sha256(stderr_raw).hexdigest()
        == EXPECTED_CHILD_STDERR_SHA256
        and stderr_raw.endswith((EXPECTED_FAILURE_MESSAGE + "\n").encode("utf-8")),
        "ordinal11 exact topology traceback changed",
    )

    observations = campaign_failure.get("partial_artifact_observations")
    _require(type(observations) is list, "ordinal11 artifact observations changed")
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
        == _FACT_BY_ROLE["attempt_open_event"].sha256
        and observations_by_path[
            ".tmp/exact-freeze/v180r12r4_campaign_measurement_attempt.json"
        ].get("sha256")
        == _FACT_BY_ROLE["campaign_attempt"].sha256,
        "ordinal11 exact one-event artifact inventory changed",
    )
    for relative_path in (
        f"{output_path}/EVIDENCE_INVENTORY.json",
        f"{output_path}/EXECUTION_CLOSURE.json",
        f"{output_path}/LEDGER_CLOSURE.json",
        f"{output_path}/OS_RECEIPT.json",
        f"{output_path}/SUBJECT_RESULT.json",
        f"{output_path}/SUBJECT_RESULT.json.partial",
        f"{output_path}/TERMINAL.json",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_cas",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification.json",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_failure.json",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_replay.json",
    ):
        _require(
            observations_by_path[relative_path].get("state") == "ABSENT",
            "ordinal11 terminal, vector, or replay absence changed",
        )

    progress = inner_failure.get("progress_observations")
    _require(type(progress) is dict, "ordinal11 launch progress changed")
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
        "ordinal11 retained progress join changed",
    )

    cleanup = inner_failure.get("measurement_cgroup_cleanup_observations")
    _require(
        type(cleanup) is list
        and [row.get("phase") for row in cleanup]
        == ["BEFORE_POPEN", "CLEANUP", "AFTER_CHILD"]
        and all(row.get("ownership_acquired") is True for row in cleanup)
        and all(row.get("root_state") == "ABSENT" for row in cleanup)
        and all(
            row.get("residual_tree_or_process_possible") is False
            for row in cleanup
        ),
        "ordinal11 cleanup or root-absence evidence changed",
    )

    freeze_id = _freeze_id(_freeze_payload(source_membership))
    _require(
        freeze_id == ORDINAL11_FAILURE_FREEZE_ID,
        "ordinal11 failure-freeze identity changed",
    )
    return FrozenOrdinal11FailureV180r12r4r6(
        freeze_id=freeze_id,
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
        host_conformance=host,
        topology_diagnostic=diagnostic,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID",
    "EXPECTED_CAMPAIGN_FAILURE_ID",
    "EXPECTED_EVENT_ID",
    "EXPECTED_INNER_LAUNCH_ATTEMPT_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_ORDINAL11_FAILURE_FREEZE_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID",
    "EXPECTED_T1_PID",
    "FrozenOrdinal11FailureV180r12r4r6",
    "OBSERVED_T2_PID",
    "ORDINAL11_FAILURE_FREEZE_ID",
    "Ordinal11FailureFreezeV180r12r4r6Error",
    "REPAIR_SCOPE",
    "freeze_ordinal11_failure_v180r12r4r6",
)
