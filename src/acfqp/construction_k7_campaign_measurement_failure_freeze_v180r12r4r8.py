"""Freeze ordinal13's consumed precompiled-source binding failure.

The formal parent-side campaign failure is ``INPUT_DRIFT`` with a connection
reset.  The complete child stderr supplies the earlier primary exception:
``V180r12r4 precompiled source binding changed``.  The retained manifest then
locates the exact defect: 85 application records satisfy the legacy
repository-prefix rule, while all 21 manifest-bound ``packaging``/``tomli``
records live under a sibling source root and fail it, beginning at index 85.

This module preserves the formal classification and the diagnosed cause as
different facts.  T1 unit ownership is likewise kept separate from full
source-binding and later topology conformance.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "e3cdd1c7993871eea43fabf582d0cec500819278f4cf2710031079c47010bef0"
)
EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "359747dd664a1a1cce505af1a92cb3f745dea2b2dd0c3c8657edb991f7ff35a8"
)
EXPECTED_CAMPAIGN_FAILURE_ID = (
    "ec85f3054e38e81eb82b1d206e053d50487a8eeff3ae741d35f4d3fa0befa16c"
)
EXPECTED_EVENT_IDS = (
    "be4b5d4264eaff0b01b61a0f21297c49880485d3bf265800f5d11e4d8a465262",
    "4213ddeec99ae49755f76383330f9676f068a2234f00bd81461a336f64fa7325",
    "7ea033dca666f388b1d3cecf147c1133a0a774df6f3b0c86d06d634a6e6671e9",
)
EXPECTED_PROCESS_BIRTH_RECEIPT_ID = (
    "ccafa5656706f7ce8d8c2b9d7d709a853fc6bedeacb85c80c39306c8ee3698fb"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "50695b80db7b1e7cf6f90751872983b9eacac362dce85bb30d75e2bdc99e1ab2"
)
EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "60f7713c044c3ebb59f85bc2c6700b6562441965418da279ffbc3c07c8255f8d"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "acfc5832a9d12fa76469a624356b3e4470f085349df397645a3d0a32e6258c0b"
)
EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "45663a9f36e2749b3c7c658df0f65e3fe360360926ddad941c7f3c386ee32208"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "1cd76127af59458d6075f00cc4747f9489cd84e955031e5815cbf59488665238"
)
EXPECTED_PROTOCOL_ID = (
    "4b0c690f3267059f166835de758f0fc1a522438d653c2741f260e7ff7d612a7e"
)
EXPECTED_AUTHORIZATION_ID = (
    "96f42cdadc9e1505ca2d2e6410a67aa0a0938156b4ad9c832ec32ae4a773ad80"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "d356fd00da968d1e0fa860d881f9bb21326c63ad0a7ea71cbcc753fb188006e6"
)
EXPECTED_C_PRE_COMMIT_ID = "599152353f9a8a3cacac6d7c1c64ded6be433d87"
EXPECTED_C_PRE_TREE_ID = "a7617cab9fcec2137c1bb6c66486316eb1374a3c"
EXPECTED_EMPTY_BRIDGE_COMMIT_ID = "dd44a0412fe897a75b716f2fb8553ad98a33c902"
EXPECTED_LITERAL_COMMIT_ID = "36fa39197d7854ce7a1c1b54d8360c2b6b8f0733"
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "132d496fc7dc6569bb6205102f9157d020ca6dacd3f4c44b149a0eb4f569de1f"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "63b22795125630204571da9e32063392b3fc29b866be16a08dbd865fc164f621"
)
EXPECTED_LAUNCH_RULE_ID = (
    "7bc77a021fc0ad0ae3f81f18938a52c1159451fbf25e83adb202249dbbeb71b9"
)
EXPECTED_MEASUREMENT_SERVICE_TOKEN = (
    "2067202637b5200c9d7a4a4a2bf06be37391b8cd3b494b9bb4ab0842d1e619c6"
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
EXPECTED_REPOSITORY_ROOT = (
    "/home/erzhu419/mine_code/acfqp-v180r12r4r7-ordinal13"
)
EXPECTED_THIRD_PARTY_ROOT = (
    "/home/erzhu419/mine_code/acfqp-v180r12r4-third-party-ordinal13"
)
EXPECTED_T1_PID = 701_322
EXPECTED_FORMAL_FAILURE_CODE = "INPUT_DRIFT"
EXPECTED_FORMAL_FAILURE_MESSAGE = (
    "ConnectionResetError: (104, 'Connection reset by peer')"
)
EXPECTED_DIAGNOSED_ERROR_TYPE = "RuntimeError"
EXPECTED_DIAGNOSED_MESSAGE = (
    "V180r12r4 precompiled source binding changed"
)
EXPECTED_CHILD_STDERR_BYTE_COUNT = 2_768
EXPECTED_CHILD_STDERR_SHA256 = (
    "dc129d50bd87de7fd926bc9000ffd0dfe05db2728335cab60296630437f22612"
)
EXPECTED_APPLICATION_SOURCE_RECORD_COUNT = 85
EXPECTED_THIRD_PARTY_SOURCE_RECORD_COUNT = 21
EXPECTED_TOTAL_SOURCE_RECORD_COUNT = 106
EXPECTED_FIRST_MISMATCH_INDEX = 85
REPAIR_SCOPE = (
    "NAMESPACE_AWARE_PRECOMPILED_SOURCE_BINDING_AND_PRIMARY_CAUSE_CONFORMANCE"
)

ORDINAL13_CAMPAIGN_ATTEMPT_ID = EXPECTED_CAMPAIGN_ATTEMPT_ID
ORDINAL13_INNER_LAUNCH_FAILURE_ID = EXPECTED_INNER_LAUNCH_FAILURE_ID
ORDINAL13_OUTER_SERVICE_FAILURE_ID = EXPECTED_OUTER_SERVICE_FAILURE_ID

_PREDECESSOR_FREEZE_ID = (
    "2f71e97fd2133c7983a400b5f536fe87740aa08c551580d62556aae5dcea496b"
)
_PREDECESSOR_INNER_FAILURE_ID = (
    "46a3d92a70424c296e0137380cdb98f99f11b47b565dce3175baeab8b3546a67"
)
_PREDECESSOR_OUTER_FAILURE_ID = (
    "a221f8d37ca354b7e1a753708d99229086ef6128fedd5cbf9879c89871846185"
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
_FREEZE_DOMAIN = (
    "acfqp:construction-k7-ordinal13-failure-freeze:v180r12r4r8"
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
    _REPOSITORY_ROOT / "retained_evidence/v180r12r4r8_ordinal13_failure"
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
        "af5239b8712fb972e92137e37dbf4be6f8b1511ed061d9b8f0863863e6b0ae89",
    ),
    _ArtifactFact(
        "materialization",
        "raw/prelaunch/materialization_terminal.json",
        41_398,
        "706488ccac2be9cb52dc65996d8772be56b815a6d94728266ac496c27a984eea",
    ),
    _ArtifactFact(
        "launch_manifest",
        "raw/prelaunch/launch_manifest.json",
        96_604,
        "8478a7fb8d2b2756d06406222389f1ef7b8d96296041198e009a09b96d07576e",
    ),
    _ArtifactFact(
        "outer_service_attempt",
        "raw/prelaunch/outer_service_attempt.json",
        5_288,
        "9e9edb0a957ba8a472bc8b56a54a5f6aa59e5b1c945a4ed02c8a5aabd3de29f6",
    ),
    _ArtifactFact(
        "inner_launch_attempt",
        "raw/prelaunch/inner_launch_attempt.json",
        4_086,
        "6b4e72f0c2b26f5ee4bbb1ae847de1d0f4bf37bf3f453d3af5e42a48bb84ca29",
    ),
    _ArtifactFact(
        "outer_service_failure",
        "raw/outer_service_failure.json",
        7_885,
        "950b344c8339fa7c1c6ed38ee4602d85995d0ba44d72fe41ec7578c4cd56182e",
    ),
    _ArtifactFact(
        "inner_launch_failure",
        "raw/inner_launch_failure.json",
        15_165,
        "ec995a7ac1bcbdc2489f092d2ce01b71fcbf5b118d94a3873de42b96a51017b5",
    ),
    _ArtifactFact(
        "host_conformance",
        "raw/host_conformance.json",
        5_339,
        "c27741adfd49870ad46e8a50f353ea082a4c40c6ceae4aeab40ea25e1a340f16",
    ),
    _ArtifactFact(
        "campaign_attempt",
        "raw/campaign/scientific_attempt.json",
        1_182,
        "40859b7208bb27f43411ecfe335f7784899373b37543ebe9fa09443325b049d7",
    ),
    _ArtifactFact(
        "campaign_failure",
        "raw/campaign/measurement_failure.json",
        7_349,
        "18fc6351c3e1b6ee9926482447f208641666a8890b7380395ca41fcbc7698fac",
    ),
    _ArtifactFact(
        "attempt_open_event",
        "raw/campaign/EVENTS/000000.json",
        766,
        "f2c8f4303cd72b200642f9950d05ea6db65895ef439a22cae36b560aed27c5b3",
    ),
    _ArtifactFact(
        "process_birth_intent_event",
        "raw/campaign/EVENTS/000001.json",
        774,
        "e476c242c8ee8097862cf1d85b08c6a1743b1c2e105e47548b31fb595fec71c9",
    ),
    _ArtifactFact(
        "process_birth_outcome_event",
        "raw/campaign/EVENTS/000002.json",
        835,
        "f2abef567271156ec2118fed41668008df8a042f535c55f466fba6358c9522a6",
    ),
)
_DIAGNOSTIC_ARTIFACT_FACT = _ArtifactFact(
    "precompiled_source_binding_observation",
    "raw/post_failure_precompiled_source_binding_observation.json",
    14_679,
    "6a310c2d6903eabfe49e718174e4d0d8f06dc1bbc9c67fe5354adbd9824d4db0",
    formal=False,
)
_ARTIFACT_FACTS = _FORMAL_ARTIFACT_FACTS + (_DIAGNOSTIC_ARTIFACT_FACT,)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}


class Ordinal13FailureFreezeV180r12r4r8Error(ValueError):
    """Raised when retained ordinal13 evidence no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal13FailureFreezeV180r12r4r8Error(message)


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
        f"ordinal13 {field} canonical identity changed",
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
            raise Ordinal13FailureFreezeV180r12r4r8Error(
                f"ordinal13 {fact.role} is unreadable"
            ) from error
        _require(
            len(raw) == fact.byte_count
            and hashlib.sha256(raw).hexdigest() == fact.sha256,
            f"ordinal13 {fact.role} raw bytes changed",
        )
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Ordinal13FailureFreezeV180r12r4r8Error(
                f"ordinal13 {fact.role} is not JSON"
            ) from error
        canonical = _canonical_bytes(document)
        expected_raw = canonical if fact.formal else canonical + b"\n"
        _require(
            type(document) is dict and raw == expected_raw,
            f"ordinal13 {fact.role} canonical bytes changed",
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
        f"ordinal13 {label} gate boundary changed",
    )


def _binding_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    application = manifest.get("source_modules")
    closure = manifest.get("third_party_source_closure")
    _require(
        type(application) is list
        and len(application) == EXPECTED_APPLICATION_SOURCE_RECORD_COUNT
        and all(
            type(row) is dict
            and (
                row.get("module") == "acfqp"
                or str(row.get("module", "")).startswith("acfqp.")
            )
            for row in application
        ),
        "ordinal13 85-record application source population changed",
    )
    _require(type(closure) is dict, "ordinal13 third-party closure changed")
    facts = closure.get("facts")
    _require(
        type(facts) is list
        and closure.get("file_count") == len(facts)
        == EXPECTED_THIRD_PARTY_SOURCE_RECORD_COUNT,
        "ordinal13 21-record third-party source population changed",
    )
    records: list[dict[str, Any]] = []
    for offset, fact in enumerate(facts):
        _require(type(fact) is dict, "ordinal13 third-party source fact changed")
        module = fact.get("module")
        relative = fact.get("relative_path")
        source_root = fact.get("source_root")
        is_package = fact.get("is_package")
        _require(
            type(module) is str
            and module
            and module.split(".", 1)[0] in {"packaging", "tomli"}
            and type(relative) is str
            and PurePosixPath(relative).suffix == ".py"
            and source_root == EXPECTED_THIRD_PARTY_ROOT
            and type(is_package) is bool,
            "ordinal13 third-party binding fact changed",
        )
        observed = f"{source_root}/{relative}"
        records.append(
            {
                "index": EXPECTED_APPLICATION_SOURCE_RECORD_COUNT + offset,
                "is_package": is_package,
                "legacy_repository_prefix_match": observed.startswith(
                    EXPECTED_REPOSITORY_ROOT + "/"
                ),
                "module": module,
                "observed_source_path": observed,
                "relative_path": relative,
                "source_root": source_root,
            }
        )
    _require(
        records[0]["index"] == EXPECTED_FIRST_MISMATCH_INDEX
        and records[0]["module"] == "packaging"
        and [row["module"] for row in records]
        == sorted(row["module"] for row in records)
        and all(row["legacy_repository_prefix_match"] is False for row in records),
        "ordinal13 first or complete binding mismatch population changed",
    )
    return records


def _expected_binding_observation(
    manifest: dict[str, Any], placement_t1: dict[str, Any]
) -> dict[str, Any]:
    records = _binding_rows(manifest)
    mismatches = [
        {
            "expected": EXPECTED_REPOSITORY_ROOT + "/",
            "field": (
                f"source_records[{row['index']}].source_path.repository_prefix"
            ),
            "module": row["module"],
            "observed": row["observed_source_path"],
        }
        for row in records
    ]
    return {
        "campaign_attempt_id": EXPECTED_CAMPAIGN_ATTEMPT_ID,
        "campaign_event_or_counter_record_issued": False,
        "campaign_failure_state_id": EXPECTED_CAMPAIGN_FAILURE_ID,
        "cause": {
            "child_stderr_byte_count": EXPECTED_CHILD_STDERR_BYTE_COUNT,
            "child_stderr_sha256": EXPECTED_CHILD_STDERR_SHA256,
            "child_stderr_truncated": False,
            "diagnosis_basis": (
                "EXACT_UNTRUNCATED_CHILD_STDERR_PLUS_MANIFEST_SOURCE_FACTS"
            ),
            "error_type": EXPECTED_DIAGNOSED_ERROR_TYPE,
            "failure_code": (
                "PRECOMPILED_SOURCE_BINDING_CONFORMANCE_FAILURE"
            ),
            "message": EXPECTED_DIAGNOSED_MESSAGE,
            "scope": "PRECOMPILED_SOURCE_RECORD_REPOSITORY_PREFIX",
        },
        "formal_cgroup_topology_conformance_diagnostic": None,
        "formal_failure_classification": {
            "failure_code": EXPECTED_FORMAL_FAILURE_CODE,
            "message": EXPECTED_FORMAL_FAILURE_MESSAGE,
            "secondary_to_child_bootstrap_failure": True,
        },
        "full_cgroup_topology_conformance_recorded": False,
        "mismatch_count": len(mismatches),
        "mismatch_rows": mismatches,
        "observation_kind": "POST_FAILURE_READ_ONLY_TYPED_DIAGNOSTIC",
        "production_unit_ownership_t1_acquired": True,
        "property_snapshots": {
            "record_population": {
                "acfqp_record_count": len(manifest["source_modules"]),
                "first_mismatch_index": EXPECTED_FIRST_MISMATCH_INDEX,
                "first_mismatch_module": records[0]["module"],
                "packaging_record_count": sum(
                    row["module"].split(".", 1)[0] == "packaging"
                    for row in records
                ),
                "third_party_record_count": len(records),
                "tomli_record_count": sum(
                    row["module"].split(".", 1)[0] == "tomli"
                    for row in records
                ),
                "total_source_record_count": (
                    len(manifest["source_modules"]) + len(records)
                ),
            },
            "repository_binding_rule": {
                "expected_repository_prefix": EXPECTED_REPOSITORY_ROOT + "/",
                "expected_repository_root": EXPECTED_REPOSITORY_ROOT,
                "legacy_predicate": (
                    "source_path.startswith(repository_root + os.sep)"
                ),
                "observed_third_party_source_roots": [
                    EXPECTED_THIRD_PARTY_ROOT
                ],
            },
            "third_party_source_records": records,
            "unit_ownership_t1": {
                "expected_source_membership": EXPECTED_SOURCE_MEMBERSHIP,
                "observed_source_membership": EXPECTED_SOURCE_MEMBERSHIP,
                "t1_pid": EXPECTED_T1_PID,
                "unit_name": EXPECTED_UNIT_NAME,
            },
        },
        "schema": (
            "acfqp.v180r12r4r8_post_failure_precompiled_source_binding_"
            "observation.v1"
        ),
        "source_binding_full_conformance": False,
        "source_binding_unit_ownership_evaluated": False,
    }


def _freeze_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.v180r12r4r8_ordinal13_failure_freeze.v1",
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
        "post_failure_precompiled_source_binding_observation_sha256": (
            _DIAGNOSTIC_ARTIFACT_FACT.sha256
        ),
        "formal_failure_classification": {
            "failure_code": EXPECTED_FORMAL_FAILURE_CODE,
            "message": EXPECTED_FORMAL_FAILURE_MESSAGE,
        },
        "diagnosed_exact_cause": {
            "error_type": EXPECTED_DIAGNOSED_ERROR_TYPE,
            "message": EXPECTED_DIAGNOSED_MESSAGE,
        },
        "repair_scope": REPAIR_SCOPE,
    }


def _freeze_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _FREEZE_DOMAIN.encode("ascii") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


EXPECTED_ORDINAL13_FAILURE_FREEZE_ID = (
    "0df765617aa1615b48ee5fd9192e3c596d6d50d1dfb1bc841e52d545e1716e25"
)
ORDINAL13_FAILURE_FREEZE_ID = _freeze_id(_freeze_payload())
if ORDINAL13_FAILURE_FREEZE_ID != EXPECTED_ORDINAL13_FAILURE_FREEZE_ID:
    raise RuntimeError("V180r12r4r8 ordinal13 failure-freeze identity changed")


@dataclass(frozen=True, slots=True)
class FrozenOrdinal13FailureV180r12r4r8:
    freeze_id: str
    campaign_attempt_id: str
    campaign_attempt_record_id: str
    campaign_failure_id: str
    event_ids: tuple[str, str, str]
    materialization_terminal_id: str
    outer_service_launch_attempt_id: str
    outer_service_failure_id: str
    inner_launch_attempt_id: str
    inner_launch_failure_id: str
    host_conformance: dict[str, Any]
    t1_placement: dict[str, Any]
    binding_observation: dict[str, Any]

    def to_contract(self) -> dict[str, Any]:
        """Return the claim-bounded ordinal13 failure contract."""

        return {
            "schema": "acfqp.v180r12r4r8_ordinal13_failure_freeze.v1",
            "freeze_id": self.freeze_id,
            "campaign_attempt_id": self.campaign_attempt_id,
            "campaign_attempt_record_id": self.campaign_attempt_record_id,
            "campaign_failure_id": self.campaign_failure_id,
            "event_ids": list(self.event_ids),
            "materialization_terminal_id": self.materialization_terminal_id,
            "outer_service_launch_attempt_id": self.outer_service_launch_attempt_id,
            "outer_service_failure_id": self.outer_service_failure_id,
            "inner_launch_attempt_id": self.inner_launch_attempt_id,
            "inner_launch_failure_id": self.inner_launch_failure_id,
            "formal_artifact_count": 13,
            "post_failure_diagnostic_artifact_count": 1,
            "post_failure_diagnostic_is_formal_campaign_artifact": False,
            "all_self_ids_verified": True,
            "self_id_count": 10,
            "prelaunch_materialization_succeeded": True,
            "source_root_count": 27,
            "full_source_conformance": True,
            "source_conformance_mismatch_count": 0,
            "source_conformance_cause": None,
            "full_host_conformance": True,
            "host_conformance_mismatch_count": 0,
            "host_conformance_cause": None,
            "host_conformance": self.host_conformance,
            "socket_buffer_capability_host_conformant": True,
            "scientific_attempt_opened": True,
            "event_kinds": [
                "ATTEMPT_OPEN",
                "PROCESS_BIRTH_INTENT",
                "PROCESS_BIRTH_OUTCOME",
            ],
            "completed_event_count": 3,
            "successful_process_birth_outcome_recorded": True,
            "formal_failure_classification": {
                "failure_code": EXPECTED_FORMAL_FAILURE_CODE,
                "message": EXPECTED_FORMAL_FAILURE_MESSAGE,
            },
            "formal_failure_is_secondary": True,
            "diagnosed_exact_cause": {
                "error_type": EXPECTED_DIAGNOSED_ERROR_TYPE,
                "message": EXPECTED_DIAGNOSED_MESSAGE,
            },
            "diagnosed_exact_cause_is_primary": True,
            "formal_campaign_failure_launch_child_created": False,
            "formal_campaign_failure_launch_exec_observed": False,
            "formal_campaign_failure_launch_pidfd_acquired": False,
            "production_runtime_placement_t1": self.t1_placement,
            "production_runtime_placement_t1_complete": True,
            "production_unit_ownership_t1_acquired": True,
            "formal_cgroup_topology_conformance_diagnostic": None,
            "full_cgroup_topology_conformance_recorded": False,
            "t2_t3_full_conformance_claimed": False,
            "binding_observation": self.binding_observation,
            "application_source_record_count": (
                EXPECTED_APPLICATION_SOURCE_RECORD_COUNT
            ),
            "third_party_source_record_count": (
                EXPECTED_THIRD_PARTY_SOURCE_RECORD_COUNT
            ),
            "total_source_record_count": EXPECTED_TOTAL_SOURCE_RECORD_COUNT,
            "source_binding_full_conformance": False,
            "source_binding_mismatch_count": 21,
            "source_binding_mismatch_rows": self.binding_observation[
                "mismatch_rows"
            ],
            "source_binding_cause": self.binding_observation["cause"],
            "first_source_binding_mismatch_index": (
                EXPECTED_FIRST_MISMATCH_INDEX
            ),
            "first_source_binding_mismatch_module": "packaging",
            "cleanup_complete": True,
            "post_failure_measurement_root_state": "ABSENT",
            "formal_service_collected": True,
            "process_may_remain": False,
            "oom_event_count": 0,
            "memory_peak_bytes": 68_714_496,
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


def freeze_ordinal13_failure_v180r12r4r8(
    retained_root: Path | None = None,
) -> FrozenOrdinal13FailureV180r12r4r8:
    """Validate and freeze the exact consumed ordinal13 failure."""

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
        documents["process_birth_outcome_event"],
    )
    binding_observation = documents["precompiled_source_binding_observation"]

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

    frozen = external.get("frozen_authorization_context")
    _require(type(frozen) is dict, "ordinal13 frozen context changed")
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
        and frozen.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and frozen.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and frozen.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and frozen.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and manifest.get("frozen_authorization_context") == frozen
        and manifest.get("repository_root") == EXPECTED_REPOSITORY_ROOT,
        "ordinal13 authorization or manifest context changed",
    )

    topology = materialization.get("git_topology")
    _require(
        type(topology) is dict
        and topology.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and topology.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and topology.get("empty_bridge_commit_id")
        == EXPECTED_EMPTY_BRIDGE_COMMIT_ID
        and topology.get("literal_commit_id") == EXPECTED_LITERAL_COMMIT_ID,
        "ordinal13 final source topology changed",
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
        and materialization.get("external_root", {}).get("sha256")
        == _FACT_BY_ROLE["external_root"].sha256
        and materialization.get("launch_manifest", {}).get("sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256,
        "ordinal13 materialization boundary changed",
    )
    source = materialization.get("working_tree_source_conformance")
    _require(
        type(source) is dict
        and manifest.get("working_tree_source_conformance") == source,
        "ordinal13 source-conformance join changed",
    )
    snapshots = source.get("snapshots")
    _require(
        source.get("source_root_count") == 27
        and source.get("mismatch_count") == 0
        and source.get("per_field_mismatches") == []
        and source.get("full_source_conformance") is True
        and source.get("unit_ownership_evaluated") is False
        and source.get("cause") is None
        and type(snapshots) is list
        and len(snapshots) == 27
        and all(
            type(row) is dict
            and row.get("conformant") is True
            and row.get("mismatch_fields") == []
            and row.get("observed_before") == row.get("observed_after")
            for row in snapshots
        ),
        "ordinal13 27-root full source conformance changed",
    )

    expected = host.get("expected")
    observed = host.get("observed")
    _require(
        type(expected) is dict
        and type(observed) is dict
        and set(expected) == set(observed)
        == {
            "cgroup_parent_fact",
            "runtime_capability_fact",
            "socket_buffer_capability",
        },
        "ordinal13 host property snapshots changed",
    )
    parent_fields = host.get("cgroup_parent_compared_fields")
    runtime_fields = host.get("runtime_capability_compared_fields")
    socket_exact = host.get("socket_buffer_capability_exact_fields")
    socket_min = host.get("socket_buffer_capability_at_least_fields")
    expected_parent = expected["cgroup_parent_fact"]
    observed_parent = observed["cgroup_parent_fact"]
    expected_runtime = expected["runtime_capability_fact"]
    observed_runtime = observed["runtime_capability_fact"]
    expected_socket = expected["socket_buffer_capability"]
    observed_socket = observed["socket_buffer_capability"]
    _require(
        host.get("schema")
        == "acfqp.v180r12r4_pre_attempt_host_conformance.v2"
        and host.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and host.get("cgroup_parent_excluded_fields") == ["self_membership"]
        and type(parent_fields) is list
        and set(parent_fields) == set(expected_parent) - {"self_membership"}
        and all(expected_parent[name] == observed_parent[name] for name in parent_fields)
        and observed_parent.get("self_membership") == EXPECTED_SOURCE_MEMBERSHIP
        and type(runtime_fields) is list
        and set(runtime_fields) == set(expected_runtime) == set(observed_runtime)
        and all(expected_runtime[name] == observed_runtime[name] for name in runtime_fields)
        and type(socket_exact) is list
        and all(expected_socket[name] == observed_socket[name] for name in socket_exact)
        and type(socket_min) is list
        and all(observed_socket[name] >= expected_socket[name] for name in socket_min)
        and host.get("mismatch_rows") == []
        and host.get("mismatch_count") == 0
        and host.get("cause") is None
        and host.get("full_host_conformance") is True,
        "ordinal13 full host and socket conformance changed",
    )

    invocation = inner_attempt.get("production_systemd_service_invocation")
    _require(
        type(invocation) is dict
        and invocation
        == outer_attempt.get("production_systemd_service_invocation")
        == outer_failure.get("production_systemd_service_invocation")
        == inner_failure.get("production_systemd_service_invocation")
        and invocation.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and invocation.get("unit_name") == EXPECTED_UNIT_NAME
        and invocation.get("delegate") is True
        and invocation.get("token_input")
        == {
            "failed_inner_launch_failure_id": _PREDECESSOR_INNER_FAILURE_ID,
            "failed_outer_service_failure_id": _PREDECESSOR_OUTER_FAILURE_ID,
            "failed_predecessor_freeze_id": _PREDECESSOR_FREEZE_ID,
            "purpose": "MEASUREMENT",
            "repair_scope": (
                "SOCKET_BUFFER_CAPABILITY_AND_T3_DIAGNOSTIC_CONFORMANCE"
            ),
        },
        "ordinal13 service identity or predecessor join changed",
    )
    _require(
        outer_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_sha256")
        == _FACT_BY_ROLE["materialization"].sha256
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("materialization_terminal_id") == materialization_id
        and inner_attempt.get("materialization_terminal_sha256")
        == _FACT_BY_ROLE["materialization"].sha256
        and inner_attempt.get("launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and inner_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID,
        "ordinal13 launch attempt joins changed",
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
        and outer_failure.get("systemd_run_return_code") == 1
        and outer_failure.get("systemd_run_timed_out") is False
        and outer_failure.get("success") is False,
        "ordinal13 outer failure join changed",
    )
    unit_absence = outer_failure.get("collected_unit_absence_observation")
    _require(
        type(unit_absence) is dict
        and unit_absence.get("unit_absent_after_wait_collect") is True
        and unit_absence.get("expected_load_state") == "not-found"
        and unit_absence.get("return_code") == 0
        and unit_absence.get("timed_out") is False,
        "ordinal13 collected unit absence changed",
    )

    _require_gates_not_run(inner_failure, "inner failure")
    _require(
        inner_failure.get("launch_attempt_id") == inner_attempt_id
        and inner_failure.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
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
        "ordinal13 inner failure boundary changed",
    )
    placement_t1 = inner_failure.get("production_runtime_placement_t1")
    _require(
        type(placement_t1) is dict
        and placement_t1.get("source_membership") == EXPECTED_SOURCE_MEMBERSHIP
        and placement_t1.get("expected_source_membership")
        == EXPECTED_SOURCE_MEMBERSHIP
        and placement_t1.get("unit_name") == EXPECTED_UNIT_NAME
        and placement_t1.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and placement_t1.get("self_pid") == EXPECTED_T1_PID
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and placement_t1.get("t1_complete_before_child_popen") is True
        and placement_t1.get("planned_measurement_root_absent") is True,
        "ordinal13 T1 unit ownership changed",
    )
    stderr = inner_failure.get("child_stderr")
    _require(type(stderr) is dict, "ordinal13 child stderr changed")
    try:
        stderr_raw = bytes.fromhex(stderr.get("retained_prefix_hex", ""))
    except ValueError:
        _fail("ordinal13 child stderr encoding changed")
    exact_primary = (EXPECTED_DIAGNOSED_ERROR_TYPE + ": " + EXPECTED_DIAGNOSED_MESSAGE)
    _require(
        stderr.get("retained_prefix_truncated") is False
        and stderr.get("byte_count") == len(stderr_raw)
        == EXPECTED_CHILD_STDERR_BYTE_COUNT
        and stderr.get("sha256")
        == hashlib.sha256(stderr_raw).hexdigest()
        == EXPECTED_CHILD_STDERR_SHA256
        and stderr_raw.count((exact_primary + "\n").encode("utf-8")) == 1
        and stderr_raw.endswith(
            ("ConnectionResetError: [Errno 104] Connection reset by peer\n").encode(
                "utf-8"
            )
        ),
        "ordinal13 exact primary child traceback changed",
    )

    _require(
        campaign_attempt.get("attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
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
        and campaign_attempt.get("one_shot_attempt_opened") is True,
        "ordinal13 campaign ATTEMPT join changed",
    )
    common = (
        EXPECTED_PROTOCOL_ID,
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_CAMPAIGN_ATTEMPT_ID,
    )
    _require(
        all(
            (event.get("protocol_id"), event.get("authorization_id"), event.get("attempt_id"))
            == common
            for event in events
        )
        and [event.get("sequence") for event in events] == [0, 1, 2]
        and [event.get("previous_event_id") for event in events]
        == [None, event_ids[0], event_ids[1]]
        and [event.get("event_kind") for event in events]
        == ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT", "PROCESS_BIRTH_OUTCOME"]
        and events[0].get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": attempt_record_id,
            "measured_value": None,
            "outcome_code": "OPEN",
        }
        and events[1].get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": None,
            "measured_value": None,
            "outcome_code": "INTENT",
        }
        and events[2].get("payload")
        == {
            "auxiliary_values": [],
            "evidence_id": EXPECTED_PROCESS_BIRTH_RECEIPT_ID,
            "measured_value": 1,
            "outcome_code": "SUCCESS",
        },
        "ordinal13 exact three-event prefix changed",
    )
    _require(
        (
            campaign_failure.get("protocol_id"),
            campaign_failure.get("authorization_id"),
            campaign_failure.get("attempt_id"),
        )
        == common
        and campaign_failure.get("failure_code")
        == EXPECTED_FORMAL_FAILURE_CODE
        and campaign_failure.get("message") == EXPECTED_FORMAL_FAILURE_MESSAGE
        and campaign_failure.get("message_sha256")
        == hashlib.sha256(EXPECTED_FORMAL_FAILURE_MESSAGE.encode()).hexdigest()
        and campaign_failure.get("last_event_id") == event_ids[2]
        and campaign_failure.get("completed_event_count") == 3
        and campaign_failure.get("launch_child_created") is False
        and campaign_failure.get("launch_exec_observed") is False
        and campaign_failure.get("launch_pidfd_acquired") is False
        and campaign_failure.get("cgroup_topology_conformance_diagnostic") is None
        and campaign_failure.get("counter_records_issued") is False
        and campaign_failure.get("successful_ledger_claimed") is False
        and campaign_failure.get("process_may_remain") is False
        and campaign_failure.get("same_identity_rerun_forbidden") is True,
        "ordinal13 formal secondary failure classification changed",
    )

    observations = campaign_failure.get("partial_artifact_observations")
    _require(type(observations) is list, "ordinal13 artifact inventory changed")
    by_path = {
        row.get("relative_path"): row for row in observations if type(row) is dict
    }
    output = ".tmp/exact-freeze/v180r12r4_campaign_measurement"
    events_path = f"{output}/EVENTS"
    _require(
        len(by_path) == len(observations) == 18
        and by_path[events_path].get("directory_entries")
        == ["000000.json", "000001.json", "000002.json"]
        and all(
            by_path[f"{events_path}/{index:06}.json"].get("sha256")
            == _FACT_BY_ROLE[role].sha256
            for index, role in enumerate(
                (
                    "attempt_open_event",
                    "process_birth_intent_event",
                    "process_birth_outcome_event",
                )
            )
        ),
        "ordinal13 three-event artifact inventory changed",
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
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_failure.json",
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_replay.json",
    ):
        _require(
            by_path[relative_path].get("state") == "ABSENT",
            "ordinal13 terminal, vector, or replay absence changed",
        )

    progress = inner_failure.get("progress_observations")
    _require(
        type(progress) is dict
        and progress.get("attempt") == _file_fact("inner_launch_attempt")
        and progress.get("host_conformance") == _file_fact("host_conformance")
        and progress.get("measurement_failure") == _file_fact("campaign_failure")
        and progress.get("output_root")
        == {"mode": 0o700, "presence": "DIRECTORY"}
        and all(
            progress.get(name) == {"presence": "ABSENT"}
            for name in _ABSENT_PROGRESS_NAMES
        ),
        "ordinal13 retained progress changed",
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
            row.get("residual_tree_or_process_possible") is False for row in cleanup
        ),
        "ordinal13 cleanup changed",
    )
    cgroup = campaign_failure.get("cgroup_failure_observation")
    memory_events = cgroup.get("memory_events") if type(cgroup) is dict else None
    _require(
        type(cgroup) is dict
        and cgroup.get("kill_outcome") == "SUCCESS"
        and cgroup.get("close_outcome") == "SUCCESS"
        and cgroup.get("reap_outcome") == "SUCCESS"
        and cgroup.get("root_process_count") == 0
        and cgroup.get("supervisor_leaf_process_count") == 0
        and cgroup.get("worker_leaf_process_count") == 0
        and cgroup.get("memory_peak_bytes") == 68_714_496
        and type(memory_events) is list
        and all(row.get("value") == 0 for row in memory_events),
        "ordinal13 cleanup, memory, or OOM facts changed",
    )

    expected_observation = _expected_binding_observation(manifest, placement_t1)
    _require(
        binding_observation == expected_observation
        and binding_observation.get("mismatch_count") == 21
        and len(binding_observation.get("mismatch_rows", [])) == 21
        and binding_observation.get("production_unit_ownership_t1_acquired")
        is True
        and binding_observation.get("source_binding_full_conformance") is False
        and binding_observation.get("full_cgroup_topology_conformance_recorded")
        is False,
        "ordinal13 typed source-binding observation changed",
    )

    freeze_id = _freeze_id(_freeze_payload())
    _require(
        freeze_id == EXPECTED_ORDINAL13_FAILURE_FREEZE_ID,
        "ordinal13 failure-freeze identity changed",
    )
    return FrozenOrdinal13FailureV180r12r4r8(
        freeze_id=freeze_id,
        campaign_attempt_id=EXPECTED_CAMPAIGN_ATTEMPT_ID,
        campaign_attempt_record_id=attempt_record_id,
        campaign_failure_id=campaign_failure_id,
        event_ids=(event_ids[0], event_ids[1], event_ids[2]),
        materialization_terminal_id=materialization_id,
        outer_service_launch_attempt_id=outer_attempt_id,
        outer_service_failure_id=outer_failure_id,
        inner_launch_attempt_id=inner_attempt_id,
        inner_launch_failure_id=inner_failure_id,
        host_conformance=host,
        t1_placement=placement_t1,
        binding_observation=binding_observation,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID",
    "EXPECTED_CAMPAIGN_FAILURE_ID",
    "EXPECTED_EVENT_IDS",
    "EXPECTED_INNER_LAUNCH_ATTEMPT_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_ORDINAL13_FAILURE_FREEZE_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID",
    "FrozenOrdinal13FailureV180r12r4r8",
    "ORDINAL13_CAMPAIGN_ATTEMPT_ID",
    "ORDINAL13_FAILURE_FREEZE_ID",
    "ORDINAL13_INNER_LAUNCH_FAILURE_ID",
    "ORDINAL13_OUTER_SERVICE_FAILURE_ID",
    "Ordinal13FailureFreezeV180r12r4r8Error",
    "REPAIR_SCOPE",
    "freeze_ordinal13_failure_v180r12r4r8",
)
