"""Freeze Ordinal14's post-publication verification transport failure.

Ordinal14 completed its measured campaign and wrote byte-identical producer-free
verification and replay payloads.  The enclosing verification bootstrap then
failed its target-agnostic six-process Git postcondition.  This freeze keeps
those facts separate: measurement and payload conformance are true, while the
inner and outer verification transports have no success receipt.

The private ``_GitProcessAudit._observed_count`` was never serialized.  The
formal mismatch is therefore only ``complete: true -> false``.  A zero-process
schedule appears solely in the explicitly non-runtime static-control-flow
inference retained after the failure.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import stat
from typing import Any


EXPECTED_CAMPAIGN_ATTEMPT_ID = (
    "73a9a50c86c400c96dd12c43f7d979d21b2b7b68b0613588861391a366121082"
)
EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "a909b79b785092d148ecab59cf500e50be1fe0ae3ec289478dffa8c8e6d088be"
)
EXPECTED_MEASUREMENT_TERMINAL_ID = (
    "8d7ad44b5a6c8808ab14d77e062006bfed920bf739f27847b47f4f2c14ec8803"
)
EXPECTED_LEDGER_CLOSURE_ID = (
    "9153285279cdd5ec326a48d955c19ae4e680b4b624249de47afebf126380d30a"
)
EXPECTED_EXECUTION_CLOSURE_ID = (
    "84cf0948ec4f4ebabce6e3c55e8aaf30985ad18c49eaa52c49f6d686565815ec"
)
EXPECTED_OS_RECEIPT_BUNDLE_ID = (
    "7b56c4b8a40818332a54477fd81c2567930d9870aef58f5074f88b8dc6905c1b"
)
EXPECTED_EVIDENCE_INVENTORY_BUNDLE_ID = (
    "dc76d17466d163a1889f1c69575182f0c005a17eaa84db32dce2f58ff302931e"
)
EXPECTED_SUBJECT_RESULT_ID = (
    "52f6498bdef63a656edbdc41a8f770ded76d4c40b0a5bb8ac03a358e516ee2f4"
)
EXPECTED_VERIFICATION_ID = (
    "7a3eae241a27283bb82e5f3eb2c0c107041008f98b5dd59b40b093c3c95d0655"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "72f3e6f7f4c7166a326f0656270c5692e7469bcfa21127a14926379b0ab2a271"
)
EXPECTED_MEASUREMENT_INNER_LAUNCH_ATTEMPT_ID = (
    "90015cfca6c4a34f51bbc43add370805abf15c4f5ec2f869c9ce07b90993b49b"
)
EXPECTED_MEASUREMENT_INNER_LAUNCH_RECEIPT_ID = (
    "0a1d6fd6de7aeef1959eef87f19e48baf806f770d135f97ed396a82391bb36c8"
)
EXPECTED_MEASUREMENT_OUTER_SERVICE_ATTEMPT_ID = (
    "9634aa48460413ca1941b203a18cd765daa4c1c84a76674c62ea0b2d3dc1544f"
)
EXPECTED_MEASUREMENT_OUTER_SERVICE_RECEIPT_ID = (
    "5d0d89f9cc7e693c8d72692c8916427b5221d73b44f21cebf72103248385ae76"
)
EXPECTED_INNER_LAUNCH_ATTEMPT_ID = (
    "93ba61a22d536342c975c3a9b8430971dd23550b941139790aa842df04e15199"
)
EXPECTED_INNER_LAUNCH_FAILURE_ID = (
    "7a1b8496f89378f5b2131a096c17fb9f7ed43ac64b544eacdfb3ea2802a65e82"
)
EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID = (
    "3543aa4ec5582f9beb01fc3d23f87582378f491a9b63470a2a00d38d83ac4441"
)
EXPECTED_OUTER_SERVICE_FAILURE_ID = (
    "aa3ee86dee489383a43a868180bd555a21978fc923c106e06e5b017adb4101bc"
)
EXPECTED_PROTOCOL_ID = (
    "9fc6ecbe63cdb65752d5bac6690903ab34ffc540abb3062b5ffde7a3695ebd49"
)
EXPECTED_AUTHORIZATION_ID = (
    "64fe137f1a6a015e7738de04a909c95367cb198f6d8c909025b8dc4432eb1fb0"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "d22afdc62bac0a6a36f740d3e6bad45425bd8fa0f114bc48d02deacf4218156d"
)
EXPECTED_C_PRE_COMMIT_ID = "fab4e7c0efdd18a577e5588834ba2fb5722ade16"
EXPECTED_C_PRE_TREE_ID = "5d8037e0a65d8771f2b1d60dafb5eb9df3598111"
EXPECTED_EMPTY_BRIDGE_COMMIT_ID = "27f9231255dc4290f57676bcadfd9a6102cc5e17"
EXPECTED_LITERAL_COMMIT_ID = "b834d176c68b8b7629b721acde250491cf4fde71"
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "5ec6496223fdd24664d142d581847f3e95456a3b0bb171df2950302e413ac60b"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "ee833b2260347a85442802459cd3ae6edd62b3abd35ba8d15b1829f7e9fa04f8"
)
EXPECTED_LAUNCH_RULE_ID = (
    "9bedb474878ba9f3c7eb9735278b03fd91299c978f959ae30433a22b41b23817"
)
EXPECTED_REPOSITORY_ROOT = (
    "/home/erzhu419/mine_code/"
    "acfqp-v180r12r4r8-ordinal14-production-b834d176-u022"
)
EXPECTED_THIRD_PARTY_ROOT = (
    "/home/erzhu419/mine_code/"
    "acfqp-v180r12r4-third-party-ordinal14-b834d176-u022"
)
EXPECTED_MEASUREMENT_SERVICE_TOKEN = (
    "1ba5304a7d653a3805fdca4754eeb7ff2feaa63794c6b866f47adda85160668d"
)
EXPECTED_VERIFICATION_SERVICE_TOKEN = (
    "14e3fead4dab312dd06026196922d455600e970d5de64624e3d47b66525c0221"
)
EXPECTED_MEASUREMENT_UNIT_NAME = (
    "acfqp-v180r12r4-measurement-"
    + EXPECTED_MEASUREMENT_SERVICE_TOKEN
    + ".service"
)
EXPECTED_VERIFICATION_UNIT_NAME = (
    "acfqp-v180r12r4-verification-"
    + EXPECTED_VERIFICATION_SERVICE_TOKEN
    + ".service"
)
EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    + EXPECTED_MEASUREMENT_UNIT_NAME
)
EXPECTED_VERIFICATION_SOURCE_MEMBERSHIP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    + EXPECTED_VERIFICATION_UNIT_NAME
)
EXPECTED_CHILD_STDERR_BYTE_COUNT = 1_082
EXPECTED_CHILD_STDERR_SHA256 = (
    "93b2610ba20088050a266432089e8eb95d2257ee84a318315a56a1364523542b"
)
EXPECTED_DIAGNOSED_MESSAGE = (
    "V180r12r4 runner secondary observations: RuntimeError: "
    "V180r12r4 six-process Git contract was incomplete"
)
EXPECTED_FORMAL_MISMATCH_ROWS = (
    {
        "expected": True,
        "field": "source_bound_runner_git_audit.complete",
        "observed": False,
    },
)
EXPECTED_GIT_SUBCOMMANDS = (
    "rev-parse",
    "log",
    "diff-tree",
    "log",
    "archive",
    "cat-file",
)
REPAIR_SCOPE = "TARGET_AWARE_RUNNER_GIT_PROCESS_CONFORMANCE"

ORDINAL14_CAMPAIGN_ATTEMPT_ID = EXPECTED_CAMPAIGN_ATTEMPT_ID
ORDINAL14_MEASUREMENT_TERMINAL_ID = EXPECTED_MEASUREMENT_TERMINAL_ID
ORDINAL14_VERIFICATION_ID = EXPECTED_VERIFICATION_ID
ORDINAL14_INNER_LAUNCH_FAILURE_ID = EXPECTED_INNER_LAUNCH_FAILURE_ID
ORDINAL14_OUTER_SERVICE_FAILURE_ID = EXPECTED_OUTER_SERVICE_FAILURE_ID

_ATTEMPT_RECORD_DOMAIN = (
    "acfqp:construction-k7-campaign-attempt-record:v180r12r4e"
)
_SERVICE_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
_SERVICE_RECEIPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-receipt:v180r12r4"
)
_SERVICE_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
_TERMINAL_DOMAIN = (
    "acfqp:construction-k7-campaign-measurement-terminal-bundle:v180r12r4"
)
_VERIFICATION_DOMAIN = (
    "acfqp:construction-k7-campaign-measurement-verification:v180r12r4"
)
_LEDGER_CLOSURE_DOMAIN = (
    "acfqp:construction-k7-campaign-ledger-closure:v180r12r4e"
)
_EXECUTION_CLOSURE_DOMAIN = (
    "acfqp:construction-k7-campaign-execution-closure:v180r12r4e"
)
_OS_RECEIPT_BUNDLE_DOMAIN = (
    "acfqp:construction-k7-campaign-os-receipt-bundle:v180r12r4"
)
_EVIDENCE_INVENTORY_BUNDLE_DOMAIN = (
    "acfqp:construction-k7-campaign-evidence-inventory-bundle:v180r12r4"
)
_SUBJECT_RESULT_DOMAIN = (
    "acfqp:construction-k7-campaign-subject-result:v180r12r4e"
)
_FREEZE_DOMAIN = (
    "acfqp:construction-k7-ordinal14-verification-failure-freeze:"
    "v180r12r4r9"
)
_GATE_NAMES = (
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
    "OFFICIAL_EXECUTION_GATE",
)
_LATER_GATE_NAMES = _GATE_NAMES[1:]

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RETAINED_ROOT = (
    _REPOSITORY_ROOT
    / "retained_evidence/v180r12r4r9_ordinal14_verification_failure"
)


@dataclass(frozen=True, slots=True)
class _ArtifactFact:
    role: str
    relative_path: str
    byte_count: int
    mode: int
    sha256: str
    formal: bool = True
    pretty: bool = False


_FORMAL_ARTIFACT_FACTS = (
    _ArtifactFact(
        "external_root",
        "v180r12r4_campaign_measurement_prelaunch_external_root.json",
        4_494,
        0o400,
        "21c5a228ef5c543bb914361df95a7fbc8c0e1d338b5ecf3e3373ec6dbae32795",
    ),
    _ArtifactFact(
        "materialization",
        "v180r12r4_campaign_measurement_prelaunch/MATERIALIZATION_TERMINAL.json",
        42_709,
        0o400,
        "5e7e59f17919b0b4135360f9541adb50565ca570ebdce4c8b4d81a5cb790bbf2",
    ),
    _ArtifactFact(
        "launch_manifest",
        "v180r12r4_campaign_measurement_prelaunch/launch_manifest.json",
        99_259,
        0o400,
        "8bd4f4ffd4aff8d7ba4fa0d7980d2c9048f57414219eff8c371d4cc40d1daabe",
    ),
    _ArtifactFact(
        "campaign_attempt",
        "v180r12r4_campaign_measurement_attempt.json",
        1_182,
        0o400,
        "417f51b2149f0530e02e6cef1eebd88f098c8971fcbab79687d64ace7855b9ae",
    ),
    _ArtifactFact(
        "host_conformance",
        "v180r12r4_campaign_measurement_pre_attempt_host_conformance.json",
        5_339,
        0o400,
        "aa88482e939bed0a036d2289f1272eaa2dc8eae1c5d8f6149e22c8a89d87cc4f",
    ),
    _ArtifactFact(
        "measurement_inner_attempt",
        "v180r12r4_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_ATTEMPT.json",
        4_354,
        0o400,
        "5c93d8c2f1ad12ba640749332ba3ff9a4ca87f6175bdabe78df9cad1ba65ab3e",
    ),
    _ArtifactFact(
        "measurement_inner_receipt",
        "v180r12r4_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_RECEIPT.json",
        9_943,
        0o400,
        "8bc76f9d182bf969213842498ccf46a281173747b4a689915144b00c557d9dcf",
    ),
    _ArtifactFact(
        "measurement_outer_attempt",
        "v180r12r4_campaign_measurement_prelaunch/MEASUREMENT_SERVICE_LAUNCH_ATTEMPT.json",
        5_506,
        0o400,
        "19e7593e2652d16ae00a1e7da2864625c1eb932bcfc9c30169f9f8ba775267eb",
    ),
    _ArtifactFact(
        "measurement_outer_receipt",
        "v180r12r4_campaign_measurement_prelaunch/MEASUREMENT_SERVICE_LAUNCH_RECEIPT.json",
        4_896,
        0o400,
        "a5dc07e3362b1bb2326d24f7db6be3d2452124d0839436c95943fb7329de18ce",
    ),
    _ArtifactFact(
        "terminal",
        "v180r12r4_campaign_measurement/TERMINAL.json",
        1_507_132,
        0o400,
        "92e214acc535e55811c071fb04876e983741c2791cf302012bbb3e102c9a912a",
    ),
    _ArtifactFact(
        "ledger_closure",
        "v180r12r4_campaign_measurement/LEDGER_CLOSURE.json",
        1_469_493,
        0o400,
        "f5d3bddcdc1661abff5795081e83ca08c9f7fc4732afc6ccd368c2c70c2ef102",
    ),
    _ArtifactFact(
        "execution_closure",
        "v180r12r4_campaign_measurement/EXECUTION_CLOSURE.json",
        1_919,
        0o400,
        "c222ac484683017da37aa929688ac7758aad407718b89caca82236b44f9e5d5a",
    ),
    _ArtifactFact(
        "os_receipt",
        "v180r12r4_campaign_measurement/OS_RECEIPT.json",
        34_422,
        0o400,
        "d47a7739be435fd63136b50b376a94a50f7c03401ef93983258d28c2245e721d",
    ),
    _ArtifactFact(
        "evidence_inventory",
        "v180r12r4_campaign_measurement/EVIDENCE_INVENTORY.json",
        870_587,
        0o400,
        "b0116d9440ebd9fbbebddc6878cf850e39e789ef35af0d13a7e37977ba337b55",
    ),
    _ArtifactFact(
        "subject_result",
        "v180r12r4_campaign_measurement/SUBJECT_RESULT.json",
        19_561,
        0o400,
        "54caed2cf31e751aa6162010ede14a6653654f5701e4498a7b38e2b03166f268",
    ),
    _ArtifactFact(
        "verification_inner_attempt",
        "v180r12r4_campaign_measurement_prelaunch/VERIFICATION_LAUNCH_ATTEMPT.json",
        4_362,
        0o400,
        "9f531d8b1db8475d04ff4e5a511348cf93c30d80228cf2fdf6132f58a5efb2b7",
    ),
    _ArtifactFact(
        "verification_outer_attempt",
        "v180r12r4_campaign_measurement_prelaunch/VERIFICATION_SERVICE_LAUNCH_ATTEMPT.json",
        5_520,
        0o400,
        "aaf1cf7ceee00a71bee8cc18395c2e6122e597a2e2c827a54ff1e199ba1d4639",
    ),
    _ArtifactFact(
        "verification",
        "v180r12r4_campaign_measurement_verification.json",
        8_101,
        0o400,
        "fdcc2eabd6ccdcf1d168ee7a15d03f4d673673d5f3e79c079f2e67a6c39b6588",
    ),
    _ArtifactFact(
        "verification_replay",
        "v180r12r4_campaign_measurement_verification_replay.json",
        8_101,
        0o400,
        "fdcc2eabd6ccdcf1d168ee7a15d03f4d673673d5f3e79c079f2e67a6c39b6588",
    ),
    _ArtifactFact(
        "verification_inner_failure",
        "v180r12r4_campaign_measurement_prelaunch_verification_launch_failure.json",
        12_701,
        0o400,
        "92f714e17e7bf3cb1b2820be2e042f8756a745d4087787ec4f5002c43f9fa5bd",
    ),
    _ArtifactFact(
        "verification_outer_failure",
        "v180r12r4_campaign_measurement_prelaunch_verification_service_launch_failure.json",
        8_337,
        0o400,
        "bb2875a7b3e653d8fca67bf73e6ed4f8dae0a3adabf7a09bb9f365c7db06f8d5",
    ),
)
_DIAGNOSTIC_ARTIFACT_FACT = _ArtifactFact(
    "runner_git_contract_observation",
    "raw/post_failure_runner_git_contract_observation.json",
    4_816,
    0o644,
    "3363356ebb7a2602f9495fdde0f9f2cd91139c1decd9497df273c91a05648c8b",
    formal=False,
    pretty=True,
)
_ARTIFACT_FACTS = _FORMAL_ARTIFACT_FACTS + (_DIAGNOSTIC_ARTIFACT_FACT,)
_FACT_BY_ROLE = {fact.role: fact for fact in _ARTIFACT_FACTS}
_ABSENT_ARTIFACTS = {
    "campaign_failure": "v180r12r4_campaign_measurement_failure.json",
    "verification_failure": (
        "v180r12r4_campaign_measurement_verification_failure.json"
    ),
    "verification_inner_receipt": (
        "v180r12r4_campaign_measurement_prelaunch/"
        "VERIFICATION_LAUNCH_RECEIPT.json"
    ),
    "verification_outer_receipt": (
        "v180r12r4_campaign_measurement_prelaunch/"
        "VERIFICATION_SERVICE_LAUNCH_RECEIPT.json"
    ),
}


class Ordinal14FailureFreezeV180r12r4r9Error(ValueError):
    """Raised when retained Ordinal14 evidence no longer matches."""


def _fail(message: str) -> None:
    raise Ordinal14FailureFreezeV180r12r4r9Error(message)


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
        f"ordinal14 {field} canonical identity changed",
    )
    return expected


def _values_for_key(value: Any, key: str) -> list[Any]:
    values: list[Any] = []
    if type(value) is dict:
        for name, child in value.items():
            if name == key:
                values.append(child)
            values.extend(_values_for_key(child, key))
    elif type(value) is list:
        for child in value:
            values.extend(_values_for_key(child, key))
    return values


def _read_documents(
    retained_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bytes]]:
    documents: dict[str, dict[str, Any]] = {}
    raw_by_role: dict[str, bytes] = {}
    for fact in _ARTIFACT_FACTS:
        path = retained_root / fact.relative_path
        try:
            status = path.stat()
            raw = path.read_bytes()
        except OSError as error:
            raise Ordinal14FailureFreezeV180r12r4r9Error(
                f"ordinal14 {fact.role} is unreadable"
            ) from error
        # Git records only the executable bit, so a committed 0400 artifact is
        # materialized as 0644 in a fresh checkout.  ``fact.mode`` preserves
        # the mode observed at the formal occurrence; it is not a checkout
        # identity that Git can reproduce.
        _require(
            stat.S_ISREG(status.st_mode),
            f"ordinal14 {fact.role} file type changed",
        )
        _require(
            len(raw) == fact.byte_count
            and hashlib.sha256(raw).hexdigest() == fact.sha256,
            f"ordinal14 {fact.role} raw bytes changed",
        )
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Ordinal14FailureFreezeV180r12r4r9Error(
                f"ordinal14 {fact.role} is not JSON"
            ) from error
        # The post-failure observation is explicitly non-formal and retains its
        # human-readable producer formatting under the exact raw hash above.
        expected_raw = raw if fact.pretty else _canonical_bytes(document)
        _require(
            type(document) is dict and raw == expected_raw,
            f"ordinal14 {fact.role} canonical bytes changed",
        )
        documents[fact.role] = document
        raw_by_role[fact.role] = raw
    for role, relative_path in _ABSENT_ARTIFACTS.items():
        _require(
            not (retained_root / relative_path).exists(),
            f"ordinal14 absent {role} unexpectedly appeared",
        )
    return documents, raw_by_role


def _file_fact(role: str) -> dict[str, Any]:
    fact = _FACT_BY_ROLE[role]
    return {
        "byte_count": fact.byte_count,
        "mode": fact.mode,
        "presence": "REGULAR_FILE",
        "sha256": fact.sha256,
    }


def _freeze_payload() -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v180r12r4r9_ordinal14_verification_failure_freeze.v1"
        ),
        "campaign_attempt_id": EXPECTED_CAMPAIGN_ATTEMPT_ID,
        "campaign_attempt_record_id": EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        "measurement_terminal_id": EXPECTED_MEASUREMENT_TERMINAL_ID,
        "verification_id": EXPECTED_VERIFICATION_ID,
        "materialization_terminal_id": EXPECTED_MATERIALIZATION_TERMINAL_ID,
        "measurement_inner_launch_attempt_id": (
            EXPECTED_MEASUREMENT_INNER_LAUNCH_ATTEMPT_ID
        ),
        "measurement_inner_launch_receipt_id": (
            EXPECTED_MEASUREMENT_INNER_LAUNCH_RECEIPT_ID
        ),
        "measurement_outer_service_attempt_id": (
            EXPECTED_MEASUREMENT_OUTER_SERVICE_ATTEMPT_ID
        ),
        "measurement_outer_service_receipt_id": (
            EXPECTED_MEASUREMENT_OUTER_SERVICE_RECEIPT_ID
        ),
        "verification_inner_launch_attempt_id": (
            EXPECTED_INNER_LAUNCH_ATTEMPT_ID
        ),
        "verification_inner_launch_failure_id": (
            EXPECTED_INNER_LAUNCH_FAILURE_ID
        ),
        "verification_outer_service_attempt_id": (
            EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID
        ),
        "verification_outer_service_failure_id": (
            EXPECTED_OUTER_SERVICE_FAILURE_ID
        ),
        "formal_artifact_sha256s": {
            fact.role: fact.sha256 for fact in _FORMAL_ARTIFACT_FACTS
        },
        "post_failure_runner_git_contract_observation_sha256": (
            _DIAGNOSTIC_ARTIFACT_FACT.sha256
        ),
        "formal_mismatch_rows": [dict(row) for row in EXPECTED_FORMAL_MISMATCH_ROWS],
        "diagnosed_exact_cause": {
            "failure_code": (
                "TARGET_AGNOSTIC_SIX_PROCESS_GIT_AUDIT_APPLIED_TO_"
                "VERIFICATION_RUNNER"
            ),
            "message": EXPECTED_DIAGNOSED_MESSAGE,
        },
        "repair_scope": REPAIR_SCOPE,
    }


def _freeze_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        _FREEZE_DOMAIN.encode("ascii") + b"\x00" + _canonical_bytes(payload)
    ).hexdigest()


EXPECTED_ORDINAL14_FAILURE_FREEZE_ID = (
    "89562134029a69da93ce1dda6e9ec70abb238050fda1f530a8c5c2f557b5eb60"
)
ORDINAL14_FAILURE_FREEZE_ID = _freeze_id(_freeze_payload())
if ORDINAL14_FAILURE_FREEZE_ID != EXPECTED_ORDINAL14_FAILURE_FREEZE_ID:
    raise RuntimeError("V180r12r4r9 ordinal14 failure-freeze identity changed")


@dataclass(frozen=True, slots=True)
class FrozenOrdinal14FailureV180r12r4r9:
    freeze_id: str
    campaign_attempt_id: str
    campaign_attempt_record_id: str
    measurement_terminal_id: str
    verification_id: str
    materialization_terminal_id: str
    measurement_inner_launch_attempt_id: str
    measurement_inner_launch_receipt_id: str
    measurement_outer_service_attempt_id: str
    measurement_outer_service_receipt_id: str
    verification_inner_launch_attempt_id: str
    verification_inner_launch_failure_id: str
    verification_outer_service_attempt_id: str
    verification_outer_service_failure_id: str
    property_snapshots: dict[str, Any]
    runner_git_contract_observation: dict[str, Any]

    def to_contract(self) -> dict[str, Any]:
        """Return the exact, claim-bounded Ordinal14 failure contract."""

        observation = self.runner_git_contract_observation
        return {
            "schema": (
                "acfqp.v180r12r4r9_ordinal14_verification_failure_freeze.v1"
            ),
            "freeze_id": self.freeze_id,
            "campaign_attempt_id": self.campaign_attempt_id,
            "campaign_attempt_record_id": self.campaign_attempt_record_id,
            "measurement_terminal_id": self.measurement_terminal_id,
            "verification_id": self.verification_id,
            "materialization_terminal_id": self.materialization_terminal_id,
            "measurement_inner_launch_attempt_id": (
                self.measurement_inner_launch_attempt_id
            ),
            "measurement_inner_launch_receipt_id": (
                self.measurement_inner_launch_receipt_id
            ),
            "measurement_outer_service_attempt_id": (
                self.measurement_outer_service_attempt_id
            ),
            "measurement_outer_service_receipt_id": (
                self.measurement_outer_service_receipt_id
            ),
            "verification_inner_launch_attempt_id": (
                self.verification_inner_launch_attempt_id
            ),
            "verification_inner_launch_failure_id": (
                self.verification_inner_launch_failure_id
            ),
            "verification_outer_service_attempt_id": (
                self.verification_outer_service_attempt_id
            ),
            "verification_outer_service_failure_id": (
                self.verification_outer_service_failure_id
            ),
            "formal_artifact_count": len(_FORMAL_ARTIFACT_FACTS),
            "post_failure_diagnostic_artifact_count": 1,
            "post_failure_diagnostic_is_formal_campaign_artifact": False,
            "all_retained_document_self_ids_verified": True,
            "self_id_document_count": 18,
            "unique_self_id_count": 17,
            "formal_artifact_facts": {
                fact.role: {
                    "relative_path": fact.relative_path,
                    **_file_fact(fact.role),
                }
                for fact in _FORMAL_ARTIFACT_FACTS
            },
            "absent_artifact_facts": {
                role: {"presence": "ABSENT", "relative_path": path}
                for role, path in _ABSENT_ARTIFACTS.items()
            },
            "campaign_failure_artifact_present": False,
            "verification_failure_artifact_present": False,
            "source_root_count": 28,
            "full_source_conformance": True,
            "source_conformance_mismatch_count": 0,
            "source_conformance_cause": None,
            "full_host_conformance": True,
            "host_conformance_mismatch_count": 0,
            "host_conformance_cause": None,
            "property_snapshots": self.property_snapshots,
            "measurement_succeeded": True,
            "measurement_inner_launch_receipt_present": True,
            "measurement_outer_service_receipt_present": True,
            "measurement_full_cgroup_topology_conformance": True,
            "measurement_runtime_placement_t1_t2_t3_complete": True,
            "verification_unit_ownership_t1_acquired": True,
            "verification_payload_conformance": True,
            "verification_payload_and_replay_byte_identical": True,
            "verification_payload_counter_completeness_gate": "PASS",
            "verification_payload_counter_closure_status": "PASS",
            "verification_transport_success": False,
            "producer_free_verification_attempted": True,
            "producer_free_verification_completed": False,
            "verification_inner_launch_receipt_present": False,
            "verification_outer_service_receipt_present": False,
            "full_verification_launch_conformance": False,
            "formal_failure_classification": {
                "failure_type": "V180r12r4PrelaunchLaunchError",
                "inner_failure_message": (
                    "source-bound child did not reach its exact durable "
                    "success state"
                ),
                "inner_return_code": 1,
                "outer_failure_message": (
                    "production systemd service did not reach its exact "
                    "inner receipt"
                ),
                "outer_systemd_run_return_code": 1,
                "stage": (
                    "POST_RUN_BOOTSTRAP_SECONDARY_OBSERVATION_AFTER_DURABLE_"
                    "VERIFICATION_PUBLICATION"
                ),
            },
            "formal_mismatch_count": 1,
            "formal_mismatch_rows": [
                dict(row) for row in EXPECTED_FORMAL_MISMATCH_ROWS
            ],
            "diagnosed_exact_cause": observation["cause"],
            "runtime_observed_git_process_count": None,
            "runtime_observed_git_process_count_recorded": False,
            "static_control_flow_inference": observation[
                "static_control_flow_inference"
            ],
            "gate_statuses_by_layer": {
                "measurement_terminal": {
                    "COUNTER_COMPLETENESS_GATE": "PENDING_INDEPENDENT_REPLAY",
                    **{name: "NOT_RUN" for name in _LATER_GATE_NAMES},
                },
                "verification_payload": {
                    "COUNTER_COMPLETENESS_GATE": "PASS",
                    "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS": "PASS",
                    **{name: "NOT_RUN" for name in _LATER_GATE_NAMES},
                },
                "verification_transport": {
                    "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
                    **{name: "NOT_RUN" for name in _LATER_GATE_NAMES},
                },
            },
            "counter_record_count": 9,
            "path_receipt_count": 9,
            "work_vector_count": 1,
            "comparison_vector_count": 1,
            "native_zero_attestation_count": 1,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "scientific_success_claimed": False,
            "open_world_absence_claimed": False,
            "counter_pass_is_payload_level_only": True,
            "full_ordinal14_occurrence_success": False,
            "identity_consumed": True,
            "same_identity_rerun_forbidden": True,
            "fresh_successor_identity_required": True,
            "repair_scope": REPAIR_SCOPE,
        }


def _documents_with_schema(
    os_receipt: dict[str, Any], schema: str
) -> list[dict[str, Any]]:
    documents = os_receipt.get("os_receipt_documents")
    _require(type(documents) is list, "ordinal14 OS receipt documents changed")
    return [
        document
        for document in documents
        if type(document) is dict and document.get("schema") == schema
    ]


def _require_host_conformance(host: dict[str, Any]) -> None:
    expected = host.get("expected")
    observed = host.get("observed")
    _require(
        type(expected) is dict
        and type(observed) is dict
        and set(expected)
        == set(observed)
        == {
            "cgroup_parent_fact",
            "runtime_capability_fact",
            "socket_buffer_capability",
        },
        "ordinal14 host property snapshots changed",
    )
    expected_parent = expected["cgroup_parent_fact"]
    observed_parent = observed["cgroup_parent_fact"]
    parent_fields = host.get("cgroup_parent_compared_fields")
    expected_runtime = expected["runtime_capability_fact"]
    observed_runtime = observed["runtime_capability_fact"]
    runtime_fields = host.get("runtime_capability_compared_fields")
    expected_socket = expected["socket_buffer_capability"]
    observed_socket = observed["socket_buffer_capability"]
    socket_exact = host.get("socket_buffer_capability_exact_fields")
    socket_minimums = host.get("socket_buffer_capability_at_least_fields")
    _require(
        host.get("schema")
        == "acfqp.v180r12r4_pre_attempt_host_conformance.v2"
        and host.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and host.get("campaign_attempt_created") is False
        and host.get("campaign_event_or_counter_record_issued") is False
        and host.get("production_unit_ownership_t1_joined") is False
        and host.get("working_tree_source_conformance_joined") is False
        and host.get("cgroup_parent_excluded_fields") == ["self_membership"]
        and type(parent_fields) is list
        and set(parent_fields) == set(expected_parent) - {"self_membership"}
        and all(
            expected_parent[name] == observed_parent[name]
            for name in parent_fields
        )
        and observed_parent.get("self_membership")
        == EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP
        and type(runtime_fields) is list
        and set(runtime_fields) == set(expected_runtime) == set(observed_runtime)
        and all(
            expected_runtime[name] == observed_runtime[name]
            for name in runtime_fields
        )
        and type(socket_exact) is list
        and all(
            expected_socket[name] == observed_socket[name]
            for name in socket_exact
        )
        and type(socket_minimums) is list
        and all(
            observed_socket[name] >= expected_socket[name]
            for name in socket_minimums
        )
        and observed_socket.get("buffer_request_bytes") == 1_048_576
        and observed_socket.get("effective_min_bytes") == 2_097_152
        and host.get("full_host_conformance") is True
        and host.get("mismatch_count") == 0
        and host.get("mismatch_rows") == []
        and host.get("cause") is None,
        "ordinal14 full host and socket conformance changed",
    )


def _require_source_and_materialization(
    external: dict[str, Any],
    materialization: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    frozen = external.get("frozen_authorization_context")
    _require(type(frozen) is dict, "ordinal14 frozen context changed")
    _require(
        external.get("repository_root") == EXPECTED_REPOSITORY_ROOT
        and materialization.get("repository_root") == EXPECTED_REPOSITORY_ROOT
        and manifest.get("repository_root") == EXPECTED_REPOSITORY_ROOT
        and external.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and external.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and external.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and external.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and external.get("third_party_source_roots")
        == {
            "packaging": EXPECTED_THIRD_PARTY_ROOT,
            "tomli": EXPECTED_THIRD_PARTY_ROOT,
        }
        and external.get(
            "created_before_v180r12r4_authorized_measurement_execution"
        )
        is True
        and external.get("v180r12r4_outcome_bytes_accessed") is False
        and manifest.get("frozen_authorization_context") == frozen
        and frozen.get("campaign_attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and frozen.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and frozen.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and frozen.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID,
        "ordinal14 authorization or external-root joins changed",
    )
    topology = materialization.get("git_topology")
    _require(
        type(topology) is dict
        and topology.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and topology.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and topology.get("empty_bridge_commit_id")
        == EXPECTED_EMPTY_BRIDGE_COMMIT_ID
        and topology.get("literal_commit_id") == EXPECTED_LITERAL_COMMIT_ID,
        "ordinal14 source topology changed",
    )
    _require(
        materialization.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and materialization.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and materialization.get("success") is True
        and materialization.get("construction_only") is True
        and materialization.get("campaign_actual_measurement") is False
        and materialization.get("scientific_occurrence_executed") is False
        and materialization.get("counter_records_issued") is False
        and materialization.get("work_vectors_issued") is False
        and materialization.get("comparison_vectors_issued") is False
        and materialization.get("external_root", {}).get("sha256")
        == _FACT_BY_ROLE["external_root"].sha256
        and materialization.get("launch_manifest", {}).get("sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and all(
            materialization.get(name) == "NOT_RUN"
            for name in _GATE_NAMES[:-1]
        )
        and materialization.get("official_execution_allowed") is False,
        "ordinal14 materialization boundary changed",
    )
    source = materialization.get("working_tree_source_conformance")
    snapshots = source.get("snapshots") if type(source) is dict else None
    _require(
        type(source) is dict
        and manifest.get("working_tree_source_conformance") == source
        and source.get("source_root_count") == 28
        and source.get("mismatch_count") == 0
        and source.get("per_field_mismatches") == []
        and source.get("full_source_conformance") is True
        and source.get("unit_ownership_evaluated") is False
        and source.get("cause") is None
        and type(snapshots) is list
        and len(snapshots) == 28
        and all(
            type(row) is dict
            and row.get("conformant") is True
            and row.get("mismatch_fields") == []
            and row.get("observed_before") == row.get("observed_after")
            for row in snapshots
        ),
        "ordinal14 28-root source conformance changed",
    )
    git = manifest.get("git")
    argv = git.get("runner_argv") if type(git) is dict else None
    _require(
        type(git) is dict
        and git.get("runner_process_count") == 6
        and type(argv) is list
        and len(argv) == 6
        and tuple(row[3] for row in argv) == EXPECTED_GIT_SUBCOMMANDS,
        "ordinal14 frozen six-process Git schedule changed",
    )
    return source


def _require_measurement_transport(
    documents: dict[str, dict[str, Any]],
    *,
    materialization_id: str,
) -> tuple[str, str, str, str]:
    inner_attempt = documents["measurement_inner_attempt"]
    inner_receipt = documents["measurement_inner_receipt"]
    outer_attempt = documents["measurement_outer_attempt"]
    outer_receipt = documents["measurement_outer_receipt"]
    inner_attempt_id = _require_self_id(
        inner_attempt,
        "launch_attempt_id",
        EXPECTED_MEASUREMENT_INNER_LAUNCH_ATTEMPT_ID,
    )
    inner_receipt_id = _require_self_id(
        inner_receipt,
        "launch_receipt_id",
        EXPECTED_MEASUREMENT_INNER_LAUNCH_RECEIPT_ID,
    )
    outer_attempt_id = _require_self_id(
        outer_attempt,
        "service_launch_attempt_id",
        EXPECTED_MEASUREMENT_OUTER_SERVICE_ATTEMPT_ID,
        domain=_SERVICE_ATTEMPT_DOMAIN,
    )
    outer_receipt_id = _require_self_id(
        outer_receipt,
        "service_launch_receipt_id",
        EXPECTED_MEASUREMENT_OUTER_SERVICE_RECEIPT_ID,
        domain=_SERVICE_RECEIPT_DOMAIN,
    )
    measurement_invocation = inner_attempt.get(
        "production_systemd_service_invocation"
    )
    _require(
        type(measurement_invocation) is dict
        and measurement_invocation
        == inner_receipt.get("production_systemd_service_invocation")
        == outer_attempt.get("production_systemd_service_invocation")
        == outer_receipt.get("production_systemd_service_invocation")
        and measurement_invocation.get("target") == "measurement"
        and measurement_invocation.get("token")
        == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and measurement_invocation.get("unit_name")
        == EXPECTED_MEASUREMENT_UNIT_NAME
        and measurement_invocation.get("delegate") is True,
        "ordinal14 measurement service identity changed",
    )
    _require(
        inner_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_id")
        == materialization_id
        and inner_attempt.get("launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and inner_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("target") == "measurement"
        and outer_attempt.get("target") == "measurement",
        "ordinal14 measurement launch-attempt joins changed",
    )
    _require(
        inner_receipt.get("launch_attempt_id") == inner_attempt_id
        and inner_receipt.get("target") == "measurement"
        and inner_receipt.get("return_code") == 0
        and inner_receipt.get("timed_out") is False
        and inner_receipt.get("success") is True
        and inner_receipt.get("failure_type") is None
        and inner_receipt.get("failure_message") is None
        and inner_receipt.get("authorized_child_measurement_execution_attempted")
        is True
        and inner_receipt.get("authorized_child_measurement_execution_completed")
        is True
        and inner_receipt.get("producer_free_verification_attempted") is False
        and inner_receipt.get("producer_free_verification_completed") is False,
        "ordinal14 successful measurement inner receipt changed",
    )
    cleanup = inner_receipt.get("measurement_cgroup_cleanup_observations")
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
        "ordinal14 measurement cleanup changed",
    )
    _require(
        outer_receipt.get("service_launch_attempt_id") == outer_attempt_id
        and outer_receipt.get("inner_launch_attempt_id") == inner_attempt_id
        and outer_receipt.get("inner_launch_terminal_kind") == "RECEIPT"
        and outer_receipt.get("inner_launch_terminal_id") == inner_receipt_id
        and outer_receipt.get("inner_launch_attempt_fact")
        == _file_fact("measurement_inner_attempt")
        and outer_receipt.get("inner_launch_receipt_fact")
        == _file_fact("measurement_inner_receipt")
        and outer_receipt.get("inner_launch_failure_fact")
        == {"presence": "ABSENT"}
        and outer_receipt.get("systemd_run_return_code") == 0
        and outer_receipt.get("systemd_run_timed_out") is False
        and outer_receipt.get("success") is True,
        "ordinal14 successful measurement outer receipt changed",
    )
    unit_absence = outer_receipt.get("collected_unit_absence_observation")
    _require(
        type(unit_absence) is dict
        and unit_absence.get("unit_absent_after_wait_collect") is True
        and unit_absence.get("expected_load_state") == "not-found"
        and unit_absence.get("return_code") == 0
        and unit_absence.get("timed_out") is False,
        "ordinal14 measurement unit collection changed",
    )
    return inner_attempt_id, inner_receipt_id, outer_attempt_id, outer_receipt_id


def _require_measurement_payloads(
    documents: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    terminal = documents["terminal"]
    ledger = documents["ledger_closure"]
    execution = documents["execution_closure"]
    os_receipt = documents["os_receipt"]
    evidence_inventory = documents["evidence_inventory"]
    subject_result = documents["subject_result"]
    terminal_id = _require_self_id(
        terminal,
        "campaign_measurement_terminal_id",
        EXPECTED_MEASUREMENT_TERMINAL_ID,
        domain=_TERMINAL_DOMAIN,
    )
    ledger_id = _require_self_id(
        ledger,
        "campaign_ledger_closure_id",
        EXPECTED_LEDGER_CLOSURE_ID,
        domain=_LEDGER_CLOSURE_DOMAIN,
    )
    execution_id = _require_self_id(
        execution,
        "campaign_execution_closure_id",
        EXPECTED_EXECUTION_CLOSURE_ID,
        domain=_EXECUTION_CLOSURE_DOMAIN,
    )
    os_receipt_id = _require_self_id(
        os_receipt,
        "campaign_os_receipt_bundle_id",
        EXPECTED_OS_RECEIPT_BUNDLE_ID,
        domain=_OS_RECEIPT_BUNDLE_DOMAIN,
    )
    evidence_inventory_id = _require_self_id(
        evidence_inventory,
        "campaign_evidence_inventory_bundle_id",
        EXPECTED_EVIDENCE_INVENTORY_BUNDLE_ID,
        domain=_EVIDENCE_INVENTORY_BUNDLE_DOMAIN,
    )
    subject_result_id = _require_self_id(
        subject_result,
        "subject_result_id",
        EXPECTED_SUBJECT_RESULT_ID,
        domain=_SUBJECT_RESULT_DOMAIN,
    )
    common = (
        EXPECTED_PROTOCOL_ID,
        EXPECTED_AUTHORIZATION_ID,
        EXPECTED_CAMPAIGN_ATTEMPT_ID,
    )
    _require(
        (
            terminal.get("protocol_id"),
            terminal.get("authorization_id"),
            terminal.get("attempt_id"),
        )
        == common
        and terminal.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and terminal.get("campaign_measurement_ledger") == ledger
        and terminal.get("campaign_ledger_closure_id") == ledger_id
        and terminal.get("campaign_execution_closure_id") == execution_id
        and terminal.get("campaign_os_receipt_bundle_id") == os_receipt_id
        and terminal.get("campaign_evidence_inventory_bundle_id")
        == evidence_inventory_id
        and terminal.get("subject_id") == subject_result_id
        and terminal.get("os_receipt_documents")
        == os_receipt.get("os_receipt_documents")
        and terminal.get("os_receipt_ids")
        == os_receipt.get("ordered_os_receipt_ids")
        and terminal.get("campaign_ledger_closure_sha256")
        == _FACT_BY_ROLE["ledger_closure"].sha256
        and terminal.get("campaign_execution_closure_sha256")
        == _FACT_BY_ROLE["execution_closure"].sha256
        and terminal.get("campaign_os_receipt_bundle_sha256")
        == _FACT_BY_ROLE["os_receipt"].sha256
        and terminal.get("campaign_evidence_inventory_bundle_sha256")
        == _FACT_BY_ROLE["evidence_inventory"].sha256,
        "ordinal14 terminal or closure joins changed",
    )
    _require(
        subject_result.get("attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and subject_result.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and subject_result.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and subject_result.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and subject_result.get("campaign_attempt_record_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
        and subject_result.get("measurement_launch_attempt_id")
        == EXPECTED_MEASUREMENT_INNER_LAUNCH_ATTEMPT_ID
        and subject_result.get("prelaunch_materialization_terminal_id")
        == EXPECTED_MATERIALIZATION_TERMINAL_ID
        and subject_result.get("prelaunch_launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and subject_result.get("prelaunch_launch_rule_id")
        == EXPECTED_LAUNCH_RULE_ID
        and subject_result.get("producer_entrypoint_called") is False
        and subject_result.get("producer_module_imported") is False
        and subject_result.get("exact_v180r12r2_verification_replayed") is True
        and subject_result.get("v180r12r2_verifier_called") is False
        and subject_result.get("v180r12r2_verifier_imported") is False
        and subject_result.get("semantic_hash_operation_count") == 137
        and subject_result.get("integrity_check_operation_count") == 145
        and subject_result.get("protocol_check_operation_count") == 15
        and subject_result.get("subject_byte_count") == 19_561
        and subject_result.get("counter_completeness_gate")
        == "PENDING_INDEPENDENT_REPLAY"
        and subject_result.get("route_component_counter_closure_status") == "PASS"
        and all(subject_result.get(name.lower()) == "NOT_RUN" for name in _LATER_GATE_NAMES)
        and subject_result.get("official_execution_allowed") is False
        and subject_result.get("official_scalar_cost") is None
        and subject_result.get("official_N_break_even") is None,
        "ordinal14 producer-free subject result or gate boundary changed",
    )
    _require(
        terminal.get("event_count") == ledger.get("event_count") == 625
        and terminal.get("evidence_document_count") == 328
        and evidence_inventory.get("evidence_document_count") == 328
        and terminal.get("os_receipt_document_count") == 12
        and os_receipt.get("os_receipt_document_count") == 12
        and terminal.get("campaign_counter_record_count") == 9
        and terminal.get("campaign_path_receipt_count") == 9
        and terminal.get("campaign_work_vector_count") == 1
        and terminal.get("campaign_comparison_vector_count") == 1
        and terminal.get("campaign_native_zero_attestation_count") == 1
        and terminal.get("all_nine_campaign_paths_strictly_positive") is True
        and terminal.get("COUNTER_COMPLETENESS_GATE")
        == "PENDING_INDEPENDENT_REPLAY"
        and terminal.get("V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS")
        == "PENDING_INDEPENDENT_REPLAY"
        and all(terminal.get(name) == "NOT_RUN" for name in _LATER_GATE_NAMES)
        and terminal.get("independent_verification_present") is False
        and terminal.get("official_execution_allowed") is False
        and terminal.get("official_scalar_cost") is None
        and terminal.get("official_N_break_even") is None
        and terminal.get("scientific_success_claimed") is False,
        "ordinal14 terminal count or gate boundary changed",
    )
    expected_counters = [
        ("common.hash_invocations", "nonkernel_compute_events", 137),
        ("common.integrity_checks", "nonkernel_compute_events", 145),
        ("common.protocol_checks", "nonkernel_compute_events", 15),
        ("io.mounted_bytes_peak", "peak_mounted_bytes", 202_507),
        ("io.output_bytes", "output_bytes", 19_561),
        ("io.read_bytes", "read_bytes", 424_575),
        ("io.staged_bytes", "staged_bytes", 202_507),
        ("memory.working_bytes_peak", "peak_working_bytes", 131_715_072),
        ("process.launches", "process_launches", 2),
    ]
    counters = ledger.get("counter_records")
    paths = ledger.get("path_receipts")
    _require(
        type(counters) is list
        and type(paths) is list
        and len(counters) == len(paths) == 9
        and [
            (row.get("path"), row.get("comparison_axis"), row.get("value"))
            for row in counters
        ]
        == expected_counters
        and all(row.get("observed") is True for row in counters)
        and [
            (row.get("path"), row.get("comparison_axis"), row.get("value"))
            for row in paths
        ]
        == expected_counters
        and all(row.get("actual_measurement_present") is True for row in paths),
        "ordinal14 nine-path measurement population changed",
    )
    comparison = ledger.get("campaign_comparison_vector")
    native_zero = ledger.get("campaign_native_zero_attestation")
    _require(
        type(comparison) is dict
        and comparison.get("values")
        == [
            {"axis": "kernel_transition_calls", "reducer": "sum", "value": 0},
            {
                "axis": "nonkernel_compute_events",
                "reducer": "sum",
                "value": 297,
            },
            {"axis": "output_bytes", "reducer": "sum", "value": 19_561},
            {
                "axis": "peak_mounted_bytes",
                "reducer": "max",
                "value": 202_507,
            },
            {
                "axis": "peak_working_bytes",
                "reducer": "max",
                "value": 131_715_072,
            },
            {"axis": "process_launches", "reducer": "sum", "value": 2},
            {"axis": "read_bytes", "reducer": "sum", "value": 424_575},
            {"axis": "staged_bytes", "reducer": "sum", "value": 202_507},
        ]
        and type(native_zero) is dict
        and native_zero.get("comparison_axis") == "kernel_transition_calls"
        and native_zero.get("comparison_axis_value") == 0
        and native_zero.get("closed_registered_planning_operation_window_only")
        is True
        and native_zero.get("not_an_os_syscall_count") is True
        and native_zero.get("open_world_absence_claimed") is False
        and execution.get("kernel_transition_calls") == 0
        and execution.get("not_an_os_syscall_count") is True
        and execution.get("open_world_absence_claimed") is False,
        "ordinal14 comparison vector or bounded native-zero claim changed",
    )
    return terminal_id, ledger, execution, os_receipt, evidence_inventory


def _require_os_property_snapshots(
    os_receipt: dict[str, Any],
    measurement_receipt: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    topology_documents = _documents_with_schema(
        os_receipt, "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
    )
    observation_documents = _documents_with_schema(
        os_receipt, "acfqp.campaign_cgroup_observation_receipt.v180r12r4"
    )
    birth_documents = _documents_with_schema(
        os_receipt, "acfqp.campaign_pidfd_birth_receipt.v180r12r4"
    )
    reap_documents = _documents_with_schema(
        os_receipt, "acfqp.campaign_pidfd_reap_receipt.v180r12r4"
    )
    _require(
        len(topology_documents) == len(observation_documents) == 1
        and len(birth_documents) == len(reap_documents) == 2,
        "ordinal14 cgroup topology or birth/reap cardinality changed",
    )
    topology = topology_documents[0]
    lifecycle = observation_documents[0]
    measurement_t1 = topology.get("production_runtime_placement_t1")
    measurement_t2 = topology.get("production_runtime_placement_t2")
    supervisor_births = [
        row for row in birth_documents if row.get("process_role") == "SUPERVISOR"
    ]
    _require(
        len(supervisor_births) == 1,
        "ordinal14 supervisor birth snapshot changed",
    )
    measurement_t3 = supervisor_births[0].get("production_runtime_placement_t3")
    _require(
        type(measurement_t1) is dict
        and measurement_t1
        == measurement_receipt.get("production_runtime_placement_t1")
        and measurement_t1.get("schema")
        == "acfqp.v180r12r4_production_runtime_placement_t1.v1"
        and measurement_t1.get("target") == "measurement"
        and measurement_t1.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and measurement_t1.get("unit_name") == EXPECTED_MEASUREMENT_UNIT_NAME
        and measurement_t1.get("source_membership")
        == EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP
        and measurement_t1.get("expected_source_membership")
        == EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP
        and measurement_t1.get("nearest_common_ancestor_is_app_slice") is True
        and measurement_t1.get("parent_cgroup_procs_o_wronly_openable") is True
        and measurement_t1.get("planned_measurement_root_absent") is True
        and measurement_t1.get("self_pid_in_source_cgroup_procs") is True
        and measurement_t1.get("t1_complete_before_child_popen") is True,
        "ordinal14 measurement T1 property snapshot changed",
    )
    _require(
        type(measurement_t2) is dict
        and measurement_t2.get("schema")
        == "acfqp.v180r12r4_production_runtime_placement_t2.v2"
        and measurement_t2.get("boundary")
        == "T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL"
        and measurement_t2.get("target") == "measurement"
        and measurement_t2.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and measurement_t2.get("unit_name") == EXPECTED_MEASUREMENT_UNIT_NAME
        and measurement_t2.get("source_membership")
        == EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP
        and measurement_t2.get("expected_source_membership")
        == EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP
        and measurement_t2.get("nearest_common_ancestor_is_app_slice") is True
        and measurement_t2.get("parent_cgroup_procs_o_wronly_openable") is True
        and measurement_t2.get("parent_pid_in_source_cgroup_procs") is True
        and measurement_t2.get("self_pid_in_source_cgroup_procs") is True
        and measurement_t2.get("planned_measurement_root_state") == "ABSENT"
        and measurement_t2.get("scientific_progress_absent") is True
        and measurement_t2.get("scientific_progress_present_paths") == [],
        "ordinal14 measurement T2 property snapshot changed",
    )
    _require(
        type(measurement_t3) is dict
        and measurement_t3.get("schema")
        == "acfqp.v180r12r4_production_runtime_placement_t3.v2"
        and measurement_t3.get("target") == "measurement"
        and measurement_t3.get("token") == EXPECTED_MEASUREMENT_SERVICE_TOKEN
        and measurement_t3.get("unit_name") == EXPECTED_MEASUREMENT_UNIT_NAME
        and measurement_t3.get("stable_across_boundaries") is True,
        "ordinal14 measurement T3 outer property snapshot changed",
    )
    before = measurement_t3.get("before_getrandom")
    immediate = measurement_t3.get("immediately_before_clone3")
    _require(
        type(before) is dict
        and type(immediate) is dict,
        "ordinal14 complete T3 checkpoints changed",
    )
    before_normalized = dict(before)
    immediate_normalized = dict(immediate)
    before_boundary = before_normalized.pop("boundary", None)
    immediate_boundary = immediate_normalized.pop("boundary", None)
    _require(
        before_boundary == "T3_BEFORE_GETRANDOM"
        and immediate_boundary == "T3_IMMEDIATELY_BEFORE_CLONE3"
        and before_normalized == immediate_normalized
        and before.get("source_membership")
        == before.get("expected_source_membership")
        == EXPECTED_MEASUREMENT_SOURCE_MEMBERSHIP
        and before.get("planned_measurement_root_state") == "PRESENT"
        and before.get("programmed_limits_revalidated") is True
        and before.get("root_empty_before_birth") is True
        and before.get("supervisor_leaf_empty_before_birth") is True
        and before.get("worker_leaf_empty_before_birth") is True
        and before.get("parent_pid_in_source_cgroup_procs") is True
        and before.get("self_pid_in_source_cgroup_procs") is True
        and before.get("target_cgroup_role") == "SUPERVISOR",
        "ordinal14 complete and stable T3 checkpoints changed",
    )
    _require(
        topology.get("filesystem_type") == "cgroup2"
        and topology.get("controllers") == ["cpu", "memory", "pids"]
        and topology.get("subtree_control") == ["memory", "pids"]
        and topology.get("sibling_leaf_topology") is True
        and topology.get("no_internal_process_rule_satisfied") is True
        and topology.get("root_process_count_before_birth") == 0
        and topology.get("root_populated_before_birth") is False
        and topology.get("leaf_process_counts_before_birth") == [0, 0]
        and topology.get("root_memory_max_bytes") == 17_179_869_184
        and topology.get("root_pids_max") == 2
        and topology.get("supervisor_leaf_pids_max") == 1
        and topology.get("worker_leaf_pids_max") == 1,
        "ordinal14 measurement topology conformance changed",
    )
    memory_events = lifecycle.get("memory_events")
    pids_events = lifecycle.get("pids_events")
    _require(
        lifecycle.get("observed_after_window_close") is True
        and lifecycle.get("memory_peak_bytes") == 131_715_072
        and lifecycle.get("memory_peak_is_observed_not_authorization_cap")
        is True
        and lifecycle.get("pids_peak") == 2
        and lifecycle.get("pids_peak_is_observed_not_authorization_cap") is True
        and lifecycle.get("root_populated") is False
        and lifecycle.get("root_process_count") == 0
        and lifecycle.get("supervisor_leaf_process_count") == 0
        and lifecycle.get("worker_leaf_process_count") == 0
        and type(memory_events) is list
        and all(row.get("value") == 0 for row in memory_events)
        and type(pids_events) is list
        and all(row.get("value") == 0 for row in pids_events)
        and all(row.get("waitid_status") == 0 for row in reap_documents)
        and all(row.get("leaf_process_count_after_reap") == 0 for row in reap_documents)
        and all(row.get("leaf_populated_after_reap") is False for row in reap_documents),
        "ordinal14 cgroup lifecycle or cleanup observations changed",
    )
    return topology, measurement_t1, measurement_t2, measurement_t3, lifecycle


def _require_verification_payload(
    documents: dict[str, dict[str, Any]],
    raw_by_role: dict[str, bytes],
) -> str:
    verification = documents["verification"]
    replay = documents["verification_replay"]
    verification_id = _require_self_id(
        verification,
        "campaign_measurement_verification_id",
        EXPECTED_VERIFICATION_ID,
        domain=_VERIFICATION_DOMAIN,
    )
    replay_id = _require_self_id(
        replay,
        "campaign_measurement_verification_id",
        EXPECTED_VERIFICATION_ID,
        domain=_VERIFICATION_DOMAIN,
    )
    _require(
        replay_id == verification_id
        and
        raw_by_role["verification"] == raw_by_role["verification_replay"]
        and verification == replay,
        "ordinal14 verification and replay bytes diverged",
    )
    _require(
        verification.get("protocol_id") == EXPECTED_PROTOCOL_ID
        and verification.get("authorization_id") == EXPECTED_AUTHORIZATION_ID
        and verification.get("authorization_evidence_id")
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and verification.get("attempt_id") == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and verification.get("campaign_measurement_terminal_id")
        == EXPECTED_MEASUREMENT_TERMINAL_ID
        and verification.get("campaign_measurement_terminal_sha256")
        == _FACT_BY_ROLE["terminal"].sha256
        and verification.get("campaign_ledger_closure_sha256")
        == _FACT_BY_ROLE["ledger_closure"].sha256
        and verification.get("campaign_execution_closure_sha256")
        == _FACT_BY_ROLE["execution_closure"].sha256
        and verification.get("campaign_os_receipt_bundle_sha256")
        == _FACT_BY_ROLE["os_receipt"].sha256
        and verification.get("campaign_evidence_inventory_bundle_sha256")
        == _FACT_BY_ROLE["evidence_inventory"].sha256,
        "ordinal14 verification evidence joins changed",
    )
    _require(
        verification.get("measurement_launch_attempt_id")
        == EXPECTED_MEASUREMENT_INNER_LAUNCH_ATTEMPT_ID
        and verification.get("measurement_launch_receipt_id")
        == EXPECTED_MEASUREMENT_INNER_LAUNCH_RECEIPT_ID
        and verification.get("measurement_launch_receipt_sha256")
        == _FACT_BY_ROLE["measurement_inner_receipt"].sha256
        and verification.get("measurement_service_launch_attempt_id")
        == EXPECTED_MEASUREMENT_OUTER_SERVICE_ATTEMPT_ID
        and verification.get("measurement_service_launch_receipt_id")
        == EXPECTED_MEASUREMENT_OUTER_SERVICE_RECEIPT_ID
        and verification.get("measurement_service_launch_attempt_sha256")
        == _FACT_BY_ROLE["measurement_outer_attempt"].sha256
        and verification.get("measurement_service_launch_receipt_sha256")
        == _FACT_BY_ROLE["measurement_outer_receipt"].sha256,
        "ordinal14 verification measurement-transport joins changed",
    )
    _require(
        verification.get("event_count") == 625
        and verification.get("evidence_document_count") == 328
        and verification.get("os_receipt_document_count") == 12
        and verification.get("campaign_counter_record_count") == 9
        and verification.get("campaign_path_receipt_count") == 9
        and verification.get("campaign_work_vector_count") == 1
        and verification.get("campaign_comparison_vector_count") == 1
        and verification.get("campaign_native_zero_attestation_count") == 1
        and verification.get("exact_625_event_schedule_independently_replayed")
        is True
        and verification.get("exact_328_evidence_inventory_independently_replayed")
        is True
        and verification.get("exact_twelve_os_receipts_independently_replayed")
        is True
        and verification.get("nine_campaign_counter_records_independently_rederived")
        is True
        and verification.get("nine_campaign_path_receipts_independently_rederived")
        is True
        and verification.get("campaign_work_vector_independently_rederived")
        is True
        and verification.get("campaign_comparison_vector_independently_rederived")
        is True
        and verification.get("bounded_native_zero_attestation_independently_rederived")
        is True
        and verification.get("production_runtime_placement_t1_t2_t3_independently_replayed")
        is True
        and verification.get("cgroup_topology_birth_reap_and_peak_independently_replayed")
        is True,
        "ordinal14 producer-free replay population changed",
    )
    _require(
        verification.get("producer_module_imported") is False
        and verification.get("finalizer_module_imported") is False
        and verification.get("campaign_measurement_ledger_kernel_imported")
        is False
        and verification.get("supervisor_module_imported") is False
        and verification.get("worker_module_imported") is False
        and verification.get("COUNTER_COMPLETENESS_GATE") == "PASS"
        and verification.get("V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS")
        == "PASS"
        and all(
            verification.get(name) == "NOT_RUN" for name in _LATER_GATE_NAMES
        )
        and verification.get("official_execution_allowed") is False
        and verification.get("official_scalar_cost") is None
        and verification.get("official_N_break_even") is None
        and verification.get("scientific_success_claimed") is False
        and verification.get("open_world_absence_claimed") is False
        and verification.get("native_zero_is_not_an_os_syscall_count") is True
        and verification.get("native_zero_is_registered_planning_comparison_axis_only")
        is True
        and verification.get("measurement_launch_receipt_directly_observes_origin_guard")
        is False
        and verification.get("runtime_role_exit_origin_guard_status")
        == "PASS_TRANSITIVE_FROZEN_BOOTSTRAP_AND_MEASUREMENT_LAUNCH_RECEIPT",
        "ordinal14 verification gate or nonclaim boundary changed",
    )
    return verification_id


def _require_verification_transport(
    documents: dict[str, dict[str, Any]],
    *,
    materialization_id: str,
) -> tuple[str, str, str, str, dict[str, Any]]:
    inner_attempt = documents["verification_inner_attempt"]
    outer_attempt = documents["verification_outer_attempt"]
    inner_failure = documents["verification_inner_failure"]
    outer_failure = documents["verification_outer_failure"]
    inner_attempt_id = _require_self_id(
        inner_attempt,
        "launch_attempt_id",
        EXPECTED_INNER_LAUNCH_ATTEMPT_ID,
    )
    outer_attempt_id = _require_self_id(
        outer_attempt,
        "service_launch_attempt_id",
        EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID,
        domain=_SERVICE_ATTEMPT_DOMAIN,
    )
    inner_failure_id = _require_self_id(
        inner_failure,
        "launch_failure_id",
        EXPECTED_INNER_LAUNCH_FAILURE_ID,
    )
    outer_failure_id = _require_self_id(
        outer_failure,
        "service_launch_failure_id",
        EXPECTED_OUTER_SERVICE_FAILURE_ID,
        domain=_SERVICE_FAILURE_DOMAIN,
    )
    invocation = inner_attempt.get("production_systemd_service_invocation")
    _require(
        type(invocation) is dict
        and invocation
        == outer_attempt.get("production_systemd_service_invocation")
        == inner_failure.get("production_systemd_service_invocation")
        == outer_failure.get("production_systemd_service_invocation")
        and invocation.get("target") == "verification"
        and invocation.get("token") == EXPECTED_VERIFICATION_SERVICE_TOKEN
        and invocation.get("unit_name") == EXPECTED_VERIFICATION_UNIT_NAME
        and invocation.get("delegate") is True,
        "ordinal14 verification unit identity changed",
    )
    _require(
        inner_attempt.get("materialization_terminal_id") == materialization_id
        and outer_attempt.get("materialization_terminal_id")
        == materialization_id
        and inner_attempt.get("launch_manifest_sha256")
        == _FACT_BY_ROLE["launch_manifest"].sha256
        and inner_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and outer_attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_attempt.get("target") == "verification"
        and outer_attempt.get("target") == "verification",
        "ordinal14 verification launch-attempt joins changed",
    )
    _require(
        inner_failure.get("launch_attempt_id") == inner_attempt_id
        and inner_failure.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
        and inner_failure.get("target") == "verification"
        and inner_failure.get("return_code") == 1
        and inner_failure.get("timed_out") is False
        and inner_failure.get("success") is False
        and inner_failure.get("attempt_lock_preserved") is True
        and inner_failure.get("same_target_identity_rerun_forbidden") is True
        and inner_failure.get("authorized_child_measurement_execution_attempted")
        is False
        and inner_failure.get("authorized_child_measurement_execution_completed")
        is False
        and inner_failure.get("producer_free_verification_attempted") is True
        and inner_failure.get("producer_free_verification_completed") is False
        and inner_failure.get("failure_type")
        == "V180r12r4PrelaunchLaunchError"
        and inner_failure.get("failure_message")
        == "source-bound child did not reach its exact durable success state"
        and all(
            inner_failure.get(name) == "NOT_RUN" for name in _GATE_NAMES[:-1]
        )
        and inner_failure.get("official_execution_allowed") is False,
        "ordinal14 verification inner failure boundary changed",
    )
    placement_t1 = inner_failure.get("production_runtime_placement_t1")
    _require(
        type(placement_t1) is dict
        and placement_t1.get("schema")
        == "acfqp.v180r12r4_production_runtime_placement_t1.v1"
        and placement_t1.get("target") == "verification"
        and placement_t1.get("token") == EXPECTED_VERIFICATION_SERVICE_TOKEN
        and placement_t1.get("unit_name") == EXPECTED_VERIFICATION_UNIT_NAME
        and placement_t1.get("source_membership")
        == EXPECTED_VERIFICATION_SOURCE_MEMBERSHIP
        and placement_t1.get("expected_source_membership")
        == EXPECTED_VERIFICATION_SOURCE_MEMBERSHIP
        and placement_t1.get("nearest_common_ancestor_is_app_slice") is True
        and placement_t1.get("parent_cgroup_procs_o_wronly_openable") is True
        and placement_t1.get("planned_measurement_root_absent") is True
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and placement_t1.get("t1_complete_before_child_popen") is True,
        "ordinal14 verification T1 unit ownership changed",
    )
    stderr = inner_failure.get("child_stderr")
    _require(type(stderr) is dict, "ordinal14 exact child stderr changed")
    try:
        stderr_raw = bytes.fromhex(stderr.get("retained_prefix_hex", ""))
    except ValueError:
        _fail("ordinal14 child stderr encoding changed")
    expected_tail = (
        "_RunnerSecondaryObservation: " + EXPECTED_DIAGNOSED_MESSAGE + "\n"
    ).encode("utf-8")
    _require(
        stderr.get("retained_prefix_truncated") is False
        and stderr.get("byte_count") == len(stderr_raw)
        == EXPECTED_CHILD_STDERR_BYTE_COUNT
        and stderr.get("sha256")
        == hashlib.sha256(stderr_raw).hexdigest()
        == EXPECTED_CHILD_STDERR_SHA256
        and stderr_raw.endswith(expected_tail),
        "ordinal14 exact untruncated secondary observation changed",
    )
    progress = inner_failure.get("progress_observations")
    _require(
        type(progress) is dict
        and progress.get("attempt") == _file_fact("verification_inner_attempt")
        and progress.get("host_conformance") == _file_fact("host_conformance")
        and progress.get("terminal") == _file_fact("terminal")
        and progress.get("ledger_closure") == _file_fact("ledger_closure")
        and progress.get("execution_closure") == _file_fact("execution_closure")
        and progress.get("os_receipt") == _file_fact("os_receipt")
        and progress.get("evidence_inventory") == _file_fact("evidence_inventory")
        and progress.get("verification") == _file_fact("verification")
        and progress.get("retained_replay") == _file_fact("verification_replay")
        and progress.get("measurement_failure") == {"presence": "ABSENT"}
        and progress.get("verification_failure") == {"presence": "ABSENT"}
        and progress.get("receipt") == {"presence": "ABSENT"},
        "ordinal14 verification progress/absence facts changed",
    )
    _require(
        outer_failure.get("service_launch_attempt_id") == outer_attempt_id
        and outer_failure.get("inner_launch_attempt_id") == inner_attempt_id
        and outer_failure.get("inner_launch_terminal_kind") == "FAILURE"
        and outer_failure.get("inner_launch_terminal_id") == inner_failure_id
        and outer_failure.get("inner_launch_attempt_fact")
        == _file_fact("verification_inner_attempt")
        and outer_failure.get("inner_launch_failure_fact")
        == _file_fact("verification_inner_failure")
        and outer_failure.get("inner_launch_receipt_fact")
        == {"presence": "ABSENT"}
        and outer_failure.get("systemd_run_return_code") == 1
        and outer_failure.get("systemd_run_timed_out") is False
        and outer_failure.get("success") is False
        and outer_failure.get("failure_type")
        == "V180r12r4PrelaunchLaunchError"
        and outer_failure.get("failure_message")
        == "production systemd service did not reach its exact inner receipt",
        "ordinal14 verification outer failure join changed",
    )
    unit_absence = outer_failure.get("collected_unit_absence_observation")
    _require(
        type(unit_absence) is dict
        and unit_absence.get("unit_absent_after_wait_collect") is True
        and unit_absence.get("expected_load_state") == "not-found"
        and unit_absence.get("return_code") == 0
        and unit_absence.get("timed_out") is False,
        "ordinal14 verification unit collection changed",
    )
    return (
        inner_attempt_id,
        inner_failure_id,
        outer_attempt_id,
        outer_failure_id,
        placement_t1,
    )


def _require_runner_git_contract_observation(
    observation: dict[str, Any],
    *,
    verification_t1: dict[str, Any],
) -> None:
    _require(
        observation.get("schema")
        == "acfqp.v180r12r4r9_post_failure_runner_git_contract_observation.v1"
        and observation.get("observation_kind")
        == "POST_FAILURE_READ_ONLY_TYPED_DIAGNOSTIC"
        and observation.get("campaign_attempt_id")
        == EXPECTED_CAMPAIGN_ATTEMPT_ID
        and observation.get("formal_inner_launch_failure_id")
        == EXPECTED_INNER_LAUNCH_FAILURE_ID
        and observation.get("formal_outer_service_failure_id")
        == EXPECTED_OUTER_SERVICE_FAILURE_ID
        and observation.get("verification_unit_ownership_t1_acquired") is True
        and observation.get("verification_payload_conformance") is True
        and observation.get("full_verification_launch_conformance") is False
        and observation.get("formal_mismatch_count") == 1
        and observation.get("formal_mismatch_rows")
        == [dict(row) for row in EXPECTED_FORMAL_MISMATCH_ROWS],
        "ordinal14 one formal runner mismatch changed",
    )
    cause = observation.get("cause")
    _require(
        type(cause) is dict
        and cause.get("failure_code")
        == "TARGET_AGNOSTIC_SIX_PROCESS_GIT_AUDIT_APPLIED_TO_VERIFICATION_RUNNER"
        and cause.get("error_type") == "_RunnerSecondaryObservation"
        and cause.get("message") == EXPECTED_DIAGNOSED_MESSAGE
        and cause.get("scope")
        == "POST_RUN_BOOTSTRAP_SECONDARY_OBSERVATION_AFTER_DURABLE_VERIFICATION_PUBLICATION"
        and cause.get("diagnosis_basis")
        == "EXACT_UNTRUNCATED_CHILD_STDERR_PLUS_FROZEN_MANIFEST_AND_VERIFICATION_RUNNER_CONTROL_FLOW",
        "ordinal14 exact diagnosed cause changed",
    )
    snapshots = observation.get("property_snapshots")
    _require(type(snapshots) is dict, "ordinal14 diagnostic snapshots changed")
    source_and_host = snapshots.get("source_and_host")
    measurement = snapshots.get("measurement")
    payload = snapshots.get("verification_payload")
    transport = snapshots.get("full_verification_launch_conformance")
    schedule = snapshots.get("verification_runner_git_schedule")
    ownership = snapshots.get("verification_unit_ownership_t1")
    _require(
        source_and_host
        == {
            "full_host_conformance": True,
            "full_source_conformance": True,
            "host_conformance_cause": None,
            "host_conformance_mismatch_count": 0,
            "source_conformance_cause": None,
            "source_conformance_mismatch_count": 0,
            "source_root_count": 28,
        }
        and measurement
        == {
            "campaign_comparison_vector_count": 1,
            "campaign_counter_record_count": 9,
            "campaign_native_zero_attestation_count": 1,
            "campaign_path_receipt_count": 9,
            "campaign_work_vector_count": 1,
            "measurement_inner_launch_receipt_present": True,
            "measurement_outer_service_receipt_present": True,
            "measurement_terminal_id": EXPECTED_MEASUREMENT_TERMINAL_ID,
        }
        and payload
        == {
            "campaign_counter_closure_status": "PASS",
            "counter_completeness_gate": "PASS",
            "payload_and_replay_byte_identical": True,
            "producer_modules_imported": False,
            "verification_id": EXPECTED_VERIFICATION_ID,
        }
        and transport
        == {
            "inner_launch_receipt_present": False,
            "inner_launch_terminal_kind": "FAILURE",
            "outer_service_receipt_present": False,
            "outer_service_terminal_kind": "FAILURE",
            "runner_exit_code": 1,
        },
        "ordinal14 payload/transport property separation changed",
    )
    _require(
        schedule
        == {
            "expected_process_count": 6,
            "observed_process_count": None,
            "observed_process_count_recorded": False,
            "process_subcommands": list(EXPECTED_GIT_SUBCOMMANDS),
        }
        and ownership
        == {
            "expected_source_membership": EXPECTED_VERIFICATION_SOURCE_MEMBERSHIP,
            "observed_source_membership": EXPECTED_VERIFICATION_SOURCE_MEMBERSHIP,
            "self_pid": verification_t1.get("self_pid"),
            "self_pid_in_source_cgroup_procs": True,
            "t1_complete_before_child_popen": True,
            "unit_name": EXPECTED_VERIFICATION_UNIT_NAME,
        },
        "ordinal14 T1 ownership or unrecorded runtime count changed",
    )
    inference = observation.get("static_control_flow_inference")
    rows = (
        inference.get("inferred_schedule_mismatch_rows")
        if type(inference) is dict
        else None
    )
    _require(
        type(inference) is dict
        and inference.get("runtime_observation") is False
        and inference.get("inferred_schedule_mismatch_count") == 7
        and type(rows) is list
        and len(rows) == 7
        and rows[0]
        == {
            "expected": 6,
            "field": "verification_runner_git_process_count",
            "inferred": 0,
        }
        and all(row.get("inferred") == "ABSENT" for row in rows[1:]),
        "ordinal14 static-only zero-process inference changed",
    )


def freeze_ordinal14_failure_v180r12r4r9(
    retained_root: Path | None = None,
) -> FrozenOrdinal14FailureV180r12r4r9:
    """Validate and freeze the consumed Ordinal14 verification failure."""

    root = _DEFAULT_RETAINED_ROOT if retained_root is None else Path(retained_root)
    documents, raw_by_role = _read_documents(root)
    formal_documents = {
        fact.role: documents[fact.role] for fact in _FORMAL_ARTIFACT_FACTS
    }
    _require(
        all(
            _values_for_key(document, "campaign_failure_id") == []
            and _values_for_key(document, "verification_failure_id") == []
            and _values_for_key(document, "observed_process_count") == []
            for document in formal_documents.values()
        )
        and _values_for_key(
            documents["runner_git_contract_observation"],
            "campaign_failure_id",
        )
        == []
        and _values_for_key(
            documents["runner_git_contract_observation"],
            "verification_failure_id",
        )
        == []
        and _values_for_key(
            documents["runner_git_contract_observation"],
            "observed_process_count",
        )
        == [None],
        "ordinal14 absent failure IDs or unrecorded process count changed",
    )
    external = documents["external_root"]
    materialization = documents["materialization"]
    manifest = documents["launch_manifest"]
    campaign_attempt = documents["campaign_attempt"]
    host = documents["host_conformance"]

    materialization_id = _require_self_id(
        materialization,
        "materialization_terminal_id",
        EXPECTED_MATERIALIZATION_TERMINAL_ID,
    )
    attempt_record_id = _require_self_id(
        campaign_attempt,
        "campaign_attempt_record_id",
        EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID,
        domain=_ATTEMPT_RECORD_DOMAIN,
    )
    source_conformance = _require_source_and_materialization(
        external, materialization, manifest
    )
    _require_host_conformance(host)
    (
        measurement_inner_attempt_id,
        measurement_inner_receipt_id,
        measurement_outer_attempt_id,
        measurement_outer_receipt_id,
    ) = _require_measurement_transport(
        documents, materialization_id=materialization_id
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
        == measurement_inner_attempt_id
        and campaign_attempt.get("one_shot_attempt_opened") is True,
        "ordinal14 one-shot campaign attempt join changed",
    )
    (
        terminal_id,
        _ledger,
        _execution,
        os_receipt,
        _evidence_inventory,
    ) = _require_measurement_payloads(documents)
    (
        topology,
        measurement_t1,
        measurement_t2,
        measurement_t3,
        lifecycle,
    ) = _require_os_property_snapshots(
        os_receipt, documents["measurement_inner_receipt"]
    )
    verification_id = _require_verification_payload(documents, raw_by_role)
    (
        verification_inner_attempt_id,
        verification_inner_failure_id,
        verification_outer_attempt_id,
        verification_outer_failure_id,
        verification_t1,
    ) = _require_verification_transport(
        documents, materialization_id=materialization_id
    )
    observation = documents["runner_git_contract_observation"]
    _require_runner_git_contract_observation(
        observation, verification_t1=verification_t1
    )

    property_snapshots = {
        "source_conformance": source_conformance,
        "host_conformance": host,
        "measurement_cgroup_topology": topology,
        "measurement_runtime_placement_t1": measurement_t1,
        "measurement_runtime_placement_t2": measurement_t2,
        "measurement_runtime_placement_t3": measurement_t3,
        "measurement_cgroup_lifecycle": lifecycle,
        "verification_runtime_placement_t1": verification_t1,
        "verification_payload": documents["verification"],
        "verification_transport": {
            "inner_failure": documents["verification_inner_failure"],
            "outer_failure": documents["verification_outer_failure"],
        },
        "runner_git_contract_observation": observation,
    }
    freeze_id = _freeze_id(_freeze_payload())
    _require(
        freeze_id
        == ORDINAL14_FAILURE_FREEZE_ID
        == EXPECTED_ORDINAL14_FAILURE_FREEZE_ID,
        "ordinal14 failure-freeze identity changed",
    )
    return FrozenOrdinal14FailureV180r12r4r9(
        freeze_id=freeze_id,
        campaign_attempt_id=EXPECTED_CAMPAIGN_ATTEMPT_ID,
        campaign_attempt_record_id=attempt_record_id,
        measurement_terminal_id=terminal_id,
        verification_id=verification_id,
        materialization_terminal_id=materialization_id,
        measurement_inner_launch_attempt_id=measurement_inner_attempt_id,
        measurement_inner_launch_receipt_id=measurement_inner_receipt_id,
        measurement_outer_service_attempt_id=measurement_outer_attempt_id,
        measurement_outer_service_receipt_id=measurement_outer_receipt_id,
        verification_inner_launch_attempt_id=verification_inner_attempt_id,
        verification_inner_launch_failure_id=verification_inner_failure_id,
        verification_outer_service_attempt_id=verification_outer_attempt_id,
        verification_outer_service_failure_id=verification_outer_failure_id,
        property_snapshots=property_snapshots,
        runner_git_contract_observation=observation,
    )


__all__ = (
    "EXPECTED_CAMPAIGN_ATTEMPT_ID",
    "EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID",
    "EXPECTED_INNER_LAUNCH_ATTEMPT_ID",
    "EXPECTED_INNER_LAUNCH_FAILURE_ID",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_MEASUREMENT_TERMINAL_ID",
    "EXPECTED_ORDINAL14_FAILURE_FREEZE_ID",
    "EXPECTED_OUTER_SERVICE_FAILURE_ID",
    "EXPECTED_OUTER_SERVICE_LAUNCH_ATTEMPT_ID",
    "EXPECTED_VERIFICATION_ID",
    "FrozenOrdinal14FailureV180r12r4r9",
    "ORDINAL14_CAMPAIGN_ATTEMPT_ID",
    "ORDINAL14_FAILURE_FREEZE_ID",
    "ORDINAL14_INNER_LAUNCH_FAILURE_ID",
    "ORDINAL14_MEASUREMENT_TERMINAL_ID",
    "ORDINAL14_OUTER_SERVICE_FAILURE_ID",
    "ORDINAL14_VERIFICATION_ID",
    "Ordinal14FailureFreezeV180r12r4r9Error",
    "REPAIR_SCOPE",
    "freeze_ordinal14_failure_v180r12r4r9",
)
