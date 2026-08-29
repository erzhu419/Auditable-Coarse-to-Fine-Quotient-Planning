"""Freeze the consumed ordinal10 pre-campaign runtime-fact failure.

Ordinal10 closed the predecessor source-mode defect: all 24 required source
roots were conformant.  It also acquired the production systemd service and
completed T1 ownership.  The source-bound runner then reported only the
generic disjunction that either a cgroup-parent fact or a runtime-capability
fact drifted before the scientific ATTEMPT was created.

The seven retained runtime artifacts contain no reobserved property snapshot,
per-field mismatch row, or exact cause dimension for that drift.  This freeze
therefore preserves that absence and never substitutes a later postmortem
Delegate diagnosis for ordinal10 runtime evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    "7d8e935e86f29c1d884d13744c9893dee44d073a305bd09738dbd3414e7054d5"
)
EXPECTED_LOGICAL_OCCURRENCE_ID = (
    "a37770e56698857e162b2099766573ec5cabfc876145496f7d54756271d66599"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "3dff00eabeb7b0821d5b537a2c5962c6665c8b376e9d4109ac74b31de37d2a65"
)
EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "137ea9b0e7f12f2d17c2b95e6cc509c79d08dcadd153252c7662f5d76342af3e"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "83496c3cf1b3e01b81715e1529c182d4930fccccdb110d1656af737e07f110ec"
)
EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "7f5c841ccfec328e40aff5c30727e580ace0e7a59529c5428366451fda90a74a"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "d1fbf4b24625927cfa723fb33fe72ef633122c62ffc003ab73648f2fb7539f07"
)
EXPECTED_MEASUREMENT_SERVICE_TOKEN = (
    "c8d74b0ae750955932b08df9de7a3566368ba20e94ccb16696037c0446577bb6"
)
EXPECTED_PREDECESSOR_FAILURE_FREEZE_ID = (
    "296731d463b996bb4ff57133505babab9b5d7a3117d6fcdaa94b8ecb1e1050d0"
)
EXPECTED_PREDECESSOR_INNER_FAILURE_ID = (
    "a08d14c74426ecc83a23d2851cced5f52f23fd8b99c11f9230846cb7df4ecd7a"
)
EXPECTED_PREDECESSOR_OUTER_FAILURE_ID = (
    "975593a7652cd71314c203a27d87b7071e9b344d983dc2b72448e1627c45146c"
)
EXPECTED_PROTOCOL_ID = (
    "eecd48abe2bfdb70ebdaf02747e4b48fb91307dc0d8564e36e61dee3bd654404"
)
EXPECTED_EXECUTION_SLOT_ID = (
    "441e09f2acb60b3f7a509d7bd1fb46c6635bb07269855a3993ff3b60a6ef17e8"
)
EXPECTED_AUTHORIZATION_ID = (
    "2ae76f19d496bf0f8596164591a1b98d4085a7e8251ed4f28776e10699958ad1"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "529f56da73c2881500dbbc7b5af51aaa45af5a62ead0ff7ee5eed68d23ab403d"
)
EXPECTED_EXECUTION_NONCE = (
    "7d4ebffb564caeb42550670bf06276f9ef7f456cfa5231acef56497f2bd62ea4"
)
EXPECTED_LAUNCH_RULE_ID = (
    "877a9f71160af1dce86c06ac8a466cc32fd2a7de46cd385aaabcc93d26e456a1"
)
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "e632515031d29fbe77f59dbe3bbe8255797a33c11142548279d319ba32166fb3"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "d9845516a7f71827dadca0b42dfd75ee272fe514cfcb9e598080bde254dc6034"
)
EXPECTED_C_PRE_COMMIT_ID = "2d36fd8c1a5caccca6e9d55893a92033d4adf083"
EXPECTED_C_PRE_TREE_ID = "ef8ba30f17ded099fe16836ba1a5d1817a004a8a"
EXPECTED_EMPTY_BRIDGE_COMMIT_ID = "935f3250bc868d8fee6ab7e01429530733a99701"
EXPECTED_LITERAL_COMMIT_ID = "8648b27152bab69baa5b2625e3dff764f52b2224"
EXPECTED_SOURCE_CONFORMANCE_DIAGNOSTIC_SHA256 = (
    "380ee5b4d17eb3bdb39ac88312c816cbcf8dd86b5c2e469baeac952de7c23f55"
)
EXPECTED_RUNTIME_EXCEPTION_TYPE = "V180R12R4RuntimeError"
EXPECTED_RUNTIME_EXCEPTION_MESSAGE = (
    "pre-attempt cgroup or runtime capability fact drifted"
)
EXPECTED_RUNTIME_STDERR_SHA256 = (
    "6a0682d479149bd95170dacb56235bb5eca3ee12348cb3d8c1317a0c5a38c30d"
)
EXPECTED_SOURCE_MEMBERSHIP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    "acfqp-v180r12r4-measurement-"
    + EXPECTED_MEASUREMENT_SERVICE_TOKEN
    + ".service"
)
REPAIR_SCOPE = (
    "PRE_ATTEMPT_CGROUP_RUNTIME_PROPERTY_SNAPSHOTS_AND_PER_FIELD_MISMATCH_"
    "DIAGNOSTIC"
)

_SERVICE_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
_SERVICE_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
_FREEZE_DOMAIN = (
    "acfqp:construction-k7-ordinal10-failure-freeze:v180r12r4r5"
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
    "measurement_failure",
    "os_receipt",
    "output_root",
    "receipt",
    "retained_replay",
    "runtime_cas",
    "terminal",
    "verification",
    "verification_failure",
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RETAINED_ROOT = (
    _REPOSITORY_ROOT / "retained_evidence/v180r12r4r5_ordinal10_failure"
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
        4_350,
        "4b76f961823077007420210fda69fe4168b131c430f5cbcfb49b6fd04939f17d",
    ),
    _ArtifactFact(
        "launch_manifest",
        "raw/prelaunch/launch_manifest.json",
        90_619,
        "0ce408353741ee160c4e9dd45ff97260d7311d78ebb5d487e30f2b9f1d1ef7e3",
    ),
    _ArtifactFact(
        "materialization",
        "raw/prelaunch/materialization_terminal.json",
        37_615,
        "4c162151ee6bbbce61d5731b8fed59946a7f0f1da0c20b4627c365c417426237",
    ),
    _ArtifactFact(
        "outer_service_attempt",
        "raw/prelaunch/outer_service_attempt.json",
        5_291,
        "ec75aafaeba30fbf76e2cb07a2bfaf291eb1d58e3fef1b22f5e5e42538986d1d",
    ),
    _ArtifactFact(
        "inner_launch_attempt",
        "raw/prelaunch/inner_launch_attempt.json",
        4_089,
        "bd03aa04a82a3c9b1d5e60bf2acff998884cb51049ea0cf1e11838b8e6b902c6",
    ),
    _ArtifactFact(
        "outer_service_failure",
        "raw/outer_service_failure.json",
        7_888,
        "7763e4e67fc8754b414a8226e8a22f5d2466fc2ad47258bc6306817fa424b1da",
    ),
    _ArtifactFact(
        "inner_launch_failure",
        "raw/inner_launch_failure.json",
        13_705,
        "16e869747b686d6fe0d81f575b18dfb5e97aea7bcc4da653b35457f756b99281",
    ),
)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}


class Ordinal10FailureFreezeV180r12r4r5Error(ValueError):
    """Raised when retained ordinal10 evidence no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal10FailureFreezeV180r12r4r5Error(message)


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
    _require(claimed == expected == actual, f"ordinal10 {field} identity changed")
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
            raise Ordinal10FailureFreezeV180r12r4r5Error(
                f"ordinal10 {fact.role} is unreadable"
            ) from error
        _require(
            len(raw) == fact.byte_count
            and hashlib.sha256(raw).hexdigest() == fact.sha256,
            f"ordinal10 {fact.role} raw bytes changed",
        )
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Ordinal10FailureFreezeV180r12r4r5Error(
                f"ordinal10 {fact.role} is not JSON"
            ) from error
        _require(
            type(document) is dict and _canonical_bytes(document) == raw,
            f"ordinal10 {fact.role} canonical bytes changed",
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
        f"ordinal10 {label} gate boundary changed",
    )


def _freeze_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _FREEZE_DOMAIN.encode("ascii") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


def _freeze_payload(source_membership: str) -> dict[str, Any]:
    return {
        "schema": "acfqp.v180r12r4r5_ordinal10_failure_freeze.v1",
        "logical_campaign_attempt_id": EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID,
        "materialization_terminal_id": EXPECTED_MATERIALIZATION_TERMINAL_ID,
        "outer_service_launch_attempt_id": (
            EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID
        ),
        "outer_service_failure_id": EXPECTED_OUTER_SERVICE_FAILURE_ID,
        "inner_launch_attempt_id": EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
        "inner_launch_failure_id": EXPECTED_INNER_LAUNCH_FAILURE_ID,
        "source_membership": source_membership,
        "source_conformance_diagnostic_sha256": (
            EXPECTED_SOURCE_CONFORMANCE_DIAGNOSTIC_SHA256
        ),
        "runtime_exception_stderr_sha256": EXPECTED_RUNTIME_STDERR_SHA256,
        "repair_scope": REPAIR_SCOPE,
    }


EXPECTED_ORDINAL10_FAILURE_FREEZE_ID = (
    "4671ff59a5b141816c8cfe9a692a55354b799f077e6bf4efc8764ee991a34dc7"
)
ORDINAL10_FAILURE_FREEZE_ID = _freeze_id(
    _freeze_payload(EXPECTED_SOURCE_MEMBERSHIP)
)
if ORDINAL10_FAILURE_FREEZE_ID != EXPECTED_ORDINAL10_FAILURE_FREEZE_ID:
    raise RuntimeError("V180r12r4r5 ordinal10 failure-freeze identity changed")


@dataclass(frozen=True, slots=True)
class FrozenOrdinal10FailureV180r12r4r5:
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
            "schema": "acfqp.v180r12r4r5_ordinal10_failure_freeze.v1",
            "freeze_id": self.freeze_id,
            "logical_campaign_attempt_id": self.logical_campaign_attempt_id,
            "materialization_terminal_id": self.materialization_terminal_id,
            "outer_service_launch_attempt_id": self.outer_service_launch_attempt_id,
            "outer_service_failure_id": self.outer_service_failure_id,
            "inner_launch_attempt_id": self.inner_launch_attempt_id,
            "inner_launch_failure_id": self.inner_launch_failure_id,
            "prelaunch_materialization_succeeded": True,
            "source_root_count": 24,
            "full_source_conformance": True,
            "source_conformance_mismatch_count": 0,
            "source_conformance_cause": None,
            "source_conformance_full_property_snapshots_recorded": True,
            "source_conformance_diagnostic": self.source_conformance_diagnostic,
            "outer_service_unit_ownership_acquired": True,
            "source_membership": self.source_membership,
            "production_runtime_placement_t1_complete": True,
            "production_runtime_placement_t2_complete": False,
            "failure_phase": "RUNNER_PRE_ATTEMPT_REVALIDATION_BEFORE_CAMPAIGN",
            "failure_class": "PRE_ATTEMPT_CGROUP_OR_RUNTIME_CAPABILITY_FACT_DRIFT",
            "runtime_exception_type": EXPECTED_RUNTIME_EXCEPTION_TYPE,
            "runtime_exception_message": EXPECTED_RUNTIME_EXCEPTION_MESSAGE,
            "runtime_failure_generic_cause_recorded": True,
            "runtime_failure_property_snapshots_recorded": False,
            "runtime_failure_per_field_mismatch_recorded": False,
            "runtime_failure_exact_cause_dimension_recorded": False,
            "postmortem_delegate_diagnostic_consumed": False,
            "authorized_child_measurement_execution_attempted": True,
            "authorized_child_measurement_execution_completed": False,
            "campaign_attempt_artifact_present": False,
            "campaign_started": False,
            "campaign_ledger_event_count": 0,
            "campaign_artifacts_absent": True,
            "counter_records_issued": False,
            "work_vectors_issued": False,
            "comparison_vectors_issued": False,
            "gate_statuses": {name: "NOT_RUN" for name in _GATE_NAMES},
            "official_execution_allowed": False,
            "independent_replay_present": False,
            "residual_tree_or_process_possible": False,
            "identity_consumed": True,
            "same_identity_rerun_forbidden": True,
            "fresh_successor_identity_required": True,
            "repair_scope": REPAIR_SCOPE,
        }


def freeze_ordinal10_failure_v180r12r4r5(
    retained_root: Path | None = None,
) -> FrozenOrdinal10FailureV180r12r4r5:
    """Validate and freeze the exact consumed ordinal10 failure."""

    root = _DEFAULT_RETAINED_ROOT if retained_root is None else Path(retained_root)
    documents, _raws = _read_documents(root)
    external = documents["external_root"]
    manifest = documents["launch_manifest"]
    materialization = documents["materialization"]
    outer_attempt = documents["outer_service_attempt"]
    inner_attempt = documents["inner_launch_attempt"]
    outer_failure = documents["outer_service_failure"]
    inner_failure = documents["inner_launch_failure"]

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

    frozen_context = external.get("frozen_authorization_context")
    _require(type(frozen_context) is dict, "ordinal10 frozen context changed")
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
        == EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and frozen_context.get("logical_occurrence_id")
        == EXPECTED_LOGICAL_OCCURRENCE_ID
        and frozen_context.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and frozen_context.get("campaign_measurement_execution_slot_id")
        == EXPECTED_EXECUTION_SLOT_ID
        and frozen_context.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and frozen_context.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and frozen_context.get("execution_nonce") == EXPECTED_EXECUTION_NONCE
        and type(frozen_context.get("cgroup_parent_fact")) is dict
        and type(frozen_context.get("runtime_capability_fact")) is dict,
        "ordinal10 external authorization boundary changed",
    )
    _require(
        manifest.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and manifest.get("frozen_authorization_context") == frozen_context,
        "ordinal10 launch manifest context join changed",
    )

    topology = materialization.get("git_topology")
    _require(type(topology) is dict, "ordinal10 Git topology changed")
    _require(
        topology.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and topology.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and topology.get("empty_bridge_commit_id")
        == EXPECTED_EMPTY_BRIDGE_COMMIT_ID
        and topology.get("literal_commit_id") == EXPECTED_LITERAL_COMMIT_ID,
        "ordinal10 final source topology changed",
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
        is True
        and materialization.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and materialization.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID,
        "ordinal10 materialization boundary changed",
    )
    _require(
        materialization.get("external_root")
        == {
            "absolute_path": (
                "/home/erzhu419/mine_code/acfqp-v180r12r4r4-ordinal10/"
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
        "ordinal10 materialization raw artifact join changed",
    )

    source_diagnostic = materialization.get("working_tree_source_conformance")
    _require(
        type(source_diagnostic) is dict
        and manifest.get("working_tree_source_conformance") == source_diagnostic
        and hashlib.sha256(_canonical_bytes(source_diagnostic)).hexdigest()
        == EXPECTED_SOURCE_CONFORMANCE_DIAGNOSTIC_SHA256,
        "ordinal10 source-conformance diagnostic join changed",
    )
    snapshots = source_diagnostic.get("snapshots")
    _require(
        source_diagnostic.get("schema")
        == "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        and source_diagnostic.get("phase")
        == "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN"
        and source_diagnostic.get("source_root_count") == 24
        and source_diagnostic.get("mismatch_count") == 0
        and source_diagnostic.get("per_field_mismatches") == []
        and source_diagnostic.get("full_source_conformance") is True
        and source_diagnostic.get("unit_ownership_evaluated") is False
        and source_diagnostic.get("cause") is None
        and type(snapshots) is list
        and len(snapshots) == 24
        and len({row.get("relative_path") for row in snapshots}) == 24
        and all(
            type(row) is dict
            and row.get("conformant") is True
            and row.get("mismatch_fields") == []
            and type(row.get("expected")) is dict
            and type(row.get("observed_before")) is dict
            and row.get("observed_before") == row.get("observed_after")
            and type(row.get("observed_content")) is dict
            for row in snapshots
        ),
        "ordinal10 24-root full source conformance changed",
    )

    materialization_fact = _FACT_BY_ROLE["materialization"]
    _require(
        outer_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_sha256")
        == materialization_fact.sha256
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and outer_attempt.get("pre_scientific_outer_dispatch") is True
        and outer_attempt.get("campaign_event_or_evidence_document") is False
        and outer_attempt.get("same_target_identity_rerun_forbidden") is True,
        "ordinal10 outer attempt join changed",
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
        and inner_attempt.get("producer_free_verification_completed") is False
        and inner_attempt.get("same_target_identity_rerun_forbidden") is True,
        "ordinal10 inner attempt boundary changed",
    )

    invocation = outer_attempt.get("production_systemd_service_invocation")
    _require(type(invocation) is dict, "ordinal10 service invocation changed")
    _require(
        invocation
        == inner_attempt.get("production_systemd_service_invocation")
        == outer_failure.get("production_systemd_service_invocation")
        == inner_failure.get("production_systemd_service_invocation")
        and invocation.get("target") == "measurement"
        and invocation.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and invocation.get("token_input")
        == {
            "failed_inner_launch_failure_id": (
                EXPECTED_PREDECESSOR_INNER_FAILURE_ID
            ),
            "failed_outer_service_failure_id": (
                EXPECTED_PREDECESSOR_OUTER_FAILURE_ID
            ),
            "failed_predecessor_freeze_id": (
                EXPECTED_PREDECESSOR_FAILURE_FREEZE_ID
            ),
            "purpose": "MEASUREMENT",
            "repair_scope": "WORKING_TREE_SOURCE_MODE_CONFORMANCE_AND_TYPED_DIAGNOSTIC",
        },
        "ordinal10 predecessor repair or service token join changed",
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
        "ordinal10 outer failure join changed",
    )
    _require_gates_not_run(inner_failure, "inner failure")
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
        and inner_failure.get("producer_free_verification_completed") is False
        and inner_failure.get("success") is False,
        "ordinal10 inner failure boundary changed",
    )

    placement = inner_failure.get("production_runtime_placement_t1")
    _require(type(placement) is dict, "ordinal10 T1 placement changed")
    source_membership = placement.get("source_membership")
    _require(
        source_membership == EXPECTED_SOURCE_MEMBERSHIP
        and source_membership == placement.get("expected_source_membership")
        and placement.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and placement.get("self_pid_in_source_cgroup_procs") is True
        and placement.get("t1_complete_before_child_popen") is True
        and placement.get("nearest_common_ancestor_is_app_slice") is True
        and placement.get("planned_measurement_root_absent") is True,
        "ordinal10 service-unit ownership evidence changed",
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
        "ordinal10 cleanup evidence changed",
    )

    progress = inner_failure.get("progress_observations")
    _require(type(progress) is dict, "ordinal10 progress observations changed")
    _require(
        progress.get("attempt") == _file_fact("inner_launch_attempt")
        and all(
            progress.get(name) == {"presence": "ABSENT"}
            for name in _ABSENT_PROGRESS_NAMES
        ),
        "ordinal10 pre-campaign artifact absence changed",
    )

    stderr = inner_failure.get("child_stderr")
    _require(type(stderr) is dict, "ordinal10 child stderr changed")
    try:
        stderr_raw = bytes.fromhex(stderr.get("retained_prefix_hex", ""))
    except ValueError:
        _fail("ordinal10 child stderr encoding changed")
    _require(
        stderr.get("retained_prefix_truncated") is False
        and stderr.get("byte_count") == len(stderr_raw) == 2_175
        and stderr.get("sha256")
        == hashlib.sha256(stderr_raw).hexdigest()
        == EXPECTED_RUNTIME_STDERR_SHA256
        and stderr_raw.endswith(
            (
                EXPECTED_RUNTIME_EXCEPTION_TYPE
                + ": "
                + EXPECTED_RUNTIME_EXCEPTION_MESSAGE
                + "\n"
            ).encode("ascii")
        ),
        "ordinal10 generic runtime exception changed",
    )
    _require(
        all(
            inner_failure.get(field) is None
            and outer_failure.get(field) is None
            for field in (
                "publication_failure_artifact",
                "publication_failure_completed",
                "publication_failure_observed_state",
                "publication_failure_path_created",
                "publication_failure_stage",
            )
        ),
        "ordinal10 publication failure boundary changed",
    )

    freeze_id = _freeze_id(_freeze_payload(source_membership))
    _require(
        freeze_id == ORDINAL10_FAILURE_FREEZE_ID,
        "ordinal10 failure-freeze identity changed",
    )
    return FrozenOrdinal10FailureV180r12r4r5(
        freeze_id=freeze_id,
        logical_campaign_attempt_id=EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID,
        materialization_terminal_id=materialization_id,
        outer_service_launch_attempt_id=outer_attempt_id,
        outer_service_failure_id=outer_failure_id,
        inner_launch_attempt_id=inner_attempt_id,
        inner_launch_failure_id=inner_failure_id,
        source_membership=source_membership,
        source_conformance_diagnostic=source_diagnostic,
    )


__all__ = (
    "EXPECTED_INNER_LAUNCH_ATTEMPT_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_ORDINAL10_FAILURE_FREEZE_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID",
    "FrozenOrdinal10FailureV180r12r4r5",
    "ORDINAL10_FAILURE_FREEZE_ID",
    "Ordinal10FailureFreezeV180r12r4r5Error",
    "REPAIR_SCOPE",
    "freeze_ordinal10_failure_v180r12r4r5",
)
